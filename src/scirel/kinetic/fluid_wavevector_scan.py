"""Construct a normalized fluid frequency scan and assemble per-frequency wavevector spectra."""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np

__all__ = ["scan_fluid_wavevectors"]


def scan_wavenumber(*, kz_scale, kn):
    """Scale the reference wavenumber by the caller's parallel-wavenumber ratio.

    This is a bounded affine adapter: ``kz = kz_scale * kn`` applies the source's
    ``kz=0.1*kn`` convention as a pure scaling of the normalisation wavenumber.
    """
    kz_scale = float(kz_scale)
    kn = float(kn)
    if not np.isfinite(kz_scale) or not np.isfinite(kn):
        raise ValueError("kz_scale and kn must be finite")
    if kn <= 0.0:
        raise ValueError("kn must be strictly positive")
    return {"kz": kz_scale * kn}


def scan_frequencies(*, omega_scale, omega_step, omega_stop, wn):
    """Build the source's frequency scan axis ``xx=(0.05:0.05:3.95)*wn`` internally.

    The declared formulation builds this colon ladder itself (``em3d_Lpole.m:82``) and saves it as
    terminal state; it is not an external argument to the declarationr. The written
    expression fixes both the ladder and its length (``nx=length(xx)`` at line 84), so this
    adapter takes only the three written bounds and derives the point count from the colon
    rule (every point is a multiple of the step from the start): ``count`` is
    ``floor((stop-start)/step)+1``, with an endpoint that differs from an exact
    multiple only by binary rounding retained as a ladder point.

    Element ``k`` is the correctly rounded value of the exact rational ``start + k*step``,
    and only then is the whole ladder scaled by the equilibrium-derived ``wn``. A plain
    float64 affine recurrence differs from the source's ladder by one ulp at roughly a
    quarter of the points, so the exact operands are carried symbolically to reproduce the
    source bit for bit. ``wn`` here is computed by this graph from the caller's raw case
    controls.
    """
    omega_scale = float(omega_scale)
    omega_step = float(omega_step)
    omega_stop = float(omega_stop)
    wn = float(wn)
    if not all(np.isfinite(v) for v in (omega_scale, omega_step, omega_stop, wn)):
        raise ValueError("omega_scale, omega_step, omega_stop and wn must be finite")
    if wn <= 0.0:
        raise ValueError("wn must be strictly positive")
    if omega_step <= 0.0:
        raise ValueError("omega_step must be strictly positive")
    base = Fraction(omega_scale)
    increment = Fraction(omega_step)
    stop = Fraction(omega_stop)
    if stop < base:
        raise ValueError("omega_stop must not be smaller than omega_scale")
    # The endpoint belongs to the colon ladder when (stop-start)/step is an
    # integer multiple up to binary rounding.  A plain floor drops endpoints for
    # decimal inputs such as 0.1:0.1:0.3 and 0.1:0.05:0.3.
    ratio = (omega_stop - omega_scale) / omega_step
    count = int(math.floor(ratio + 1e-12 * max(1.0, abs(ratio)))) + 1
    if count < 1:
        raise ValueError("the derived colon ladder must contain at least one point")
    ladder = np.array([float(base + k * increment) for k in range(count)], dtype=np.float64)
    return {"omegas": ladder * wn, "count": count}


def scan_fluid_wavevectors(
    ms,
    qs,
    ns_unit,
    Ts_unit,
    B0,
    n00,
    T00,
    omega_scale,
    omega_step,
    omega_stop,
    kz_scale,
    max_harmonic,
    j_order,
    keep=5,
):
    """Derive the axis and equilibrium state, then scan the fluid dispersion matrix."""
    # These are graph dependencies, not namespace dependencies.  Resolve them
    # at call time so discovering the public scan operator does not import five
    # additional numerical modules or their transitive helpers.
    from .fluid_dispersion_matrix import assemble_fluid_dispersion_matrix
    from .fluid_wavevector_eigensolve import solve_fluid_wavevector_eigenproblem
    from .gamma_lpole_coefficients import get_gamma_lpole_coefficients
    from .species_equilibrium_scales import derive_species_equilibrium_scales
    from .z_pole_coefficients import get_z_pole_coefficients

    scales = derive_species_equilibrium_scales(
        ms=ms, qs=qs, ns_unit=ns_unit, Ts_unit=Ts_unit, B0=B0, n00=n00, T00=T00
    )
    lpole = get_gamma_lpole_coefficients(max_harmonic=max_harmonic)
    poles = get_z_pole_coefficients(j_order=j_order)
    assemble = assemble_fluid_dispersion_matrix
    eigensolve = solve_fluid_wavevector_eigenproblem

    grid = scan_frequencies(
        omega_scale=omega_scale, omega_step=omega_step, omega_stop=omega_stop, wn=scales["wn"]
    )
    omegas = grid["omegas"]
    if np.any(omegas == 0.0):
        raise ValueError("the derived scan axis must not contain a zero frequency")
    kz = scan_wavenumber(kz_scale=kz_scale, kn=scales["kn"])["kz"]
    n_species = int(np.asarray(qs, dtype=float).size)
    spectra = np.empty(omegas.size, dtype=object)
    selected = np.empty(omegas.size, dtype=object)
    heads = np.empty(omegas.size, dtype=object)
    sizes = np.empty(omegas.size, dtype=object)
    for index in range(omegas.size):
        assembled = assemble(
            omega=float(omegas[index]),
            kz=kz,
            c2=scales["c2"],
            epsilon0=scales["epsilon0"],
            wps2=scales["wps2"],
            wcs=scales["wcs"],
            vts=scales["vts"],
            rhocs=scales["rhocs"],
            sgns=scales["sgns"],
            absrhocs=scales["absrhocs"],
            cn_residues=lpole["residues"],
            cn_poles=lpole["poles"],
            order_lengths=lpole["order_lengths"],
            bzj=poles["bzj"],
            czj=poles["czj"],
            max_harmonic=max_harmonic,
            n_species=n_species,
        )
        solved = eigensolve(matrix=assembled["M"], kn=scales["kn"], keep=keep)
        spectra[index] = solved["eigenvalues"]
        selected[index] = solved["selected"]
        heads[index] = solved["head"]
        sizes[index] = (assembled["matrix_size"], assembled["nonzero_entries"])
    return {
        "scales": scales,
        "kn": scales["kn"],
        "wn": scales["wn"],
        "omegas": omegas,
        "count": grid["count"],
        "kx_spectra": spectra,
        "kx_selected": selected,
        "kx_head": heads,
        "kz": kz,
        "matrix_sizes": sizes,
        "graph_order": [
            "species_equilibrium_scales",
            "scan_wavenumber",
            "scan_frequencies",
            "gamma_lpole_coefficients",
            "z_pole_coefficients",
            "fluid_dispersion_matrix",
            "fluid_wavevector_eigensolve",
        ],
    }

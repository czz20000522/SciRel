"""Build a deterministic normalized frequency grid and evaluate kinetic wavevector roots over it."""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np

__all__ = ["scan_kinetic_wavevectors"]


def scan_frequencies(*, omega_scale, omega_step, omega_stop, wn):
    """Materialise the source's colon ladder ``xx=(0.11:0.05:3.95).*wn`` internally.

    The declared formulation writes the whole ladder as a literal colon expression
    (``bonk/main_tst.m:88`` builds ``xx=(0.11:0.05:3.95).*wcn+0*wcn``), so the ladder
    length ``nx=length(xx)`` is itself a source-program fact rather than an external
    argument. This adapter therefore takes only the three written bounds and derives both
    the point count and the values: the element count follows the colon rule that every
    point is a multiple of the step from the start; ``count`` is
    ``floor((stop-start)/step)+1``, with an endpoint that differs from an exact
    multiple only by binary rounding retained as a ladder point.

    Element ``k`` is the correctly rounded value of the exact rational ``start + k*step``,
    and only then is the whole ladder scaled by ``wn``. A plain float64 affine recurrence
    differs from that ladder by one ulp at roughly a quarter of the points, and the frozen
    source's root solver is sensitive enough that a one-ulp frequency shift changes which
    zero it converges to. The exact operands are therefore carried symbolically so the
    rounding matches the source's ladder bit for bit.
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


def seed_wavenumber(*, kx_scale, kn):
    """Seed the continuation solver with the source's fixed initial guess.

    ``bonk/main_tst.m:97`` sets ``x01=(0.6+0.0i)*kn`` once before the frequency sweep, and
    the ``x01=kx1`` continuation line is commented out, so every frequency reuses this same
    seed. This adapter only applies that initial scaling; the caller does not supply ``kn``,
    it is derived here from the equilibrium controls.
    """
    kx_scale = float(kx_scale)
    kn = float(kn)
    if not np.isfinite(kx_scale) or not np.isfinite(kn):
        raise ValueError("kx_scale and kn must be finite")
    if kn <= 0.0:
        raise ValueError("kn must be strictly positive")
    return {"kx_start": complex(kx_scale * kn, 0.0)}


def scan_kinetic_wavevectors(
    ms,
    qs,
    ns_unit,
    Ts_unit,
    B0,
    n00,
    T00,
    kz,
    omega_scale,
    omega_step,
    omega_stop,
    kx_scale=0.6,
    tol_fun=1e-16,
    tol_x=1e-16,
    max_iterations=400,
    max_function_evals=100,
):
    """Return the equilibrium state, the derived scan grid and the per-frequency roots.

    ``kz`` is the declarationr's own absolute parallel wavenumber (``bonk/main_tst.m:37``
    writes ``kz=2*5.0`` and ``:50`` writes ``kz=0.0``); it is a caller-owned physical
    control in 1/m and is not reconstructed from any source-derived reference wavenumber.
    The frequency ladder bounds are the source's written colon expression, so both the
    ladder and its length are derived here.
    """
    # Resolve the scale operator first so invalid equilibrium controls keep their existing
    # validation and do not load the numerical root-solver graph unnecessarily.
    from .species_equilibrium_scales import derive_species_equilibrium_scales

    scales = derive_species_equilibrium_scales(
        ms=ms, qs=qs, ns_unit=ns_unit, Ts_unit=Ts_unit, B0=B0, n00=n00, T00=T00
    )
    kz = float(kz)
    if not np.isfinite(kz):
        raise ValueError("kz must be finite")

    # This is a graph dependency rather than a namespace dependency.  Import it only
    # once the public scan is actually called and its lightweight inputs are valid.
    from .kinetic_wavevector_roots import solve_kinetic_wavevector_roots

    grid = scan_frequencies(
        omega_scale=omega_scale, omega_step=omega_step, omega_stop=omega_stop, wn=scales["wn"]
    )
    omegas = grid["omegas"]
    kx_start = seed_wavenumber(kx_scale=kx_scale, kn=scales["kn"])["kx_start"]

    solved = solve_kinetic_wavevector_roots(
        B0=B0,
        qs=qs,
        ms=ms,
        ns0=scales["ns0"],
        Ts0=scales["Ts0"],
        omegas=omegas,
        kz=kz,
        kx_start=kx_start,
        tol_fun=tol_fun,
        tol_x=tol_x,
        max_iterations=max_iterations,
        max_function_evals=max_function_evals,
    )
    return {
        "scales": scales,
        "kz": kz,
        "count": grid["count"],
        "omegas": omegas,
        "kx_start": kx_start,
        "roots": solved["roots"],
        "residuals": solved["residuals"],
        "determinant_scale": solved["determinant_scale"],
        "exit_flags": solved["exit_flags"],
        "iterations": solved["iterations"],
        "function_evals": solved["function_evals"],
        "converged": solved["converged"],
        "solver": solved["solver"],
        "graph_order": [
            "species_equilibrium_scales",
            "scan_frequencies",
            "seed_wavenumber",
            "kinetic_wavevector_roots",
        ],
    }

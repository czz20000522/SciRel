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
    r"""Scan the fluid wavevector spectrum over equilibrium and frequency grids.

    Parameters
    ----------
    ms : real numeric
        Mass of each species, entering the thermal speed and cyclotron frequency Shape:
        (S,) one-dimensional species axis. Constraints: Finite positive masses, one
        value per species. Units: [kg].
    qs : real numeric
        Charge of each species, setting the sign of the cyclotron frequency and coupling
        terms Shape: (S,) one-dimensional species axis. Constraints: Finite nonzero
        charges, one value per species. Units: [C].
    ns_unit : real numeric
        Density of each species relative to the reference density Shape: (S,)
        one-dimensional species axis. Constraints: Finite positive density ratios
        matching the species axis. Units: [dimensionless].
    Ts_unit : real numeric
        Temperature of each species relative to the reference temperature Shape: (S,)
        one-dimensional species axis. Constraints: Finite positive temperature ratios
        matching the species axis. Units: [dimensionless].
    B0 : real numeric
        Background magnetic-field strength, setting the cyclotron-frequency scale Shape:
        scalar. Constraints: Finite nonzero background field. Units: [T].
    n00 : real numeric
        Reference number density Shape: scalar. Constraints: Finite positive reference
        density. Units: [m^-3].
    T00 : real numeric
        Reference temperature Shape: scalar. Constraints: Finite positive reference
        temperature in eV. Units: [eV].
    omega_scale : real numeric
        Start fraction of the scan frequency ladder (0.05 in the source implementation);
        multiplied by the wn derived internally by this graph to give the absolute start
        frequency Shape: scalar. Constraints: Finite scan start; every derived angular
        frequency must be nonzero. Units: [dimensionless].
    omega_step : real numeric
        Equal-step fraction of the scan frequency ladder (0.05 in the source
        implementation); multiplied by the wn derived internally by this graph to give
        the absolute step Shape: scalar. Constraints: Finite strictly positive scan
        step. Units: [dimensionless].
    omega_stop : real numeric
        Stop multiple of the scan frequency ladder (3.95 in the source implementation);
        together with the start and step it defines the source's colon expression, from
        which the number of scan frequencies follows Shape: scalar. Constraints: Finite
        scan endpoint not below the start. Units: [dimensionless].
    kz_scale : real numeric
        Parallel wavenumber relative to kn, giving the kz used by the scan Shape:
        scalar. Constraints: Finite parallel-wavenumber ratio. Units: [dimensionless].
    max_harmonic : integer
        Maximum Bessel harmonic order N, setting the number of matrix blocks Shape:
        integer scalar. Constraints: Integer from 0 through 7, limited by the frozen
        L-pole tables. Units: [dimensionless].
    j_order : integer
        Z-pole order J, selecting the pole table and setting each species' pole-block
        size Shape: integer scalar. Constraints: Integer 8 or 12, selecting a frozen
        Z-pole table. Units: [dimensionless].
    keep : integer, optional
        Number of leading branches returned per frequency Shape: integer scalar.
        Constraints: Positive integer branch count. Default: 5. Units: [dimensionless].

    Returns
    -------
    scales : mapping
        Per-species scales derived from the equilibrium inputs and consumed by both
        assembly and the eigensolve Shape: mapping/dict. Constraints: The returned value
        follows the stated shape and physical normalization. Units: [mixed (each key
        carries its own unit)].
    kn : real numeric
        Wavenumber normalization scale derived internally by this graph,
        kn=1/max|rho_cs|, returned as a top-level physical quantity Shape: scalar.
        Constraints: The returned value follows the stated shape and physical
        normalization. Units: [1/m].
    wn : real numeric
        Frequency normalization scale derived internally by this graph, wn=min|w_cs|,
        returned as a top-level physical quantity Shape: scalar. Constraints: The
        returned value follows the stated shape and physical normalization. Units:
        [rad/s].
    omegas : real numeric
        Scan angular-frequency axis derived internally by this graph,
        xx=(omega_scale:omega_step:omega_stop)*wn, which is the xx vector stored by the
        source implementation Shape: (F,) one-dimensional frequency axis. Constraints:
        The returned value follows the stated shape and physical normalization. Units:
        [rad/s].
    count : integer
        Number of frequencies derived from the source's colon-style
        (omega_scale:omega_step:omega_stop) ladder Shape: integer scalar. Constraints:
        The returned value follows the stated shape and physical normalization. Units:
        [dimensionless].
    kx_spectra : object array
        Complete kx spectrum at each frequency Shape: (F,) object array of full complex
        spectra. Constraints: The returned value follows the stated shape and physical
        normalization. Units: [1/m].
    kx_selected : object array
        Branches at each frequency that pass the real-part threshold, sorted in
        ascending |Im| order Shape: (F,) object array of variable-length complex
        branches. Constraints: The returned value follows the stated shape and physical
        normalization. Units: [1/m].
    kx_head : object array
        First keep branches at each frequency, forming the scan curves Shape: (F,)
        object array of variable-length complex branches. Constraints: The returned
        value follows the stated shape and physical normalization. Units: [1/m].
    kz : real numeric
        Parallel wavenumber actually used by this scan Shape: scalar. Constraints: The
        returned value follows the stated shape and physical normalization. Units:
        [1/m].
    matrix_sizes : object array
        Matrix order and number of nonzero entries at each frequency Shape: (F,) object
        array of (matrix order, nonzero count) tuples. Constraints: The returned value
        follows the stated shape and physical normalization. Units: [dimensionless].
    graph_order : string sequence
        Execution order of this graph Shape: (7,) string array. Constraints: The
        returned value follows the stated shape and physical normalization. Units: [not
        applicable].

    Raises
    ------
    LinAlgError
        If the numerical eigensolver cannot produce a spectrum.
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    derive_species_equilibrium_scales
        Related kinetic amplitude or dispersion operator in the same workflow.
    get_gamma_lpole_coefficients
        Related kinetic amplitude or dispersion operator in the same workflow.
    get_z_pole_coefficients
        Related kinetic amplitude or dispersion operator in the same workflow.
    assemble_fluid_dispersion_matrix
        Related kinetic amplitude or dispersion operator in the same workflow.
    solve_fluid_wavevector_eigenproblem
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        The graph derives species scales, constructs the frequency and
        parallel-wavenumber axes, assembles one matrix per frequency, and solves each
        matrix directly. Completed point data are not exposed when any point fails.
        Supported scope: Derive the equilibrium frequency ladder, assemble one L/J-pole
        matrix per frequency, and select fluid kx branches. Excluded scope: No
        unrequested mode identity or accuracy guarantee is inferred.

    Examples
    --------
    >>> from scirel.kinetic import scan_fluid_wavevectors
    >>> r=scan_fluid_wavevectors(ms=[9.1094e-31],qs=[-1.60217662e-19],ns_unit=[1],Ts_unit=[1],B0=1,n00=6.075e19,T00=1000,omega_scale=0.5,omega_step=0.05,omega_stop=0.5,kz_scale=0.1,max_harmonic=0,j_order=8); assert r['count']==1
    """
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

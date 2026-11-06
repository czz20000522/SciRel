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
    r"""Derive the frequency ladder and fixed seed, then solve a signed complex Ronnmark kx root at every frequency.

    Parameters
    ----------
    ms : real numeric
        Species masses, entering the thermal speed and the cyclotron frequency [kg] Shape: (S,) one-
        dimensional species axis. Finite positive masses, one value per species.
    qs : real numeric
        Species charges, setting the sign of the cyclotron frequency [C] Shape: (S,) one-dimensional species
        axis. Finite nonzero charges, one value per species.
    ns_unit : real numeric
        Species densities as multiples of the reference density [dimensionless] Shape: (S,) one-dimensional
        species axis. Finite positive density ratios matching the species axis.
    Ts_unit : real numeric
        Species temperatures as multiples of the reference temperature [dimensionless] Shape: (S,) one-
        dimensional species axis. Finite positive temperature ratios matching the species axis.
    B0 : real numeric
        Background magnetic-field strength, calibrating the cyclotron-frequency scale [T] Shape: scalar.
        Finite nonzero background field.
    n00 : real numeric
        Reference number density [m^-3] Shape: scalar. Finite positive reference density.
    T00 : real numeric
        Reference temperature [eV] Shape: scalar. Finite positive reference temperature in eV.
    kz : real numeric
        Absolute parallel wavenumber, the kz fixed by the source driver (2*5.0 for case 1 and 0.0 for case
        2), entering the parallel resonance argument; the caller supplies this physical control directly,
        with no conversion from any reference wavenumber [1/m] Shape: scalar. Finite absolute parallel
        wavenumber; zero is supported by the kinetic paths.
    omega_scale : real numeric
        Start multiple of the scanned frequency ladder; multiplied by wn it gives the first angular
        frequency [dimensionless] Shape: scalar. Finite scan start; every derived angular frequency must be
        nonzero.
    omega_step : real numeric
        Step multiple of the scanned frequency ladder; multiplied by wn it gives the spacing between
        adjacent frequency points; both source scans use 0.05 [dimensionless] Shape: scalar. Finite strictly
        positive scan step.
    omega_stop : real numeric
        End multiple of the scanned frequency ladder (3.95 in the source); together with the start and step
        it fixes the source's colon expression, from which the number of ladder points follows
        [dimensionless] Shape: scalar. Finite scan endpoint not below the start.
    kx_scale : real numeric
        Complex initial value shared by all frequency points as a fraction of kn; the source fixes it at 0.6
        and performs no continuation between frequency points [dimensionless] Shape: scalar. Default: 0.6.
        Finite fixed-seed ratio.
    tol_fun : real numeric
        Relative residual convergence tolerance corresponding to the reference runtime `TolFun`
        [dimensionless] Shape: scalar. Default: 1e-16. Finite strictly positive residual tolerance.
    tol_x : real numeric
        Relative variable-step convergence tolerance corresponding to the reference runtime `Tolx`
        [dimensionless] Shape: scalar. Default: 1e-16. Finite strictly positive step tolerance.
    max_iterations : integer
        Maximum iterations per frequency point, corresponding to the reference runtime `MaxIter`
        [dimensionless] Shape: scalar integer. Default: 400. Positive integer iteration bound.
    max_function_evals : integer
        Maximum objective-function evaluations per frequency point, corresponding to the reference runtime
        `MaxFunEvals` [dimensionless] Shape: scalar integer. Default: 100. Positive integer function-
        evaluation bound.

    Returns
    -------
    scales : mapping
        Per-species scales derived from the equilibrium inputs, shared by the wavenumber calibration and
        root finding [mixed (each key carries its own units)] Shape: mapping dict. The returned value
        follows the stated shape and physical normalization.
    kz : real numeric
        Parallel wavenumber actually used in this scan, taken directly from the caller's absolute control
        value [1/m] Shape: scalar. The returned value follows the stated shape and physical normalization.
    count : integer
        Number of frequency points derived from the source colon ladder (omega_scale:omega_step:omega_stop)
        [dimensionless] Shape: scalar integer. The returned value follows the stated shape and physical
        normalization.
    omegas : real numeric
        Angular-frequency sequence actually used in this scan [rad/s] Shape: (F,) one-dimensional frequency
        axis. The returned value follows the stated shape and physical normalization.
    kx_start : complex128 array
        Starting complex initial value for continuation root finding [1/m] Shape: scalar complex. The
        returned value follows the stated shape and physical normalization.
    roots : complex128 array
        Complex perpendicular-wavenumber root obtained at each frequency point [1/m] Shape: (F,) one-
        dimensional frequency-axis complex array. The returned value follows the stated shape and physical
        normalization.
    residuals : complex128 array
        Dispersion-determinant residual at each root [dimensionless] Shape: (F,) one-dimensional frequency-
        axis complex array. The returned value follows the stated shape and physical normalization.
    determinant_scale : real numeric
        Maximum modulus of the dielectric-tensor elements at each root, used as the cancellation scale for
        the residual [dimensionless] Shape: (F,) one-dimensional frequency-axis floating-point array. The
        returned value follows the stated shape and physical normalization.
    exit_flags : integer
        The reference runtime fsolve exit flag at each frequency point, restricted to {1,2,3,0,-2,-3} [not
        applicable] Shape: (F,) one-dimensional frequency-axis integer array. The returned value follows the
        stated shape and physical normalization.
    iterations : integer
        Iteration count actually used at each frequency point [dimensionless] Shape: (F,) one-dimensional
        frequency-axis integer array. The returned value follows the stated shape and physical
        normalization.
    function_evals : integer
        Objective-evaluation count actually used at each frequency point [dimensionless] Shape: (F,) one-
        dimensional frequency-axis integer array. The returned value follows the stated shape and physical
        normalization.
    converged : bool
        Whether the exit flag is positive at each frequency point, that is, whether the reference runtime
        judged convergence [not applicable] Shape: (F,) one-dimensional frequency-axis boolean array. The
        returned value follows the stated shape and physical normalization.
    solver : string sequence
        Root-finding algorithm label [not applicable] Shape: scalar string. The returned value follows the
        stated shape and physical normalization.
    graph_order : string sequence
        Fixed execution-order label for this graph [not applicable] Shape: (4,) string sequence. The
        returned value follows the stated shape and physical normalization.

    Raises
    ------
    ValueError
        Raises ValueError from `scan_frequencies`/`seed_wavenumber` for nonfinite bounds, nonpositive
        `wn`/`kn`/`omega_step`, `omega_stop < omega_scale`, an empty ladder, or nonfinite `kz`; invalid
        equilibrium controls fail in `derive_species_equilibrium_scales` before the root graph is
        imported.

    See Also
    --------
    scirel.kinetic.species_equilibrium_scales.derive_species_equilibrium_scales : Related contract dependency.
    scirel.kinetic.kinetic_wavevector_roots.solve_kinetic_wavevector_roots : Related contract dependency.

    Notes
    -----
    The graph derives its ordered frequency ladder from wn and a single kx_start=kx_scale*kn; the
    bounded root solver repeats that seed independently at every frequency. homogeneous magnetized
    Maxwellian multi-species plasma Assumptions: All species controls describe one shared equilibrium
    snapshot.

    Examples
    --------
    >>> from scirel.kinetic import scan_kinetic_wavevectors
    >>> r=scan_kinetic_wavevectors(ms=[9.1094e-31],qs=[-1.60217662e-19],ns_unit=[1],Ts_unit=[1],B0=1,n00=6.075e19,T00=1000,kz=0,omega_scale=0.11,omega_step=0.05,omega_stop=0.11); assert r['count']==1
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

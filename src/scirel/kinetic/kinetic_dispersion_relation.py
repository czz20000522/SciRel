"""Small composition operators for normalized kinetic dispersion probes. Each helper validates its scalar contract before assembling a shared equilibrium query."""

from __future__ import annotations

import numpy as np

__all__ = ["evaluate_kinetic_dispersion_relation"]


def probe_frequency(*, omega_frac, wn):
    """Scale the caller's angular-frequency fraction by the graph's own normalisation.

    This is a bounded scalar affine adapter. The declarationr writes its frequency probe
    as a fraction of its own normalisation frequency (``w=wf(p)*wcn``), so the caller gives
    the dimensionless fraction and the graph supplies the ``wn`` it derived from the same
    equilibrium controls. No source-captured absolute frequency enters the call.
    """
    omega_frac = float(omega_frac)
    wn = float(wn)
    if not np.isfinite(omega_frac) or not np.isfinite(wn):
        raise ValueError("omega_frac and wn must be finite")
    if wn <= 0.0:
        raise ValueError("wn must be strictly positive")
    return {"omega": omega_frac * wn}


def probe_wavenumber(*, kx_frac, kn):
    """Scale the caller's perpendicular-wavenumber fraction by the graph's own normalisation.

    The source writes ``kx=kxf(p)*kn``; the graph supplies the ``kn`` it derived from the
    same equilibrium controls, so the physical probe value is computed here rather than
    injected from any captured source result.
    """
    kx_frac = float(kx_frac)
    kn = float(kn)
    if not np.isfinite(kx_frac) or not np.isfinite(kn):
        raise ValueError("kx_frac and kn must be finite")
    if kn <= 0.0:
        raise ValueError("kn must be strictly positive")
    return {"kx": kx_frac * kn}


def omega_to_frequency(*, omega):
    """Convert an angular frequency to a frequency.

    This is a bounded unit adapter: ``f = omega / (2*pi)`` is the SI definition of the
    angular-frequency convention, not a scientific mapping.
    """
    omega = float(omega)
    if not np.isfinite(omega):
        raise ValueError("omega must be finite")
    return {"f": omega / (2.0 * np.pi)}


def evaluate_kinetic_dispersion_relation(
    ms,
    qs,
    ns_unit,
    Ts_unit,
    B0,
    n00,
    T00,
    omega_frac,
    kz,
    kx_frac,
    lmx=5,
):
    r"""Evaluate conventional finite-harmonic and Ronnmark determinants at the same derived equilibrium wavepoint.

    Parameters
    ----------
    ms : real numeric
        Mass of each species, entering the thermal speed and cyclotron frequency [kg] Shape: (S,) one-
        dimensional species axis. Finite positive masses, one value per species.
    qs : real numeric
        Charge of each species, setting the sign of the cyclotron frequency and coupling terms [C] Shape:
        (S,) one-dimensional species axis. Finite nonzero charges, one value per species.
    ns_unit : real numeric
        Density of each species relative to the reference density [dimensionless] Shape: (S,) one-
        dimensional species axis. Finite positive density ratios matching the species axis.
    Ts_unit : real numeric
        Temperature of each species relative to the reference temperature [dimensionless] Shape: (S,) one-
        dimensional species axis. Finite positive temperature ratios matching the species axis.
    B0 : real numeric
        Background magnetic-field strength, setting the cyclotron frequency and entering the pole-resonance
        argument [T] Shape: scalar. Finite nonzero background field.
    n00 : real numeric
        Reference number density, converting relative to absolute density [m^-3] Shape: scalar. Finite
        positive reference density.
    T00 : real numeric
        Reference temperature, converting relative to absolute temperature [eV] Shape: scalar. Finite
        positive reference temperature in eV.
    omega_frac : real numeric
        Angular frequency as a multiple of the wn derived internally by this graph (the source
        implementation writes w=wf(p)*wcn); the caller supplies a dimensionless ratio and this graph derives
        the absolute angular frequency [dimensionless] Shape: scalar. Finite ratio producing nonzero angular
        frequency.
    kz : real numeric
        Wavevector component parallel to the magnetic field, entering the parallel-resonance argument [1/m]
        Shape: scalar. Finite absolute parallel wavenumber; zero is supported by the kinetic paths.
    kx_frac : real numeric
        Perpendicular wavenumber as a multiple of the kn derived internally by this graph (the source
        implementation writes kx=kxf(p)*kn); the caller supplies a dimensionless ratio and this graph
        derives the absolute perpendicular wavenumber [dimensionless] Shape: scalar. Finite perpendicular-
        wavenumber ratio.
    lmx : integer
        Bessel truncation order for the conventional harmonic sum [dimensionless] Shape: integer scalar.
        Default: 5. Non-negative integer harmonic truncation.

    Returns
    -------
    scales : mapping
        Per-species scales derived from the equilibrium inputs, shared by both dispersion paths from the
        same state snapshot [mixed (each key carries its own unit)] Shape: mapping/dict. The returned value
        follows the stated shape and physical normalization.
    determinant_sum_n : complex128 array
        Dispersion determinant of the conventional truncated-harmonic-sum path [dimensionless] Shape:
        complex scalar. The returned value follows the stated shape and physical normalization.
    determinant_ronnmark : complex128 array
        Dispersion determinant of the Ronnmark fast path [dimensionless] Shape: complex scalar. The returned
        value follows the stated shape and physical normalization.
    K_sum_n : complex128 array
        Dielectric tensor of the conventional sum path [dimensionless] Shape: (3, 3) complex matrix. The
        returned value follows the stated shape and physical normalization.
    D_sum_n : complex128 array
        Dispersion tensor of the conventional sum path [dimensionless] Shape: (3, 3) complex matrix. The
        returned value follows the stated shape and physical normalization.
    K_ronnmark : complex128 array
        Dielectric tensor of the Ronnmark path [dimensionless] Shape: (3, 3) complex matrix. The returned
        value follows the stated shape and physical normalization.
    D_ronnmark : complex128 array
        Dispersion tensor of the Ronnmark path [dimensionless] Shape: (3, 3) complex matrix. The returned
        value follows the stated shape and physical normalization.
    branches : string sequence
        Method-branch label selected for each (species, pole) combination on the Ronnmark path [not
        applicable] Shape: (S*J,) string sequence. The returned value follows the stated shape and physical
        normalization.
    omega : real numeric
        Absolute angular frequency derived by this graph from omega_frac and the internal wn [rad/s] Shape:
        scalar. The returned value follows the stated shape and physical normalization.
    kx : real numeric
        Absolute perpendicular wavenumber derived by this graph from kx_frac and the internal kn [1/m]
        Shape: scalar. The returned value follows the stated shape and physical normalization.
    f : real numeric
        Frequency converted from the absolute angular frequency [Hz] Shape: scalar. The returned value
        follows the stated shape and physical normalization.
    graph_order : string sequence
        Fixed execution-order labels of this graph [not applicable] Shape: (6,) string sequence. The
        returned value follows the stated shape and physical normalization.

    Raises
    ------
    ValueError
        Raises ValueError from `derive_species_equilibrium_scales`, `probe_frequency`/`probe_wavenumber`
        (nonfinite fractions, nonpositive `wn`/`kn`) or nonfinite `kz`; argument or `lmx` errors from
        the kinetic sum propagate.

    See Also
    --------
    scirel.kinetic.species_equilibrium_scales.derive_species_equilibrium_scales : Related contract dependency.
    scirel.kinetic.kinetic_dispersion_sum_fluid.evaluate_fluid_kinetic_dispersion_sum : Related contract dependency.
    scirel.kinetic.kinetic_dispersion_ronnmark.evaluate_kinetic_dispersion_ronnmark : Related contract dependency.

    Notes
    -----
    The graph derives omega=omega_frac*wn, kx=kx_frac*kn and f=omega/(2*pi), then evaluates the Weideman
    sum and Ronnmark paths with shared SI species state. homogeneous magnetized Maxwellian multi-species
    plasma Assumptions: All species controls describe one shared equilibrium snapshot.

    Examples
    --------
    >>> from scirel.kinetic import evaluate_kinetic_dispersion_relation
    >>> r=evaluate_kinetic_dispersion_relation(ms=[9.1094e-31],qs=[-1.60217662e-19],ns_unit=[1],Ts_unit=[1],B0=1,n00=6.075e19,T00=1000,omega_frac=1,kz=1326.1942478795652,kx_frac=1); assert 'determinant_sum_n' in r and 'determinant_ronnmark' in r
    """
    # Resolve the scale operator first so its established input validation runs before
    # loading the two determinant implementations and their numerical helpers.
    from .species_equilibrium_scales import derive_species_equilibrium_scales

    scales = derive_species_equilibrium_scales(
        ms=ms, qs=qs, ns_unit=ns_unit, Ts_unit=Ts_unit, B0=B0, n00=n00, T00=T00
    )
    kz = float(kz)
    if not np.isfinite(kz):
        raise ValueError("kz must be finite")

    # These are graph dependencies, not namespace dependencies.  Load them only at the
    # public call boundary after the shared equilibrium and scalar checks have succeeded.
    from .kinetic_dispersion_ronnmark import evaluate_kinetic_dispersion_ronnmark
    from .kinetic_dispersion_sum_fluid import evaluate_fluid_kinetic_dispersion_sum

    omega = probe_frequency(omega_frac=omega_frac, wn=scales["wn"])["omega"]
    kx = probe_wavenumber(kx_frac=kx_frac, kn=scales["kn"])["kx"]
    f = omega_to_frequency(omega=omega)["f"]
    shared = dict(B0=B0, qs=qs, ms=ms, ns0=scales["ns0"], Ts0=scales["Ts0"], f=f, kz=kz, kx=kx)
    summed = evaluate_fluid_kinetic_dispersion_sum(**shared, lmx=lmx)
    ronnmark = evaluate_kinetic_dispersion_ronnmark(**shared)
    return {
        "scales": scales,
        "omega": omega,
        "kx": kx,
        "f": f,
        "determinant_sum_n": summed["determinant"],
        "determinant_ronnmark": ronnmark["determinant"],
        "K_sum_n": summed["K"],
        "D_sum_n": summed["D"],
        "K_ronnmark": ronnmark["K"],
        "D_ronnmark": ronnmark["D"],
        "branches": ronnmark["branches"],
        "graph_order": [
            "species_equilibrium_scales",
            "probe_frequency",
            "probe_wavenumber",
            "omega_to_frequency",
            "kinetic_dispersion_sum_n",
            "kinetic_dispersion_ronnmark",
        ],
    }

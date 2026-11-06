"""Derive validated SI equilibrium scales for a species mixture in one vectorized assembly."""

from __future__ import annotations

import numpy as np


_C2 = (2.99792458e8) ** 2
_EPSILON0 = 8.854187817e-12
_KB = 1.38064852e-23
_EV_TO_K = 1.6022e-19


def _species_vector(value, name):
    try:
        raw = np.asarray(value, dtype=object)
        typed = np.asarray(value)
        if (
            raw.ndim != 1
            or raw.size == 0
            or any(isinstance(item, (bool, np.bool_)) for item in raw.flat)
            or typed.dtype.kind not in "iuf"
        ):
            raise ValueError(f"{name} must be a non-empty real species vector")
        values = np.asarray(value, dtype=float)
    except (TypeError, OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be a non-empty real species vector") from error
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{name} must contain finite values")
    return values


def _scalar(value, name, *, positive=False, nonzero=False):
    raw = np.asarray(value)
    if raw.ndim != 0 or raw.dtype.kind not in "iuf":
        raise ValueError(f"{name} must be a finite real scalar")
    try:
        result = float(value)
    except (TypeError, OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be a finite real scalar") from error
    if not np.isfinite(result) or (positive and result <= 0.0) or (nonzero and result == 0.0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'non-zero'}")
    return result


def derive_species_equilibrium_scales(*, ms, qs, ns_unit, Ts_unit, B0, n00, T00):
    r"""Derive SI thermal, cyclotron, plasma-frequency, gyroradius and Debye scales for a nonempty species mixture from reference density and temperature.

    Parameters
    ----------
    ms : real numeric
        Species masses on the shared species axis. [kg] Shape: (S,), S >= 1. Finite and strictly positive;
        boolean values are rejected.
    qs : real numeric
        Signed species charges on the shared species axis. [C] Shape: (S,), same S as ms. Finite and
        nonzero; boolean values are rejected.
    ns_unit : real numeric
        Species density factor relative to n00. [dimensionless] Shape: (S,), same S as ms. Finite and
        strictly positive; boolean values are rejected.
    Ts_unit : real numeric
        Species temperature factor relative to T00. [dimensionless] Shape: (S,), same S as ms. Finite and
        strictly positive; boolean values are rejected.
    B0 : real numeric
        Signed background magnetic field. [T] Shape: scalar. Finite and nonzero; boolean values are
        rejected.
    n00 : real numeric
        Reference number density. [m^-3] Shape: scalar. Finite and strictly positive; boolean values are
        rejected.
    T00 : real numeric
        Reference temperature before conversion to kelvin. [eV] Shape: scalar. Finite and strictly positive;
        boolean values are rejected.

    Returns
    -------
    c2 : float
        Fixed vacuum light-speed squared. [m^2/s^2] Shape: scalar. Equals (2.99792458e8)^2.
    epsilon0 : float
        Fixed vacuum permittivity. [F/m] Shape: scalar. Equals 8.854187817e-12.
    kB : float
        Fixed Boltzmann constant. [J/K] Shape: scalar. Equals 1.38064852e-23.
    c : float
        Vacuum light speed from sqrt(c2). [m/s] Shape: scalar. Finite and positive.
    ns0 : float64
        Absolute species number density. [m^-3] Shape: (S,). Finite and strictly positive.
    Ts0 : float64
        Species temperature after eV-to-kelvin conversion. [K] Shape: (S,). Finite and strictly positive.
    vts : float64
        Species thermal speed with sqrt(2) factor. [m/s] Shape: (S,). Finite and strictly positive.
    wcs : float64
        Signed species cyclotron angular frequency. [rad/s] Shape: (S,). Finite and nonzero.
    wps2 : float64
        Species plasma angular-frequency squared. [rad^2/s^2] Shape: (S,). Finite and strictly positive.
    wp2 : float
        Sum of species plasma angular-frequency squared. [rad^2/s^2] Shape: scalar. Finite and strictly
        positive.
    rhocs : float64
        Signed species gyroradius using sqrt(kB*T/m)/wcs. [m] Shape: (S,). Finite and nonzero.
    absrhocs : float64
        Absolute species gyroradius. [m] Shape: (S,). Finite and strictly positive.
    sgns : float64
        Sign of signed species gyroradius. [dimensionless] Shape: (S,). Each value is -1 or +1.
    lambdaDs : float64
        Species Debye length. [m] Shape: (S,). Finite and strictly positive.
    kDs : float64
        Inverse species Debye length. [m^-1] Shape: (S,). Finite and strictly positive.
    wcn : float
        Minimum absolute species cyclotron angular frequency. [rad/s] Shape: scalar. Finite and strictly
        positive.
    rhocn : float
        Maximum absolute species gyroradius. [m] Shape: scalar. Finite and strictly positive.
    kn : float
        Inverse rhocn scan scale. [m^-1] Shape: scalar. Finite and strictly positive.
    wn : float
        Cyclotron-frequency scan scale equal to wcn. [rad/s] Shape: scalar. Finite and strictly positive.

    Raises
    ------
    ValueError
        Raises ValueError for empty, non-one-dimensional, mismatched, nonnumeric, boolean, nonfinite or
        nonpositive vectors where positivity is required; zero charge or field and nonpositive n00/T00
        also fail. Raises ValueError if a derived scale is nonfinite, unrepresentable or collapses to
        zero; other unexpected NumPy errors propagate.

    See Also
    --------
    scirel.kinetic : Public kinetic-domain operators.

    Notes
    -----
    n_s=ns_unit_s*n00; T_s[K]=Ts_unit_s*T00[eV]*1.6022e-19/kB; vts=sqrt(2*kB*T_s/m_s); wcs=q_s*B0/m_s;
    wps2=n_s*q_s^2/(m_s*epsilon0); rhocs=sqrt(kB*T_s/m_s)/wcs;
    lambdaDs=sqrt(epsilon0*kB*T_s/(n_s*q_s^2)); wcn=min(abs(wcs)); rhocn=max(abs(rhocs)); kn=1/rhocn;
    wn=wcn. Fixed constants are c2=(2.99792458e8)^2, epsilon0=8.854187817e-12 and kB=1.38064852e-23.
    Magnetized Maxwellian species equilibrium using the declared thermal-speed and signed-gyroradius
    conventions Assumptions: The caller supplies species values in SI units and reference temperature in
    eV. Thermal speed contains sqrt(2), while the signed gyroradius uses sqrt(kB*T/m) without that
    factor.

    Examples
    --------
    >>> from scirel.kinetic import derive_species_equilibrium_scales
    >>> r = derive_species_equilibrium_scales(ms=[9.1094e-31], qs=[-1.60217662e-19], ns_unit=[1.0], Ts_unit=[1.0], B0=1.0, n00=6.075e19, T00=1000.0)
    >>> assert r['wcs'][0] < 0 and r['rhocs'][0] < 0
    >>> assert r['wn'] == r['wcn'] and r['kn'] == 1.0 / r['rhocn']
    """
    ms = _species_vector(ms, "ms")
    qs = _species_vector(qs, "qs")
    ns_unit = _species_vector(ns_unit, "ns_unit")
    Ts_unit = _species_vector(Ts_unit, "Ts_unit")
    if qs.shape != ms.shape or ns_unit.shape != ms.shape or Ts_unit.shape != ms.shape:
        raise ValueError("species vectors must share the same shape")
    if np.any(ms <= 0.0) or np.any(ns_unit <= 0.0) or np.any(Ts_unit <= 0.0):
        raise ValueError("mass, density ratio and temperature ratio must be positive")
    if np.any(qs == 0.0):
        raise ValueError("each species charge must be non-zero")
    B0 = _scalar(B0, "B0", nonzero=True)
    n00 = _scalar(n00, "n00", positive=True)
    T00 = _scalar(T00, "T00", positive=True)

    # Preserve the declared fluid operation order for the bounded reference oracles.
    with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
        ns0 = ns_unit * n00
        Ts0 = Ts_unit * T00 * _EV_TO_K / _KB
        vts = np.sqrt(2.0 * _KB * Ts0 / ms)
        wcs = qs * B0 / ms
        wps2 = ns0 * qs**2 / ms / _EPSILON0
        rhocs = np.sqrt(_KB * Ts0 / ms) / wcs
        absrhocs = np.abs(rhocs)
        sgns = np.sign(rhocs)
        lambdaDs = np.sqrt(_EPSILON0 * _KB * Ts0 / (ns0 * qs**2))
        wcn = float(np.min(np.abs(wcs)))
        rhocn = float(np.max(np.abs(rhocs)))
        result = {
            "c2": _C2,
            "epsilon0": _EPSILON0,
            "kB": _KB,
            "c": float(np.sqrt(_C2)),
            "ns0": ns0,
            "Ts0": Ts0,
            "vts": vts,
            "wcs": wcs,
            "wps2": wps2,
            "wp2": float(np.sum(wps2)),
            "rhocs": rhocs,
            "absrhocs": absrhocs,
            "sgns": sgns,
            "lambdaDs": lambdaDs,
            "kDs": 1.0 / lambdaDs,
            "wcn": wcn,
            "rhocn": rhocn,
            "kn": 1.0 / rhocn,
            "wn": wcn,
        }
    if any(not np.all(np.isfinite(value)) for value in result.values()):
        raise ValueError("derived species scale is not representable")
    if (
        any(
            np.any(np.asarray(result[name]) <= 0.0)
            for name in (
                "ns0",
                "Ts0",
                "vts",
                "wps2",
                "wp2",
                "absrhocs",
                "lambdaDs",
                "kDs",
                "wcn",
                "rhocn",
                "kn",
                "wn",
            )
        )
        or np.any(wcs == 0.0)
        or np.any(rhocs == 0.0)
    ):
        raise ValueError("derived species scale collapsed to zero")
    return result


__all__ = ["derive_species_equilibrium_scales"]

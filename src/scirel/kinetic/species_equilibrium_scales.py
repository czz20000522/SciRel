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
        if raw.ndim != 1 or raw.size == 0 or any(
            isinstance(item, (bool, np.bool_)) for item in raw.flat
        ) or typed.dtype.kind not in "iuf":
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
    """Derive per-species thermal, cyclotron, plasma and Debye SI scales.

    ``ms`` [kg], ``qs`` [C], ``ns_unit`` and ``Ts_unit`` [-] share a species axis.
    ``B0`` [T] is signed; ``n00`` [m^-3] and ``T00`` [eV] are positive reference
    values. The thermal speed uses sqrt(2 kB T/m), while the signed gyroradius
    uses sqrt(kB T/m)/omega_c, as in the fluidBW source convention.
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

    # Preserve the frozen fluidBW operation order for its bounded source oracles.
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
    if any(
        np.any(np.asarray(result[name]) <= 0.0)
        for name in ("ns0", "Ts0", "vts", "wps2", "wp2", "absrhocs", "lambdaDs", "kDs", "wcn", "rhocn", "kn", "wn")
    ) or np.any(wcs == 0.0) or np.any(rhocs == 0.0):
        raise ValueError("derived species scale collapsed to zero")
    return result


__all__ = ["derive_species_equilibrium_scales"]

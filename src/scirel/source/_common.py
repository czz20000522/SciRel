"""Shared grid validation and stable discrete profile normalization."""
from __future__ import annotations
import numpy as np


def grid(rho_norm, vpr, drho_norm):
    values = []
    for value, name in zip(
        (rho_norm, vpr, drho_norm), ("rho_norm", "vpr", "drho_norm")
    ):
        a = np.asarray(value)
        if np.ma.isMaskedArray(value) or a.ndim != 1 or a.size == 0 or a.dtype.kind not in "iuf":
            raise ValueError(f"{name} must be a nonempty one-dimensional real array")
        a = np.asarray(a, dtype=np.float64)
        if not np.all(np.isfinite(a)):
            raise ValueError(f"{name} must be finite")
        values.append(a)
    rho, vpr_a, drho = values
    if rho.size != vpr_a.size or rho.size != drho.size:
        raise ValueError("rho_norm, vpr and drho_norm must have equal length")
    if np.any(np.diff(rho) <= 0) or np.any(rho < 0) or np.any(rho > 1):
        raise ValueError("rho_norm must be strictly increasing in [0, 1]")
    if np.any(vpr_a <= 0) or np.any(drho <= 0):
        raise ValueError("vpr and drho_norm must be strictly positive")
    return rho, vpr_a, drho


def scalar(value, name):
    a = np.asarray(value)
    if np.ma.isMaskedArray(value) or a.ndim != 0 or a.dtype.kind not in "iuf":
        raise ValueError(f"{name} must be a real scalar")
    x = float(a)
    if not np.isfinite(x):
        raise ValueError(f"{name} must be finite")
    return x


def width_scalar(value):
    a = np.asarray(value)
    if np.ma.isMaskedArray(value) or a.ndim != 0 or a.dtype.kind not in "iuf":
        raise ValueError("width must be a real scalar")
    return float(a)


def normalize_log_shape(log_shape, weights, total):
    log_shape = np.asarray(log_shape, dtype=np.longdouble)
    weights = np.asarray(weights, dtype=np.longdouble)
    if not np.all(np.isfinite(log_shape)):
        # A valid finite input may still produce an overflowed intermediate;
        # use the finite limiting endpoint when possible.
        if np.any(np.isnan(log_shape)):
            raise FloatingPointError("profile exponent is not representable")
    peak = np.max(log_shape)
    if not np.isfinite(peak):
        raise FloatingPointError("profile exponent is not representable")
    with np.errstate(over="ignore", invalid="ignore"):
        shape = np.exp(log_shape - peak)
    denominator = np.sum(shape * weights, dtype=np.longdouble)
    if not np.isfinite(denominator) or denominator == 0:
        raise FloatingPointError("profile normalization is not representable")
    result = (np.longdouble(total) / denominator) * shape
    if not np.all(np.isfinite(result)) or np.any(np.abs(result) > np.finfo(np.float64).max):
        raise FloatingPointError("profile result is not representable")
    cast_result = np.asarray(result, dtype=np.float64)
    # Tiny tails may round to zero, as in the profile convention, provided their loss does not
    # destroy the requested discrete integral. The relative gate is fixed at
    # 64 float64 epsilons, with no absolute floor that could hide a tiny total.
    integral = np.sum(cast_result.astype(np.longdouble) * weights, dtype=np.longdouble)
    if total != 0 and abs((integral - np.longdouble(total)) / np.longdouble(total)) > 64 * np.finfo(np.float64).eps:
        raise FloatingPointError("float64 rounding cannot preserve the profile integral")
    return cast_result

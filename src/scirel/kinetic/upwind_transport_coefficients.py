"""KN1DPy H/H2 Ak/Bk/Fk/Ck/Dk/Gk spatial transport coefficients."""
from __future__ import annotations

import numpy as np

__all__ = ["assemble_neutral_upwind_transport_coefficients"]


def _finite_real_array(value, name):
    try:
        if isinstance(value, (list, tuple)) and any(
            isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
        ):
            raise ValueError
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite real array") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite real array")
    return result


def assemble_neutral_upwind_transport_coefficients(x_m, vx, collision_frequency_s_inv, source_distribution):
    """Return source forward/backward trapezoidal transport coefficients."""
    x = _finite_real_array(x_m, "x_m")
    axial = _finite_real_array(vx, "vx")
    alpha = _finite_real_array(collision_frequency_s_inv, "collision_frequency_s_inv")
    source = _finite_real_array(source_distribution, "source_distribution")
    if x.ndim != 1 or axial.ndim != 1 or x.size < 2 or np.any(axial == 0.0) or alpha.ndim != 3 or source.shape != alpha.shape or alpha.shape[1:] != (axial.size, x.size) or np.any(alpha < 0.0):
        raise ValueError("x/vx/alpha/source contract is invalid")
    with np.errstate(over="ignore", invalid="ignore"):
        spacings = np.diff(x)
    if not np.all(np.isfinite(spacings)) or np.any(spacings <= 0.0):
        raise ValueError("x_m must have finite positive spatial steps")
    positive, negative = np.flatnonzero(axial > 0.0), np.flatnonzero(axial < 0.0)
    if positive.size == 0 or negative.size == 0:
        raise ValueError("vx must contain positive and negative branches")
    a = np.zeros_like(alpha)
    b = np.zeros_like(alpha)
    f = np.zeros_like(alpha)
    c = np.zeros_like(alpha)
    d = np.zeros_like(alpha)
    g = np.zeros_like(alpha)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        for k, dx in enumerate(spacings):
            denominator = 2.0 * axial[positive][None, :] + dx * alpha[:, positive, k + 1]
            a[:, positive, k] = (2.0 * axial[positive][None, :] - dx * alpha[:, positive, k]) / denominator
            b[:, positive, k] = dx / denominator
            f[:, positive, k] = dx * (source[:, positive, k + 1] + source[:, positive, k]) / denominator
        for k in range(1, x.size):
            dx = spacings[k - 1]
            denominator = -2.0 * axial[negative][None, :] + dx * alpha[:, negative, k - 1]
            c[:, negative, k] = (-2.0 * axial[negative][None, :] - dx * alpha[:, negative, k]) / denominator
            d[:, negative, k] = dx / denominator
            g[:, negative, k] = dx * (source[:, negative, k] + source[:, negative, k - 1]) / denominator
    if not all(np.all(np.isfinite(field)) for field in (a, b, f, c, d, g)):
        raise ValueError("transport coefficients must be finite")
    return {"Ak": a, "Bk": b, "Fk": f, "Ck": c, "Dk": d, "Gk": g, "positive_vx_indices": positive, "negative_vx_indices": negative}

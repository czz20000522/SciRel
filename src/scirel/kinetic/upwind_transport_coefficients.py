"""KN1DPy H/H2 Ak/Bk/Fk/Ck/Dk/Gk spatial transport coefficients."""
from __future__ import annotations

import numpy as np


def assemble_neutral_upwind_transport_coefficients(x_m, vx, collision_frequency_s_inv, source_distribution):
    """Return source forward/backward trapezoidal transport coefficients."""
    x = np.asarray(x_m, dtype=float)
    axial = np.asarray(vx, dtype=float)
    alpha = np.asarray(collision_frequency_s_inv, dtype=float)
    source = np.asarray(source_distribution, dtype=float)
    if x.ndim != 1 or axial.ndim != 1 or x.size < 2 or np.any(np.diff(x) <= 0.0) or not np.all(np.isfinite(x)) or np.any(axial == 0.0) or not np.all(np.isfinite(axial)) or alpha.ndim != 3 or source.shape != alpha.shape or alpha.shape[1:] != (axial.size, x.size) or not np.all(np.isfinite(alpha)) or np.any(alpha < 0.0) or not np.all(np.isfinite(source)):
        raise ValueError("x/vx/alpha/source contract is invalid")
    positive, negative = np.flatnonzero(axial > 0.0), np.flatnonzero(axial < 0.0)
    if positive.size == 0 or negative.size == 0:
        raise ValueError("vx must contain positive and negative branches")
    a = np.zeros_like(alpha)
    b = np.zeros_like(alpha)
    f = np.zeros_like(alpha)
    c = np.zeros_like(alpha)
    d = np.zeros_like(alpha)
    g = np.zeros_like(alpha)
    for k, dx in enumerate(np.diff(x)):
        denominator = 2.0 * axial[positive][None, :] + dx * alpha[:, positive, k + 1]
        a[:, positive, k] = (2.0 * axial[positive][None, :] - dx * alpha[:, positive, k]) / denominator
        b[:, positive, k] = dx / denominator
        f[:, positive, k] = dx * (source[:, positive, k + 1] + source[:, positive, k]) / denominator
    for k in range(1, x.size):
        dx = x[k] - x[k - 1]
        denominator = -2.0 * axial[negative][None, :] + dx * alpha[:, negative, k - 1]
        c[:, negative, k] = (-2.0 * axial[negative][None, :] - dx * alpha[:, negative, k]) / denominator
        d[:, negative, k] = dx / denominator
        g[:, negative, k] = dx * (source[:, negative, k] + source[:, negative, k - 1]) / denominator
    return {"Ak": a, "Bk": b, "Fk": f, "Ck": c, "Dk": d, "Gk": g, "positive_vx_indices": positive, "negative_vx_indices": negative}

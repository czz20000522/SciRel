"""KN1DPy first-flight and scattered-generation bidirectional propagation."""
from __future__ import annotations

import numpy as np


def propagate_neutral_generation(vx, Ak, Bk, Fk, Ck, Dk, Gk, generation_kind, incoming_boundary=None, scattered_source_distribution=None):
    """Return one source-style neutral generation for `first_flight` or `scattered`."""
    axial = np.asarray(vx, dtype=float)
    coefficients = [np.asarray(value, dtype=float) for value in (Ak, Bk, Fk, Ck, Dk, Gk)]
    a, b, f, c, d, g = coefficients
    if axial.ndim != 1 or any(value.ndim != 3 or value.shape != a.shape for value in coefficients) or a.shape[1] != axial.size or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)) or not np.all(np.isfinite(f)) or not np.all(np.isfinite(c)) or not np.all(np.isfinite(d)) or not np.all(np.isfinite(g)):
        raise ValueError("vx and coefficient fields are invalid")
    positive, negative = axial > 0.0, axial < 0.0
    if not np.any(positive) or not np.any(negative) or generation_kind not in ("first_flight", "scattered"):
        raise ValueError("vx branches or generation_kind are invalid")
    generation = np.zeros_like(a)
    if generation_kind == "first_flight":
        boundary = np.asarray(incoming_boundary, dtype=float)
        if boundary.shape != a.shape[:2] or not np.all(np.isfinite(boundary)) or scattered_source_distribution is not None:
            raise ValueError("first_flight needs exactly one finite incoming_boundary")
        generation[:, positive, 0] = boundary[:, positive]
        for k in range(a.shape[2] - 1):
            generation[:, positive, k + 1] = generation[:, positive, k] * a[:, positive, k] + f[:, positive, k]
        for k in range(a.shape[2] - 1, 0, -1):
            generation[:, negative, k - 1] = generation[:, negative, k] * c[:, negative, k] + g[:, negative, k]
    else:
        source = np.asarray(scattered_source_distribution, dtype=float)
        if source.shape != a.shape or not np.all(np.isfinite(source)) or incoming_boundary is not None:
            raise ValueError("scattered needs exactly one finite scattered_source_distribution")
        for k in range(a.shape[2] - 1):
            generation[:, positive, k + 1] = generation[:, positive, k] * a[:, positive, k] + b[:, positive, k] * (source[:, positive, k + 1] + source[:, positive, k])
        for k in range(a.shape[2] - 1, 0, -1):
            generation[:, negative, k - 1] = generation[:, negative, k] * c[:, negative, k] + d[:, negative, k] * (source[:, negative, k - 1] + source[:, negative, k])
    return generation

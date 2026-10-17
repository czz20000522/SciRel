"""KN1DPy first-flight and scattered-generation bidirectional propagation."""
from __future__ import annotations

import numpy as np

__all__ = ["propagate_neutral_generation"]


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


def propagate_neutral_generation(vx, Ak, Bk, Fk, Ck, Dk, Gk, generation_kind, incoming_boundary=None, scattered_source_distribution=None):
    """Return one source-style neutral generation for `first_flight` or `scattered`."""
    axial = _finite_real_array(vx, "vx")
    coefficients = [
        _finite_real_array(value, name)
        for name, value in zip(("Ak", "Bk", "Fk", "Ck", "Dk", "Gk"), (Ak, Bk, Fk, Ck, Dk, Gk))
    ]
    a, b, f, c, d, g = coefficients
    if axial.ndim != 1 or any(value.ndim != 3 or value.shape != a.shape for value in coefficients) or a.shape[1] != axial.size:
        raise ValueError("vx and coefficient fields are invalid")
    positive, negative = axial > 0.0, axial < 0.0
    if not np.any(positive) or not np.any(negative) or not isinstance(generation_kind, str) or generation_kind not in ("first_flight", "scattered"):
        raise ValueError("vx branches or generation_kind are invalid")
    if a.shape[2] < 1:
        raise ValueError("nx must be at least one for generation propagation")
    generation = np.zeros_like(a)
    if generation_kind == "first_flight":
        if incoming_boundary is None or scattered_source_distribution is not None:
            raise ValueError("first_flight needs exactly one finite incoming_boundary")
        boundary = _finite_real_array(incoming_boundary, "incoming_boundary")
        if boundary.shape != a.shape[:2]:
            raise ValueError("first_flight needs exactly one finite incoming_boundary")
        generation[:, positive, 0] = boundary[:, positive]
        with np.errstate(over="ignore", invalid="ignore"):
            for k in range(a.shape[2] - 1):
                generation[:, positive, k + 1] = generation[:, positive, k] * a[:, positive, k] + f[:, positive, k]
            for k in range(a.shape[2] - 1, 0, -1):
                generation[:, negative, k - 1] = generation[:, negative, k] * c[:, negative, k] + g[:, negative, k]
    else:
        if scattered_source_distribution is None or incoming_boundary is not None:
            raise ValueError("scattered needs exactly one finite scattered_source_distribution")
        source = _finite_real_array(scattered_source_distribution, "scattered_source_distribution")
        if source.shape != a.shape:
            raise ValueError("scattered needs exactly one finite scattered_source_distribution")
        with np.errstate(over="ignore", invalid="ignore"):
            for k in range(a.shape[2] - 1):
                generation[:, positive, k + 1] = generation[:, positive, k] * a[:, positive, k] + b[:, positive, k] * (source[:, positive, k + 1] + source[:, positive, k])
            for k in range(a.shape[2] - 1, 0, -1):
                generation[:, negative, k - 1] = generation[:, negative, k] * c[:, negative, k] + d[:, negative, k] * (source[:, negative, k - 1] + source[:, negative, k])
    if not np.all(np.isfinite(generation)):
        raise ValueError("generation must be finite")
    return generation

"""Cell-local charge-exchange source from an explicit previous generation."""

from __future__ import annotations

import numpy as np


def _real_array(value, name):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            isinstance(value, (list, tuple))
            and any(isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat)
        ):
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite real array") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite real array")
    return result


def assemble_simple_charge_exchange_source(
    target_distribution,
    charge_exchange_frequency_s_inv,
    previous_generation_distribution,
    cylindrical_weight,
    dvx,
):
    """Scale target by each cell's quadrature-contracted CX rate."""
    target = _real_array(target_distribution, "target_distribution")
    alpha = _real_array(charge_exchange_frequency_s_inv, "charge_exchange_frequency_s_inv")
    previous = _real_array(
        previous_generation_distribution, "previous_generation_distribution"
    )
    weight = _real_array(cylindrical_weight, "cylindrical_weight")
    axial_width = _real_array(dvx, "dvx")
    if (
        target.ndim != 3
        or alpha.shape != target.shape
        or previous.shape != target.shape
        or weight.shape != target.shape[:2]
        or axial_width.shape != (target.shape[1],)
    ):
        raise ValueError("Simple_CX fields must be finite and aligned; rates and quadrature must be nonnegative")
    if np.any(alpha < 0) or np.any(weight < 0) or np.any(axial_width < 0):
        raise ValueError("Simple_CX fields must be finite and aligned; rates and quadrature must be nonnegative")
    with np.errstate(over="ignore", invalid="ignore"):
        rate = np.sum(
            weight[:, :, None] * alpha * previous * axial_width[None, :, None],
            axis=(0, 1),
        )
        result = target * rate[None, None, :]
    if not np.all(np.isfinite(result)):
        raise ValueError("the assembled scattered source must be finite")
    return result

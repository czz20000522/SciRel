"""Normalized charge-exchange source h*integral(alpha_CX*F_previous*d^3u)."""

from __future__ import annotations

import numpy as np

__all__ = ["assemble_simple_charge_exchange_source"]


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
    charge_exchange_frequency_m_inv,
    previous_generation_distribution,
    cylindrical_weight,
    dvx,
):
    """Return a spatial source in F/m on dimensionless velocity nodes.

    ``target_distribution`` is a caller-provided dimensionless shape h,
    ``previous_generation_distribution`` is a distribution density F, and
    ``charge_exchange_frequency_m_inv`` is alpha_CX=nu_CX/Vth. Quadrature
    weights integrate over normalized velocity volume. The caller owns h's
    normalization: only a unit weighted integral makes the source number
    integral equal the CX loss integral. No normalization or density division
    is performed here; signed finite h is used as given.
    """
    target = _real_array(target_distribution, "target_distribution")
    alpha = _real_array(charge_exchange_frequency_m_inv, "charge_exchange_frequency_m_inv")
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
        # Contract the predecessor once in velocity space; the target field
        # is then scaled independently at every spatial node.
        weighted_previous = weight[:, :, None] * previous * axial_width[None, :, None]
        rate = np.sum(alpha * weighted_previous, axis=(0, 1))
        result = target * rate[None, None, :]
    if not np.all(np.isfinite(result)):
        raise ValueError("the assembled scattered source must be finite")
    return result

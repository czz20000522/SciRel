"""Assemble neutral total-loss frequency on a cylindrical velocity mesh."""

from __future__ import annotations

import numpy as np

__all__ = ["assemble_neutral_total_collision_frequency"]


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
        raise ValueError(f"{name} must contain finite real values") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain finite real values")
    return result


def assemble_neutral_total_collision_frequency(
    vr,
    vx,
    base_loss_frequency_s_inv,
    elastic_frequency_s_inv,
    pipe_diameter_m,
    charge_exchange_frequency_s_inv=None,
    charge_exchange_enabled=True,
):
    """Return optional CX + base loss + elastic loss + finite-pipe wall loss."""
    if not isinstance(charge_exchange_enabled, (bool, np.bool_)):
        raise ValueError("charge_exchange_enabled must be a boolean scalar")
    radial = _real_array(vr, "vr")
    axial = _real_array(vx, "vx")
    base = _real_array(base_loss_frequency_s_inv, "base_loss_frequency_s_inv")
    elastic = _real_array(elastic_frequency_s_inv, "elastic_frequency_s_inv")
    diameter = _real_array(pipe_diameter_m, "pipe_diameter_m")
    if (
        radial.ndim != 1
        or axial.ndim != 1
        or base.ndim != 1
        or elastic.shape != base.shape
        or diameter.shape != base.shape
        or radial.size == 0
        or axial.size == 0
        or np.any(radial <= 0.0)
        or np.any(base < 0.0)
        or np.any(elastic < 0.0)
        or np.any(diameter < 0.0)
    ):
        raise ValueError("velocity axes and base/elastic/pipe profiles are invalid")
    shape = (radial.size, axial.size, base.size)
    wall = np.zeros(shape, dtype=float)
    positive_diameter = diameter > 0.0
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        wall[:, :, positive_diameter] = (
            2.0 * radial[:, None, None] / diameter[None, None, positive_diameter]
        )
        total = base[None, None, :] + elastic[None, None, :] + wall
        if charge_exchange_enabled:
            if charge_exchange_frequency_s_inv is None:
                raise ValueError("enabled charge exchange needs its explicit frequency field")
            charge_exchange = _real_array(
                charge_exchange_frequency_s_inv, "charge_exchange_frequency_s_inv"
            )
            if charge_exchange.shape != shape or np.any(charge_exchange < 0.0):
                raise ValueError("charge-exchange frequency must be nonnegative and (nvr,nvx,nx)")
            total = total + charge_exchange
    if not np.all(np.isfinite(total)):
        raise ValueError("the assembled total loss frequency is not finite")
    return total

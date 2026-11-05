"""Incoming neutral boundary-flux normalization over the positive-vx half.

One leaf recovered from the saved the neutral-transport formulation ``入射中性边界通量归一化`` package, integrated as
:func:`normalize_incoming_neutral_boundary`:

scale a caller-owned H or H2 boundary shape distribution on the positive
axial-velocity half space to a requested incoming neutral particle flux,
returning the scaled incoming boundary distribution, the applied scalar
scale, and the pre-scale incoming flux integral
``Vth * sum(volume * shape * vx)`` over ``vx > 0``.

The saved positive-half arithmetic and operation order are retained for
finite real inputs. SciRel enforces the declared real, finite, nonnegative
quadrature and finite-output contract that the saved implementation did not
fully check. The negative half of the returned
distribution is exactly zero (the source's incoming-boundary semantics), and
the scale is ``abs(target_flux) / incoming_flux`` exactly as saved -- a
negative requested flux produces the same positive scale. A zero target
produces a zero scale and zero boundary.

Evidence ceiling: maintained tests establish the normalization and the
fail-closed contracts. Finite valid-path comparison with the saved
implementation is bounded historical development evidence, not qualified-L1
provenance; the saved bundle's strict D1 qualification has been withdrawn.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "normalize_incoming_neutral_boundary",
]


def _real_array(value, name):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            not isinstance(value, np.ndarray)
            and any(
                isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
            )
        ):
            raise ValueError
        return np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a real numeric array") from error


def _real_scalar(value, name):
    try:
        raw = np.asarray(value)
        if raw.ndim != 0 or raw.dtype.kind not in "iuf":
            raise ValueError
        return float(raw)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a real numeric scalar") from error


def _incoming_flux(shape, axial, volume, speed):
    """Contract the positive axial half-space without mutating the shape."""
    positive = axial > 0.0
    return speed * np.sum(volume[:, positive] * shape[:, positive] * axial[None, positive])


def normalize_incoming_neutral_boundary(
    boundary_shape, vx, cylindrical_volume, thermal_speed_m_s, target_flux_m2_s
):
    """Scale the positive-vx source shape to the source desired incoming flux.

    Parameters
    ----------
    boundary_shape
        The caller's boundary shape as a finite nonnegative ``(nvr, nvx)``
        array (axial velocity on the second axis).
    vx
        The axial velocity axis, a finite one-dimensional ``(nvx,)`` array
        containing at least one positive node.
    cylindrical_volume
        The cylindrical quadrature weight, finite, shape ``(nvr, nvx)``.
    thermal_speed_m_s
        The positive thermal speed in ``m/s`` (the :doc:`thermal speed scale
        <thermal_speed_scale>` of the species).
    target_flux_m2_s
        The requested incoming particle flux in ``m^-2 s^-1`` (finite).

    Returns
    -------
    tuple
        ``(incoming_boundary, scale, incoming_flux)``: the scaled boundary
        distribution (zero on the nonpositive-vx half), the applied positive
        scale, and the pre-scale positive-half flux integral.

    Raises
    ------
    ValueError
        If any contract above is violated.
    """
    shape = _real_array(boundary_shape, "boundary_shape")
    axial = _real_array(vx, "vx")
    volume = _real_array(cylindrical_volume, "cylindrical_volume")
    speed = _real_scalar(thermal_speed_m_s, "thermal_speed_m_s")
    target = _real_scalar(target_flux_m2_s, "target_flux_m2_s")
    if (
        shape.ndim != 2
        or axial.ndim != 1
        or shape.shape[1] != axial.size
        or volume.shape != shape.shape
        or not np.all(np.isfinite(shape))
        or not np.all(np.isfinite(axial))
        or not np.all(np.isfinite(volume))
        or np.any(shape < 0.0)
        or np.any(volume < 0.0)
        or not np.isfinite(speed)
        or speed <= 0.0
        or not np.isfinite(target)
    ):
        raise ValueError("boundary shape, quadrature, thermal speed, or target flux is invalid")
    positive = axial > 0.0
    if not np.any(positive):
        raise ValueError("vx must contain a positive incoming half")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        incoming_flux = _incoming_flux(shape, axial, volume, speed)
    if not np.isfinite(incoming_flux):
        raise ValueError("incoming flux must be finite")
    if incoming_flux <= 0.0:
        raise ValueError("positive-vx boundary shape must have positive flux")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        scale = abs(target) / incoming_flux
    if not np.isfinite(scale) or (target != 0.0 and scale == 0.0):
        raise ValueError("boundary scale must be finite and positive for nonzero target flux")
    incoming_boundary = np.zeros_like(shape)
    with np.errstate(over="ignore", invalid="ignore"):
        incoming_boundary[:, positive] = shape[:, positive] * scale
    if not np.all(np.isfinite(incoming_boundary)):
        raise ValueError("incoming boundary must be finite")
    return incoming_boundary, float(scale), float(incoming_flux)

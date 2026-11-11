"""Scalar closed-form Green response for a collection of circular coils."""

from __future__ import annotations

import numpy as np

from scirel.electromagnetism.greens import compute_greens

MU0_OVER_2PI = 2.0e-7


def evaluate_filament_coil_green_field(
    regularized_radius_m,
    observation_z_m,
    coil_radius_m,
    coil_z_m,
    current_a,
    turns,
):
    """Return summed ``(psi, B_R, B_Z)`` for aligned coil arrays.

    ``regularized_radius_m`` is already offset by the geometry operator.  The
    response therefore applies no second axis shift.  Coincident rings are
    singular and rejected before any nonfinite response can escape.

    The per-ring response comes from
    :func:`scirel.electromagnetism.compute_greens`, the canonical
    circular-filament kernel.  That kernel uses a small-modulus
    hypergeometric branch below ``m = 0.5`` and the complementary elliptic
    form above it, so the flux and radial field stay accurate near the
    cylindrical axis where the ``(2-m)K-2E`` combination cancels (issue #10
    item 4).  Reusing it also removes a second, independent implementation of
    the same Green relation; the remaining duplicate between ``field`` and
    ``electromagnetism`` is tracked in #155.
    """
    radius = float(regularized_radius_m)
    observation_z_m = float(observation_z_m)
    coil_radius, coil_z, current, winding = (
        np.asarray(value, dtype=float) for value in (coil_radius_m, coil_z_m, current_a, turns)
    )
    if radius <= 0.0 or not np.isfinite(radius) or not np.isfinite(observation_z_m):
        raise ValueError(
            "regularized observation coordinates must be finite and positive in radius"
        )
    if any(
        value.ndim != 1 or value.shape != coil_radius.shape for value in (coil_z, current, winding)
    ):
        raise ValueError(
            "coil inputs and elliptic values must be same-shape vectors with valid geometry"
        )
    if not all(
        np.all(np.isfinite(value)) for value in (coil_radius, coil_z, current, winding)
    ) or np.any(coil_radius <= 0.0):
        raise ValueError(
            "coil inputs and elliptic values must be same-shape vectors with valid geometry"
        )
    separation2 = (radius - coil_radius) ** 2 + (observation_z_m - coil_z) ** 2
    if np.any(separation2 <= 0.0):
        raise ValueError("singular coil geometry: observation point on a filament ring")

    sources = np.column_stack((coil_radius, coil_z, winding * current))
    targets = np.array([[radius, observation_z_m]])
    psi, b_r, b_z = compute_greens(sources, targets)
    result = (float(psi[0]), float(b_r[0]), float(b_z[0]))
    if not all(np.isfinite(value) for value in result):
        raise ValueError("filament-coil response overflowed to a non-finite value")
    return result


__all__ = ["evaluate_filament_coil_green_field"]

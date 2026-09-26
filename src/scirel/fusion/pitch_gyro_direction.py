"""FIDASIM pitch_to_vec local velocity-direction mapping.

Source: FIDASIM ``pitch_to_vec`` — one pitch/gyro-angle pair plus an
orthonormal local frame ``(a_unit, b_unit, c_unit)`` map to the unit
velocity direction ``sqrt(1 - pitch^2)*cos(gyroangle)*a_unit + pitch*b_unit
+ sqrt(1 - pitch^2)*sin(gyroangle)*c_unit``: the pitch fixes the component
along ``b_unit`` (``dot(direction, b_unit) == pitch``) and the gyro angle
rotates the perpendicular remainder within the ``a_unit``-``c_unit`` plane.
The frame must be orthonormal (unit norms, pairwise-orthogonal within
1e-12); the pitch must lie in ``[-1, 1]``.
"""
from __future__ import annotations

import numpy as np

__all__ = ["pitch_gyro_to_velocity_direction"]


def pitch_gyro_to_velocity_direction(*, pitch, gyroangle_rad, a_unit, b_unit, c_unit):
    a, b, c = (np.asarray(x, dtype=float) for x in (a_unit, b_unit, c_unit))
    if any(x.shape != (3,) or not np.all(np.isfinite(x)) for x in (a, b, c)) or not np.isfinite(pitch) or not np.isfinite(gyroangle_rad) or abs(pitch) > 1:
        raise ValueError("finite orthogonal basis vectors, finite gyro angle and pitch in [-1,1] are required")
    if not all(np.isclose(np.linalg.norm(x), 1.0, atol=1e-12, rtol=0) for x in (a, b, c)) or not np.isclose(np.dot(a, b), 0, atol=1e-12) or not np.isclose(np.dot(a, c), 0, atol=1e-12) or not np.isclose(np.dot(b, c), 0, atol=1e-12):
        raise ValueError("a_unit, b_unit and c_unit must be an orthonormal basis")
    sine = np.sqrt(max(1.0 - pitch ** 2, 0.0))
    return sine * np.cos(gyroangle_rad) * a + pitch * b + sine * np.sin(gyroangle_rad) * c

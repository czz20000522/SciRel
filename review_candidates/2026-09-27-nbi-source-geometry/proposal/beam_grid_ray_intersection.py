"""FIDASIM finite rectilinear beam-grid ray entry/exit mapping.

Source: FIDASIM ``grid_intersect`` finite rectilinear branch -- enumerate the
six faces of an axis-aligned box in the source's ``+x,-x,+y,-y,+z,-z`` order,
keep faces whose parallel coordinates stay inside the closed side bounds, and
pair the first valid face with the first later valid face more than ``0.001``
cm away.  ``dot(direction, delta)`` then orders entry and exit along the ray.
This discrete face order is part of the contract and is not replaced by a
generic slab test.  The enumeration is an infinite-line face-pair test with
no origin-side check (a pinned saved-arm semantic): the ordered pair may lie
entirely behind the ray origin -- an origin inside the grid legitimately
reports its entry behind the origin, and a ray pointing away from the grid
still reports ``intersects_grid=True`` -- so callers needing forward-only
geometry must validate the returned points themselves.  No intersection, a
tangential degeneracy, or a missing
second distinct face returns the input origin for both points with zero
length and ``intersects_grid=False``.

Registered hardening against the saved arm: grid lengths must be finite
(the saved arm's positivity test lets NaN lengths pass to a silent
no-intersection result), and the returned geometry must stay finite.
"""
from __future__ import annotations

import numpy as np

__all__ = ["intersect_ray_with_rectilinear_grid"]


def intersect_ray_with_rectilinear_grid(ray_origin_cm, ray_direction, grid_center_cm, grid_lengths_cm):
    """Return the source-ordered entry/exit of one ray with a finite rectilinear grid."""
    origin = np.asarray(ray_origin_cm, dtype=float)
    direction = np.asarray(ray_direction, dtype=float)
    center = np.asarray(grid_center_cm, dtype=float)
    lengths = np.asarray(grid_lengths_cm, dtype=float)
    if any(value.shape != (3,) or not np.all(np.isfinite(value)) for value in (origin, direction, center, lengths)):
        raise ValueError("ray and grid vectors must be finite shape-[3] arrays")
    if np.any(lengths <= 0.0) or not np.all(np.isfinite(lengths)):
        raise ValueError("grid_lengths_cm must be finite and strictly positive")

    points = np.zeros((6, 3), dtype=float)
    valid = np.zeros(6, dtype=bool)
    for side in range(6):
        axis = side // 2
        if abs(direction[axis]) == 0.0:
            continue
        sign = 0.5 if side % 2 == 0 else -0.5
        point = origin + direction * ((center[axis] + sign * lengths[axis] - origin[axis]) / direction[axis])
        other_axes = [index for index in range(3) if index != axis]
        if all(abs(point[index] - center[index]) <= 0.5 * lengths[index] for index in other_axes):
            points[side] = point
            valid[side] = True

    entry = origin.copy()
    exit_point = origin.copy()
    first = next((index for index, present in enumerate(valid) if present), None)
    if first is None:
        return {"entry_point_cm": entry, "exit_point_cm": exit_point, "intersection_length_cm": 0.0, "intersects_grid": False}
    second = next((index for index in range(first + 1, 6) if valid[index] and np.linalg.norm(points[index] - points[first]) > 1.0e-3), None)
    if second is None:
        return {"entry_point_cm": entry, "exit_point_cm": exit_point, "intersection_length_cm": 0.0, "intersects_grid": False}
    delta = points[second] - points[first]
    if float(np.dot(direction, delta)) > 0.0:
        entry, exit_point = points[first], points[second]
    else:
        entry, exit_point = points[second], points[first]
    length = float(np.linalg.norm(exit_point - entry))
    # Registered hardening: extreme magnitudes can overflow the face points
    # (the saved arm returns non-finite geometry silently when a surviving
    # candidate face is non-finite).
    if not (np.all(np.isfinite(entry)) and np.all(np.isfinite(exit_point)) and np.isfinite(length)):
        raise ValueError(
            "grid-intersection outputs are non-finite for finite but extreme "
            "input magnitudes (registered hardening)")
    return {"entry_point_cm": entry, "exit_point_cm": exit_point, "intersection_length_cm": length, "intersects_grid": True}

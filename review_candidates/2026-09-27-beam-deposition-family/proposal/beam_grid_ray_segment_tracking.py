"""FIDASIM ``track`` beam-grid DDA segment traversal.

Source: FIDASIM ``track`` (the saved package ``束网格射线分段跟踪``,
src/fidasim.f90:9271-9466) -- deterministic cell-by-cell traversal of the
caller's Cartesian beam grid: per-axis exit times from the cell center
plus half a cell width along the velocity sign, the source's two-record
plasma-crossing split (crossing time located by 50 fixed subdivisions),
the adaptive subsegment count from the caller's parameter callback, and
the one-based cell indices.  Zero velocity returns the source's empty
traversal; the crossing-limit hit pops the last segment once (source
``cc`` decrement quirk) and reports ``max_crossings``.

Registered hardenings against the saved arm: the segment/crossing/split
limits and the adaptive mode must be genuine integers (bools rejected;
the saved arm's ``isinstance(int)`` test accepted ``True`` as ``1``).
"""
from __future__ import annotations

import numpy as np

__all__ = ["trace_beam_grid_ray_segments"]


def _strict_positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 1:
        raise ValueError(f"{name} must be a genuine positive integer (registered hardening)")
    return int(value)


def trace_beam_grid_ray_segments(
    start_position_cm,
    velocity_cm_s,
    initial_grid_index_one_based,
    x_cell_centers_cm,
    y_cell_centers_cm,
    z_cell_centers_cm,
    cell_width_cm,
    max_track_segments,
    max_crossings,
    in_plasma_at,
    adaptive_mode=0,
    max_cell_splits=1,
    split_tolerance=0.0,
    adaptive_parameter_at=None,
):
    """Return source-ordered ``track`` records from caller-owned grid state."""
    start = np.asarray(start_position_cm, dtype=float)
    velocity = np.asarray(velocity_cm_s, dtype=float)
    index_values = np.asarray(initial_grid_index_one_based, dtype=float)
    index = index_values.astype(int)
    centers = tuple(np.asarray(values, dtype=float) for values in (
        x_cell_centers_cm, y_cell_centers_cm, z_cell_centers_cm))
    width = np.asarray(cell_width_cm, dtype=float)
    # Registered hardening: genuine integer limits; the saved arm accepted
    # bools here because bool subclasses int.
    max_track_segments = _strict_positive_integer(max_track_segments, "max_track_segments")
    max_crossings = _strict_positive_integer(max_crossings, "max_crossings")
    max_cell_splits = _strict_positive_integer(max_cell_splits, "max_cell_splits")
    if (start.shape != (3,) or velocity.shape != (3,) or index.shape != (3,)
            or width.shape != (3,) or not np.all(np.isfinite(start))
            or not np.all(np.isfinite(velocity)) or not np.all(np.isfinite(width))
            or np.any(width <= 0.0) or adaptive_mode not in range(8)
            or not callable(in_plasma_at) or any(values.ndim != 1 or values.size < 1
                                                  or not np.all(np.isfinite(values))
                                                  for values in centers)
            or not isinstance(adaptive_mode, (int, np.integer))
            or not np.all(index_values == index) or np.any(index < 1)
            or np.any(index > [values.size for values in centers])):
        raise ValueError("finite grid, one-based initial index, positive limits, and plasma predicate are required")
    if np.dot(velocity, velocity) == 0.0:
        return {"segments": [], "ntrack": 0, "plasma_crossings": 0, "terminal_reason": "zero_velocity"}
    adaptive = adaptive_mode if split_tolerance != 0.0 else 0
    if adaptive and (not np.isfinite(split_tolerance) or split_tolerance <= 0.0
                     or not callable(adaptive_parameter_at)):
        raise ValueError("positive split_tolerance and adaptive_parameter_at are required for adaptive mode")
    direction_sign = np.sign(velocity).astype(int)
    working_velocity = np.where(velocity == 0.0, 1.0e-3, velocity)
    cell_center = np.array([values[i - 1] for values, i in zip(centers, index)], dtype=float)
    position = start.copy()
    in_plasma = bool(in_plasma_at(position))
    segments, crossings = [], 0
    terminal_reason = "ntrack_limit"
    for _ in range(max_track_segments):
        if len(segments) >= max_track_segments:
            break
        dt_by_axis = np.abs(((cell_center + 0.5 * width * direction_sign) - position) / working_velocity)
        axis = int(np.argmin(dt_by_axis))
        duration = float(dt_by_axis[axis])
        next_position = position + duration * working_velocity
        next_in_plasma = bool(in_plasma_at(next_position))
        record_index = tuple(int(value) for value in index)
        if in_plasma != next_in_plasma:
            if len(segments) + 2 > max_track_segments:
                raise ValueError("max_track_segments cannot store this source two-record plasma crossing")
            crossing_duration = 0.0
            for _ in range(50):
                crossing_duration += duration / 50.0
                if bool(in_plasma_at(position + working_velocity * crossing_duration)) == next_in_plasma:
                    break
            segments.extend((
                {"position_cm": position + 0.5 * crossing_duration * working_velocity,
                 "duration_s": crossing_duration, "grid_index_one_based": record_index},
                {"position_cm": position + 0.5 * (crossing_duration + duration) * working_velocity,
                 "duration_s": duration - crossing_duration, "grid_index_one_based": record_index},
            ))
            crossings += 1
        elif not adaptive:
            segments.append({"position_cm": position + 0.5 * duration * working_velocity,
                             "duration_s": duration, "grid_index_one_based": record_index})
        else:
            parameter_start = float(adaptive_parameter_at(position, adaptive))
            parameter_end = float(adaptive_parameter_at(next_position, adaptive))
            if not np.isfinite(parameter_start) or not np.isfinite(parameter_end):
                raise ValueError("adaptive_parameter_at must return finite values")
            inverse_parameter = 1.0 if parameter_start + parameter_end <= 0.0 else 2.0 / (parameter_start + parameter_end)
            count = int(np.ceil(abs(parameter_start - parameter_end) * inverse_parameter
                                / (duration * np.linalg.norm(working_velocity) * split_tolerance)))
            count = min(max(count, 1), max_cell_splits)
            if len(segments) + count > max_track_segments:
                raise ValueError("max_track_segments cannot store source adaptive subsegments")
            for subsegment in range(1, count + 1):
                elapsed = duration * subsegment / count
                segments.append({"position_cm": position + 0.5 * elapsed * working_velocity,
                                 "duration_s": duration / count, "grid_index_one_based": record_index})
        position = next_position
        in_plasma = next_in_plasma
        index[axis] += direction_sign[axis]
        cell_center[axis] += width[axis] * direction_sign[axis]
        if index[axis] < 1 or index[axis] > centers[axis].size:
            terminal_reason = "grid_exit"
            break
        if crossings >= max_crossings:
            segments.pop()  # FIDASIM decrements cc once after a crossing-limit hit.
            terminal_reason = "max_crossings"
            break
    return {"segments": segments, "ntrack": len(segments), "plasma_crossings": crossings,
            "terminal_reason": terminal_reason}

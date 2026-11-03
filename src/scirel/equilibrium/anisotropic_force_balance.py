"""Axisymmetric gyrotropic pressure-tensor force and current closure."""
from __future__ import annotations

import math
import struct
import numpy as np

from scirel._anisotropic_numerics import pressure_divergence, residual_metrics

MU0 = 4.0e-7 * np.pi
__all__ = ["compute_anisotropic_force_balance"]


def _source_hypot(left, right):
    """Evaluate ``hypot`` with the retained source's finite-range behavior."""
    left, right = np.broadcast_arrays(np.asarray(left, dtype=float), np.asarray(right, dtype=float))
    result = []
    for first, second in zip(left.flat, right.flat):
        x, y = abs(float(first)), abs(float(second))
        if math.isinf(x) or math.isinf(y):
            result.append(math.inf)
            continue
        if math.isnan(x) or math.isnan(y):
            result.append(math.nan)
            continue
        if x < y:
            x, y = y, x
        if x == 0.0:
            result.append(0.0)
            continue
        _, exponent = math.frexp(x)
        scaled_x = math.ldexp(x, -exponent)
        scaled_y = math.ldexp(y, -exponent)
        bits = struct.unpack(">Q", struct.pack(">d", scaled_x))[0] & 18446744073575333888
        high = struct.unpack(">d", struct.pack(">Q", bits))[0]
        low = scaled_x - high
        scaled_norm = math.sqrt(high * high - (scaled_y * -scaled_y - low * (scaled_x + high)))
        try:
            result.append(math.ldexp(scaled_norm, exponent))
        except OverflowError:
            result.append(math.inf)
    return np.asarray(result, dtype=float).reshape(left.shape)


def compute_anisotropic_force_balance(
    r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular, active_mask=None
):
    """Compute ``div(P)``, toroidal current, and closure diagnostics.

    Inputs are finite, rectilinear ``[Z, R]`` arrays.  The imported numerical
    kernel supplies the local pressure divergence; this wrapper adds the
    dimensionless parallel-force and firehose diagnostics used by the graph
    solvers.
    """
    arrays = [np.asarray(value, dtype=float) for value in
              (r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular)]
    shape = arrays[0].shape
    if any(value.ndim != 2 or value.shape != shape or not np.all(np.isfinite(value))
           for value in arrays):
        raise ValueError("R, Z, field, and pressure inputs must be finite same-shape [Z,R] arrays")
    r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular = arrays
    r_axis, z_axis = r_grid[0], z_grid[:, 0]
    if (r_axis.size < 3 or z_axis.size < 3
            or not np.allclose(r_grid, r_axis[None, :])
            or not np.allclose(z_grid, z_axis[:, None])):
        raise ValueError("a rectilinear R-Z grid with at least 3 points per axis is required")
    if (r_axis[0] < 0.0 or np.any(np.diff(r_axis) <= 0.0)
            or np.any(np.diff(z_axis) <= 0.0)
            or np.any(p_parallel < 0.0) or np.any(p_perpendicular < 0.0)):
        raise ValueError("grid axes and pressures are invalid")
    mask = np.ones(shape, dtype=bool) if active_mask is None else np.asarray(active_mask, dtype=bool)
    if mask.shape != shape:
        raise ValueError("active_mask must match the R-Z grid")

    result = pressure_divergence(
        r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular
    )
    force_norm = np.hypot(result["force_R"], result["force_Z"])
    diagnostics = residual_metrics(
        result["parallel_force"], force_norm, result["parallel_force_roundoff"], mask
    )
    result.update({
        "parallel_force_error": diagnostics["error"],
        "parallel_force_absolute": diagnostics["absolute"],
        "parallel_force_error_raw": diagnostics["raw_relative"],
        "parallel_force_roundoff_rms": diagnostics["roundoff"],
        "parallel_force_roundoff_consistent": diagnostics["roundoff_consistent"],
        "firehose_margin": 1.0 - MU0 * (p_parallel - p_perpendicular)
        / np.maximum(result["B"] ** 2, np.finfo(float).tiny),
    })
    return result

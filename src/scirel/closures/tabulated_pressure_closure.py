"""Interpolate isotropic or anisotropic pressure tables on ``(B, psi)``."""

import numpy as np

from scirel._result import Result


def _bracket(axis, query):
    """Return lower indices and interpolation fractions, allowing extrapolation."""
    index = np.searchsorted(axis, query, side="right") - 1
    index = np.clip(index, 0, axis.size - 2)
    left = axis[index]
    fraction = (query - left) / (axis[index + 1] - left)
    return index, fraction


def _linear(axis, table, query):
    index, fraction = _bracket(axis, query)
    return table[index] + fraction * (table[index + 1] - table[index])


def _bilinear(b_axis, psi_axis, table, field, flux):
    b_index, b_fraction = _bracket(b_axis, field)
    psi_index, psi_fraction = _bracket(psi_axis, flux)
    lower = table[b_index, psi_index]
    along_psi = lower + psi_fraction * (table[b_index, psi_index + 1] - lower)
    upper = table[b_index + 1, psi_index]
    upper_along_psi = upper + psi_fraction * (table[b_index + 1, psi_index + 1] - upper)
    return along_psi + b_fraction * (upper_along_psi - along_psi)


def _apply_domain(values, field, flux, *, b_grid, psi_grid, bounds_error, fill_value):
    """Apply the public out-of-domain policy to an interpolated array."""
    outside = (flux < psi_grid[0]) | (flux > psi_grid[-1])
    if b_grid is not None:
        outside |= (field < b_grid[0]) | (field > b_grid[-1])
    if bounds_error and np.any(outside):
        raise ValueError("query point is outside the interpolation domain")
    if not bounds_error and fill_value is not None:
        values = np.array(values, copy=True)
        values[outside] = fill_value
    return values


def evaluate_tabulated_pressure(
    magnetic_field,
    psi,
    psi_grid,
    p_parallel_table,
    p_perpendicular_table=None,
    b_grid=None,
    bounds_error=True,
    fill_value=None,
):
    """Return linearly interpolated parallel and perpendicular pressures.

    A one-dimensional table is a function of ``psi`` and must be isotropic.
    A two-dimensional table uses axes ``(B, psi)``.  With ``bounds_error``
    false, ``fill_value=None`` selects linear extrapolation and a finite scalar
    fills out-of-domain points.  Tables and returned pressures are finite and
    nonnegative; interpolation does not certify force balance.

    Returns
    -------
    The top-level value is a ``scirel._result.Result`` mapping; field values
    are available by key and preserve the baseline key order.
    p_parallel : NumPy float64 array [Pa by caller table convention]
        Interpolated parallel pressure at broadcast queries.
    p_perpendicular : NumPy float64 array [Pa by caller table convention]
        Interpolated perpendicular pressure, or a copy of parallel pressure in the one-dimensional
        branch.
    is_isotropic : Python bool [dimensionless]
        Whether the complete supplied component tables are exactly equal after float64 conversion.
    table_dimension : int [dimensionless]
        Number of table interpolation coordinates."""
    psi_axis = np.asarray(psi_grid, dtype=float)
    parallel_table = np.asarray(p_parallel_table, dtype=float)
    if (
        psi_axis.ndim != 1
        or psi_axis.size < 2
        or not np.all(np.isfinite(psi_axis))
        or np.any(np.diff(psi_axis) <= 0.0)
    ):
        raise ValueError("psi_grid must be one-dimensional, finite, and strictly increasing")
    if not np.all(np.isfinite(parallel_table)) or np.any(parallel_table < 0.0):
        raise ValueError("pressure tables must be finite and nonnegative")
    if not isinstance(bounds_error, (bool, np.bool_)):
        raise ValueError("bounds_error must be boolean")
    if fill_value is not None:
        fill_array = np.asarray(fill_value, dtype=float)
        if fill_array.ndim != 0 or not np.isfinite(fill_array) or float(fill_array) < 0.0:
            raise ValueError("fill_value must be a finite nonnegative scalar or None")
        fill_value = float(fill_array)

    field, flux = np.broadcast_arrays(
        np.asarray(magnetic_field, dtype=float), np.asarray(psi, dtype=float)
    )
    if not np.all(np.isfinite(field)) or not np.all(np.isfinite(flux)):
        raise ValueError("magnetic_field and psi must be finite")

    if b_grid is None:
        # Keep the optional scientific stack lazy: a valid interpolation call
        # advertises the same capability boundary as the other table tools.
        import scipy  # noqa: F401

        if parallel_table.shape != psi_axis.shape:
            raise ValueError("an isotropic pressure table must match psi_grid")
        if p_perpendicular_table is not None:
            perpendicular_table = np.asarray(p_perpendicular_table, dtype=float)
            if (
                perpendicular_table.shape != psi_axis.shape
                or not np.all(np.isfinite(perpendicular_table))
                or np.any(perpendicular_table < 0.0)
            ):
                raise ValueError(
                    "an isotropic perpendicular pressure table must match psi_grid and be finite and nonnegative"
                )
            if not np.array_equal(parallel_table, perpendicular_table):
                raise ValueError(
                    "b_grid=None requires equal parallel and perpendicular pressure tables"
                )
        pressure = _linear(psi_axis, parallel_table, flux)
        pressure = _apply_domain(
            pressure,
            field,
            flux,
            b_grid=None,
            psi_grid=psi_axis,
            bounds_error=bool(bounds_error),
            fill_value=fill_value,
        )
        if not np.all(np.isfinite(pressure)) or np.any(pressure < 0.0):
            raise ValueError("interpolated pressure must be finite and nonnegative")
        return Result(
            {
                "p_parallel": pressure,
                "p_perpendicular": pressure.copy(),
                "is_isotropic": True,
                "table_dimension": 1,
            }
        )

    b_axis = np.asarray(b_grid, dtype=float)
    import scipy  # noqa: F401

    perpendicular_table = (
        parallel_table
        if p_perpendicular_table is None
        else np.asarray(p_perpendicular_table, dtype=float)
    )
    expected_shape = (b_axis.size, psi_axis.size)
    if (
        b_axis.ndim != 1
        or b_axis.size < 2
        or not np.all(np.isfinite(b_axis))
        or np.any(np.diff(b_axis) <= 0.0)
    ):
        raise ValueError("b_grid must be one-dimensional, finite, and strictly increasing")
    if (
        parallel_table.shape != expected_shape
        or perpendicular_table.shape != expected_shape
        or not np.all(np.isfinite(perpendicular_table))
        or np.any(perpendicular_table < 0.0)
    ):
        raise ValueError(
            "anisotropic pressure tables must be finite nonnegative arrays with shape (len(b_grid), len(psi_grid))"
        )

    parallel = _bilinear(b_axis, psi_axis, parallel_table, field, flux)
    perpendicular = _bilinear(b_axis, psi_axis, perpendicular_table, field, flux)
    parallel = _apply_domain(
        parallel,
        field,
        flux,
        b_grid=b_axis,
        psi_grid=psi_axis,
        bounds_error=bool(bounds_error),
        fill_value=fill_value,
    )
    perpendicular = _apply_domain(
        perpendicular,
        field,
        flux,
        b_grid=b_axis,
        psi_grid=psi_axis,
        bounds_error=bool(bounds_error),
        fill_value=fill_value,
    )
    if (
        not np.all(np.isfinite(parallel))
        or not np.all(np.isfinite(perpendicular))
        or np.any(parallel < 0.0)
        or np.any(perpendicular < 0.0)
    ):
        raise ValueError("interpolated pressures must be finite and nonnegative")
    return Result(
        {
            "p_parallel": parallel,
            "p_perpendicular": perpendicular,
            "is_isotropic": bool(np.array_equal(parallel_table, perpendicular_table)),
            "table_dimension": 2,
        }
    )


__all__ = ["evaluate_tabulated_pressure"]

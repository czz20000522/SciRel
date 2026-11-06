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
    """Interpolate isotropic or anisotropic pressure tables on broadcast queries.

    Parameters
    ----------
    magnetic_field : real array-like
        Magnetic-field query used as the first interpolation coordinate when
        ``b_grid`` is supplied and otherwise only for broadcasting. [T by caller convention]
        Shape: scalar or array broadcast-compatible with ``psi``. Values must
        be finite; positivity is not checked.
    psi : real array-like
        Flux-coordinate query at the same broadcast samples as
        ``magnetic_field``. [same flux unit as psi_grid; historical label Wb]
        Shape: scalar or array broadcast-compatible with ``magnetic_field``.
        Values must be finite; coordinate and unit consistency are caller
        obligations.
    psi_grid : real array-like
        Strictly increasing flux interpolation axis shared by both pressure
        tables. [same caller flux unit as psi] Shape: one-dimensional
        ``(N_psi,)`` with at least two points. Values must be finite.
    p_parallel_table : real array-like
        Parallel pressure samples on ``psi_grid`` or on the tensor
        ``(b_grid, psi_grid)``. [Pa by caller convention] Shape: ``(N_psi,)``
        when ``b_grid`` is None; otherwise ``(N_B, N_psi)``. Values must be
        finite and nonnegative.
    p_perpendicular_table : real array-like or None, optional
        Optional perpendicular pressure samples. [Pa by caller convention]
        Shape: None or the same shape as ``p_parallel_table``. Default: None.
        In the one-dimensional branch a supplied table must exactly equal the
        parallel table; in the two-dimensional branch it defaults to the
        parallel table.
    b_grid : real array-like or None, optional
        Optional magnetic-field interpolation axis; supplying it selects the
        two-dimensional branch. [same field unit as magnetic_field, historically T]
        Shape: None or one-dimensional ``(N_B,)`` with at least two points.
        Default: None. Values must be finite and strictly increasing.
    bounds_error : bool, optional
        Whether out-of-domain queries raise. [dimensionless] Shape: scalar.
        Default: True. Must be boolean.
    fill_value : real scalar or None, optional
        Constant out-of-domain pressure when ``bounds_error`` is false.
        [Pa when not None] Shape: scalar or None. Default: None, which requests
        linear extrapolation in that mode. A supplied value must be finite and
        nonnegative.

    Returns
    -------
    p_parallel : numpy.ndarray
        Interpolated parallel pressure at the broadcast queries. [Pa by caller
        table convention] Shape: broadcast shape of ``magnetic_field`` and
        ``psi``, including zero-dimensional scalar output.
    p_perpendicular : numpy.ndarray
        Interpolated perpendicular pressure, or a copy of parallel pressure in
        the one-dimensional branch. [Pa by caller table convention] Shape:
        same as ``p_parallel``.
    is_isotropic : bool
        Whether the complete supplied component tables are exactly equal after
        float64 conversion. [dimensionless] Shape: scalar.
    table_dimension : int
        Number of table interpolation coordinates: one without ``b_grid`` and
        two with it. [dimensionless] Shape: scalar.

    Raises
    ------
    ValueError
        If an axis has invalid rank, length, ordering or finiteness; a table
        has invalid shape, nonfinite values or negative values; ``bounds_error``
        is not boolean; ``fill_value`` is invalid; queries are nonfinite or
        cannot broadcast; an out-of-domain query is rejected; or interpolation
        returns a nonfinite or negative pressure.

    See Also
    --------
    scirel.closures.close_hall_two_fluid_pressure : Hall pressure state that consumes pressure profiles.

    Notes
    -----
    With ``b_grid=None`` the pressure is linear in ``psi`` and the result is
    isotropic. With ``b_grid`` present the pressure is bilinear on
    ``(B, psi)``. ``bounds_error=True`` rejects any query outside the selected
    axes. With ``bounds_error=False``, ``fill_value=None`` uses the same
    linear/bilinear extrapolation while a finite nonnegative scalar fills
    outside points. The operation interpolates caller-supplied tables only; it
    does not infer a pressure law, find flux surfaces or certify force balance.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.closures import evaluate_tabulated_pressure
    >>> b_axis = np.array([1.0, 2.0])
    >>> psi_axis = np.array([0.0, 1.0])
    >>> parallel = np.array([[2.0, 4.0], [4.0, 6.0]])
    >>> perpendicular = np.array([[3.0, 5.0], [5.0, 7.0]])
    >>> a = evaluate_tabulated_pressure(1.5, 0.25, psi_axis, parallel, perpendicular, b_axis)
    >>> np.testing.assert_allclose(a['p_parallel'], 3.5)
    >>> np.testing.assert_allclose(a['p_perpendicular'], 4.5)
    >>> assert a['is_isotropic'] is False
    >>> b = evaluate_tabulated_pressure(10.0, 0.5, psi_axis, [2.0, 6.0])
    >>> np.testing.assert_allclose(b['p_parallel'], 4.0)
    >>> np.testing.assert_allclose(b['p_perpendicular'], 4.0)
    >>> assert b['is_isotropic'] is True
    >>> assert a['table_dimension']==2 and b['table_dimension']==1
    """
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

"""Discretization of a signed permanent-ring approximation."""

import numpy as np

from scirel._result import Result


def discretize_permanent_ring(r0, z0, width, height, mu_hat_deg=0.0):
    """Discretize a permanent ring as a named point/weight result.

    Parameters
    ----------
    r0 : real scalar
        Radial coordinate of the section centroid [m]. Finite and nonnegative;
        resulting filament radii must remain nonnegative.
    z0 : real scalar
        Axial coordinate of the section centroid [m]. Finite.
    width : real scalar
        Separation of the two radial surface-filament groups [m]. Finite and
        strictly positive.
    height : real scalar
        Axial extent spanned by eight points on each group before rotation [m].
        Finite and strictly positive.
    mu_hat_deg : real scalar, optional
        Cross-section rotation about its centroid [degree]. Finite; every
        nonzero angle is rotated. Default is ``0.0``.

    Returns
    -------
    rz_pts : ndarray of float64, shape [16,2]
        Field ``rz_pts`` of the returned ``scirel._result.Result`` mapping:
        ordered filament positions, each row ``[R,Z]`` in [m,m].
    default_weights : ndarray of float64, shape [16]
        Field ``default_weights`` of the returned result mapping: relative
        source weights in point order [dimensionless].

    Raises
    ------
    ValueError
        If inputs are nonfinite or invalid, the rotation crosses the
        cylindrical axis, or output points are nonfinite.

    See Also
    --------
    scirel.field.superpose_current_green_field : Weighted response contraction.

    Notes
    -----
    The two arrays are stored directly in one ``scirel._result.Result``
    mapping. No nested mapping is returned, and mapping access remains
    available alongside attribute access. The first eight weights are ``-1``
    and the last eight are ``+1``.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.field import discretize_permanent_ring
    >>> result = discretize_permanent_ring(2.0, 3.0, 4.0, 2.0)
    >>> assert isinstance(result, Result)
    >>> assert list(result) == ['rz_pts', 'default_weights']
    >>> assert result.rz_pts is result['rz_pts']
    >>> assert result['rz_pts'].shape == (16, 2)
    >>> np.testing.assert_allclose(result['rz_pts'][:8, 0], 0.0)
    >>> np.testing.assert_allclose(result['rz_pts'][8:, 0], 4.0)
    >>> np.testing.assert_allclose(
    ...     result['rz_pts'][:8, 1], np.linspace(2.0, 4.0, 8)
    ... )
    >>> np.testing.assert_allclose(
    ...     result['default_weights'], [-1.0] * 8 + [1.0] * 8
    ... )
    """
    center = np.asarray((r0, z0), dtype=float)
    dimensions = np.asarray((width, height, mu_hat_deg), dtype=float)
    if not np.all(np.isfinite(center)) or not np.all(np.isfinite(dimensions)):
        raise ValueError("ring geometry must be finite")
    if center[0] < 0.0 or dimensions[0] <= 0.0 or dimensions[1] <= 0.0:
        raise ValueError("ring geometry must have nonnegative radius and positive dimensions")
    with np.errstate(over="ignore", invalid="ignore"):
        radial = center[0] + np.array([-0.5, 0.5]) * dimensions[0]
        axial = np.linspace(center[1] - 0.5 * dimensions[1], center[1] + 0.5 * dimensions[1], 8)
        points = np.vstack(
            (
                np.column_stack((np.full(8, radial[0]), axial)),
                np.column_stack((np.full(8, radial[1]), axial)),
            )
        )
        if dimensions[2] != 0.0:
            theta = np.deg2rad(dimensions[2])
            rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
            points = (points - center) @ rotation + center
    if not np.all(np.isfinite(points)) or np.any(points[:, 0] < 0.0):
        raise ValueError("ring geometry crosses the cylindrical axis or contains nonfinite points")
    return Result({"rz_pts": points, "default_weights": np.r_[-np.ones(8), np.ones(8)]})


__all__ = ["discretize_permanent_ring"]

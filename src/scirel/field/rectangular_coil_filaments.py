"""Vectorized rectangular coil filament geometry."""

from __future__ import annotations

import numpy as np


def _positive_integer(name, value):
    if isinstance(value, (bool, np.bool_)) or int(value) != value or int(value) <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _positive_scalar(name, value):
    value = float(value)
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be a positive finite scalar")
    return value


def discretize_rectangular_coil(r0, z0, nr, nz, dr, dz, angle_deg=0.0):
    """Return ordered ``(R, Z)`` centers for a rectangular filament array.

    Parameters
    ----------
    r0 : real scalar
        Coil-section center radius [m]. Finite and nonnegative.
    z0 : real scalar
        Coil-section center axial coordinate [m]. Finite.
    nr : integer scalar
        Number of radial filament centers [count]. Positive, not boolean, and
        strictly integral.
    nz : integer scalar
        Number of axial filament centers [count]. Positive, not boolean, and
        strictly integral.
    dr : real scalar
        Positive finite radial center spacing [m].
    dz : real scalar
        Positive finite axial center spacing [m].
    angle_deg : real scalar, optional
        In-plane rotation angle [degree] using the maintained row-vector sign
        convention. Finite; the default is ``0.0``.

    Returns
    -------
    rz_pts : ndarray of float64, shape [nr*nz,2]
        Ordered filament center coordinates [m,m] in radial-outer, axial-inner
        order. Every radius is nonnegative.

    Raises
    ------
    ValueError
        If a center or angle is nonfinite, a count is not a positive integer,
        a spacing is not positive, ``r0`` is negative, or the rotated points
        cross the cylindrical axis.

    See Also
    --------
    scirel.field.solve_multi_coil_vacuum_field : Build fields from rectangular coil records.
    scirel.electromagnetism.RectangularCoil : Parameterized rectangular source array.

    Notes
    -----
    The radial index is outermost and the axial index is innermost. Rotation is
    applied to row vectors around the declared centroid, so a positive angle
    follows the package cylindrical drawing convention. The returned array is a
    geometry-only center table; it does not assign current, weights, or finite
    conductor cross-sections.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.field import discretize_rectangular_coil
    >>> points = discretize_rectangular_coil(1.0, 2.0, nr=2, nz=3, dr=0.4, dz=0.2)
    >>> np.testing.assert_allclose(points, [[0.8, 1.8], [0.8, 2.0], [0.8, 2.2], [1.2, 1.8], [1.2, 2.0], [1.2, 2.2]])
    """
    r0, z0 = float(r0), float(z0)
    if not np.isfinite(r0) or not np.isfinite(z0):
        raise ValueError("r0 and z0 must be finite")
    if r0 < 0.0:
        raise ValueError("r0 must be a nonnegative cylindrical radius")
    nr, nz = _positive_integer("nr", nr), _positive_integer("nz", nz)
    dr, dz = _positive_scalar("dr", dr), _positive_scalar("dz", dz)
    angle_deg = float(angle_deg)
    if not np.isfinite(angle_deg):
        raise ValueError("angle_deg must be finite")

    radial = np.linspace(r0 - 0.5 * dr * (nr - 1), r0 + 0.5 * dr * (nr - 1), nr)
    axial = np.linspace(z0 - 0.5 * dz * (nz - 1), z0 + 0.5 * dz * (nz - 1), nz)
    points = np.column_stack((np.repeat(radial, nz), np.tile(axial, nr)))
    if angle_deg != 0.0:
        theta = np.deg2rad(angle_deg)
        cosine, sine = np.cos(theta), np.sin(theta)
        rotation = np.array([[cosine, -sine], [sine, cosine]])
        points = (points - np.array([r0, z0])) @ rotation + np.array([r0, z0])
    if np.any(points[:, 0] < 0.0):
        raise ValueError("coil geometry crosses the cylindrical axis")
    return points


__all__ = ["discretize_rectangular_coil"]

"""Two-dimensional rotations in cylindrical ``(R, Z)`` coordinates."""

from __future__ import annotations

import math

import numpy as np

__all__ = ["rotate"]


def rotate(pts, angle, pivot=(0.0, 0.0)):
    """Planar cylindrical rotation

    Parameters
    ----------
    pts : Finite float64
        Point rows [m] Shape: ``(...,2)``. Final dimension length 2

    angle : float
        Rotation angle [degree] Shape: ``scalar``. Finite degrees

    pivot : Finite float64, optional
        Rotation pivot [m] Shape: ``(2,)``. Finite R,Z pivot Optional; default ``[0.0,
        0.0]``.

    Returns
    -------
    rotated : Finite float64
        Rotated points [m] Shape: ``(...,2)``. Input shape preserved

    Raises
    ------
    ValueError
        Raises ValueError for nonfinite coordinates, mismatched shapes, negative radius, malformed point dimensions, or invalid rectangular bounds/counts.

    See Also
    --------
    PointsMesh : Points mesh.
    RectMesh : Rectangular R-Z mesh.
    Mesh : Related geometry callable.

    Notes
    -----
    Clockwise-positive row-vector rotation in degrees

    **Coordinates.** Cylindrical R,Z

    **Boundary.** Finite 2-vector pivot and points

    **Preconditions.**

    * Inputs satisfy the documented finite cylindrical coordinate and shape contract

    **Limits.**

    * 3-D physical rotation
    * Nonfinite points

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import rotate
    >>> rotated = rotate([[1.0, 0.0]], 90.0)
    >>> np.testing.assert_allclose(rotated, [[0.0, -1.0]], atol=1e-15)
    """
    points = np.asarray(pts, dtype=float)
    if points.shape[-1] != 2:
        raise ValueError("points must have a final dimension of length 2")
    if not np.all(np.isfinite(points)):
        raise ValueError("points must contain only finite values")
    center = np.asarray(pivot, dtype=float)
    if center.shape != (2,):
        raise ValueError("pivot must contain (R, Z)")
    if not np.all(np.isfinite(center)):
        raise ValueError("pivot must contain only finite values")
    angle = float(angle)
    if not math.isfinite(angle):
        raise ValueError("angle must be finite")
    radians = math.radians(angle)
    cosine, sine = math.cos(radians), math.sin(radians)
    rotation = np.array([[cosine, -sine], [sine, cosine]])
    return (points - center) @ rotation + center

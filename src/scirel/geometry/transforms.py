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
        Rotation angle [rad] Shape: ``scalar``. Finite radians

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
        Raises ValueError for scalar pts, points without a final axis of length 2,
        nonfinite point coordinates, a pivot not shaped (2,) or containing nonfinite
        values, or a nonfinite angle. Negative R is not rejected by this planar
        transform.
    FloatingPointError
        If finite inputs produce nonfinite intermediate values or rotated points.

    See Also
    --------
    PointsMesh : Points mesh.
    RectMesh : Rectangular R-Z mesh.
    Mesh : Related geometry callable.

    Notes
    -----
    Clockwise-positive row-vector rotation in radians. This planar operation
    does not enforce nonnegative R on input points, pivot or output points.

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
    >>> rotated = rotate([[1.0, 0.0]], np.pi / 2)
    >>> np.testing.assert_allclose(rotated, [[0.0, -1.0]], atol=1e-15)
    """
    points = np.asarray(pts, dtype=float)
    if points.ndim == 0 or points.shape[-1] != 2:
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
    cosine, sine = math.cos(angle), math.sin(angle)
    rotation = np.array([[cosine, -sine], [sine, cosine]])
    with np.errstate(over="ignore", invalid="ignore"):
        rotated = (points - center) @ rotation + center
    if not np.all(np.isfinite(rotated)):
        raise FloatingPointError(
            "pts, angle and pivot produced "
            f"{np.count_nonzero(~np.isfinite(rotated))} nonfinite rotated values "
            f"(shape {rotated.shape}, dtype {rotated.dtype}); "
            "rotation intermediates and results must be finite float64; "
            "see scirel.geometry.rotate"
        )
    return rotated

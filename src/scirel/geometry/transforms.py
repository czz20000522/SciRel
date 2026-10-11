"""Two-dimensional row-vector rotations in cylindrical ``(R, Z)`` space."""
from __future__ import annotations
import math
import numpy as np


def rotate(pts, angle, pivot=(0.0, 0.0)):
    """Rotate points clockwise-positive by ``angle`` degrees about ``pivot``.

    The operation follows the source row-vector convention and returns a new
    array; input arrays are never mutated.
    """
    arr = np.asarray(pts, dtype=float)
    if arr.shape[-1] != 2:
        raise ValueError("points must have a final dimension of length 2")
    p = np.asarray(pivot, dtype=float)
    if p.shape != (2,):
        raise ValueError("pivot must contain (R, Z)")
    angle = math.radians(float(angle))
    c, s = math.cos(angle), math.sin(angle)
    matrix = np.array([[c, -s], [s, c]])
    return (arr - p) @ matrix + p


__all__ = ["rotate"]

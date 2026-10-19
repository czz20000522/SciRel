"""Two-dimensional rotations in cylindrical ``(R, Z)`` coordinates."""
from __future__ import annotations

import math

import numpy as np

__all__ = ["rotate"]


def rotate(pts, angle, pivot=(0.0, 0.0)):
    """Rotate points clockwise-positive by ``angle`` degrees about ``pivot``."""
    points = np.asarray(pts, dtype=float)
    if points.shape[-1] != 2:
        raise ValueError("points must have a final dimension of length 2")
    center = np.asarray(pivot, dtype=float)
    if center.shape != (2,):
        raise ValueError("pivot must contain (R, Z)")
    radians = math.radians(float(angle))
    cosine, sine = math.cos(radians), math.sin(radians)
    rotation = np.array([[cosine, -sine], [sine, cosine]])
    return (points - center) @ rotation + center

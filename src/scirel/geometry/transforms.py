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

"""Aggregate weighted circular-filament field responses."""

import numpy as np

from scirel.electromagnetism.greens import compute_greens


def circular_filament_green_response(rzw, rz_pts):
    """Sum ordered weighted ring responses on ``(R, Z)`` target points.

    Rows with zero radius or zero weight are inactive.  Positive-radius exact
    source/target coincidences retain the discrete zero-self convention.  The
    returned values are per ampere: ``gpsi`` is Wb/rad, and ``gBR``/``gBZ``
    are tesla.
    """
    if np.iscomplexobj(rzw) or np.iscomplexobj(rz_pts):
        raise ValueError("source and target coordinates/weights must be real")
    sources = np.asarray(rzw, dtype=float)
    if sources.size == 0:
        sources = np.empty((0, 3), dtype=float)
    targets = np.asarray(rz_pts, dtype=float)
    if sources.ndim != 2 or sources.shape[1] != 3:
        raise ValueError("rzw must have shape (n_filaments, 3)")
    if targets.ndim != 2 or targets.shape[1] != 2:
        raise ValueError("rz_pts must have shape (n_points, 2)")
    if not np.all(np.isfinite(sources)) or not np.all(np.isfinite(targets)):
        raise ValueError("rzw and rz_pts must contain only finite values")
    if np.any(sources[:, 0] < 0.0) or np.any(targets[:, 0] < 0.0):
        raise ValueError("source and target cylindrical radii must be nonnegative")

    response = np.zeros((3, len(targets)), dtype=float)
    for source in sources:
        if source[0] == 0.0 or source[2] == 0.0:
            continue
        off_self = ~((targets[:, 0] == source[0]) & (targets[:, 1] == source[1]))
        if np.any(off_self):
            values = compute_greens(source[None, :], targets[off_self])
            response[:, off_self] += np.asarray(values)
    if not np.all(np.isfinite(response)):
        raise FloatingPointError("circular filament response is not representable")
    return dict(zip(("gpsi", "gBR", "gBZ"), response))


__all__ = ["circular_filament_green_response"]

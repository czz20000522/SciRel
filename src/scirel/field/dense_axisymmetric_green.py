"""Per-source axisymmetric Green response matrices."""

from __future__ import annotations

import numpy as np

from scirel.electromagnetism.greens import green_response_matrices


def dense_axisymmetric_green_response(rz_pts, source_rzw):
    """Return ``gpsi``, ``gBR`` and ``gBZ`` arrays indexed by target/source."""
    if np.iscomplexobj(rz_pts) or np.iscomplexobj(source_rzw):
        raise ValueError("target/source coordinates and weights must be real")
    targets = np.asarray(rz_pts, dtype=float)
    sources = np.asarray(source_rzw, dtype=float)
    if sources.shape == (0,):
        sources = np.empty((0, 3), dtype=float)
    if targets.ndim != 2 or targets.shape[1] != 2:
        raise ValueError("rz_pts must have shape (n_targets, 2)")
    if sources.ndim != 2 or sources.shape[1] != 3:
        raise ValueError("source_rzw must have shape (n_sources, 3)")
    if not np.all(np.isfinite(targets)) or not np.all(np.isfinite(sources)):
        raise ValueError("rz_pts and source_rzw must contain only finite values")
    if np.any(targets[:, 0] < 0.0) or np.any(sources[:, 0] < 0.0):
        raise ValueError("cylindrical radii must be nonnegative")
    gpsi, gbr, gbz = green_response_matrices(targets, sources)
    return {"gpsi": gpsi, "gBR": gbr, "gBZ": gbz}


__all__ = ["dense_axisymmetric_green_response"]

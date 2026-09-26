"""FIDASIM mc_beam_grid explicit-uniform Cartesian cell sample.

Source: FIDASIM ``mc_beam_grid`` — one birth position inside a Cartesian
beam-grid cell is the cell center plus the cell width times a
zero-mean shift of caller-owned uniform draws in ``[0, 1)``.  The
randomness stays caller-owned (deterministic, replayable mapping); the
draws must lie in ``[0, 1)`` and widths are nonnegative.
"""
from __future__ import annotations

import numpy as np

__all__ = ["sample_beam_grid_cell"]


def sample_beam_grid_cell(*, cell_center_cm, cell_width_cm, uniform_draws):
    """Return one birth position inside a Cartesian beam-grid cell."""
    center, width, u = (np.asarray(x, dtype=float) for x in (cell_center_cm, cell_width_cm, uniform_draws))
    if center.shape != (3,) or width.shape != (3,) or u.shape != (3,) or not all(np.all(np.isfinite(x)) for x in (center, width, u)) or np.any(width < 0) or np.any(u < 0) or np.any(u >= 1):
        raise ValueError("finite shape-(3,) center/width and [0,1) uniform draws are required")
    result = center + width * (u - 0.5)
    # Registered hardening: finite extreme magnitudes can overflow the product
    # or sum; the saved arm would return Inf silently.
    if not np.all(np.isfinite(result)):
        raise ValueError(
            "beam-grid cell sampling overflowed to non-finite values for "
            "finite but extreme input magnitudes (registered hardening)")
    return result

"""Compute a masked toroidal volume from an explicit finite R/Z grid."""

from __future__ import annotations

from math import pi

import numpy as np

__all__ = ["plasma_volume"]


def plasma_volume(
    R: np.ndarray,
    dR: float,
    dZ: float,
    core_mask: np.ndarray,
) -> float:
    """Return the toroidally revolved volume represented by a masked grid.

    ``R`` contains major-radius coordinates in metres.  The caller supplies
    uniform radial and vertical cell widths and a numeric or Boolean mask;
    values are multiplied exactly as supplied before reduction.
    """
    volume_element = 2.0 * pi * R * dR * dZ
    volume_element *= core_mask
    return float(np.sum(volume_element))

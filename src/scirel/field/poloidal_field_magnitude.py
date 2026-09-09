"""Finite poloidal-field magnitude with the Pleiades numerical floor."""

import numpy as np


def compute_poloidal_field_magnitude(br, bz):
    """Return ``max(sqrt(BR**2 + BZ**2), 1e-30)`` on the caller grid."""
    radial = np.asarray(br, dtype=float)
    axial = np.asarray(bz, dtype=float)
    if radial.shape != axial.shape or radial.ndim != 2:
        raise ValueError("br and bz must be same-shape two-dimensional [Z,R] arrays")
    if not np.all(np.isfinite(radial)) or not np.all(np.isfinite(axial)):
        raise ValueError("br and bz must contain only finite values")
    if radial.size == 0:
        raise ValueError("br and bz must contain at least one grid point")
    with np.errstate(over="ignore"):
        magnitude = np.maximum(np.hypot(radial, axial), 1.0e-30)
    if not np.all(np.isfinite(magnitude)):
        raise ValueError("poloidal magnitude exceeds the finite floating-point range")
    lower, upper = (magnitude.size - 1) // 2, magnitude.size // 2
    ordered = np.partition(magnitude.ravel(), (lower, upper))
    # Nonnegative midpoint without adding two potentially near-maximum floats.
    reference = ordered[lower] + (ordered[upper] - ordered[lower]) * 0.5
    return {"B": magnitude, "B0_default": float(reference)}


__all__ = ['compute_poloidal_field_magnitude']

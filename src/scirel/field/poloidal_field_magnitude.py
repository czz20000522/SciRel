"""Poloidal magnetic-field magnitude on a two-dimensional grid."""
import numpy as np


def compute_poloidal_field_magnitude(br, bz):
    """Return a finite ``B`` magnitude and its default reference value.

    The floor at ``1e-30`` is part of the public numerical contract.  The
    reference is the median computed by a difference-first interpolation so
    two very large neighboring values do not overflow when averaged.
    """
    radial, axial = np.asarray(br, dtype=float), np.asarray(bz, dtype=float)
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
    lower = (magnitude.size - 1) // 2
    upper = magnitude.size // 2
    ordered = np.partition(magnitude.ravel(), (lower, upper))
    reference = ordered[lower] + 0.5 * (ordered[upper] - ordered[lower])
    return {"B": magnitude, "B0_default": float(reference)}


__all__ = ["compute_poloidal_field_magnitude"]

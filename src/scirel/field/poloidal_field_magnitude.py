"""Finite poloidal-field magnitude with the SciRel numerical floor."""
import numpy as np

def compute_poloidal_field_magnitude(br, bz):
    """Return ``max(sqrt(BR**2 + BZ**2), 1e-30)`` on the caller grid."""
    radial = np.asarray(br, dtype=float)
    axial = np.asarray(bz, dtype=float)
    if radial.shape != axial.shape or radial.ndim != 2:
        raise ValueError('br and bz must be same-shape two-dimensional [Z,R] arrays')
    if not np.all(np.isfinite(radial)) or not np.all(np.isfinite(axial)):
        raise ValueError('br and bz must contain only finite values')
    magnitude = np.maximum(np.hypot(radial, axial), 1e-30)
    return {'B': magnitude, 'B0_default': float(np.nanmedian(magnitude))}
__all__ = ['compute_poloidal_field_magnitude']

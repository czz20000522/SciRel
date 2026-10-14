"""Fixed 16-filament geometry from the shared validated MagnetRing source."""
import numpy as np
from scirel.electromagnetism.sources import MagnetRing


def discretize_permanent_ring(r0, z0, width, height, mu_hat_deg=0.0):
    """Return two radial faces, eight points each, and dimensionless +/-1 weights.

    Positive degrees rotate clockwise in the (R,Z) drawing about the centroid.
    Every nonzero angle is rotated, including angles below 1e-12 degrees.
    Geometry must remain finite with nonnegative cylindrical radius. These
    weights describe geometry; they do not specify magnetization or amperes.
    """
    with np.errstate(over='ignore', invalid='ignore'):
        try:
            ring = MagnetRing(r0=r0, z0=z0, width=width, height=height, mu_hat=mu_hat_deg)
        except ValueError as exc:
            if 'non-negative radius' in str(exc):
                raise ValueError('ring geometry crosses the cylindrical axis or contains nonfinite points') from exc
            raise
    return {'rz_pts': ring.rz_pts.copy(), 'default_weights': ring.weights.copy()}


__all__ = ['discretize_permanent_ring']

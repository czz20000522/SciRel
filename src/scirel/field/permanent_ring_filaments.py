"""Surface-current filament geometry for the source SciRel MagnetRing."""
import math
import numpy as np
_ZERO_ANGLE_ATOL_DEG = 1e-12

def discretize_permanent_ring(r0, z0, width, height, mu_hat_deg=0.0):
    """Return the source-defined 16 MagnetRing surface filaments and weights.

    Positive ``mu_hat_deg`` uses the source row-vector rotation matrix.  In the
    standard (R,Z) Cartesian drawing this is clockwise about the ring centroid.
    """
    r0, z0, width, height, mu_hat_deg = (float(r0), float(z0), float(width), float(height), float(mu_hat_deg))
    if not all((np.isfinite(value) for value in (r0, z0, width, height, mu_hat_deg))):
        raise ValueError('r0, z0, width, height, and mu_hat_deg must be finite')
    if width <= 0.0 or height <= 0.0:
        raise ValueError('width and height must be positive')
    if r0 < 0.0:
        raise ValueError('r0 must be a nonnegative cylindrical radius')
    half_width, half_height = (width / 2.0, height / 2.0)
    z_space = np.linspace(-half_height, half_height, 8)
    rz_pts = np.empty((16, 2), dtype=float)
    rz_pts[:8, 0] = r0 - half_width
    rz_pts[8:, 0] = r0 + half_width
    rz_pts[:8, 1] = z0 + z_space
    rz_pts[8:, 1] = z0 + z_space
    default_weights = np.ones(16, dtype=float)
    default_weights[:8] = -1.0
    if np.isclose(mu_hat_deg, 0.0, rtol=0.0, atol=_ZERO_ANGLE_ATOL_DEG):
        if np.any(rz_pts[:, 0] < 0.0):
            raise ValueError('ring geometry crosses the cylindrical axis')
        return {'rz_pts': rz_pts, 'default_weights': default_weights}
    angle = math.pi * mu_hat_deg / 180.0
    cosine, sine = (np.cos(angle), np.sin(angle))
    rotation = np.array([[cosine, -sine], [sine, cosine]])
    centroid = np.array([r0, z0])
    rz_pts = (rz_pts - centroid) @ rotation + centroid
    if np.any(rz_pts[:, 0] < 0.0):
        raise ValueError('rotated ring geometry crosses the cylindrical axis')
    return {'rz_pts': rz_pts, 'default_weights': default_weights}
__all__ = ['discretize_permanent_ring']

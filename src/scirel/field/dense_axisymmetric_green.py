"""Dense axisymmetric Green matrices for explicit target/source points."""
from __future__ import annotations
import numpy as np
from scipy.special import ellipe, ellipk

def dense_axisymmetric_green_response(rz_pts, source_rzw):
    """Return per-source ``psi``, ``B_R`` and ``B_Z`` Green columns.

    ``rz_pts`` is the target point list ``[R, Z]``.  ``source_rzw`` is the
    source list ``[R0, Z0, weight]``; the third column is a linear source
    weight and is not a current value or a cell-area factor.
    """
    rz_pts = np.asarray(rz_pts, dtype=float)
    source_rzw = np.asarray(source_rzw, dtype=float)
    if source_rzw.size == 0:
        source_rzw = np.empty((0, 3), dtype=float)
    if rz_pts.ndim != 2 or rz_pts.shape[1] != 2:
        raise ValueError('rz_pts must have shape (n_targets, 2)')
    if source_rzw.ndim != 2 or source_rzw.shape[1] != 3:
        raise ValueError('source_rzw must have shape (n_sources, 3)')
    if not np.all(np.isfinite(rz_pts)) or not np.all(np.isfinite(source_rzw)):
        raise ValueError('rz_pts and source_rzw must contain only finite values')
    r = rz_pts[:, 0]
    z = rz_pts[:, 1]
    source_r = source_rzw[:, 0]
    source_z = source_rzw[:, 1]
    source_weight = source_rzw[:, 2]
    if np.any(r < 0.0) or np.any(source_r < 0.0):
        raise ValueError('cylindrical radii must be nonnegative')
    n_target = r.size
    n_source = source_r.size
    gpsi = np.zeros((n_target, n_source), dtype=float)
    g_br = np.zeros_like(gpsi)
    g_bz = np.zeros_like(gpsi)
    r_squared = r * r
    prefactor = 1e-07
    with np.errstate(all='ignore'):
        for column, (r0, z0, weight) in enumerate(source_rzw):
            if np.isclose(r0, 0.0, rtol=0.0, atol=1e-12):
                continue
            z_delta_squared = (z - z0) ** 2
            d_plus = np.sqrt(z_delta_squared + (r + r0) ** 2)
            d_minus = np.sqrt(z_delta_squared + (r - r0) ** 2)
            k_squared = 4.0 * r * r0 / (d_plus * d_plus)
            elliptic_k = ellipk(k_squared)
            elliptic_e = ellipe(k_squared)
            denominator = d_minus * d_minus * d_plus
            factor_1 = elliptic_k * d_minus * d_minus
            factor_2 = (z_delta_squared + r_squared + r0 * r0) * elliptic_e
            psi = weight * prefactor * r * r0 / d_plus * 4.0 / k_squared * ((2.0 - k_squared) * elliptic_k - 2.0 * elliptic_e)
            br = -2.0 * weight * prefactor * (z - z0) * (factor_1 - factor_2) / (r * denominator)
            bz = 2.0 * weight * prefactor * (factor_1 - (factor_2 - 2.0 * r0 * r0 * elliptic_e)) / denominator
            psi[~np.isfinite(psi)] = 0.0
            br[~np.isfinite(br)] = 0.0
            bz[~np.isfinite(bz)] = 0.0
            gpsi[:, column] = psi
            g_br[:, column] = br
            g_bz[:, column] = bz
    return {'gpsi': gpsi, 'gBR': g_br, 'gBZ': g_bz}
__all__ = ['dense_axisymmetric_green_response']

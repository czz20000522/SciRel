"""Axisymmetric circular-filament Green response from the SciRel source."""
import numpy as np
from scipy.special import ellipe, ellipk

def circular_filament_green_response(rzw, rz_pts):
    """Return ``psi``, ``BR`` and ``BZ`` responses of weighted circular filaments."""
    rzw = np.asarray(rzw, dtype=float)
    if rzw.size == 0:
        rzw = np.empty((0, 3), dtype=float)
    rz_pts = np.asarray(rz_pts, dtype=float)
    if rzw.ndim != 2 or rzw.shape[1] != 3:
        raise ValueError('rzw must have shape (n_filaments, 3)')
    if rz_pts.ndim != 2 or rz_pts.shape[1] != 2:
        raise ValueError('rz_pts must have shape (n_points, 2)')
    if not np.all(np.isfinite(rzw)) or not np.all(np.isfinite(rz_pts)):
        raise ValueError('rzw and rz_pts must contain only finite values')
    if np.any(rzw[:, 0] < 0.0) or np.any(rz_pts[:, 0] < 0.0):
        raise ValueError('source and target cylindrical radii must be nonnegative')
    r, z = (rz_pts[:, 0], rz_pts[:, 1])
    gpsi = np.zeros(r.size, dtype=float)
    g_br = np.zeros(r.size, dtype=float)
    g_bz = np.zeros(r.size, dtype=float)
    r_squared = r * r
    prefactor = 1e-07
    with np.errstate(all='ignore'):
        for r0, z0, weight in rzw:
            if np.isclose(r0, 0.0, rtol=0.0, atol=1e-12):
                continue
            z_delta_squared = (z - z0) * (z - z0)
            d_plus = np.sqrt(z_delta_squared + (r + r0) * (r + r0))
            d_minus = np.sqrt(z_delta_squared + (r - r0) * (r - r0))
            k_squared = 4.0 * r * r0 / (d_plus * d_plus)
            elliptic_k = ellipk(k_squared)
            elliptic_e = ellipe(k_squared)
            denominator = d_plus * d_minus * d_minus
            factor_1 = elliptic_k * d_minus * d_minus
            factor_2 = (z_delta_squared + r_squared + r0 * r0) * elliptic_e
            psi_term = weight * prefactor * r * r0 * 4.0 / d_plus / k_squared * ((2.0 - k_squared) * elliptic_k - 2.0 * elliptic_e)
            br_term = -2.0 * weight * prefactor * (z - z0) * (factor_1 - factor_2) / (r * denominator)
            bz_term = 2.0 * weight * prefactor * (factor_1 - (factor_2 - 2.0 * r0 * r0 * elliptic_e)) / denominator
            psi_term[~np.isfinite(psi_term)] = 0.0
            br_term[~np.isfinite(br_term)] = 0.0
            bz_term[~np.isfinite(bz_term)] = 0.0
            gpsi += psi_term
            g_br += br_term
            g_bz += bz_term
    return {'gpsi': gpsi, 'gBR': g_br, 'gBZ': g_bz}
__all__ = ['circular_filament_green_response']

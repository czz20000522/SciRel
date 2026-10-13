"""Weighted circular-filament response with explicit discrete zero-self rule."""
import numpy as np
from scirel.electromagnetism.greens import compute_greens


def circular_filament_green_response(rzw, rz_pts):
    """Sum signed loop responses, preserving the aggregate source interface.

    psi=R*A_phi is Wb/rad per ampere and BR/BZ are T per ampere. Every
    positive source radius is retained; only exactly zero-radius sources or
    zero weights vanish. Axis target BZ uses its analytic limit. Exact
    coincident positive-radius pairs contribute zero under the predecessor
    discrete compatibility convention, not a physical conductor self-field.
    Arithmetic failures propagate instead of silently becoming zero.
    Any empty source array retains the original empty-set shorthand; dense
    per-source response has its own stricter empty-shape contract.
    原近轴剔除及非有限值填零已纠正，保留加权源求和与精确自点离散约定。
    """
    if np.iscomplexobj(rzw) or np.iscomplexobj(rz_pts):
        raise ValueError('source and target coordinates/weights must be real')
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
    output = np.zeros((3,len(rz_pts)))
    with np.errstate(over='raise',divide='raise',invalid='raise'):
        for source in rzw:
            a,z0,w=source
            if a==0. or w==0.:
                continue
            off_self=~((rz_pts[:,0]==a)&(rz_pts[:,1]==z0))
            output[:,off_self] += compute_greens(source[None,:],rz_pts[off_self])
    if not np.all(np.isfinite(output)):
        raise FloatingPointError('circular filament response is not representable')
    return dict(zip(('gpsi','gBR','gBZ'),output))


__all__ = ['circular_filament_green_response']

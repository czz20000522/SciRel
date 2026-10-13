"""Dense axisymmetric Green matrices for explicit target/source points."""
from __future__ import annotations
import numpy as np
from scirel.electromagnetism.greens import green_response_matrices

def dense_axisymmetric_green_response(rz_pts, source_rzw):
    """Return per-source ``psi``, ``B_R`` and ``B_Z`` Green columns.

    Every positive source radius is retained, including below 1e-12 m.
    Exactly coincident source/target pairs keep the explicit discrete zero-self
    convention; this is not a finite-wire self-field. Axis targets retain their
    analytic nonzero BZ. Arithmetic failures raise instead of being zero-filled.
    psi=R*A_phi is Wb/rad per ampere, field components T per ampere.
    原近轴剔除与非有限值填零已按理想圆电流丝方程纠正。

    ``rz_pts`` is the target point list ``[R, Z]``.  ``source_rzw`` is the
    source list ``[R0, Z0, weight]``; the third column is a linear source
    weight and is not a current value or a cell-area factor.
    An empty one-dimensional source sequence is accepted as shorthand for
    a ``(0, 3)`` source matrix; other shapes must satisfy the source contract.
    """
    if np.iscomplexobj(rz_pts) or np.iscomplexobj(source_rzw):
        raise ValueError('target/source coordinates and weights must be real')
    rz_pts = np.asarray(rz_pts, dtype=float)
    source_rzw = np.asarray(source_rzw, dtype=float)
    if source_rzw.shape == (0,):
        source_rzw = np.empty((0, 3), dtype=float)
    if rz_pts.ndim != 2 or rz_pts.shape[1] != 2:
        raise ValueError('rz_pts must have shape (n_targets, 2)')
    if source_rzw.ndim != 2 or source_rzw.shape[1] != 3:
        raise ValueError('source_rzw must have shape (n_sources, 3)')
    if not np.all(np.isfinite(rz_pts)) or not np.all(np.isfinite(source_rzw)):
        raise ValueError('rz_pts and source_rzw must contain only finite values')
    if np.any(rz_pts[:,0] < 0.) or np.any(source_rzw[:,0] < 0.):
        raise ValueError('cylindrical radii must be nonnegative')
    gpsi,g_br,g_bz = green_response_matrices(rz_pts,source_rzw)
    return {'gpsi': gpsi, 'gBR': g_br, 'gBZ': g_bz}
__all__ = ['dense_axisymmetric_green_response']

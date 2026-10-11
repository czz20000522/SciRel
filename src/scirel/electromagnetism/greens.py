"""Static circular-filament Green functions, SI, with psi = R A_phi.

Derived from Pleiades fields.py (D0 be412aa) and Simpson et al., NASA
20010038494, equations (1), (24), (25), (30). The source prefactor and signs
are retained; silent nonfinite-to-zero handling is intentionally replaced.
Small elliptic parameter uses the analytic hypergeometric representation of
the same vector potential to avoid subtractive cancellation, not a cutoff
that zeros the radial field. No finite-wire or permeability model is implied.
"""
from __future__ import annotations
import numpy as np
from scipy.special import ellipkm1, ellipe, hyp2f1


def _array(value, columns, name):
    arr = np.asarray(value, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != columns:
        raise ValueError(f'{name} must have shape (N, {columns})')
    if np.any(~np.isfinite(arr)) or np.any(arr[:, 0] < 0):
        raise ValueError(f'{name} must be finite with non-negative cylindrical radius')
    return arr


def compute_greens(rzw, rz_pts):
    """Return ``(psi, BR, BZ)`` for signed circular-filament weights.

    ``rzw`` is an (Ns,3) array of radius, height (m), and current weight.
    ``rz_pts`` is an (Nt,2) array of target R,Z (m). Outputs are (Nt,) arrays,
    in Wb/rad and T per ampere of common set current. A Python *list of
    arrays* represents independent sets and returns (Nset,Nt) arrays; plain
    row lists must first be converted to an ndarray to avoid ambiguity.

    Axis values are analytic. Exactly zero-radius loops and zero-weight
    filaments contribute zero; every positive loop radius is retained.
    Coincidence with an active positive-radius filament raises ValueError.
    NumPy overflow, division-by-zero and invalid operations, and nonfinite
    outputs raise FloatingPointError instead of being replaced by zero.
    Underflow is not trapped; extreme-scale accuracy is not qualified.
    """
    points = _array(rz_pts, 2, 'rz_pts')
    if isinstance(rzw, list):
        vals = [compute_greens(v, points) for v in rzw]
        if not vals:
            return tuple(np.zeros((0, len(points))) for _ in range(3))
        return tuple(np.stack([v[j] for v in vals]) for j in range(3))
    sources = _array(rzw, 3, 'rzw')
    out = np.zeros((3, len(points)))
    r, z = points.T
    with np.errstate(over='raise', divide='raise', invalid='raise'):
        for a, z0, weight in sources:
            if a == 0 or weight == 0:
                continue
            h = z-z0
            if np.any((r == a) & (h == 0)):
                raise ValueError('target coincident with singular circular filament')
            d = np.hypot(r+a, h)
            q = (np.hypot(r-a, h)/d)**2
            m = 4*(r/d)*(a/d)
            small = m < .05
            psi, br, bz = np.zeros((3, len(points)))
            if np.any(small):
                rs, hs, ds, ms = r[small], h[small], d[small], m[small]
                H = hyp2f1(1.5, 1.5, 3., ms)
                Hp = .75*hyp2f1(2.5, 2.5, 4., ms)
                # psi = pi*1e-7*a^2*r^2/d^3 H(m); differentiate analytically.
                c = np.pi*1e-7*(a/ds)**2/ds
                dm = 4*(a/ds)/ds - 2*ms*((rs+a)/ds)/ds
                psi[small] = c*rs**2*H
                br[small] = c*(rs/ds)*(hs/ds)*(3*H+2*ms*Hp)
                bz[small] = c*((2-3*(rs/ds)*((rs+a)/ds))*H+rs*Hp*dm)
            large = ~small
            if np.any(large):
                rl, hl, dl, ql, ml = r[large], h[large], d[large], q[large], m[large]
                K, E = ellipkm1(ql), ellipe(1-ql)
                rho2 = np.hypot(rl-a, hl)**2
                psi[large] = 1e-7*dl*((2-ml)*K-2*E)
                br[large] = 2e-7*hl/(rl*dl)*(-K+(a*a+rl*rl+hl*hl)/rho2*E)
                bz[large] = 2e-7/dl*(K+(a*a-rl*rl-hl*hl)/rho2*E)
            out += weight*np.array([psi, br, bz])
    if np.any(~np.isfinite(out)):
        raise FloatingPointError('Green function output is not representable as finite float64')
    return tuple(out)


def get_gpsi(R, Z):
    """Return the actual-coordinate discrete loop flux matrix (target, source).

    R,Z are matching finite 2-D coordinate arrays in metres; row-major flattening
    fixes source and target order. Entries are Wb/rad per ampere, psi=R*A_phi.
    Self diagonal and zero-radius sources have exactly zero flux under the
    original discrete compatibility rule (not finite-conductor self-inductance).
    Distinct array entries cannot represent coincident positive-radius loops.

    D2 correction of Pleiades analysis/math.py:get_gpsi: shifting reflected row
    blocks assumes uniform axial spacing and repeated radial coordinates. Direct
    evaluation uses actual coordinates and supports irregular/asymmetric geometry.
    """
    if np.iscomplexobj(R) or np.iscomplexobj(Z):
        raise ValueError("R,Z must be real coordinate arrays")
    r,z=np.asarray(R,dtype=float),np.asarray(Z,dtype=float)
    if (r.ndim!=2 or z.shape!=r.shape or not np.all(np.isfinite(r)) or
            not np.all(np.isfinite(z)) or np.any(r<0)):
        raise ValueError("R,Z must be matching finite 2-D arrays with nonnegative R")
    points=np.column_stack((r.ravel(),z.ravel()))
    active=points[points[:,0]>0]
    if len(np.unique(active,axis=0))!=len(active):
        raise ValueError("distinct positive-radius loop entries cannot be coincident")
    matrix=np.zeros((len(points),len(points)))
    for j,(a,h) in enumerate(points):
        if a==0:continue
        off_self=np.arange(len(points))!=j
        matrix[off_self,j]=compute_greens(np.array([[a,h,1.]]),points[off_self])[0]
    return matrix


__all__ = ['compute_greens','get_gpsi']

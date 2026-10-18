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


def _load_special_functions():
    """Load SciPy's elliptic/hypergeometric kernels at numerical call time."""
    from scipy.special import ellipkm1, ellipe, hyp2f1

    return ellipkm1, ellipe, hyp2f1


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
    ellipkm1 = ellipe = hyp2f1 = None
    with np.errstate(over='raise', divide='raise', invalid='raise'):
        for a, z0, weight in sources:
            if a == 0 or weight == 0:
                continue
            h = z-z0
            # Validate the singularity before loading SciPy.  This keeps
            # rejected calls dependency-light while preserving source order
            # and the original failure precedence for later sources.
            if np.any((r == a) & (h == 0)):
                raise ValueError('target coincident with singular circular filament')
            if ellipkm1 is None:
                ellipkm1, ellipe, hyp2f1 = _load_special_functions()
            d = np.hypot(r+a, h)
            q = (np.hypot(r-a, h)/d)**2
            m = 4*(r/d)*(a/d)
            # The K/E vector-potential subtraction loses relative precision
            # well above m=.05 (an 80-digit witness at m=.1096 exceeds 2e-14).
            # Use the equivalent analytic expression through m<.5; this is a
            # numerical formula partition, never a geometry/field cutoff.
            small = m < .5
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
                # Factor the difference of squares before multiplying: near a
                # wire, separately rounded a² and R² erase radial separation.
                bz[large] = 2e-7/dl*(K+((a-rl)*(a+rl)-hl*hl)/rho2*E)
            out += weight*np.array([psi, br, bz])
    if np.any(~np.isfinite(out)):
        raise FloatingPointError('Green function output is not representable as finite float64')
    return tuple(out)


def _weighted_psi(rzw, rz_pts, *, zero_self=False, max_pairs=1_000_000):
    """Return the weighted ``psi`` sum for many sources in bounded blocks.

    This private path is used by regular-grid consumers that need only the
    flux component.  It keeps the same formula partition and exact zero-self
    compatibility rule as :func:`compute_greens`, but broadcasts a bounded
    source block over all targets instead of making one Python call per
    source.  ``max_pairs`` bounds the temporary ``(source, target)`` arrays so
    a large target grid does not turn the optimization into an allocation
    spike.
    """
    sources = _array(rzw, 3, 'rzw')
    points = _array(rz_pts, 2, 'rz_pts')
    result = np.zeros(len(points))
    if not len(sources) or not len(points):
        return result

    active = sources[(sources[:, 0] > 0.0) & (sources[:, 2] != 0.0)]
    if not len(active):
        return result
    ellipkm1, ellipe, hyp2f1 = _load_special_functions()
    block_size = max(1, min(len(active), int(max_pairs) // max(1, len(points))))
    r = points[:, 0][None, :]
    z = points[:, 1][None, :]

    with np.errstate(over='raise', divide='raise', invalid='raise'):
        for start in range(0, len(active), block_size):
            block = active[start:start + block_size]
            a = block[:, 0, None]
            z0 = block[:, 1, None]
            h = z - z0
            if zero_self:
                self_mask = (r == a) & (z == z0)
                # Avoid evaluating the singular expression; the compatibility
                # value is assigned back to zero after the regular formula.
                h = np.where(self_mask, 1.0, h)
            d = np.hypot(r + a, h)
            q = (np.hypot(r - a, h) / d) ** 2
            m = 4 * (r / d) * (a / d)
            small = m < 0.5
            psi = np.zeros_like(m)
            a_full = np.broadcast_to(a, m.shape)
            r_full = np.broadcast_to(r, m.shape)
            if np.any(small):
                ds = d[small]
                rs = r_full[small]
                ms = m[small]
                H = hyp2f1(1.5, 1.5, 3.0, ms)
                c = np.pi * 1e-7 * (a_full[small] / ds) ** 2 / ds
                psi[small] = c * rs**2 * H
            large = ~small
            if np.any(large):
                dl = d[large]
                ql = q[large]
                ml = m[large]
                K, E = ellipkm1(ql), ellipe(1 - ql)
                psi[large] = 1e-7 * dl * ((2 - ml) * K - 2 * E)
            if zero_self:
                psi[self_mask] = 0.0
            result += np.add.reduce(block[:, 2, None] * psi, axis=0)

    if not np.all(np.isfinite(result)):
        raise FloatingPointError('weighted Green psi output is not representable as finite float64')
    return result


def _psi_matrix(points, *, max_pairs=1_000_000):
    """Return the unit-weight ``psi`` matrix for positive-radius sources.

    ``points`` is the flattened ``(R, Z)`` coordinate table used by
    :func:`get_gpsi`.  The source axis is evaluated in bounded blocks so the
    temporary source/target arrays remain bounded independently of the dense
    output matrix.  This is the matrix analogue of :func:`_weighted_psi`; it
    deliberately keeps the same small-modulus hypergeometric and large-modulus
    elliptic partition as :func:`compute_greens`.
    """
    source_indices = np.flatnonzero(points[:, 0] > 0.0)
    matrix = np.zeros((len(points), len(source_indices)))
    if not len(source_indices) or not len(points):
        return matrix

    ellipkm1, ellipe, hyp2f1 = _load_special_functions()
    block_size = max(1, min(len(source_indices), int(max_pairs) // max(1, len(points))))
    r = points[:, 0][None, :]
    z = points[:, 1][None, :]

    with np.errstate(over='raise', divide='raise', invalid='raise'):
        for start in range(0, len(source_indices), block_size):
            indices = source_indices[start:start + block_size]
            block = points[indices]
            a = block[:, 0, None]
            z0 = block[:, 1, None]
            h = z - z0
            self_mask = (r == a) & (z == z0)
            # Avoid evaluating the singular self expression; compatibility
            # values are assigned back to zero after the regular formula.
            h = np.where(self_mask, 1.0, h)
            d = np.hypot(r + a, h)
            q = (np.hypot(r - a, h) / d) ** 2
            m = 4 * (r / d) * (a / d)
            small = m < 0.5
            psi = np.zeros_like(m)
            a_full = np.broadcast_to(a, m.shape)
            r_full = np.broadcast_to(r, m.shape)
            if np.any(small):
                ds = d[small]
                rs = r_full[small]
                ms = m[small]
                H = hyp2f1(1.5, 1.5, 3.0, ms)
                Hp = 0.75 * hyp2f1(2.5, 2.5, 4.0, ms)
                c = np.pi * 1e-7 * (a_full[small] / ds) ** 2 / ds
                dm = 4 * (a_full[small] / ds) / ds - 2 * ms * (
                    (rs + a_full[small]) / ds
                ) / ds
                psi[small] = c * rs**2 * H
                # Keep compute_greens' arithmetic-failure contract even though
                # get_gpsi only returns psi: its historical implementation
                # evaluated BR/BZ for every off-self pair as well.
                _ = c * (rs / ds) * ((h[small] / ds) * (3 * H + 2 * ms * Hp))
                _ = c * (
                    (2 - 3 * (rs / ds) * ((rs + a_full[small]) / ds)) * H
                    + rs * Hp * dm
                )
            large = ~small
            if np.any(large):
                dl = d[large]
                ql = q[large]
                ml = m[large]
                K, E = ellipkm1(ql), ellipe(1 - ql)
                psi[large] = 1e-7 * dl * ((2 - ml) * K - 2 * E)
                rho2 = np.hypot(r_full[large] - a_full[large], h[large]) ** 2
                _ = 2e-7 * h[large] / (r_full[large] * dl) * (
                    -K + (a_full[large] ** 2 + r_full[large] ** 2 + h[large] ** 2) / rho2 * E
                )
                _ = 2e-7 / dl * (
                    K + ((a_full[large] - r_full[large]) * (a_full[large] + r_full[large])
                         - h[large] ** 2) / rho2 * E
                )
            psi[self_mask] = 0.0
            matrix[:, start:start + len(indices)] = psi.T

    if not np.all(np.isfinite(matrix)):
        raise FloatingPointError('Green psi matrix output is not representable as finite float64')
    return matrix


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
    active_indices = np.flatnonzero(points[:, 0] > 0.0)
    if len(active_indices):
        matrix[:, active_indices] = _psi_matrix(points)
    return matrix


def green_response_matrices(rz_pts, rzw=None):
    """Return ordered per-filament ``(psi, BR, BZ)`` response matrices.

    Each matrix has shape ``(Ntarget, Nsource)``; neither coordinate order is
    sorted or reflected. Targets are ``(R,Z)`` metres. Sources are ``(R,Z,w)``
    with signed dimensionless weights (the predecessor's ``csign``), or
    ``(R,Z)`` with unit weights. ``rzw=None`` uses the target coordinates as
    unit-weight sources. Multiply a matrix by an ordered source-current vector
    in amperes to obtain Wb/rad (psi=R*A_phi) or tesla. Weights are applied once;
    no device current is inferred.

    Exact source/target coordinate coincidences contribute zero by the explicit
    discrete compatibility convention of Pleiades analysis/math.py. This is
    neither a finite-wire self-field nor a near-coincidence cutoff. Nonzero
    separation uses the actual-coordinate corrected kernel; its arithmetic
    failures propagate. Zero-radius *sources* contribute zero; axis targets
    retain the analytic nonzero BZ. Repeated positive-radius target nodes are
    rejected when they implicitly define the source grid. Explicit sources may
    repeat, representing independently weighted columns at the same position.

    This serial composite absorbs the old full/parallel per-source builders;
    acceleration and their original spelling are not scientific capabilities.
    """
    if np.iscomplexobj(rz_pts) or (rzw is not None and np.iscomplexobj(rzw)):
        raise ValueError('target and source coordinates/weights must be real')
    targets = _array(rz_pts, 2, 'rz_pts')
    if rzw is None:
        active = targets[targets[:, 0] > 0]
        if len(np.unique(active, axis=0)) != len(active):
            raise ValueError('implicit positive-radius source nodes cannot be coincident')
        sources = np.column_stack((targets, np.ones(len(targets))))
    else:
        raw = np.asarray(rzw, dtype=float)
        if raw.ndim != 2 or raw.shape[1] not in (2, 3):
            raise ValueError('rzw must have shape (Nsource, 2) or (Nsource, 3)')
        sources = (np.column_stack((raw, np.ones(len(raw))))
                   if raw.shape[1] == 2 else raw)
        sources = _array(sources, 3, 'rzw')
    response = np.zeros((3, len(targets), len(sources)))
    for j, (a, z0, weight) in enumerate(sources):
        if a == 0 or weight == 0:
            continue
        off_self = ~((targets[:, 0] == a) & (targets[:, 1] == z0))
        response[:, off_self, j] = compute_greens(sources[j:j+1], targets[off_self])
    return tuple(response)


__all__ = ['compute_greens','get_gpsi','green_response_matrices']

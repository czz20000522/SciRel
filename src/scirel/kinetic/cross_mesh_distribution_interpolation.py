"""Source-free cross-mesh distribution interpolation (interp_fvrvxx).

Reproduces KN1DPy ``interp_fvrvxx`` (``KN1DPy/interp_fvrvxx.py``), the N5 outer
H<->H2 handoff seam that transfers a velocity distribution between two phase
space meshes (``fH -> fHM``, ``fH2 -> fH2A``, ``fSH -> fSHA``;
``KN1DPy/kn1d.py:439,475-476``).

Algorithm (faithful to the saved formal operator, which has no cache or
w_new branch: it recomputes the weight matrix every call, exactly like this
stateless port.  The original KN1DPy runtime's weight cache lifecycle is a
pure optimisation -- the weight matrix is a deterministic function of the
two meshes -- but that cache lives in the original source runtime, not in
the saved formal operator, so this port cannot and does not claim to
exercise it):

- ``fV = sqrt(Tnorm_b / Tnorm_a)`` scales mesh_b velocity cells onto mesh_a.
- ``weight`` (nvrb*nvxb, nvra*nvxa) holds the 4-D cell-overlap volume integral
  ``2*pi*(vraMax^2 - vraMin^2)*(vxaMax - vxaMin)/(Vr2pidVrb*dVxb)`` for every
  overlapping (ib,jb,ia,ja) velocity cell.
- ``fb_xa = weight @ fa.reshape(nvra*nvxa, nxa, order='F')`` transfers the
  distribution onto mesh_b's velocity space evaluated on the mesh_a x grid.
- x-interpolation: ``kL = locate(mesh_a.x, mesh_b.x[k])`` (searchsorted),
  ``f = (x_b[k]-x_a[kL])/(x_a[kR]-x_a[kL])`` linear in x.
- Moment correction (``correct=1``): AN/BN perturbation moments built from the
  padded ``Nij`` cell densities, four sign branches for (alpha,beta), step
  ``s = min(1/max(-RHS[ii]/Nij[ii]), 1)``, iterate while ``s < 1`` so the
  interpolated ``fb`` reproduces the source ``Wx``/``E`` moments.
- Density rescale: ``tot_b[k0:k1+1] = interp1d(x_a, tot_a,
  fill_value="extrapolate")(x_b[k0:k1+1])``, renormalising ``fb`` where its
  own integrated total exceeds ``min(fb>0)``.

Input contract: ``fa (nvra,nvxa,nxa)``, mesh_a ``(vr,vx,x,Tnorm)``, mesh_b
``(vr,vx,x,Tnorm)``, ``correct`` branch selector.  ``do_warn`` triggers the
source boundary warnings only (output unchanged).

The operator is deliberately stateless: the source's ``INTERP_FVRVXX_internal``
cache is a deterministic memoisation of the weight matrix, so recomputing it
per call cannot change the result.  Fail-closed on the source's own exception
paths (velocity-space overlap required, x overlap required).
"""
from __future__ import annotations

import numpy as np
from scipy import interpolate

_Q = 1.602177e-19         # elementary charge, coulombs (source constant)
_H_MASS = 1.6726231e-27   # hydrogen mass, kg (source constant)


# ---------------------------------------------------------------------------
# helpers reproduced verbatim from the source package (make_dvr_dvx, locate)
# ---------------------------------------------------------------------------
def _make_dvr_dvx(vr, vx):
    """Reproduce KN1DPy.make_dvr_dvx (velocity-space differential elements)."""
    vr = np.asarray(vr, dtype=float)
    vx = np.asarray(vx, dtype=float)
    nvr = vr.size
    nvx = vx.size

    _vr = np.append(vr, 2 * vr[-1] - vr[-2])
    vr_mid = np.concatenate(([0.0], 0.5 * (_vr + np.roll(_vr, -1))))

    vrR = np.roll(vr_mid, -1)[0:nvr]
    vrL = vr_mid[0:nvr].copy()

    Vr2pidVr = np.pi * (vrR**2 - vrL**2)
    VrVr4pidVr = (4 / 3) * np.pi * (vrR**3 - vrL**3)

    _vx = np.concatenate(([2 * vx[0] - vx[1]], vx, [2 * vx[-1] - vx[-2]]))

    vxR = 0.5 * (np.roll(_vx, -1) + _vx)[1:nvx + 1]
    vxL = 0.5 * (np.roll(_vx, 1) + _vx)[1:nvx + 1]

    dVx = vxR - vxL

    vol = Vr2pidVr[:, np.newaxis] * dVx

    Deltavx = vxR - vxL
    Deltavr = vrR - vrL

    vth_Deltavx = np.zeros((nvr + 2, nvx + 2))
    vx_Deltavx = np.zeros((nvr + 2, nvx + 2))
    vr_Deltavr = np.zeros((nvr + 2, nvx + 2))
    vth_Deltavx[1:nvr + 1, 1:nvx + 1] = 1.0 / Deltavx
    vx_Deltavx[1:nvr + 1, 1:nvx + 1] = vx / Deltavx
    vr_Deltavr[1:nvr + 1, 1:nvx + 1] = vr[:, np.newaxis] / Deltavr[:, np.newaxis]

    vr2vx2 = vr[:, np.newaxis]**2 + vx**2

    jp = np.where(vx > 0)[0]
    jn = np.where(vx < 0)[0]
    jpa = int(jp[0]) if len(jp) > 0 else None
    jpb = int(jp[-1]) if len(jp) > 0 else None
    jna = int(jn[0]) if len(jn) > 0 else None
    jnb = int(jn[-1]) if len(jn) > 0 else None

    return (Vr2pidVr, VrVr4pidVr, dVx, vrL, vrR, vxL, vxR,
            vol, vth_Deltavx, vx_Deltavx, vr_Deltavr, vr2vx2,
            jpa, jpb, jna, jnb)


def _locate(table, value):
    """Reproduce KN1DPy.locate (searchsorted-based index location).

    Returns a scalar int for a scalar ``value`` (matching the source, whose
    ``len(indices) == 1`` branch collapses to a scalar), so that downstream
    scalar arithmetic like ``wxa[k] = ... + ...*f`` stays scalar.
    """
    table = np.asarray(table)
    value = np.atleast_1d(value)
    asc = table[0] <= table[-1]
    if not asc:
        table = table[::-1]
    indices = np.searchsorted(table, value, side='right' if asc else 'left') - 1
    if not asc:
        indices = len(table) - indices - 1
    indices[value < table[0]] = -1
    indices[value >= table[-1]] = len(table) - 1
    if len(indices) == 1:
        indices = indices[0]
    return indices


def _as_1d(arr, name):
    a = np.asarray(arr, dtype=float)
    if a.ndim != 1 or a.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be finite")
    return a


def _as_3d(arr, name, nvr, nvx, nx):
    a = np.asarray(arr, dtype=float)
    if a.ndim != 3 or a.shape != (nvr, nvx, nx):
        raise ValueError(f"{name} must have shape ({nvr},{nvx},{nx})")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be finite")
    return a


def interp_distribution_across_mesh(
    fa,
    vr_a,
    vx_a,
    x_a,
    Tnorm_a,
    vr_b,
    vx_b,
    x_b,
    Tnorm_b,
    correct=1,
    do_warn=None,
):
    """Interpolate a distribution between two phase-space meshes.

    Parameters
    ----------
    fa : (nvra,nvxa,nxa) input distribution on mesh_a.
    vr_a, vx_a, x_a : mesh_a radial/axial velocity and spatial nodes.
    Tnorm_a : mesh_a normalisation temperature (eV).
    vr_b, vx_b, x_b : mesh_b radial/axial velocity and spatial nodes.
    Tnorm_b : mesh_b normalisation temperature (eV).
    correct : 1 to apply the source moment-correction loop (default), 0 to
        return the raw interpolant.
    do_warn : None to skip the source boundary-truncation warnings.

    Returns
    -------
    fb : (nvrb,nvxb,nxb) interpolated distribution on mesh_b.
    """
    vr_a = _as_1d(vr_a, "vr_a")
    vx_a = _as_1d(vx_a, "vx_a")
    x_a = _as_1d(x_a, "x_a")
    vr_b = _as_1d(vr_b, "vr_b")
    vx_b = _as_1d(vx_b, "vx_b")
    x_b = _as_1d(x_b, "x_b")
    Tnorm_a = float(Tnorm_a)
    Tnorm_b = float(Tnorm_b)
    if Tnorm_a <= 0.0 or Tnorm_b <= 0.0 or not np.isfinite(Tnorm_a) or not np.isfinite(Tnorm_b):
        raise ValueError("Tnorm_a and Tnorm_b must be positive and finite")
    for name, a in (("vr_a", vr_a), ("vr_b", vr_b),
                     ("vx_a", vx_a), ("vx_b", vx_b),
                     ("x_a", x_a), ("x_b", x_b)):
        if np.any(np.diff(a) <= 0.0):
            raise ValueError(f"{name} must be strictly increasing")
    # Declared r62 fail-closed narrowing: the saved arm leaves the minimum
    # node count unvalidated; a single-node vx_a raises a raw IndexError in
    # the correction branch (vx[1] access), and a single-node x_a/x_b or
    # vr_a/vr_b can enter _locate / _make_dvr_dvx with undefined semantics.
    # The exact document requires at least 2 nodes per axis; this asset
    # fail-closes with a named ValueError for each case, which is a
    # declared divergence from the saved arm's raw IndexError. The
    # saved-arm divergences are pinned by regression tests.
    for name, a in (("vr_a", vr_a), ("vx_a", vx_a), ("x_a", x_a),
                     ("vr_b", vr_b), ("vx_b", vx_b), ("x_b", x_b)):
        if a.size < 2:
            raise ValueError(f"{name} must have at least two nodes")
    nvra, nvxa, nxa = vr_a.size, vx_a.size, x_a.size
    nvrb, nvxb, nxb = vr_b.size, vx_b.size, x_b.size
    fa = _as_3d(fa, "fa", nvra, nvxa, nxa)

    fV = np.sqrt(Tnorm_b / Tnorm_a)

    #   Overlapping index ranges (source oki/okj/okk)
    oki = np.where((fV * vr_b <= max(vr_a)) & (fV * vr_b >= min(vr_a)))[0]
    if len(oki) < 1:
        raise ValueError('No values of Vrb are within range of Vra')
    i0, i1 = oki[0], oki[-1]

    okj = np.where((fV * vx_b <= max(vx_a)) & (fV * vx_b >= min(vx_a)))[0]
    if okj.size < 1:
        raise ValueError('No values of Vxb are within range of Vxa')
    j0, j1 = okj[0], okj[-1]

    okk = np.where((x_b <= max(x_a)) & (x_b >= min(x_a)))[0]
    if okk.size < 1:
        raise ValueError('No values of Xb are within range of Xa')
    k0, k1 = okk[0], okk[-1]

    fb = np.zeros((nvrb, nvxb, nxb))

    dvr_dvx_a = _make_dvr_dvx(vr_a, vx_a)
    Vr2pidVra, _, dVxa, vraL, vraR, vxaL, vxaR = dvr_dvx_a[:7]
    Vra2Vxa2 = dvr_dvx_a[11]

    dvr_dvx_b = _make_dvr_dvx(vr_b, vx_b)
    (Vr2pidVrb, _, dVxb, vrbL, vrbR, vxbL, vxbR, Vol,
     Vth_DVx, Vx_DVx, Vr_DVr, Vrb2Vxb2, jpa, jpb, jna, jnb) = dvr_dvx_b

    #   Weight matrix (deterministic function of the meshes; the original
    #   source cache only memoises this and cannot change the result)
    _weight = np.zeros((nvrb, nvxb, nvra, nvxa))
    weight = np.zeros((nvrb * nvxb, nvra * nvxa))
    for ib in range(nvrb):
        for jb in range(nvxb):
            for ia in range(nvra):
                vraMin = max([fV * vrbL[ib], vraL[ia]])
                vraMax = min([fV * vrbR[ib], vraR[ia]])
                for ja in range(nvxa):
                    vxaMin = max([fV * vxbL[jb], vxaL[ja]])
                    vxaMax = min([fV * vxbR[jb], vxaR[ja]])
                    if vraMax > vraMin and vxaMax > vxaMin:
                        _weight[ib, jb, ia, ja] = (2 * np.pi * (vraMax**2 - vraMin**2)
                                                   * (vxaMax - vxaMin)
                                                   / (Vr2pidVrb[ib] * dVxb[jb]))
    weight = np.reshape(_weight, weight.shape, order='F')

    #   Transfer onto mesh_b velocity space, evaluated on the mesh_a x grid
    fb_xa = np.zeros((nvrb * nvxb, nxa))
    _fa = np.reshape(fa, (nvra * nvxa, nxa), order='F')
    fb_xa = weight @ _fa

    #   Desired moments of fb on the mesh_a x grid (source _Wxa/_Ea)
    na = np.zeros(nxa)
    _Wxa = np.zeros(nxa)
    _Ea = np.zeros(nxa)
    for k in range(nxa):
        na[k] = np.sum(Vr2pidVra * (fa[:, :, k] @ dVxa))
        if na[k] > 0:
            _Wxa[k] = np.sqrt(Tnorm_a) * np.sum(Vr2pidVra * (fa[:, :, k] @ (vx_a * dVxa))) / na[k]
            _Ea[k] = Tnorm_a * np.sum(Vr2pidVra * ((Vra2Vxa2 * fa[:, :, k]) @ dVxa)) / na[k]

    #   x-interpolation of fb and of the moment targets
    wxa = np.zeros(nxb)
    Ea = np.zeros(nxb)
    for k in range(k0, k1 + 1):
        kL = np.maximum(_locate(x_a, x_b[k]), 0)
        kR = np.minimum(kL + 1, x_a.size - 1)
        kL = np.minimum(kL, kR - 1)

        f = (x_b[k] - x_a[kL]) / (x_a[kR] - x_a[kL])
        fb[:, :, k] = np.reshape((fb_xa[:, kL] + (fb_xa[:, kR] - fb_xa[:, kL]) * f),
                                 fb[:, :, k].shape, order='F')
        wxa[k] = _Wxa[kL] + (_Wxa[kR] - _Wxa[kL]) * f
        Ea[k] = _Ea[kL] + (_Ea[kR] - _Ea[kL]) * f

    #   Moment correction (source correct loop)
    if correct:
        AN = np.zeros((nvrb, nvxb, 2))
        BN = np.zeros((nvrb, nvxb, 2))
        sgn = np.array([1, -1])

        for k in range(nxb):
            allow_neg = 0
            nb = np.sum(Vr2pidVrb * (fb[:, :, k] @ dVxb))
            if nb > 0:
                goto_correct = True
                while goto_correct:
                    goto_correct = False
                    nb = np.sum(Vr2pidVrb * (fb[:, :, k] @ dVxb))
                    Wxb = np.sqrt(Tnorm_b) * np.sum(Vr2pidVrb * (fb[:, :, k] @ (vx_b * dVxb))) / nb
                    Eb = Tnorm_b * np.sum(Vr2pidVrb * ((Vrb2Vxb2 * fb[:, :, k]) @ dVxb)) / nb

                    Nij = np.zeros((nvrb + 2, nvxb + 2))
                    Nij[1:nvrb + 1, 1:nvxb + 1] = fb[:, :, k] * Vol / nb

                    cutoff = 1.0e-6 * np.max(Nij)
                    ii = np.where((abs(Nij) < cutoff) & (abs(Nij) > 0))
                    if ii[0].size > 0:
                        Nij[ii] = 0.0

                    if max(Nij[2, :]) <= 0:
                        allow_neg = 1

                    Nijp1_vx_Dvx = np.roll(Nij * Vx_DVx, shift=-1, axis=1)
                    Nij_vx_Dvx = Nij * Vx_DVx
                    Nijm1_vx_Dvx = np.roll(Nij * Vx_DVx, shift=1, axis=1)
                    Nip1j_vr_Dvr = np.roll(Nij * Vr_DVr, shift=-1, axis=0)
                    Nij_vr_Dvr = Nij * Vr_DVr
                    Nim1j_vr_Dvr = np.roll(Nij * Vr_DVr, shift=1, axis=0)

                    _AN = np.roll(Nij * Vth_DVx, shift=1, axis=1) - Nij * Vth_DVx
                    AN[:, :, 0] = _AN[1:nvrb + 1, 1:nvxb + 1]

                    _AN = -np.roll(Nij * Vth_DVx, shift=-1, axis=1) + Nij * Vth_DVx
                    AN[:, :, 1] = _AN[1:nvrb + 1, 1:nvxb + 1]

                    BN[:, jpa + 1:jpb + 1, 0] = (Nijm1_vx_Dvx[1:nvrb + 1, jpa + 2:jpb + 2]
                                                - Nij_vx_Dvx[1:nvrb + 1, jpa + 2:jpb + 2])
                    BN[:, jpa, 0] = -Nij_vx_Dvx[1:nvrb + 1, jpa + 1]
                    BN[:, jnb, 0] = Nij_vx_Dvx[1:nvrb + 1, jnb + 1]
                    BN[:, jna:jnb, 0] = (-Nijp1_vx_Dvx[1:nvrb + 1, jna + 1:jnb + 1]
                                         + Nij_vx_Dvx[1:nvrb + 1, jna + 1:jnb + 1])
                    BN[:, :, 0] = (BN[:, :, 0]
                                   + Nim1j_vr_Dvr[1:nvrb + 1, 1:nvxb + 1]
                                   - Nij_vr_Dvr[1:nvrb + 1, 1:nvxb + 1])

                    BN[:, jpa + 1:jpb + 1, 1] = (-Nijp1_vx_Dvx[1:nvrb + 1, jpa + 2:jpb + 2]
                                                 + Nij_vx_Dvx[1:nvrb + 1, jpa + 2:jpb + 2])
                    BN[:, jpa, 1] = -Nijp1_vx_Dvx[1:nvrb + 1, jpa + 1]
                    BN[:, jnb, 1] = Nijm1_vx_Dvx[1:nvrb + 1, jnb + 1]
                    BN[:, jna:jnb, 1] = (Nijm1_vx_Dvx[1:nvrb + 1, jna + 1:jnb + 1]
                                         - Nij_vx_Dvx[1:nvrb + 1, jna + 1:jnb + 1])
                    BN[1:nvrb, :, 1] = (BN[1:nvrb, :, 1]
                                        - Nip1j_vr_Dvr[2:nvrb + 1, 1:nvxb + 1]
                                        + Nij_vr_Dvr[2:nvrb + 1, 1:nvxb + 1])
                    BN[0, :, 1] = BN[0, :, 1] - Nip1j_vr_Dvr[1, 1:nvxb + 1]

                    if allow_neg:
                        BN[0, :, 1] = BN[0, :, 1] - Nij_vr_Dvr[1, 1:nvxb + 1]
                        BN[1, :, 1] = BN[1, :, 1] + Nij_vr_Dvr[1, 1:nvxb + 1]

                    Nij = Nij[1:nvrb + 1, 1:nvxb + 1]

                    TB1 = np.zeros(2, float)
                    TB2 = np.zeros(2, float)

                    for ia in range(2):
                        TA1 = np.sqrt(Tnorm_b) * np.sum((AN[:, :, ia] @ vx_b))
                        TA2 = Tnorm_b * np.sum(Vrb2Vxb2 * AN[:, :, ia])
                        for ib in range(2):
                            if TB1[ib] == 0:
                                TB1[ib] = np.sqrt(Tnorm_b) * np.sum((BN[:, :, ib] @ vx_b))
                            if TB2[ib] == 0:
                                TB2[ib] = Tnorm_b * np.sum(Vrb2Vxb2 * BN[:, :, ib])

                            denom = TA2 * TB1[ib] - TA1 * TB2[ib]
                            beta = 0
                            alpha = 0

                            if (denom != 0) and (TA1 != 0):
                                beta = (TA2 * (wxa[k] - Wxb) - TA1 * (Ea[k] - Eb)) / denom
                                alpha = (wxa[k] - Wxb - TB1[ib] * beta) / TA1

                            do_break = ((alpha * sgn[ia]) > 0) and ((beta * sgn[ib]) > 0)
                            if do_break:
                                break
                        if do_break:
                            break

                    RHS = AN[:, :, ia] * alpha + BN[:, :, ib] * beta

                    s = 1
                    if not allow_neg:
                        ii = np.nonzero(Nij)
                        if np.size(ii) > 0:
                            s = min(1 / np.max(-RHS[ii] / Nij[ii]), 1)

                    fb[:, :, k] = nb * (Nij + s * RHS) / Vol
                    goto_correct = (s < 1)

    #   Boundary warnings (source do_warn block; output unchanged)
    if do_warn is not None:
        from warnings import warn
        big = np.max(fb)
        if (i0 > 0) or (i1 < nvrb - 1):
            for k in range(k0, k1 + 1):
                for j in range(j0, j1 + 1):
                    if (i0 > 0) and (fb[i0, j, k] > do_warn * big):
                        warn('Non-zero value of fb detected at min(Vra) boundary')
                    if (i1 < nvrb - 1) and (fb[i1, j, k] > do_warn * big):
                        warn('Non-zero value of fb detected at max(Vra) boundary')
        if (j0 > 0) or (j1 < nvxb - 1):
            for k in range(k0, k1 + 1):
                for i in range(i0, i1 + 1):
                    if (j0 > 0) and (fb[i, j0, k] > do_warn * big):
                        warn('Non-zero value of fb detected at min(Vxa) boundary')
                    if (j1 < nvxb - 1) and (fb[i, j1, k] > do_warn * big):
                        warn('Non-zero value of fb detected at max(Vxa) boundary')
        if (k0 > 0) or (k1 < nxb - 1):
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    if (k0 > 0) and (fb[i, j, k0] > do_warn * big):
                        warn('Non-zero value of fb detected at min(Xa) boundary')
                    if (k1 < nxb - 1) and (fb[i, j, k1] > do_warn * big):
                        warn('Non-zero value of fb detected at max(Xa) boundary')

    #   Density rescale (source rescale block)
    tot_a = np.zeros(nxa)
    for k in range(nxa):
        tot_a[k] = np.sum(Vr2pidVra * (fa[:, :, k] @ dVxa))
    tot_b = np.zeros(nxb)
    tot_b[k0:k1 + 1] = interpolate.interp1d(x_a, tot_a, fill_value="extrapolate")(x_b[k0:k1 + 1])
    ii = np.where(fb > 0)
    if ii[0].size > 0:
        min_tot = np.min(np.array(fb[ii]))
        for k in range(k0, k1 + 1):
            tot = np.sum(Vr2pidVrb * (fb[:, :, k] @ dVxb))
            if tot > min_tot:
                fb[:, :, k] = fb[:, :, k] * tot_b[k] / tot

    if not np.all(np.isfinite(fb)):
        raise ValueError("fb must be finite")
    return fb




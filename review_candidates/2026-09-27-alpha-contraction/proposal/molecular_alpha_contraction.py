"""Source-free molecular collision-frequency contraction (Alpha three-family).

Reproduces the ``SIG ? f -> Alpha`` contraction of KN1DPy ``kinetic_h2.py``
for the molecular three-family Alpha collision frequencies:

- ``Alpha_CX``   : H2 + H2+ charge exchange, ``Alpha_CX[:,:,k]   = F^{-1}(SIG_CX   @ F(fHp_hat*nHP))``
- ``Alpha_H2_H`` : H2-H    elastic,          ``Alpha_H2_H[:,:,k] = F^{-1}(SIG_H2_H @ F(fH))``
- ``Alpha_H2_P`` : H2-H+   elastic,          ``Alpha_H2_P[:,:,k] = F^{-1}(SIG_H2_P @ F(fi_hat*ni))``

``F`` / ``F^{-1}`` are the source legacy Fortran-order flatten/restore:
``Work[:] = src[:,:,k].reshape(Work.shape, order='F')`` and
``out[:,:,k] = (...).reshape(out[:,:,k].shape, order='F')``
(kinetic_h2.py:1136-1137, 1203-1204, 1225-1226).  The operator is
self-contained and takes the already-assembled ``SIG_*`` matrices
(N3-1/N3-2 / ``operators/分子氢碰撞矩阵组装``) plus explicit predecessor
distributions.  Bounded negative cells inherited from the signed elastic SIG
families are reproduced as-is, never clamped.

Source-exact density handling (kinetic_h2.py:1221-1223): ``ni = n`` and, when
``ni_correct`` is set, ``ni = np.maximum((n - nHP), 0)``.  ``Alpha_CX`` uses
``fHp_hat[:,:,k]*nHP[k]`` (kinetic_h2.py:1203) -- the H2+ Maxwellian seeded
with the molecular-ion temperature ``THP`` and scaled by the H2+ density.

KNOWN SOURCE DEFECT (registered for expert review): kinetic_h2.py:1204 writes
``Alpha_CX[:,:,k] = SIG_CX @ Work`` with no Fortran-order reshape, which
crashes on the canonical ``nvr*nvx != nvx`` carrier.  This operator reproduces
the intended (reshape-fixed) contraction, matching the disposable workcopy
probe that applied the minimal ``.reshape(Alpha_CX[:,:,k].shape, order='F')``
fix to walk the source through the probe run.  The defect is preserved
verbatim in the immutable source and flagged in ``operator.md`` expert review.
"""
from __future__ import annotations

import numpy as np


def contract_molecular_hydrogen_alpha_frequencies(
    SIG_CX, SIG_H2_H, SIG_H2_P, fH, fHp_hat, fi_hat, n, nHP, ni_correct=False
):
    """Contract the molecular three-family SIG matrices to Alpha frequencies.

    Parameters
    ----------
    SIG_CX : (N, N) array, H2 + H2+ charge-exchange collision matrix.
    SIG_H2_H : (N, N) array, H2-H elastic collision matrix.
    SIG_H2_P : (N, N) array, H2-H+ elastic collision matrix.
    fH : (nvr, nvx, nx) array, atomic-H neutral velocity distribution.
    fHp_hat : (nvr, nvx, nx) array, H2+ molecular-ion Maxwellian seed
        (drift vxi, temperature THP).
    fi_hat : (nvr, nvx, nx) array, H+ proton Maxwellian seed
        (drift vxi, temperature Ti).
    n : (nx,) array, electron density profile (source ``mesh.ne``), used as the
        ion density ``ni`` unless ``ni_correct`` is set.
    nHP : (nx,) array, H2+ molecular-ion density profile (m^-3).
    ni_correct : bool, if True use ``ni = maximum((n - nHP), 0)`` instead of
        ``ni = n`` (kinetic_h2.py:1222-1223).

    Returns
    -------
    dict with ``Alpha_CX``, ``Alpha_H2_H``, ``Alpha_H2_P``, each
    ``(nvr, nvx, nx)``.
    """
    SIG_CX = np.asarray(SIG_CX, dtype=float)
    SIG_H2_H = np.asarray(SIG_H2_H, dtype=float)
    SIG_H2_P = np.asarray(SIG_H2_P, dtype=float)
    fH = np.asarray(fH, dtype=float)
    fHp_hat = np.asarray(fHp_hat, dtype=float)
    fi_hat = np.asarray(fi_hat, dtype=float)
    n = np.asarray(n, dtype=float)
    nHP = np.asarray(nHP, dtype=float)

    nvr, nvx, nx = fH.shape
    if SIG_CX.ndim != 2 or SIG_CX.shape[0] != SIG_CX.shape[1]:
        raise ValueError("invalid SIG_CX: expected 2-D square matrix")
    nsig = SIG_CX.shape[0]
    if nsig != nvr * nvx:
        raise ValueError("invalid SIG_CX dimension for velocity-space carrier")
    for name, sig in (("SIG_H2_H", SIG_H2_H), ("SIG_H2_P", SIG_H2_P)):
        if sig.ndim != 2 or sig.shape != (nsig, nsig):
            raise ValueError(f"invalid {name}: expected ({nsig}, {nsig}) matrix")
    if n.ndim != 1 or n.size != nx:
        raise ValueError("invalid n: expected (nx,) electron density")
    if nHP.ndim != 1 or nHP.size != nx:
        raise ValueError("invalid nHP: expected (nx,) H2+ density")
    if fHp_hat.shape != (nvr, nvx, nx) or fi_hat.shape != (nvr, nvx, nx):
        raise ValueError("invalid fHp_hat/fi_hat: expected (nvr, nvx, nx)")
    for name, arr in (("SIG_CX", SIG_CX), ("SIG_H2_H", SIG_H2_H),
                      ("SIG_H2_P", SIG_H2_P), ("fH", fH),
                      ("fHp_hat", fHp_hat), ("fi_hat", fi_hat),
                      ("n", n), ("nHP", nHP)):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} contains a non-finite value")

    # Source-exact ion density (kinetic_h2.py:1221-1223).
    ni = n
    if ni_correct:
        ni = np.maximum((n - nHP), 0)

    Alpha_CX = np.zeros((nvr, nvx, nx))
    Alpha_H2_H = np.zeros((nvr, nvx, nx))
    Alpha_H2_P = np.zeros((nvr, nvx, nx))
    Work = np.zeros((nsig,))

    for k in range(nx):
        # Alpha_CX (source kinetic_h2.py:1203-1204, Option A, reshape-fixed)
        Work[:] = (fHp_hat[:, :, k] * nHP[k]).reshape(Work.shape, order="F")
        Alpha_CX[:, :, k] = (SIG_CX @ Work).reshape(Alpha_CX[:, :, k].shape, order="F")

        # Alpha_H2_H (source kinetic_h2.py:1136-1137)
        Work[:] = fH[:, :, k].reshape(Work.shape, order="F")
        Alpha_H2_H[:, :, k] = (SIG_H2_H @ Work).reshape(Alpha_H2_H[:, :, k].shape, order="F")

        # Alpha_H2_P (source kinetic_h2.py:1225-1226)
        Work[:] = (fi_hat[:, :, k] * ni[k]).reshape(Work.shape, order="F")
        Alpha_H2_P[:, :, k] = (SIG_H2_P @ Work).reshape(Alpha_H2_P[:, :, k].shape, order="F")

    for name, arr in (("Alpha_CX", Alpha_CX), ("Alpha_H2_H", Alpha_H2_H),
                      ("Alpha_H2_P", Alpha_H2_P)):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} contraction produced a non-finite array")

    return {
        "Alpha_CX": Alpha_CX,
        "Alpha_H2_H": Alpha_H2_H,
        "Alpha_H2_P": Alpha_H2_P,
    }



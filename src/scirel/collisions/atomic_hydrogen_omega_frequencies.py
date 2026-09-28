"""Source-free atomic elastic-frequency aggregation (Omega family).

Reproduces the Omega_* elastic-collision aggregation of KN1DPy ``kinetic_h.py``
(moment block, kinetic_h.py:1116-1188):

- ``VxH[k]``       : H x-flow velocity,      ``Vth * sum(Vr2pidVr * (fH[:,:,k] @ (vx*dVx))) / nH[k]``
- ``Omega_H_P[k]`` : H-H+ elastic,           ``sum(Vr2pidVr * ((Alpha_H_P[:,:,k]*fH[:,:,k]) @ dVx)) / (nH[k]*DeltaVx)``
- ``Omega_H_H2[k]``: H-H2 elastic,           ``sum(Vr2pidVr * ((Alpha_H_H2[:,:,k]*fH[:,:,k]) @ dVx)) / (nH[k]*DeltaVx)``
- ``Omega_H_H[k]`` : H-H  elastic,           ``sum(Vr2pidVr * ((Alpha_H_H*fH[:,:,k]) @ dVx)) / (nH[k]*Wpp)``
- ``Omega_EL``     : ``Omega_H_P + Omega_H_H2 + Omega_H_H``
- ``Wperp_paraH``  : perpendicular 2nd moment feeding ``Wpp`` (dual-branch, see below)

The ``DeltaVx`` clamp is ``MagDeltaVx = max(|DeltaVx|, DeltaVx_tol)`` then
``DeltaVx = sign(DeltaVx)*MagDeltaVx`` with the legacy symbolic ``sign``
(``int(x>0)-int(x<0)``).  Omega_H_P uses ``vxi``, Omega_H_H2 uses ``vxH2``.
``Wpp = sign(Wpp)*max(|Wpp|, Wpp_tol)``.  All three Omega families are then
clamped ``max(Omega_*, 0)`` — source semantics preserved, outputs are
non-negative by construction.

``Wperp_paraH`` dual branch (kinetic_h.py:1159-1167): when
``np.sum(MH_H_sum) <= 0`` the vr2 projection is integrated directly
``vr2_2vx_ran2[i,:] = vr[i]**2 - 2*(vx - VxH[k]/Vth)**2``;  otherwise
``-sum(Vr2pidVr*((vr2_2vx2_2D*(MH_H_sum[:,:,k]-fH[:,:,k])) @ dVx))/nH[k]``.
Both branches are reproduced verbatim.

Omega_H_H inline re-contraction: inside the H_H_EL block the source recomputes
``Alpha_H_H`` from ``SIG_H_H @ F(fH[:,:,k])`` with the branch-time ``fH``
(kinetic_h.py:1174-1175), identical to the N334 contraction.  The operator
repeats the Fortran-order flatten/restore exactly.
"""
from __future__ import annotations

import numpy as np

__all__ = ["assemble_atomic_hydrogen_omega_frequencies"]


def _sign_symbolic(x):
    """Legacy KN1DPy ``sign`` (kinetic_h.py util): 1 positive, -1 negative, 0 zero."""
    return int(x > 0) - int(x < 0)


def assemble_atomic_hydrogen_omega_frequencies(
    fH,
    nH,
    Alpha_H_P,
    Alpha_H_H2,
    SIG_H_H,
    Vr2pidVr,
    dVx,
    vr,
    vx,
    Vth,
    vxi,
    vxH2,
    MH_H_sum,
    vr2_2vx2_2D,
    DeltaVx_tol=0.01,
    Wpp_tol=0.001,
    H_P_EL=True,
    H_H2_EL=True,
    H_H_EL=True,
):
    """Assemble the atomic H elastic-frequencies Omega family.

    Parameters
    ----------
    fH : (nvr, nvx, nx) array, atomic neutral H velocity distribution at branch time.
    nH : (nx,) array, atomic H density per cell.
    Alpha_H_P : (nvr, nvx, nx) array, H-H+ elastic Alpha frequencies (N334 output).
    Alpha_H_H2 : (nvr, nvx, nx) array, H-H2 elastic Alpha frequencies (N334 output).
    SIG_H_H : (N, N) array, H-H elastic collision matrix (N4-1 output).
    Vr2pidVr : (nvr,) array, cylindrical radial velocity-space weights.
    dVx : (nvx,) array, vx mesh spacing.
    vr : (nvr,) array, radial-vr mesh.
    vx : (nvx,) array, vx mesh.
    Vth : float, H thermal speed (m/s).
    vxi : (nx,) array, ion flow velocity at each cell (m/s).
    vxH2 : (nx,) array, molecular H2 flow velocity (m/s).
    MH_H_sum : (nvr, nvx, nx) array, accumulated H-H elastic moment at branch time.
    vr2_2vx2_2D : (nvr, nvx) array, vr^2 - 2*vx^2 projection kernel.
    DeltaVx_tol : float, floor for |DeltaVx|/Vth (default source value 0.01).
    Wpp_tol : float, floor for |Wpp| (default source value 0.001).
    H_P_EL, H_H2_EL, H_H_EL : bool, enable flags.

    Returns
    -------
    dict with ``VxH``, ``Omega_H_P``, ``Omega_H_H2``, ``Omega_H_H``,
    ``Omega_EL``, ``Wperp_paraH``, each ``(nx,)``.
    """
    fH = np.asarray(fH, dtype=float)
    nH = np.asarray(nH, dtype=float)
    Alpha_H_P = np.asarray(Alpha_H_P, dtype=float)
    Alpha_H_H2 = np.asarray(Alpha_H_H2, dtype=float)
    SIG_H_H = np.asarray(SIG_H_H, dtype=float)
    Vr2pidVr = np.asarray(Vr2pidVr, dtype=float)
    dVx = np.asarray(dVx, dtype=float)
    vr = np.asarray(vr, dtype=float)
    vx = np.asarray(vx, dtype=float)
    vxi = np.asarray(vxi, dtype=float)
    vxH2 = np.asarray(vxH2, dtype=float)
    MH_H_sum = np.asarray(MH_H_sum, dtype=float)
    vr2_2vx2_2D = np.asarray(vr2_2vx2_2D, dtype=float)

    if fH.ndim != 3 or any(size == 0 for size in fH.shape):
        raise ValueError("invalid fH: expected nonempty 3-D (nvr, nvx, nx) carrier")
    nvr, nvx, nx = fH.shape
    if SIG_H_H.ndim != 2 or SIG_H_H.shape[0] != SIG_H_H.shape[1]:
        raise ValueError("invalid SIG_H_H: expected 2-D square matrix")
    nsig = SIG_H_H.shape[0]
    if nsig != nvr * nvx:
        raise ValueError("invalid SIG_H_H dimension for velocity-space carrier")
    if nH.ndim != 1 or nH.size != nx:
        raise ValueError("invalid nH: expected (nx,) H density")
    if vxi.shape != (nx,) or vxH2.shape != (nx,):
        raise ValueError("invalid vxi/vxH2: expected (nx,) velocities")
    for name, arr in (("Alpha_H_P", Alpha_H_P), ("Alpha_H_H2", Alpha_H_H2),
                      ("MH_H_sum", MH_H_sum)):
        if arr.ndim != 3 or arr.shape != (nvr, nvx, nx):
            raise ValueError(f"invalid {name}: expected (nvr, nvx, nx)")
    for name, arr, size in (("Vr2pidVr", Vr2pidVr, nvr), ("dVx", dVx, nvx),
                            ("vr", vr, nvr), ("vx", vx, nvx)):
        if arr.ndim != 1 or arr.size != size:
            raise ValueError(f"invalid {name}: expected 1-D axis of length {size}")
    if vr2_2vx2_2D.ndim != 2 or vr2_2vx2_2D.shape != (nvr, nvx):
        raise ValueError("invalid vr2_2vx2_2D: expected (nvr, nvx) kernel")
    for name, arr in (("fH", fH), ("nH", nH), ("Alpha_H_P", Alpha_H_P),
                      ("Alpha_H_H2", Alpha_H_H2), ("SIG_H_H", SIG_H_H),
                      ("Vr2pidVr", Vr2pidVr), ("dVx", dVx), ("vr", vr),
                      ("vx", vx), ("vxi", vxi), ("vxH2", vxH2),
                      ("MH_H_sum", MH_H_sum), ("vr2_2vx2_2D", vr2_2vx2_2D)):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} contains a non-finite value")
    for name, value in (("Vth", Vth), ("DeltaVx_tol", DeltaVx_tol), ("Wpp_tol", Wpp_tol)):
        scalar = np.asarray(value)
        if scalar.ndim != 0 or scalar.dtype.kind not in "iuf" or not np.isfinite(scalar) or float(scalar) <= 0.0:
            raise ValueError(f"{name} must be a finite positive real scalar")
    Vth = float(Vth)
    DeltaVx_tol = float(DeltaVx_tol)
    Wpp_tol = float(Wpp_tol)
    if np.any(nH <= 0.0) and (H_P_EL or H_H2_EL or H_H_EL):
        # source gates the whole Omega block on np.argwhere(nH <= 0).size <= 0
        raise ValueError("nH must be positive where elastic frequencies are assembled")

    VxH = np.zeros(nx)
    Omega_H_P = np.zeros(nx)
    Omega_H_H2 = np.zeros(nx)
    Omega_H_H = np.zeros(nx)
    Wperp_paraH = np.zeros(nx)
    vr2_2vx_ran2 = np.zeros((nvr, nvx))

    if H_P_EL or H_H2_EL or H_H_EL:
        for k in range(nx):
            VxH[k] = Vth * np.sum(Vr2pidVr * (fH[:, :, k] @ (vx * dVx))) / nH[k]

    if H_P_EL:
        for k in range(nx):
            DeltaVx = (VxH[k] - vxi[k]) / Vth
            MagDeltaVx = np.maximum(abs(DeltaVx), DeltaVx_tol)
            DeltaVx = _sign_symbolic(DeltaVx) * MagDeltaVx
            if not np.isfinite(DeltaVx) or DeltaVx == 0.0:
                raise ValueError("zero velocity difference in Omega_H_P")
            Omega_H_P[k] = np.sum(
                Vr2pidVr * ((Alpha_H_P[:, :, k] * fH[:, :, k]) @ dVx)
            ) / (nH[k] * DeltaVx)
        Omega_H_P = np.maximum(Omega_H_P, 0)

    if H_H2_EL:
        for k in range(nx):
            DeltaVx = (VxH[k] - vxH2[k]) / Vth
            MagDeltaVx = np.maximum(abs(DeltaVx), DeltaVx_tol)
            DeltaVx = _sign_symbolic(DeltaVx) * MagDeltaVx
            if not np.isfinite(DeltaVx) or DeltaVx == 0.0:
                raise ValueError("zero velocity difference in Omega_H_H2")
            Omega_H_H2[k] = np.sum(
                Vr2pidVr * ((Alpha_H_H2[:, :, k] * fH[:, :, k]) @ dVx)
            ) / (nH[k] * DeltaVx)
        Omega_H_H2 = np.maximum(Omega_H_H2, 0)

    if H_H_EL:
        if np.sum(MH_H_sum) <= 0:
            # vr2 projection branch (direct)
            for k in range(nx):
                VxHk = Vth * np.sum(Vr2pidVr * (fH[:, :, k] @ (vx * dVx))) / nH[k]
                for i in range(nvr):
                    vr2_2vx_ran2[i, :] = vr[i] ** 2 - 2 * ((vx - (VxHk / Vth)) ** 2)
                Wperp_paraH[k] = np.sum(
                    Vr2pidVr * ((vr2_2vx_ran2 * fH[:, :, k]) @ dVx)
                ) / nH[k]
        else:
            # accumulated elastic-moment branch
            for k in range(nx):
                M_fH = MH_H_sum[:, :, k] - fH[:, :, k]
                Wperp_paraH[k] = -np.sum(
                    Vr2pidVr * ((vr2_2vx2_2D * M_fH) @ dVx)
                ) / nH[k]
        for k in range(nx):
            Work = fH[:, :, k].reshape((nsig,), order="F")
            # The source writes into its preallocated C-order Alpha buffer;
            # retain that carrier layout before the weighted reduction.
            Alpha_H_H = np.array(
                (SIG_H_H @ Work).reshape((nvr, nvx), order="F"),
                order="C",
                copy=True,
            )
            Wpp = Wperp_paraH[k]
            MagWpp = np.maximum(np.abs(Wpp), Wpp_tol)
            Wpp = _sign_symbolic(Wpp) * MagWpp
            if not np.isfinite(Wpp) or Wpp == 0.0:
                raise ValueError("zero perpendicular moment in Omega_H_H")
            Omega_H_H[k] = np.sum(
                Vr2pidVr * ((Alpha_H_H * Work.reshape((nvr, nvx), order="F")) @ dVx)
            ) / (nH[k] * Wpp)
        Omega_H_H = np.maximum(Omega_H_H, 0)

    Omega_EL = Omega_H_P + Omega_H_H2 + Omega_H_H

    result = {
        "VxH": VxH,
        "Omega_H_P": Omega_H_P,
        "Omega_H_H2": Omega_H_H2,
        "Omega_H_H": Omega_H_H,
        "Omega_EL": Omega_EL,
        "Wperp_paraH": Wperp_paraH,
    }
    if any(not np.all(np.isfinite(value)) for value in result.values()):
        raise ValueError("Omega assembly produced a non-finite result")
    return result

"""Source-free molecular H2 elastic-frequency aggregation (Omega_H2 family).

Reproduces the Omega_H2_* elastic-collision aggregation of KN1DPy
``kinetic_h2.py`` (kinetic_h2.py:1232-1296):

- ``VxH2[k]``         : H2 x-flow velocity, ``Vth * sum(Vr2pidVr*(fH2[:,:,k] @ (vx*dVx))) / nH2[k]``
- ``Omega_H2_P[k]``   : H2-H+ elastic, ``sum(Vr2pidVr*((Alpha_H2_P[:,:,k]*fH2[:,:,k]) @ dVx)) / (nH2[k]*DeltaVx)``
- ``Omega_H2_H[k]``   : H2-H  elastic, ``sum(Vr2pidVr*((Alpha_H2_H[:,:,k]*fH2[:,:,k]) @ dVx) / (nH2[k]*DeltaVx))``
- ``Omega_H2_H2[k]``  : H2-H2 elastic, ``sum(Vr2pidVr*((Alpha_H2_H2*Work) @ dVx)) / (nH2[k]*Wpp)``
- ``Omega_EL``        : ``Omega_H2_P + Omega_H2_H + Omega_H2_H2``
- ``Wperp_paraH2``    : perpendicular 2nd moment feeding ``Wpp`` (dual-branch, see below)

The ``DeltaVx`` clamp is ``MagDeltaVx = max(|DeltaVx|, DeltaVx_tol)`` then
``DeltaVx = sign(DeltaVx)*MagDeltaVx`` with the legacy symbolic ``sign``
(``int(x>0)-int(x<0)``).  Omega_H2_P uses ``vxi`` (ion drift),
Omega_H2_H uses ``VxH`` (atomic-H flow velocity, kinetic_h2.py:1267),
Omega_H2_H2 uses ``Wperp_paraH2`` clamped to ``Wpp``.  All three Omega
families are then clamped ``max(Omega_*, 0)`` (kinetic_h2.py:1258,1271,1297).

Source-exact operator ordering: the Omega_H2_P denominator ``(nH2[k]*DeltaVx)``
divides OUTSIDE the ``np.sum`` (kinetic_h2.py:1257) while the Omega_H2_H
denominator divides INSIDE (kinetic_h2.py:1270) -- preserved verbatim for
bit-identical reproduction (both are scalar divisions but the summation
order differs in floating point).

``Wperp_paraH2`` dual branch (kinetic_h2.py:1279-1287): when
``np.sum(MH2_H2_sum) < 0`` the vr2 projection is integrated directly
``vr2_2vx_ran2[i,:] = vr[i]**2 - 2*(vx - VxH2[k]/Vth)**2``;  otherwise
``M_fH2 = MH2_H2_sum[:,:,k] - fH2[:,:,k]`` then
``-sum(Vr2pidVr*((vr2_2vx2_2D*M_fH2) @ dVx))/nH2[k]``.
Both branches are reproduced verbatim.  NOTE the branch test is
``< 0`` (NOT ``<= 0`` as in the atomic kinetic_h.py) so a zero
accumulator takes the else (M_fH2) path -- the path exercised by the
registered N360 probe evidence.

Omega_H2_H2 inline re-contraction: inside the H2_H2_EL block the source
recomputes ``Alpha_H2_H2`` from ``SIG_H2_H2 @ F(fH2[:,:,k])`` with the
branch-time ``fH2`` (kinetic_h2.py:1290-1291).  The operator repeats the
Fortran-order flatten/restore exactly.
"""
from __future__ import annotations

import numpy as np

__all__ = ["assemble_molecular_hydrogen_omega_frequencies"]


def _sign_symbolic(x):
    """Legacy KN1DPy ``sign`` (kinetic_h2.py util): 1 positive, -1 negative, 0 zero."""
    return int(x > 0) - int(x < 0)


def assemble_molecular_hydrogen_omega_frequencies(
    fH2,
    nH2,
    Alpha_H2_P,
    Alpha_H2_H,
    SIG_H2_H2,
    Vr2pidVr,
    dVx,
    vr,
    vx,
    Vth,
    vxi,
    VxH,
    MH2_H2_sum,
    vr2_2vx2_2D,
    DeltaVx_tol=0.01,
    Wpp_tol=0.001,
    H2_P_EL=True,
    H2_H_EL=True,
    H2_H2_EL=True,
):
    """Assemble the molecular H2 elastic-frequencies Omega family.

    Parameters
    ----------
    fH2 : (nvr, nvx, nx) array, molecular neutral H2 distribution at branch time.
    nH2 : (nx,) array, molecular H2 density per cell.
    Alpha_H2_P : (nvr, nvx, nx) array, H2-H+ elastic Alpha frequencies (molecular N3-3 output).
    Alpha_H2_H : (nvr, nvx, nx) array, H2-H elastic Alpha frequencies (molecular N3-3 output).
    SIG_H2_H2 : (N, N) array, H2-H2 elastic collision matrix (molecular N3-1/N3-2 output).
    Vr2pidVr : (nvr,) array, cylindrical radial velocity-space weights.
    dVx : (nvx,) array, vx mesh spacing.
    vr : (nvr,) array, radial-vr mesh.
    vx : (nvx,) array, vx mesh.
    Vth : float, H2 thermal speed (m/s).
    vxi : (nx,) array, ion flow velocity at each cell (m/s).
    VxH : (nx,) array, atomic-H flow velocity at each cell (m/s).
    MH2_H2_sum : (nvr, nvx, nx) array, accumulated H2-H2 elastic moment at branch time.
    vr2_2vx2_2D : (nvr, nvx) array, vr^2 - 2*vx^2 projection kernel.
    DeltaVx_tol : float, floor for |DeltaVx|/Vth (default source value 0.01).
    Wpp_tol : float, floor for |Wpp| (default source value 0.001).
    H2_P_EL, H2_H_EL, H2_H2_EL : bool, enable flags.

    Returns
    -------
    dict with ``VxH2``, ``Omega_H2_P``, ``Omega_H2_H``, ``Omega_H2_H2``,
    ``Omega_EL``, ``Wperp_paraH2``, each ``(nx,)``.
    """
    fH2 = np.asarray(fH2, dtype=float)
    nH2 = np.asarray(nH2, dtype=float)
    Alpha_H2_P = np.asarray(Alpha_H2_P, dtype=float)
    Alpha_H2_H = np.asarray(Alpha_H2_H, dtype=float)
    SIG_H2_H2 = np.asarray(SIG_H2_H2, dtype=float)
    Vr2pidVr = np.asarray(Vr2pidVr, dtype=float)
    dVx = np.asarray(dVx, dtype=float)
    vr = np.asarray(vr, dtype=float)
    vx = np.asarray(vx, dtype=float)
    vxi = np.asarray(vxi, dtype=float)
    VxH = np.asarray(VxH, dtype=float)
    MH2_H2_sum = np.asarray(MH2_H2_sum, dtype=float)
    vr2_2vx2_2D = np.asarray(vr2_2vx2_2D, dtype=float)

    if fH2.ndim != 3 or any(size == 0 for size in fH2.shape):
        raise ValueError("invalid fH2: expected nonempty 3-D (nvr, nvx, nx) carrier")
    nvr, nvx, nx = fH2.shape
    if SIG_H2_H2.ndim != 2 or SIG_H2_H2.shape[0] != SIG_H2_H2.shape[1]:
        raise ValueError("invalid SIG_H2_H2: expected 2-D square matrix")
    nsig = SIG_H2_H2.shape[0]
    if nsig != nvr * nvx:
        raise ValueError("invalid SIG_H2_H2 dimension for velocity-space carrier")
    if nH2.ndim != 1 or nH2.size != nx:
        raise ValueError("invalid nH2: expected (nx,) H2 density")
    if vxi.shape != (nx,) or VxH.shape != (nx,):
        raise ValueError("invalid vxi/VxH: expected (nx,) velocities")
    for name, arr in (("Alpha_H2_P", Alpha_H2_P), ("Alpha_H2_H", Alpha_H2_H),
                      ("MH2_H2_sum", MH2_H2_sum)):
        if arr.ndim != 3 or arr.shape != (nvr, nvx, nx):
            raise ValueError(f"invalid {name}: expected (nvr, nvx, nx)")
    for name, arr, size in (("Vr2pidVr", Vr2pidVr, nvr), ("dVx", dVx, nvx),
                            ("vr", vr, nvr), ("vx", vx, nvx)):
        if arr.ndim != 1 or arr.size != size:
            raise ValueError(f"invalid {name}: expected 1-D axis of length {size}")
    if vr2_2vx2_2D.ndim != 2 or vr2_2vx2_2D.shape != (nvr, nvx):
        raise ValueError("invalid vr2_2vx2_2D: expected (nvr, nvx) kernel")
    for name, arr in (("fH2", fH2), ("nH2", nH2), ("Alpha_H2_P", Alpha_H2_P),
                      ("Alpha_H2_H", Alpha_H2_H), ("SIG_H2_H2", SIG_H2_H2),
                      ("Vr2pidVr", Vr2pidVr), ("dVx", dVx), ("vr", vr),
                      ("vx", vx), ("vxi", vxi), ("VxH", VxH),
                      ("MH2_H2_sum", MH2_H2_sum), ("vr2_2vx2_2D", vr2_2vx2_2D)):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} contains a non-finite value")
    for name, value in (("Vth", Vth), ("DeltaVx_tol", DeltaVx_tol), ("Wpp_tol", Wpp_tol)):
        scalar = np.asarray(value)
        if scalar.ndim != 0 or scalar.dtype.kind not in "iuf" or not np.isfinite(scalar) or float(scalar) <= 0.0:
            raise ValueError(f"{name} must be a finite positive real scalar")
    Vth = float(Vth)
    DeltaVx_tol = float(DeltaVx_tol)
    Wpp_tol = float(Wpp_tol)
    if np.any(nH2 <= 0.0) and (H2_P_EL or H2_H_EL or H2_H2_EL):
        # source gates the whole Omega block on np.argwhere(nH2 <= 0).size <= 0
        raise ValueError("nH2 must be positive where elastic frequencies are assembled")

    VxH2 = np.zeros(nx)
    Omega_H2_P = np.zeros(nx)
    Omega_H2_H = np.zeros(nx)
    Omega_H2_H2 = np.zeros(nx)
    Wperp_paraH2 = np.zeros(nx)
    vr2_2vx_ran2 = np.zeros((nvr, nvx))
    Work = np.zeros(nvr * nvx)
    Alpha_H2_H2 = np.zeros((nvr, nvx))

    if H2_P_EL or H2_H_EL or H2_H2_EL:
        for k in range(nx):
            VxH2[k] = Vth * np.sum(Vr2pidVr * (fH2[:, :, k] @ (vx * dVx))) / nH2[k]

    if H2_P_EL:
        for k in range(nx):
            DeltaVx = (VxH2[k] - vxi[k]) / Vth
            MagDeltaVx = np.maximum(abs(DeltaVx), DeltaVx_tol)
            DeltaVx = _sign_symbolic(DeltaVx) * MagDeltaVx
            if not np.isfinite(DeltaVx) or DeltaVx == 0.0:
                raise ValueError("zero velocity difference in Omega_H2_P")
            Omega_H2_P[k] = np.sum(
                Vr2pidVr * ((Alpha_H2_P[:, :, k] * fH2[:, :, k]) @ dVx)
            ) / (nH2[k] * DeltaVx)
        Omega_H2_P = np.maximum(Omega_H2_P, 0)

    if H2_H_EL:
        for k in range(nx):
            DeltaVx = (VxH2[k] - VxH[k]) / Vth
            MagDeltaVx = np.maximum(abs(DeltaVx), DeltaVx_tol)
            DeltaVx = _sign_symbolic(DeltaVx) * MagDeltaVx
            if not np.isfinite(DeltaVx) or DeltaVx == 0.0:
                raise ValueError("zero velocity difference in Omega_H2_H")
            # source kinetic_h2.py:1270 -- denominator INSIDE the sum
            Omega_H2_H[k] = np.sum(
                Vr2pidVr * ((Alpha_H2_H[:, :, k] * fH2[:, :, k]) @ dVx) / (nH2[k] * DeltaVx)
            )
        Omega_H2_H = np.maximum(Omega_H2_H, 0)

    if H2_H2_EL:
        if np.sum(MH2_H2_sum) < 0:
            for k in range(nx):
                for i in range(nvr):
                    vr2_2vx_ran2[i, :] = vr[i] ** 2 - 2 * (vx - VxH2[k] / Vth) ** 2
                Wperp_paraH2[k] = np.sum(
                    Vr2pidVr * ((vr2_2vx_ran2 * fH2[:, :, k]) @ dVx)
                ) / nH2[k]
        else:
            for k in range(nx):
                M_fH2 = MH2_H2_sum[:, :, k] - fH2[:, :, k]
                Wperp_paraH2[k] = -np.sum(
                    Vr2pidVr * ((vr2_2vx2_2D * M_fH2) @ dVx)
                ) / nH2[k]

        for k in range(nx):
            Work[:] = fH2[:, :, k].reshape(Work.shape, order="F")
            Alpha_H2_H2[:] = (SIG_H2_H2 @ Work).reshape(Alpha_H2_H2.shape, order="F")
            Wpp = Wperp_paraH2[k]
            MagWpp = np.maximum(abs(Wpp), Wpp_tol)
            Wpp = _sign_symbolic(Wpp) * MagWpp
            if not np.isfinite(Wpp) or Wpp == 0.0:
                raise ValueError("zero perpendicular moment in Omega_H2_H2")
            Omega_H2_H2[k] = np.sum(
                Vr2pidVr * ((Alpha_H2_H2 * Work.reshape(Alpha_H2_H2.shape, order="F")) @ dVx)
            ) / (nH2[k] * Wpp)
        Omega_H2_H2 = np.maximum(Omega_H2_H2, 0)

    Omega_EL = Omega_H2_P + Omega_H2_H + Omega_H2_H2

    result = {
        "VxH2": VxH2,
        "Omega_H2_P": Omega_H2_P,
        "Omega_H2_H": Omega_H2_H,
        "Omega_H2_H2": Omega_H2_H2,
        "Omega_EL": Omega_EL,
        "Wperp_paraH2": Wperp_paraH2,
    }
    if any(not np.all(np.isfinite(value)) for value in result.values()):
        raise ValueError("Omega assembly produced a non-finite result")
    return result

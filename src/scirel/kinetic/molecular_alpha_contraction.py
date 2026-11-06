"""Source-free molecular collision-frequency contraction (Alpha three-family).

Reproduces the ``SIG ? f -> Alpha`` contraction of the neutral-transport formulation ``kinetic_h2.py``
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

__all__ = ["contract_molecular_hydrogen_alpha_frequencies"]


def _real_array(value, name):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite real array") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must be a finite real array")
    return result


def _batched_matrix_vectors(matrix, field):
    """Apply one square matrix to every Fortran-order spatial column.

    The singleton batch dimensions keep this local contraction independent of
    any external collision-table object or global workspace.
    """
    n_cells = field.shape[2]
    flat = field.reshape((matrix.shape[0], n_cells), order="F")
    values = np.matmul(matrix[None, :, :], flat.T[:, :, None]).squeeze(2).T
    return values.reshape(field.shape, order="F")


def contract_molecular_hydrogen_alpha_frequencies(
    SIG_CX, SIG_H2_H, SIG_H2_P, fH, fHp_hat, fi_hat, n, nHP, ni_correct=False
):
    r"""Per spatial cell, contract the molecular three-family assembled SIG collision matrices (CX, H2-H, H2-H+) with the Fortran-order flattened predecessor distributions to three (nvr,nvx,nx) Alpha collision-frequency fields; ni_correct selects the source's max(n - nHP, 0) ion-density correction.

    Parameters
    ----------
    SIG_CX : real array-like, shape [N, N] with N = nvr*nvx
        Assembled H2 + H2+ charge-exchange collision matrix from the molecular three-family assembly: sigma_cx_hh evaluated on the velocity-carrier energy grid, multiplied by the relative speed and the (Vr2pidVr*dVx) quadrature weight, laid out on the Fortran-order flattened (nvr*nvx) velocity carrier. [source-discrete assembled collision-matrix measure (cross section x relative speed x velocity-space weight); no implicit conversion].
        Constraints: Finite; must be 2-D square with order exactly nvr*nvx. The typical assembly yields a nonnegative SIG_CX, but the contraction preserves whatever sign pattern the caller supplies.
    SIG_H2_H : real array-like, shape [N, N] with N = nvr*nvx
        Assembled H2-H elastic collision matrix: sigma_el_h_hh with weight Vr2pidVr*dVx times the signed vx_vx factor, on the same Fortran-order velocity carrier. [source-discrete assembled collision-matrix measure (cross section x relative speed x velocity-space weight); no implicit conversion].
        Constraints: Finite; 2-D square with order exactly nvr*nvx. Contains bounded negative cells from the signed vx_vx factor; reproduced as-is.
    SIG_H2_P : real array-like, shape [N, N] with N = nvr*nvx
        Assembled H2-H+ elastic collision matrix: sigma_el_p_h (two energy branches) with weight Vr2pidVr*dVx times the signed vx_vx factor, on the same Fortran-order velocity carrier. [source-discrete assembled collision-matrix measure (cross section x relative speed x velocity-space weight); no implicit conversion].
        Constraints: Finite; 2-D square with order exactly nvr*nvx. Contains bounded negative cells from the signed vx_vx factor; reproduced as-is.
    fH : real array-like, shape [nvr,nvx,nx]
        Atomic neutral velocity distribution on the cylindrical (vr,vx) mesh, the predecessor carried unchanged into the Alpha_H2_H contraction. [source-discrete distribution density].
        Constraints: Finite; shape (nvr,nvx,nx) exactly; its leading axes define N = nvr*nvx for every SIG matrix.
    fHp_hat : real array-like, shape [nvr,nvx,nx]
        H2+ molecular-ion Maxwellian seed distribution on the cylindrical (vr,vx) mesh (drift vxi, temperature THP); scaled cell-wise by nHP[k] inside the Alpha_CX contraction. [source-discrete normalized distribution density].
        Constraints: Finite; shape (nvr,nvx,nx) exactly.
    fi_hat : real array-like, shape [nvr,nvx,nx]
        H+ proton Maxwellian seed distribution on the cylindrical (vr,vx) mesh (drift vxi, temperature Ti); scaled cell-wise by ni[k] inside the Alpha_H2_P contraction. [source-discrete normalized distribution density].
        Constraints: Finite; shape (nvr,nvx,nx) exactly.
    n : real array-like, shape [nx]
        Electron density profile (source mesh.ne), used as the ion density ni in the Alpha_H2_P contraction unless ni_correct is set. [m^-3].
        Constraints: Finite; 1-D with size nx. Negative or zero entries are not rejected at runtime: the contraction uses each value as given.
    nHP : real array-like, shape [nx]
        H2+ molecular-ion density profile scaling the fHp_hat carrier in the Alpha_CX contraction and entering the ni_correct density correction. [m^-3].
        Constraints: Finite; 1-D with size nx. Negative or zero entries are not rejected at runtime.
    ni_correct : boolean scalar, shape scalar
        Branch selector for the source's ion-density correction: when set, ni = max(n - nHP, 0) instead of ni = n (kinetic_h2.py:1221-1223). [dimensionless].
        Constraints: Truthiness selects the corrected-density branch; both branches are exercised by the maintained tests.
        Default: False.

    Returns
    -------
    Alpha_CX : float64 array, shape [nvr,nvx,nx]
        H2 + H2+ charge-exchange collision-frequency field: SIG_CX contracted with the Fortran-order flattened (fHp_hat*nHP) carrier, one (nvr,nvx) slice per spatial cell. [m^-1 (subject to the caller's assembled SIG measure; no implicit conversion)].
        Constraints: Finite (fail closed otherwise); nonnegative wherever SIG_CX is nonnegative; never clamped.
    Alpha_H2_H : float64 array, shape [nvr,nvx,nx]
        H2-H elastic collision-frequency field: SIG_H2_H contracted with the Fortran-order flattened fH slice. [m^-1 (subject to the caller's assembled SIG measure; no implicit conversion)].
        Constraints: Finite (fail closed otherwise); bounded negative cells inherited from the signed vx_vx SIG factor are reproduced as-is, never clamped.
    Alpha_H2_P : float64 array, shape [nvr,nvx,nx]
        H2-H+ elastic collision-frequency field: SIG_H2_P contracted with the Fortran-order flattened (fi_hat*ni) carrier, ni = n or max(n - nHP, 0) per the ni_correct branch. [m^-1 (subject to the caller's assembled SIG measure; no implicit conversion)].
        Constraints: Finite (fail closed otherwise); bounded negative cells inherited from the signed vx_vx SIG factor are reproduced as-is, never clamped.

    Raises
    ------
    ValueError
        Raises ValueError when a SIG matrix is not 2-D square, when any SIG order differs from the nvr*nvx carrier, when any distribution is not (nvr,nvx,nx), when n or nHP is not 1-D of size nx, or when any input contains a non-finite value. Raises ValueError if any contracted family produces a non-finite array; no partial results are returned. Not applicable. Never returned.

    See Also
    --------
    scirel.kinetic.contract_atomic_hydrogen_alpha_frequencies : Related neutral-transport operation.

    Notes
    -----
        The per-k matrix-vector contraction: each family multiplies one assembled (N,N) SIG matrix by the Fortran-order flattening of one predecessor distribution carried on the (nvr*nvx,) Work buffer and restores the product to the (nvr,nvx) slice. The CX family carries fHp_hat (the H2+ Maxwellian seeded with drift vxi and temperature THP) scaled cell-wise by nHP[k]; the H2-H family carries the bare atomic distribution fH; the H2-P family carries the proton seed fi_hat scaled by ni, where ni = n or, when ni_correct is set, ni = max(n - nHP, 0) cell-wise.
    finite aligned inputs of the declared shapes; negative or zero densities are not rejected at runtime -- every finite density profile is contracted as given (the ni_correct branch clamps n - nHP at zero cell-wise, which is a source-defined density correction, not a positivity gate); bounded negative output cells inherited from the signed elastic SIG families (vx_vx factors) are reproduced as-is, never clamped

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import contract_molecular_hydrogen_alpha_frequencies
    >>> nvr, nvx, nx = 2, 3, 2
    >>> N = nvr * nvx
    >>> fH = np.ones((nvr, nvx, nx))
    >>> fHp_hat = np.ones((nvr, nvx, nx))
    >>> fi_hat = np.ones((nvr, nvx, nx))
    >>> n = np.full(nx, 1e18)
    >>> nHP = np.full(nx, 4e17)
    >>> result = contract_molecular_hydrogen_alpha_frequencies(
    ...     np.eye(N), np.eye(N), np.eye(N), fH, fHp_hat, fi_hat, n, nHP,
    ... )
    >>> assert set(result) == {"Alpha_CX", "Alpha_H2_H", "Alpha_H2_P"}
    >>> np.testing.assert_array_equal(result["Alpha_CX"], fHp_hat * 4e17)
    >>> np.testing.assert_array_equal(result["Alpha_H2_P"], fi_hat * 1e18)
    >>> corrected = contract_molecular_hydrogen_alpha_frequencies(
    ...     np.eye(N), np.eye(N), np.eye(N), fH, fHp_hat, fi_hat, n, nHP, ni_correct=True,
    ... )
    >>> np.testing.assert_array_equal(corrected["Alpha_H2_P"], fi_hat * 6e17)
    """
    SIG_CX = _real_array(SIG_CX, "SIG_CX")
    SIG_H2_H = _real_array(SIG_H2_H, "SIG_H2_H")
    SIG_H2_P = _real_array(SIG_H2_P, "SIG_H2_P")
    fH = _real_array(fH, "fH")
    fHp_hat = _real_array(fHp_hat, "fHp_hat")
    fi_hat = _real_array(fi_hat, "fi_hat")
    n = _real_array(n, "n")
    nHP = _real_array(nHP, "nHP")

    if fH.ndim != 3:
        raise ValueError("invalid fH: expected (nvr, nvx, nx)")
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
    for name, arr in (
        ("SIG_CX", SIG_CX),
        ("SIG_H2_H", SIG_H2_H),
        ("SIG_H2_P", SIG_H2_P),
        ("fH", fH),
        ("fHp_hat", fHp_hat),
        ("fi_hat", fi_hat),
        ("n", n),
        ("nHP", nHP),
    ):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} contains a non-finite value")

    # Source-exact ion density (kinetic_h2.py:1221-1223).
    ni = n
    if ni_correct:
        ni = np.maximum((n - nHP), 0)

    fHp_weighted = fHp_hat * nHP[None, None, :]
    fi_weighted = fi_hat * ni[None, None, :]
    Alpha_CX = _batched_matrix_vectors(SIG_CX, fHp_weighted)
    Alpha_H2_H = _batched_matrix_vectors(SIG_H2_H, fH)
    Alpha_H2_P = _batched_matrix_vectors(SIG_H2_P, fi_weighted)

    for name, arr in (
        ("Alpha_CX", Alpha_CX),
        ("Alpha_H2_H", Alpha_H2_H),
        ("Alpha_H2_P", Alpha_H2_P),
    ):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} contraction produced a non-finite array")

    return {
        "Alpha_CX": Alpha_CX,
        "Alpha_H2_H": Alpha_H2_H,
        "Alpha_H2_P": Alpha_H2_P,
    }

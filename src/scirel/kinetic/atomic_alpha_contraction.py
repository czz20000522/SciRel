"""Source-free atomic collision-frequency contraction (Alpha four-family).

Reproduces the ``SIG ? f -> Alpha`` contraction of the neutral-transport formulation ``kinetic_h.py`` for
the atomic four-family Alpha collision frequencies:

- ``Alpha_CX``  : H + H+  charge exchange,     ``Alpha_CX[:,:,k]  = F^{-1}(SIG_CX  @ F(fi_hat*ni))``
- ``Alpha_H_H2`` : H-H2  elastic,              ``Alpha_H_H2[:,:,k] = F^{-1}(SIG_H_H2 @ F(fH2))``
- ``Alpha_H_P``  : H-H+  elastic,              ``Alpha_H_P[:,:,k] = F^{-1}(SIG_H_P  @ F(fi_hat*ni))``
- ``Alpha_H_H``  : H-H   elastic,              ``Alpha_H_H[:,:,k] = F^{-1}(SIG_H_H  @ F(fH))``

``F`` / ``F^{-1}`` are the source legacy Fortran-order flatten/restore:
``Work[:] = src[:,:,k].reshape(Work.shape, order='F')`` and
``out[:,:,k] = (...).reshape(out[:,:,k].shape, order='F')`` (kinetic_h.py:1041-1042,
1060-1061, 1075-1076, 1163-1165).  The operator is self-contained and takes the
already-assembled ``SIG_*`` matrices (N4-1 / ``operators/原子氢碰撞矩阵组装``) plus
explicit predecessor distributions.  Bounded negative cells inherited from the
signed elastic SIG families are reproduced as-is, never clamped.
"""

from __future__ import annotations

import numpy as np

__all__ = ["contract_atomic_hydrogen_alpha_frequencies"]


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

    Each column remains an ``N x 1`` matrix-vector product, preserving the
    reduction path of the source loop while moving only the spatial axis into
    a batch dimension.  The matrix and field are owned by this call, so the
    contraction cannot leak mutable state between species.
    """
    n_cells = field.shape[2]
    flat = field.reshape((matrix.shape[0], n_cells), order="F")
    values = np.matmul(matrix[None, :, :], flat.T[:, :, None]).squeeze(2).T
    return values.reshape(field.shape, order="F")


def contract_atomic_hydrogen_alpha_frequencies(
    SIG_CX, SIG_H_H, SIG_H_H2, SIG_H_P, fi_hat, ni, fH2, fH
):
    r"""Per spatial cell, contract the atomic four-family assembled SIG collision matrices (CX, H-H2, H-P, H-H) with the Fortran-order flattened input distributions to four (nvr,nvx,nx) Alpha collision-frequency fields.

    Parameters
    ----------
    SIG_CX : real array-like, shape [N, N] with N = nvr*nvx
        Assembled H + H+ charge-exchange collision matrix from the atomic four-family assembly: sigma_cx evaluated on the velocity-carrier energy grid, multiplied by the relative speed and the (Vr2pidVr*dVx) quadrature weight, laid out on the Fortran-order flattened (nvr*nvx) velocity carrier. [source-discrete assembled collision-matrix measure (cross section x relative speed x velocity-space weight); no implicit conversion].
        Constraints: Finite; must be 2-D square with order exactly nvr*nvx. The declared assembly produces a nonnegative SIG_CX; the contraction preserves whatever sign pattern the caller supplies.
    SIG_H_H : real array-like, shape [N, N] with N = nvr*nvx
        Assembled H-H elastic (viscosity-branch) collision matrix: sigma_el_h_h with the mu energy factor and the Boltzmann 3/8 constant, weight Vr2pidVr*dVx, on the same Fortran-order velocity carrier. [source-discrete assembled collision-matrix measure (cross section x relative speed x velocity-space weight); no implicit conversion].
        Constraints: Finite; 2-D square with order exactly nvr*nvx. Contains bounded negative cells from the signed elastic factors; reproduced as-is.
    SIG_H_H2 : real array-like, shape [N, N] with N = nvr*nvx
        Assembled H-H2 elastic collision matrix: sigma_el_h_hh with weight Vr2pidVr*dVx times the signed vx_vx factor, on the same Fortran-order velocity carrier. [source-discrete assembled collision-matrix measure (cross section x relative speed x velocity-space weight); no implicit conversion].
        Constraints: Finite; 2-D square with order exactly nvr*nvx. Contains bounded negative cells from the signed vx_vx factor; reproduced as-is.
    SIG_H_P : real array-like, shape [N, N] with N = nvr*nvx
        Assembled H-H+ elastic collision matrix: sigma_el_p_h (two energy branches) with weight Vr2pidVr*dVx times the signed vx_vx factor, on the same Fortran-order velocity carrier. [source-discrete assembled collision-matrix measure (cross section x relative speed x velocity-space weight); no implicit conversion].
        Constraints: Finite; 2-D square with order exactly nvr*nvx. Contains bounded negative cells from the signed vx_vx factor; reproduced as-is.
    fi_hat : real array-like, shape [nvr,nvx,nx]
        Atomic neutral Maxwellian seed distribution on the cylindrical (vr,vx) velocity mesh, one (nvr,nvx) slice per spatial cell; scaled cell-wise by ni[k] inside the Alpha_CX and Alpha_H_P contractions. [source-discrete normalized distribution density].
        Constraints: Finite; shape (nvr,nvx,nx) exactly; its leading axes define N = nvr*nvx for every SIG matrix.
    ni : real array-like, shape [nx]
        Ion density profile scaling the fi_hat carrier in the Alpha_CX and Alpha_H_P contractions (one value per spatial cell). [m^-3].
        Constraints: Finite; 1-D with size nx. Negative or zero entries are not rejected at runtime: the contraction uses each value as given.
    fH2 : real array-like, shape [nvr,nvx,nx]
        Molecular neutral velocity distribution on the cylindrical (vr,vx) mesh, the predecessor carried unchanged into the Alpha_H_H2 contraction. [source-discrete distribution density].
        Constraints: Finite; shape (nvr,nvx,nx) exactly.
    fH : real array-like, shape [nvr,nvx,nx]
        Atomic neutral velocity distribution on the cylindrical (vr,vx) mesh, the predecessor carried unchanged into the Alpha_H_H contraction. [source-discrete distribution density].
        Constraints: Finite; shape (nvr,nvx,nx) exactly.

    Returns
    -------
    Alpha_CX : float64 array, shape [nvr,nvx,nx]
        H + H+ charge-exchange collision-frequency field: SIG_CX contracted with the Fortran-order flattened (fi_hat*ni) carrier, one (nvr,nvx) slice per spatial cell. [m^-1 (subject to the caller's assembled SIG measure; no implicit conversion)].
        Constraints: Finite (fail closed otherwise); nonnegative on the declared domain where SIG_CX is nonnegative; never clamped.
    Alpha_H_H2 : float64 array, shape [nvr,nvx,nx]
        H-H2 elastic collision-frequency field: SIG_H_H2 contracted with the Fortran-order flattened fH2 slice. [m^-1 (subject to the caller's assembled SIG measure; no implicit conversion)].
        Constraints: Finite (fail closed otherwise); bounded negative cells inherited from the signed vx_vx SIG factor are reproduced as-is, never clamped.
    Alpha_H_P : float64 array, shape [nvr,nvx,nx]
        H-H+ elastic collision-frequency field: SIG_H_P contracted with the Fortran-order flattened (fi_hat*ni) carrier. [m^-1 (subject to the caller's assembled SIG measure; no implicit conversion)].
        Constraints: Finite (fail closed otherwise); bounded negative cells inherited from the signed vx_vx SIG factor are reproduced as-is, never clamped.
    Alpha_H_H : float64 array, shape [nvr,nvx,nx]
        H-H elastic collision-frequency field: SIG_H_H contracted with the Fortran-order flattened fH slice. [m^-1 (subject to the caller's assembled SIG measure; no implicit conversion)].
        Constraints: Finite (fail closed otherwise); bounded negative cells inherited from the signed vx_vx / vr2_vx2 SIG factors are reproduced as-is, never clamped.

    Raises
    ------
    ValueError
        Raises ValueError when a SIG matrix is not 2-D square, when any SIG order differs from the nvr*nvx carrier, when any distribution is not (nvr,nvx,nx), when ni is not 1-D of size nx, or when any input contains a non-finite value. Raises ValueError if any contracted family produces a non-finite array; no partial results are returned. Not applicable. Never returned.

    See Also
    --------
    scirel.kinetic.evaluate_bessel_gamma : Related neutral-transport operation.

    Notes
    -----
        The per-k matrix-vector contraction: each family multiplies one assembled (N,N) SIG matrix by the Fortran-order flattening of one input distribution carried on the (nvr*nvx,) Work buffer and restores the product to the (nvr,nvx) slice. The CX and H-P families carry fi_hat scaled cell-wise by ni[k]; the H-H2 and H-H families carry the bare distributions fH2 and fH.
    finite aligned inputs of the declared shapes; negative or zero densities are not rejected at runtime -- every finite density profile is contracted as given; bounded negative output cells inherited from the signed elastic SIG families (vx_vx / vr2_vx2 factors) are reproduced as-is, never clamped

    When the input matrices come from SciRel's atomic collision-matrix
    assembly, ``SIG_H_P`` already includes resonant charge-exchange momentum.
    The corresponding H-P momentum moment must not be added to that of a
    full-velocity charge-exchange gain-loss operator using ``SIG_CX`` and
    ``Alpha_CX``. This direct composition is unsupported. Returning both
    contracted fields does not combine their collision operators, validate
    caller-supplied cross sections or provide a replacement scattering model.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import contract_atomic_hydrogen_alpha_frequencies
    >>> nvr, nvx, nx = 2, 3, 2
    >>> N = nvr * nvx
    >>> fi_hat = np.ones((nvr, nvx, nx))
    >>> result = contract_atomic_hydrogen_alpha_frequencies(
    ...     np.eye(N), np.eye(N), np.eye(N), np.eye(N), fi_hat,
    ...     np.full(nx, 1e18), fi_hat, fi_hat,
    ... )
    >>> assert set(result) == {"Alpha_CX", "Alpha_H_H2", "Alpha_H_P", "Alpha_H_H"}
    >>> np.testing.assert_array_equal(result["Alpha_CX"], fi_hat * 1e18)
    >>> np.testing.assert_array_equal(result["Alpha_H_H2"], fi_hat)
    >>> try:
    ...     contract_atomic_hydrogen_alpha_frequencies(
    ...         np.eye(2), np.eye(N), np.eye(N), np.eye(N), fi_hat,
    ...         np.full(nx, 1e18), fi_hat, fi_hat,
    ...     )
    ... except ValueError:
    ...     pass
    ... else:
    ...     raise AssertionError("a SIG order differing from the velocity carrier must be rejected")
    """
    SIG_CX = _real_array(SIG_CX, "SIG_CX")
    SIG_H_H = _real_array(SIG_H_H, "SIG_H_H")
    SIG_H_H2 = _real_array(SIG_H_H2, "SIG_H_H2")
    SIG_H_P = _real_array(SIG_H_P, "SIG_H_P")
    fi_hat = _real_array(fi_hat, "fi_hat")
    ni = _real_array(ni, "ni")
    fH2 = _real_array(fH2, "fH2")
    fH = _real_array(fH, "fH")

    if fi_hat.ndim != 3:
        raise ValueError("invalid fi_hat: expected (nvr, nvx, nx)")
    nvr, nvx, nx = fi_hat.shape
    if SIG_CX.ndim != 2 or SIG_CX.shape[0] != SIG_CX.shape[1]:
        raise ValueError("invalid SIG_CX: expected 2-D square matrix")
    nsig = SIG_CX.shape[0]
    if nsig != nvr * nvx:
        raise ValueError("invalid SIG_CX dimension for velocity-space carrier")
    for name, sig in (("SIG_H_H", SIG_H_H), ("SIG_H_H2", SIG_H_H2), ("SIG_H_P", SIG_H_P)):
        if sig.ndim != 2 or sig.shape != (nsig, nsig):
            raise ValueError(f"invalid {name}: expected ({nsig}, {nsig}) matrix")
    if ni.ndim != 1 or ni.size != nx:
        raise ValueError("invalid ni: expected (nx,) ion density")
    if fH2.shape != (nvr, nvx, nx) or fH.shape != (nvr, nvx, nx):
        raise ValueError("invalid fH2/fH: expected (nvr, nvx, nx)")
    for name, arr in (
        ("SIG_CX", SIG_CX),
        ("SIG_H_H2", SIG_H_H2),
        ("SIG_H_P", SIG_H_P),
        ("SIG_H_H", SIG_H_H),
        ("fi_hat", fi_hat),
        ("ni", ni),
        ("fH2", fH2),
        ("fH", fH),
    ):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} contains a non-finite value")

    fi_weighted = fi_hat * ni[None, None, :]
    Alpha_CX = _batched_matrix_vectors(SIG_CX, fi_weighted)
    Alpha_H_H2 = _batched_matrix_vectors(SIG_H_H2, fH2)
    Alpha_H_P = _batched_matrix_vectors(SIG_H_P, fi_weighted)
    Alpha_H_H = _batched_matrix_vectors(SIG_H_H, fH)

    for name, arr in (
        ("Alpha_CX", Alpha_CX),
        ("Alpha_H_H2", Alpha_H_H2),
        ("Alpha_H_P", Alpha_H_P),
        ("Alpha_H_H", Alpha_H_H),
    ):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} contraction produced a non-finite array")

    return {
        "Alpha_CX": Alpha_CX,
        "Alpha_H_H2": Alpha_H_H2,
        "Alpha_H_P": Alpha_H_P,
        "Alpha_H_H": Alpha_H_H,
    }

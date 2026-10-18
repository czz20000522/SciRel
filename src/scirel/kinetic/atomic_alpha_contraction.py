"""Source-free atomic collision-frequency contraction (Alpha four-family).

Reproduces the ``SIG ? f -> Alpha`` contraction of KN1DPy ``kinetic_h.py`` for
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
    a batch dimension.
    """
    n_cells = field.shape[2]
    flat = field.reshape((matrix.shape[0], n_cells), order="F")
    values = np.matmul(matrix[None, :, :], flat.T[:, :, None]).squeeze(2).T
    return values.reshape(field.shape, order="F")


def contract_atomic_hydrogen_alpha_frequencies(
    SIG_CX, SIG_H_H, SIG_H_H2, SIG_H_P, fi_hat, ni, fH2, fH
):
    """Contract the atomic four-family SIG matrices to Alpha collision frequencies.

    Parameters
    ----------
    SIG_CX : (N, N) array, H + H+ charge-exchange collision matrix.
    SIG_H_H : (N, N) array, H-H elastic collision matrix.
    SIG_H_H2 : (N, N) array, H-H2 elastic collision matrix.
    SIG_H_P : (N, N) array, H-H+ elastic collision matrix.
    fi_hat : (nvr, nvx, nx) array, neutral-atom Maxwellian seed distribution.
    ni : (nx,) array, ion density profile (m^-3).
    fH2 : (nvr, nvx, nx) array, molecular neutral velocity distribution.
    fH : (nvr, nvx, nx) array, atomic neutral velocity distribution.

    SIG_CX, SIG_H_H, SIG_H_H2, SIG_H_P : (N, N) arrays.  ``SIG_H_H`` is the
    H-H elastic matrix consumed by ``Alpha_H_H``.

    Returns
    -------
    dict with ``Alpha_CX``, ``Alpha_H_H2``, ``Alpha_H_P``, ``Alpha_H_H``,
    each ``(nvr, nvx, nx)``.
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
    for name, arr in (("SIG_CX", SIG_CX), ("SIG_H_H2", SIG_H_H2),
                      ("SIG_H_P", SIG_H_P), ("SIG_H_H", SIG_H_H),
                      ("fi_hat", fi_hat), ("ni", ni), ("fH2", fH2), ("fH", fH)):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} contains a non-finite value")

    fi_weighted = fi_hat * ni[None, None, :]
    Alpha_CX = _batched_matrix_vectors(SIG_CX, fi_weighted)
    Alpha_H_H2 = _batched_matrix_vectors(SIG_H_H2, fH2)
    Alpha_H_P = _batched_matrix_vectors(SIG_H_P, fi_weighted)
    Alpha_H_H = _batched_matrix_vectors(SIG_H_H, fH)

    for name, arr in (("Alpha_CX", Alpha_CX), ("Alpha_H_H2", Alpha_H_H2),
                      ("Alpha_H_P", Alpha_H_P), ("Alpha_H_H", Alpha_H_H)):
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} contraction produced a non-finite array")

    return {
        "Alpha_CX": Alpha_CX,
        "Alpha_H_H2": Alpha_H_H2,
        "Alpha_H_P": Alpha_H_P,
        "Alpha_H_H": Alpha_H_H,
    }

"""Solve the assembled fluid wavevector eigenproblem and retain deterministic mode diagnostics."""
from __future__ import annotations

import operator
import numpy as np

__all__ = ["solve_fluid_wavevector_eigenproblem"]


def _source_runtime_eigvals(matrix):
    from scipy.linalg.lapack import zgeev

    """Return the eigenvalues via the general complex LAPACK driver the source runtime calls.

    The frozen source ``em3d_Lpole.m:238`` evaluates ``d = eig(matM)`` in Octave. For a
    general complex matrix Octave's single-output ``eig`` is the LAPACK driver ``zgeev``
    with ``jobvl=jobvr='N'`` (eigenvalues only); ``zgeev`` balances the matrix internally
    before the Schur reduction. This helper calls that driver directly with its minimum
    work array.

    NumPy's ``linalg.eigvals`` and SciPy's high-level ``linalg.eig``/``linalg.eigvals``
    instead size the work array from the LAPACK workspace query and take the larger
    blocked code path. On the frozen scan the two leading ``|Im(kx)|`` branches are a
    near-tie (canonical row 76 gap ~9.6e-7 1/m); the blocked and minimum-workspace driver
    paths round that pair differently and therefore order it differently. Calling the
    driver directly reproduces the source runtime's saved ordered ``kxx`` on every row of
    the canonical and sealed-holdout cases within the declared tolerance, while the
    wrapper default does not.
    """
    a = np.ascontiguousarray(matrix, dtype=np.complex128)
    n = int(a.shape[0])
    values, _vl, _vr, info = zgeev(a, lwork=max(1, 2 * n), compute_vl=0, compute_vr=0)
    if info != 0:
        raise np.linalg.LinAlgError(f"general eigensolver failed to converge (info={info})")
    return np.asarray(values, dtype=np.complex128)


def solve_fluid_wavevector_eigenproblem(*, matrix, kn, real_floor_scale=1e-5, keep=5):
    """Return the perpendicular wavenumbers of the fluid matrix eigenproblem.

    The caller supplies the assembled matrix ``matrix`` (complex, square) and the wavenumber
    normalisation ``kn`` [1/m]. The relation solved is ``kx * X = matrix @ X``; eigenvalues with
    ``Re(kx) <= real_floor_scale * kn`` are rejected as non-propagating, and the survivors are
    ordered by ascending ``|Im(kx)|`` so that the least damped branch comes first.
    """

    matrix = np.asarray(matrix, dtype=complex)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or matrix.shape[0] == 0:
        raise ValueError("matrix must be a non-empty square complex matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("matrix must be finite")
    kn = float(kn)
    if not np.isfinite(kn) or kn <= 0.0:
        raise ValueError("kn must be finite and strictly positive")
    real_floor_scale = float(real_floor_scale)
    if not np.isfinite(real_floor_scale) or real_floor_scale < 0.0:
        raise ValueError("real_floor_scale must be finite and non-negative")
    if isinstance(keep, (bool, np.bool_)):
        raise ValueError("keep must be a positive integer")
    try:
        keep = operator.index(keep)
    except TypeError:
        raise ValueError("keep must be a positive integer") from None
    if keep < 1:
        raise ValueError("keep must be at least 1")

    eigenvalues = _source_runtime_eigvals(matrix)
    floor = real_floor_scale * kn
    selected = eigenvalues[np.real(eigenvalues) > floor]
    order = np.argsort(np.abs(np.imag(selected)), kind="stable")
    selected = selected[order]
    head = selected[:keep] if selected.size else selected
    return {
        "eigenvalues": eigenvalues,
        "selected": selected,
        "head": head,
        "eigenvalue_count": int(eigenvalues.size),
        "selected_count": int(selected.size),
        "returned_count": int(head.size),
        "real_floor": float(floor),
        "sort_key": "ascending_abs_imag",
    }

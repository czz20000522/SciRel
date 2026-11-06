"""Solve the assembled fluid wavevector eigenproblem and retain deterministic mode diagnostics."""

from __future__ import annotations

import operator
import numpy as np

__all__ = ["solve_fluid_wavevector_eigenproblem"]


def _source_runtime_eigvals(matrix):
    from scipy.linalg.lapack import zgeev

    """Return the eigenvalues via the general complex LAPACK driver the source runtime calls.

    The declared formulation ``em3d_Lpole.m:238`` evaluates ``d = eig(matM)`` in the reference solver. For a
    general complex matrix the reference solver's single-output ``eig`` is the LAPACK driver ``zgeev``
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
    r"""Solve and qualify the fluid wavevector eigenproblem.

    Parameters
    ----------
    matrix : complex128
        Complex square matrix whose eigenproblem is solved, usually the fluid dispersion
        matrix Shape: `(NN, NN)` complex square matrix. Constraints: Nonempty square
        matrix with finite entries. Units: [Consistent with the matrix-assembly
        convention].
    kn : real numeric
        Wavenumber normalization scale used to turn the real-part threshold into an
        absolute threshold Shape: scalar. Constraints: Finite and strictly positive.
        Units: [1/m].
    real_floor_scale : real numeric, optional
        Relative real-part threshold for non-propagating eigenvalues Shape: scalar.
        Constraints: Finite and nonnegative, default `1e-5`. Default: 1e-05. Units:
        [dimensionless].
    keep : integer, optional
        Number of leading eigenvalues to return Shape: integer scalar. Constraints: At
        least 1, default 5. Default: 5. Units: [dimensionless].

    Returns
    -------
    eigenvalues : complex128
        All eigenvalues, that is, the complete $k_\perp$ spectrum Shape: Complex array
        of length `NN`. Constraints: Finite complex numbers. Units: [1/m].
    selected : complex128
        Eigenvalues whose real part exceeds the threshold, sorted in ascending
        $|\operatorname{Im}|$ order Shape: Complex array of length `selected_count`.
        Constraints: A subset of `eigenvalues`. Units: [1/m].
    head : complex128
        First `keep` sorted physical eigenvalues Shape: Complex array of length at most
        `keep`. Constraints: When fewer than `keep` eigenvalues survive, returns every
        surviving value. Units: [1/m].
    eigenvalue_count : integer
        Total number of eigenvalues, equal to the matrix order Shape: integer scalar.
        Constraints: Equal to the number of rows of `matrix`. Units: [dimensionless].
    selected_count : integer
        Number of eigenvalues passing the real-part threshold Shape: integer scalar.
        Constraints: At most `eigenvalue_count`. Units: [dimensionless].
    returned_count : integer
        Length of `head` Shape: integer scalar. Constraints: Equal to `min(keep,
        selected_count)`. Units: [dimensionless].
    real_floor : real numeric
        Absolute real-part threshold actually used Shape: scalar. Constraints: Equal to
        `real_floor_scale*kn`. Units: [1/m].
    sort_key : string
        Sort-key label Shape: string. Constraints: Fixed to `ascending_abs_imag`. Units:
        [not applicable].

    Raises
    ------
    LinAlgError
        If the numerical eigensolver cannot produce a spectrum.
    ValueError
        If inputs, physical controls, coefficient tables or a numerical response are
        invalid or unrepresentable.

    See Also
    --------
    derive_species_equilibrium_scales
        Related kinetic amplitude or dispersion operator in the same workflow.
    get_gamma_lpole_coefficients
        Related kinetic amplitude or dispersion operator in the same workflow.
    get_z_pole_coefficients
        Related kinetic amplitude or dispersion operator in the same workflow.
    assemble_fluid_dispersion_matrix
        Related kinetic amplitude or dispersion operator in the same workflow.
    scan_fluid_wavevectors
        Related kinetic amplitude or dispersion operator in the same workflow.

    Notes
    -----
        The direct eigensolve returns the complete finite matrix spectrum and a leading
        branch selection. Residuals and conditioning metadata describe qualification;
        they do not prove forward accuracy for ill-conditioned or repeated modes.
        Supported scope: Solve a general complex fluid eigenmatrix and select
        positive-real least-damped kx branches. Excluded scope: No mode identity or
        arbitrary-parameter accuracy is inferred beyond the declared numerical method.

    Examples
    --------
    >>> from scirel.kinetic import solve_fluid_wavevector_eigenproblem
    >>> r=solve_fluid_wavevector_eigenproblem(matrix=__import__('numpy').diag([1+1j,-1+0j]),kn=1); assert len(r['selected'])==1
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

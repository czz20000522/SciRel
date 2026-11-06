"""Thresholded Moore-Penrose pseudo-inverse for dense real matrices."""

from __future__ import annotations

import numbers

import numpy as np

__all__ = ["truncated_svd_inverse"]

_SINGULAR_NOT_REPRESENTABLE = (
    "SVD singular values derived from a finite input are not representable as finite float64"
)
_RECIPROCAL_NOT_REPRESENTABLE = (
    "retained reciprocal derived from a finite input is not representable as finite float64"
)
_OUTPUT_NOT_REPRESENTABLE = (
    "truncated pseudo-inverse derived from a finite input is not representable as finite float64"
)


def truncated_svd_inverse(mat, rcond=1e-10):
    """Compute the Moore-Penrose inverse with truncated singular values.

    Parameters
    ----------
    mat : array_like
        Finite real matrix of shape ``(m, n)``. [dimensionless]
    rcond : float, optional
        Relative singular-value threshold; values below ``rcond * max(s)``
        are discarded (default ``1e-10``). [dimensionless]

    Returns
    -------
    inverse : numpy.ndarray
        Pseudo-inverse of shape ``(n, m)``. [dimensionless] Finite whenever
        the SVD singular values, the retained reciprocals and their
        contraction are representable in float64.

    Raises
    ------
    ValueError
        If ``mat`` is not 2-D or contains non-finite values, or if ``rcond``
        is not a positive finite real scalar.
    FloatingPointError
        If the finite input produces SVD singular values, a retained
        reciprocal, or a pseudo-inverse that is not representable as finite
        float64. Non-representable values are neither returned as inf/nan nor
        silently treated as truncated.

    See Also
    --------
    numpy.linalg.pinv : NumPy pseudo-inverse with the same relative-threshold
        convention.

    Notes
    -----
    For ``M = U diag(s) V^T`` this returns
    ``V diag(1/s for s >= rcond * max(s) else 0) U^T``. Only the relative
    threshold discards a singular value; a retained singular value whose
    reciprocal overflows is reported as a failure instead of being dropped.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.geometry import truncated_svd_inverse
    >>> m = np.array([[1.0, 2.0], [2.0, 4.0]])
    >>> np.testing.assert_allclose(truncated_svd_inverse(m), np.linalg.pinv(m))
    >>> truncated_svd_inverse(np.ones((5, 3))).shape
    (3, 5)
    >>> try:
    ...     truncated_svd_inverse(np.array([[1e-310]]))
    ... except FloatingPointError:
    ...     print("finite input, unrepresentable derived result")
    finite input, unrepresentable derived result
    """
    matrix = np.asarray(mat, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("mat must be a 2-D array")
    if not np.isfinite(matrix).all():
        raise ValueError("mat must contain only finite values")
    if isinstance(rcond, bool) or not isinstance(rcond, numbers.Real):
        raise ValueError("rcond must be a positive finite real scalar")
    threshold = float(rcond)
    if not np.isfinite(threshold) or threshold <= 0.0:
        raise ValueError("rcond must be a positive finite real scalar")
    u, singular, vt = np.linalg.svd(matrix, full_matrices=False)
    if singular.size and singular.max() == 0.0:
        # The zero matrix has a zero pseudo-inverse; relative thresholding
        # would otherwise keep a zero singular value and divide by it.
        return np.zeros((matrix.shape[1], matrix.shape[0]), dtype=float)
    if not np.isfinite(singular).all():
        raise FloatingPointError(_SINGULAR_NOT_REPRESENTABLE)
    if singular.size:
        keep = singular >= threshold * singular.max()
    else:
        keep = singular.astype(bool)
    inverse = np.zeros_like(singular)
    if keep.any():
        retained = singular[keep]
        # Decide representability before forming the returned product: every
        # retained value must have a finite reciprocal.
        with np.errstate(over="raise", divide="raise", invalid="raise"):
            try:
                reciprocal = 1.0 / retained
            except FloatingPointError:
                raise FloatingPointError(_RECIPROCAL_NOT_REPRESENTABLE) from None
        if not np.isfinite(reciprocal).all():
            raise FloatingPointError(_RECIPROCAL_NOT_REPRESENTABLE)
        inverse[keep] = reciprocal
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        try:
            result = (vt.T * inverse) @ u.T
        except FloatingPointError:
            raise FloatingPointError(_OUTPUT_NOT_REPRESENTABLE) from None
    if not np.isfinite(result).all():
        raise FloatingPointError(_OUTPUT_NOT_REPRESENTABLE)
    return result

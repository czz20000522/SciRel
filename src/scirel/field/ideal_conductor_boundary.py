"""Finite-dimensional ideal-conductor boundary correction."""

import numpy as np

from scirel._result import Result


def _finite_array(name, value, ndim):
    array = np.asarray(value, dtype=float)
    if array.ndim != ndim:
        raise ValueError(f"{name} must be a {ndim}-D array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def correct_ideal_conductor_boundary_flux(
    uncorrected_field_flux,
    boundary_sample_matrix,
    green_boundary_to_boundary,
    green_boundary_to_field,
    rcond=1e-10,
):
    """Cancel sampled boundary flux as a named truncated-SVD result.

    Parameters
    ----------
    uncorrected_field_flux : real array-like, shape [N_field]
        ``psi=R A_phi`` before boundary-source correction at field points
        [Wb/rad]. Finite one-dimensional vector of length ``N_field``.
    boundary_sample_matrix : real array-like, shape [N_boundary,N_field]
        Linear map from field flux to sampled boundary flux [dimensionless].
        Finite two-dimensional matrix.
    green_boundary_to_boundary : real array-like, shape [N_boundary,N_source]
        Boundary-sample psi response per unit boundary-source current
        [Wb/rad/A]. Finite, nonempty two-dimensional matrix.
    green_boundary_to_field : real array-like, shape [N_field,N_source]
        Field-point psi response per unit boundary-source current [Wb/rad/A].
        Finite two-dimensional matrix with the same source axis as
        ``green_boundary_to_boundary``.
    rcond : real scalar, optional
        Relative cutoff for singular values of the boundary Green matrix
        [dimensionless]. Finite and nonnegative; values above one can retain
        no singular values. Default is ``1e-10``.

    Returns
    -------
    corrected_field_flux : ndarray of float64, shape [N_field]
        Field ``corrected_field_flux`` of the returned
        ``scirel._result.Result`` mapping: uncorrected field psi plus
        ``Gbf @ boundary_currents`` [Wb/rad].
    boundary_currents : ndarray of float64, shape [N_source]
        Field ``boundary_currents`` of the returned result mapping:
        equivalent source-current coefficients from the truncated pseudoinverse
        [A].
    boundary_flux_correction : ndarray of float64, shape [N_boundary]
        Field ``boundary_flux_correction`` of the returned result mapping:
        ``Gbb @ boundary_currents`` at boundary samples [Wb/rad].
    field_flux_correction : ndarray of float64, shape [N_field]
        Field ``field_flux_correction`` of the returned result mapping:
        ``Gbf @ boundary_currents`` at field points [Wb/rad].
    singular_values : ndarray of float64, shape [min(N_boundary,N_source)]
        Field ``singular_values`` of the returned result mapping: boundary
        Green singular values in descending order [Wb/rad/A].
    effective_rank : int
        Field ``effective_rank`` of the returned result mapping: count of
        singular values strictly above the relative cutoff [count].
    residual : ndarray of float64, shape [N_boundary]
        Field ``residual`` of the returned result mapping: original sampled
        boundary psi plus boundary-source correction [Wb/rad].
    residual_norm : float
        Field ``residual_norm`` of the returned result mapping: Euclidean norm
        of the boundary residual [Wb/rad].

    Raises
    ------
    ValueError
        If inputs are nonfinite, have wrong rank, are incompatible or empty,
        or if ``rcond`` is invalid.
    numpy.linalg.LinAlgError
        If the underlying SVD fails to converge.

    See Also
    --------
    scirel.electromagnetism.green_response_matrices : Dense Green responses.

    Notes
    -----
    The eight fields are stored directly in one ``scirel._result.Result``
    mapping. No nested mapping is returned, and mapping access remains
    available alongside attribute access. Rank truncation can leave a nonzero
    residual.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.field import correct_ideal_conductor_boundary_flux
    >>> psi = np.array([3.0, -1.0, 2.0])
    >>> sample = np.array([[1.0, 0.0, 0.0], [0.0, 0.5, 0.5]])
    >>> gbb = np.diag([2.0, 4.0])
    >>> gbf = np.array([[2.0, 0.0], [-1.0, 3.0], [1.0, 5.0]])
    >>> assert np.allclose(sample @ gbf, gbb)
    >>> result = correct_ideal_conductor_boundary_flux(psi, sample, gbb, gbf)
    >>> assert isinstance(result, Result)
    >>> assert list(result) == [
    ...     'corrected_field_flux', 'boundary_currents',
    ...     'boundary_flux_correction', 'field_flux_correction',
    ...     'singular_values', 'effective_rank', 'residual', 'residual_norm'
    ... ]
    >>> assert result.corrected_field_flux is result['corrected_field_flux']
    >>> np.testing.assert_allclose(
    ...     result['corrected_field_flux'], [0.0, 0.125, -0.125]
    ... )
    >>> np.testing.assert_allclose(result['residual'], 0.0)
    >>> assert result['effective_rank'] == 2
    """
    field_flux = _finite_array("uncorrected_field_flux", uncorrected_field_flux, 1)
    samples = _finite_array("boundary_sample_matrix", boundary_sample_matrix, 2)
    boundary_green = _finite_array("green_boundary_to_boundary", green_boundary_to_boundary, 2)
    field_green = _finite_array("green_boundary_to_field", green_boundary_to_field, 2)
    if not np.isfinite(rcond) or rcond < 0.0:
        raise ValueError("rcond must be a non-negative finite value")
    if samples.shape[1] != field_flux.size:
        raise ValueError("boundary_sample_matrix column count must match uncorrected_field_flux")
    if boundary_green.shape[0] != samples.shape[0]:
        raise ValueError("green_boundary_to_boundary row count must match boundary samples")
    if field_green.shape[1] != boundary_green.shape[1]:
        raise ValueError("green_boundary_to_field must use the same boundary-source axis")
    if field_green.shape[0] != field_flux.size:
        raise ValueError("green_boundary_to_field row count must match uncorrected_field_flux")
    if boundary_green.size == 0:
        raise ValueError("green_boundary_to_boundary must not be empty")

    boundary_flux = samples @ field_flux
    left, singular_values, right_transpose = np.linalg.svd(boundary_green, full_matrices=False)
    keep = singular_values > rcond * singular_values[0]
    reciprocal = np.zeros_like(singular_values)
    reciprocal[keep] = 1.0 / singular_values[keep]
    pseudo_inverse = right_transpose.T @ (reciprocal[:, None] * left.T)
    boundary_currents = pseudo_inverse @ -boundary_flux
    boundary_correction = boundary_green @ boundary_currents
    field_correction = field_green @ boundary_currents
    residual = boundary_flux + boundary_correction
    return Result(
        {
            "corrected_field_flux": field_flux + field_correction,
            "boundary_currents": boundary_currents,
            "boundary_flux_correction": boundary_correction,
            "field_flux_correction": field_correction,
            "singular_values": singular_values,
            "effective_rank": int(np.count_nonzero(keep)),
            "residual": residual,
            "residual_norm": float(np.linalg.norm(residual)),
        }
    )


__all__ = ["correct_ideal_conductor_boundary_flux"]

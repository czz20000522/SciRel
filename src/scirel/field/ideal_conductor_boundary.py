"""Finite-dimensional ideal-conductor boundary correction."""

import math

import numpy as np

from scirel._result import Result


def _finite_array(name, value, ndim):
    array = np.asarray(value, dtype=float)
    if array.ndim != ndim:
        raise ValueError(f"{name} must be a {ndim}-D array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _dyadic(value):
    numerator, denominator = float(value).as_integer_ratio()
    return numerator, 1 - denominator.bit_length()


def _scaled_sum(terms):
    """Round an exact dyadic sum to 53 bits, without bounding its exponent.

    Each term is an integer times a power of two. Integer accumulation avoids
    both overflowing partial sums and losing small terms before cancellation.
    Only the final significand is rounded, to nearest with ties to even.
    """
    terms = [(n, e) for n, e in terms if n]
    if not terms:
        return 0.0, 0
    exponent = min(e for _, e in terms)
    total = sum(n << (e - exponent) for n, e in terms)
    magnitude = abs(total)
    shift = max(0, magnitude.bit_length() - 53)
    rounded = magnitude >> shift
    if shift:
        remainder = magnitude - (rounded << shift)
        halfway = 1 << (shift - 1)
        if remainder > halfway or (remainder == halfway and rounded % 2):
            rounded += 1
    mantissa, adjustment = math.frexp(float(rounded if total >= 0 else -rounded))
    return mantissa, exponent + shift + adjustment


def _exact_matvec(matrix, vector):
    dyadics = [(*_dyadic(m), int(e)) for m, e in zip(*vector, strict=True)]
    result = []
    for row in matrix:
        terms = []
        for coefficient, (n, e, scale) in zip(row, dyadics, strict=True):
            a, b = _dyadic(coefficient)
            terms.append((a * n, b + e + scale))
        result.append(_scaled_sum(terms))
    if not result:
        return np.zeros(0), np.zeros(0, dtype=np.int64)
    mantissa, exponent = zip(*result, strict=True)
    return np.array(mantissa), np.array(exponent, dtype=np.int64)


def _compensated_dot(matrix, vector, absolute_sum):
    """Pairwise sum with exact product/sum remainders in the bounded range.

    Both operands span at most 399 exponents. Matrix entries are normalized
    below one or already have exponents in [-200,200]; the vector is below
    one. Splitting at 27 bits cannot overflow, and nonzero remainder products
    stay normal (their lowest possible bit is >= 2**-904).
    """
    splitter = 2.0**27 + 1.0
    product = matrix * vector
    split = splitter * matrix
    high_a = split - (split - matrix)
    low_a = matrix - high_a
    split = splitter * vector
    high_b = split - (split - vector)
    low_b = vector - high_b
    remainder = ((high_a * high_b - product) + high_a * low_b + low_a * high_b) + low_a * low_b
    exact = np.all(remainder == 0.0, axis=1)
    correction = np.sum(remainder, axis=1)
    columns = matrix.shape[1]
    depth = 0
    while product.shape[1] > 1:
        pairs = product.shape[1] // 2
        a = product[:, : 2 * pairs : 2]
        b = product[:, 1 : 2 * pairs : 2]
        total = a + b
        virtual_b = total - a
        remainder = (a - (total - virtual_b)) + (b - virtual_b)
        exact &= np.all(remainder == 0.0, axis=1)
        correction += np.sum(remainder, axis=1)
        product = np.column_stack((total, product[:, -1])) if product.shape[1] % 2 else total
        depth += 1
    value = product[:, 0] + correction
    # Remainders have total magnitude <= (depth+1)*u*sum(abs(products)).
    # Rounding their sums contributes O(n*(depth+1)*u**2); factor 8 also
    # bounds the rounded positive absolute_sum and combining level sums.
    unit = np.finfo(float).eps / 2.0
    error = 8.0 * (columns + 1) * (depth + 1) * unit**2 * absolute_sum + 2 * unit * np.abs(value)
    return value, exact | (error <= 64 * np.finfo(float).eps * np.abs(value))


def _scaled_matvec(matrix, vector):
    """Use certified vectorized dots; exact rows handle unsafe ranges/cancellation."""
    mantissa, exponent = vector
    rows, columns = matrix.shape
    nonzero_vector = mantissa != 0.0
    if not columns or not np.any(nonzero_vector):
        return np.zeros(rows), np.zeros(rows, dtype=np.int64)
    absolute_matrix = np.abs(matrix)
    maximum = float(np.max(absolute_matrix, initial=0.0))
    if maximum == 0.0:
        return np.zeros(rows), np.zeros(rows, dtype=np.int64)
    nonzero_matrix = absolute_matrix != 0.0
    matrix_scale = math.frexp(maximum)[1]
    matrix_minimum = math.frexp(
        float(np.min(absolute_matrix, where=nonzero_matrix, initial=np.inf))
    )[1]
    vector_scale = int(np.max(exponent[nonzero_vector]))
    unit = np.finfo(float).eps / 2.0
    if (
        matrix_scale - matrix_minimum > 399
        or vector_scale - np.min(exponent[nonzero_vector]) > 399
        or columns * unit > 1.0 / 16.0
    ):
        return _exact_matvec(matrix, vector)
    if matrix_minimum >= -200 and matrix_scale <= 200:
        matrix_scale = 0
        scaled_matrix = matrix
    else:
        scaled_matrix = np.ldexp(matrix, -matrix_scale)
        absolute_matrix = np.ldexp(absolute_matrix, -matrix_scale)
    scaled_vector = np.ldexp(mantissa, exponent - vector_scale)
    value = scaled_matrix @ scaled_vector
    absolute_sum = absolute_matrix @ np.abs(scaled_vector)
    operations = np.count_nonzero(nonzero_matrix, axis=1)
    gamma = operations * unit / (1.0 - operations * unit)
    # Standard dot bound gamma_n*sum(abs(a*b)); also account for the rounded
    # positive dot used to bound that sum. This gate admits <=64eps error
    # relative to the computed component, not just a finite/nonzero result.
    error = (1 + 8 * np.finfo(float).eps) * gamma * absolute_sum / (1.0 - gamma)
    safe = error <= 64 * np.finfo(float).eps * np.abs(value)
    uncertain = ~safe
    if np.any(uncertain):
        value[uncertain], safe[uncertain] = _compensated_dot(
            scaled_matrix[uncertain], scaled_vector, absolute_sum[uncertain]
        )
    output_mantissa, output_exponent = np.frexp(value)
    output_exponent = output_exponent.astype(np.int64) + matrix_scale + vector_scale
    if not np.all(safe):
        output_mantissa[~safe], output_exponent[~safe] = _exact_matvec(matrix[~safe], vector)
    return output_mantissa, output_exponent


def _scaled_add(first, second):
    a, ea = first
    b, eb = second
    scale = np.where(a == 0.0, eb, np.where(b == 0.0, ea, np.maximum(ea, eb)))
    # If exponents differ by >54, the smaller operand is below half an ulp
    # of the already rounded larger operand; losing that tail cannot change
    # its nearest rounding. Possible cancellation has close, exact scales.
    total = np.ldexp(a, ea - scale) + np.ldexp(b, eb - scale)
    mantissa, exponent = np.frexp(total)
    return mantissa, exponent.astype(np.int64) + scale


def _materialize(vector):
    return np.ldexp(*vector)


def _scaled_norm(vector):
    mantissa, exponents = vector
    nonzero = mantissa != 0.0
    if not np.any(nonzero):
        return 0.0
    exponent = int(np.max(exponents[nonzero]))
    normalized = np.ldexp(mantissa, exponents - exponent)
    return float(np.ldexp(np.hypot.reduce(normalized), exponent))


def _svd_scale(matrix):
    """Choose an exact power-of-two scaling without discarding any input bit.

    The preferred exponent puts the largest entry in [1/2,1). Scaling down
    cannot move any entry's lowest nonzero bit below 2**-1074, so constrain it
    by that bit's exponent too. Scaling up cannot lose bits or overflow here.
    Mixed-scale matrices may therefore remain larger than one; no entry is
    silently dropped to obtain a normalized matrix. This protects the scaling
    conversion, not the conditioning or accuracy of the underlying SVD.
    """
    nonzero = matrix[matrix != 0.0]
    if not nonzero.size:
        return matrix, 0
    exponents = np.frexp(nonzero)[1]
    exponent = int(np.max(exponents))
    if exponent > 0 and np.min(exponents) - exponent < -1021:
        for value in nonzero:
            numerator, power = _dyadic(value)
            magnitude = abs(numerator)
            lowest_bit = (magnitude & -magnitude).bit_length() - 1 + power
            exponent = min(exponent, lowest_bit + 1074)
    return np.ldexp(matrix, -exponent), exponent


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
    FloatingPointError
        If SVD produces nonfinite singular values, or a required current,
        flux, singular value or residual norm is not representable as finite
        float64, or a nonzero current rounds to zero. Internal projections
        and mode coefficients may exceed that range without making the final
        result unrepresentable. Final flux underflow alone is allowed.
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

    For ``Gbb = U diag(s) V.T``, retain exactly ``s > rcond*s[0]`` and
    evaluate ``V @ ((U.T @ -sampled_flux) / s)`` in those directions.
    Scale the Green matrix by an exact power of two before SVD, constrained
    to preserve every input bit. Keep the internal singular values at that
    scale; the strict cutoff still uses physical float64 singular values
    and the rounded float64 product. Sampling, projection, modal division,
    current reconstruction and corrections retain separate binary exponents
    until each output is formed. Bounded-range dot products use vectorized
    arithmetic with a componentwise rounding-error check, including product
    and sum remainder compensation when needed. Unsafe ranges or unresolved
    cancellation use exact binary product accumulation instead. No reciprocal
    or full pseudoinverse is formed. A nonzero current lost to zero at output
    raises; otherwise Green corrections use the returned float64 currents.
    The residual norm uses
    scaled hypotenuse accumulation rather than squaring residual entries.
    Residual entries and their norm are rounded independently at output;
    the norm can be nonzero even if every entry rounds to subnormal zero.

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

    with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
        flux = np.frexp(field_flux)
        boundary_flux = _scaled_matvec(samples, flux)
        scaled_green, green_exponent = _svd_scale(boundary_green)
        left, internal_singular, right_transpose = np.linalg.svd(scaled_green, full_matrices=False)
        singular_values = np.ldexp(internal_singular, green_exponent)
        if not np.all(np.isfinite(singular_values)):
            raise FloatingPointError("boundary Green singular values are not finite float64")
        # An overflowing nonnegative cutoff still excludes all singular values,
        # just as in the original strict comparison (rcond may exceed one).
        with np.errstate(over="ignore"):
            keep = singular_values > rcond * singular_values[0]
        projection = _scaled_matvec(left[:, keep].T, (-boundary_flux[0], boundary_flux[1]))
        divisor, divisor_exponent = np.frexp(internal_singular[keep])
        quotient, quotient_exponent = np.frexp(projection[0] / divisor)
        modes = (
            quotient,
            projection[1] - divisor_exponent - green_exponent + quotient_exponent,
        )
        currents = _scaled_matvec(right_transpose[keep].T, modes)
        boundary_currents = _materialize(currents)
        if np.any((currents[0] != 0.0) & (boundary_currents == 0.0)):
            raise FloatingPointError(
                "nonzero boundary current underflows to zero at float64 output"
            )
        reusable_currents = np.frexp(boundary_currents)
        boundary_correction = _scaled_matvec(boundary_green, reusable_currents)
        field_correction = _scaled_matvec(field_green, reusable_currents)
        residual = _scaled_add(boundary_flux, boundary_correction)
        result = {
            "corrected_field_flux": _materialize(_scaled_add(flux, field_correction)),
            "boundary_currents": boundary_currents,
            "boundary_flux_correction": _materialize(boundary_correction),
            "field_flux_correction": _materialize(field_correction),
            "singular_values": singular_values,
            "effective_rank": int(np.count_nonzero(keep)),
            "residual": _materialize(residual),
            "residual_norm": _scaled_norm(residual),
        }
    if any(not np.all(np.isfinite(value)) for value in result.values()):
        raise FloatingPointError("boundary correction is not representable as finite float64")
    return Result(result)


__all__ = ["correct_ideal_conductor_boundary_flux"]

"""Spatial source-shape normalization with trapezoidal measure.

This relation normalizes a nonnegative spatial source profile:

normalize a nonnegative one-dimensional spatial source profile to unit
integral under the trapezoidal measure, returning the unit-integral shape in
``m^-1`` and the original spatial integral.

The saved trapezoidal arithmetic and unit-integral re-check with
``rtol=1e-12, atol=1e-14`` are retained for finite real arrays. SciRel rejects
boolean, string and complex coercions that the saved implementation accepted
or raised inconsistently. A zero profile is rejected, never silently replaced.

Evidence ceiling: maintained tests establish the normalization against an
independent trapezoidal recomputation and the failure contract. Finite
valid-path comparison with the saved implementation is bounded historical
development evidence, not qualified-L1 provenance; the saved bundle's strict
D1 qualification has been withdrawn.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "normalize_spatial_source_shape",
]


def _real_array(value, name):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            not isinstance(value, np.ndarray)
            and any(
                isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
            )
        ):
            raise ValueError
        return np.asarray(value, dtype=float)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a real numeric array") from error


def _trapezoid(values, coordinates):
    """Assemble the one-dimensional trapezoid rule locally with NumPy."""
    return np.sum(0.5 * (values[1:] + values[:-1]) * np.diff(coordinates))


def normalize_spatial_source_shape(source, x_m):
    r"""Normalize a nonnegative one-dimensional spatial source profile to unit integral under the trapezoidal measure, returning the unit-integral shape and the original integral.

    Parameters
    ----------
    source : real array-like, shape [n]
        The source profile. [source units].
        Constraints: A finite nonnegative real numeric one-dimensional array; boolean, string and complex coercions are rejected.
    x_m : real array-like, shape [n]
        The spatial coordinates. [m].
        Constraints: Finite real numeric values, strictly increasing, at least two nodes, aligned to the source; boolean, string and complex coercions are rejected.

    Returns
    -------
    shape_m_inv : float64 array, shape [n]
        The unit-integral source shape. [m^-1].
        Constraints: Finite and nonnegative; trapezoidal integral exactly re-checked to 1.
    integral_source : float scalar, shape scalar
        The original spatial integral. [source units times m].
        Constraints: Finite and strictly positive.

    Raises
    ------
    ValueError
        Raises ValueError for boolean, string or complex coercions, or when the alignment, finiteness, monotonicity or positivity contract is violated, or the normalized shape fails its unit-integral re-check. Raises ValueError when the integral or normalized shape is non-finite or the integral is nonpositive; no fallback is selected. Not applicable. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.normalize_incoming_neutral_boundary : Related neutral-transport operation.

    Notes
    -----
        The NumPy trapezoidal rule on the caller's coordinates; the unit-integral re-check uses rtol 1e-12, atol 1e-14; a zero profile is rejected, never silently replaced
    aligned finite one-dimensional profile and strictly increasing coordinates with at least two nodes; nonnegative source; finite positive integral

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import normalize_spatial_source_shape
    >>> source = np.array([1.0, 2.0, 1.0])
    >>> x_m = np.array([0.0, 1.0, 2.0])
    >>> result = normalize_spatial_source_shape(source, x_m)
    >>> assert result['integral_source'] == 3.0
    >>> np.testing.assert_array_equal(result['shape_m_inv'], source / 3.0)
    >>> assert np.trapezoid(result['shape_m_inv'], x_m) == 1.0
    >>> try:
    ...     normalize_spatial_source_shape(np.array([0.0, 0.0]), np.array([0.0, 1.0]))
    ... except ValueError as error:
    ...     assert 'positive spatial integral' in str(error)
    ... else:
    ...     raise AssertionError('a zero profile must be rejected')
    """
    profile = _real_array(source, "source")
    coordinates = _real_array(x_m, "x_m")
    if (
        profile.ndim != 1
        or coordinates.ndim != 1
        or profile.size != coordinates.size
        or profile.size < 2
        or not np.all(np.isfinite(profile))
        or not np.all(np.isfinite(coordinates))
        or np.any(profile < 0.0)
        or np.any(np.diff(coordinates) <= 0.0)
    ):
        raise ValueError("source and x_m must be aligned finite one-dimensional profiles")
    # For a nonnegative profile on a strictly increasing grid, an all-zero
    # profile has a zero integral by construction.  Reject it before loading
    # the integration backend so this invalid-input path stays dependency-light.
    if not np.any(profile > 0.0):
        raise ValueError("source must have a positive spatial integral")

    # Import on the valid path to preserve the package's optional-backend
    # visibility contract; the local assembler below remains the source of
    # the returned values.
    import scipy.integrate  # noqa: F401

    integral = float(_trapezoid(profile, coordinates))
    if not np.isfinite(integral) or integral <= 0.0:
        raise ValueError("source must have a positive spatial integral")
    shape = profile / integral
    if not np.all(np.isfinite(shape)):
        raise ValueError("normalized source shape must be finite")
    normalized_integral = float(_trapezoid(shape, coordinates))
    if not np.isclose(normalized_integral, 1.0, rtol=1.0e-12, atol=1.0e-14):
        raise ValueError("normalized source shape failed its unit-integral check")
    return {"shape_m_inv": shape, "integral_source": integral}

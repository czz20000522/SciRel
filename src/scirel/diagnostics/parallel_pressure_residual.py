"""Fixed-flux gyrotropic parallel-pressure compatibility check."""

import numpy as np

from scirel._result import Result

from ._fixed_flux_derivative import fixed_flux_derivative


def compute_parallel_pressure_residual(
    p_parallel,
    p_perp,
    magnetic_field,
    rtol=0.01,
    atol=1e-6,
    strict=False,
    *,
    dp_parallel_dB=None,
    field_axis=None,
    psi=None,
):
    """Check a local fixed-flux parallel-pressure relation.

    Parameters
    ----------
    p_parallel : array_like, shape (...)
        Parallel pressure samples in ``[Pa]``.  Values must be finite; negative
        values are not rejected.  The shape must exactly match ``p_perp`` and
        ``magnetic_field``, and the sample set must be nonempty.
    p_perp : array_like, shape (...)
        Perpendicular pressure samples in ``[Pa]`` with the same shape and
        finiteness constraints as ``p_parallel``.
    magnetic_field : array_like, shape (...)
        Positive magnetic-field magnitudes in ``[T]`` at the same samples.
        Duplicate field values are allowed with an explicit derivative;
        sampled fixed-flux lines require strict monotonicity.
    rtol : real scalar, optional
        Maximum allowed normalized residual for the ``passed`` flag in
        ``[dimensionless]``.  It must be finite and nonnegative.  The default
        is ``0.01``.
    atol : real scalar, optional
        Positive absolute pressure scale used in the normalized-residual
        denominator in ``[Pa]``.  It must be finite and strictly positive.  The
        default is ``1e-6``.
    strict : truth-valued, optional
        If truthy and the maximum normalized residual exceeds ``rtol``, raise
        ``ValueError`` instead of returning ``passed=False`` in
        ``[boolean flag]``.  It is interpreted by Python truth value and is not
        type-checked.  The default is ``False``.
    dp_parallel_dB : real scalar, array_like, or callable, optional
        Explicit fixed-psi derivative ``(partial p_parallel / partial B)_psi``
        in ``[Pa/T]``.  A scalar or array must broadcast exactly to the sample
        shape; a callable is evaluated as ``callable(B, psi)``.  It cannot be
        combined with ``field_axis``.
    field_axis : integer, optional
        Axis whose lines vary magnetic-field magnitude at fixed ``psi`` in
        ``[axis index]``.  With no explicit derivative, each line must contain
        at least two unique strictly monotone field samples.
    psi : real scalar or array_like, optional
        Flux labels broadcastable to the sample shape in
        ``[consistent caller flux coordinate]``.  It is mandatory and exactly
        constant along ``field_axis`` for sampled derivatives, and is forwarded
        to an explicit derivative callable otherwise.

    Returns
    -------
    rhs : ndarray of float64, same shape as the inputs
        Field ``rhs`` of the returned ``scirel._result.Result`` mapping,
        containing ``p_parallel - magnetic_field * dp_parallel_dB`` in
        ``[Pa]``.
    error : ndarray of float64, same shape as the inputs
        Field ``error`` of the returned result mapping, containing
        ``p_perp - rhs`` in ``[Pa]``.
    relative_error : ndarray of float64, same shape as the inputs
        Field ``relative_error`` of the returned result mapping, containing
        ``abs(error) / max(abs(p_perp), abs(rhs), atol)`` in
        ``[dimensionless]``.
    max_relative_error : float
        Field ``max_relative_error`` of the returned result mapping,
        containing the maximum pointwise relative error in
        ``[dimensionless]``.
    mean_relative_error : float
        Field ``mean_relative_error`` of the returned result mapping,
        containing the arithmetic mean of the pointwise relative errors in
        ``[dimensionless]``.
    passed : bool
        Field ``passed`` of the returned result mapping.  It is ``True``
        exactly when ``max_relative_error <= rtol`` in ``[boolean]``.
    dp_parallel_dB : ndarray of float64, same shape as the pressures
        Field ``dp_parallel_dB`` of the returned result mapping, containing
        the fixed-psi derivative actually used by the diagnostic in ``[Pa/T]``.
    derivative_method : str
        Field ``derivative_method`` of the returned result mapping,
        describing the derivative source in ``[text]``: either an explicit
        fixed-flux derivative or a declared fixed-flux axis finite difference.

    Raises
    ------
    ValueError
        If derivative information is missing or conflicts with ``field_axis``,
        array shapes or sample sets are invalid, values are nonfinite, the
        magnetic field is not strictly positive, a field axis is invalid,
        ``rtol`` or ``atol`` violates its bounds, or ``strict`` detects a
        failure.
    FloatingPointError
        If the derivative or a computed pressure residual is not finite.
    TypeError
        If a numeric input cannot be converted to float64 or a derivative
        callable has an incompatible call signature.

    See Also
    --------
    scirel.diagnostics.compute_pointwise_firehose_margin
        Evaluate the pointwise firehose pressure margin without a derivative.
    scirel.diagnostics.compute_firehose_mirror_margins
        Evaluate local firehose and fixed-flux mirror margins together.

    Notes
    -----
    The diagnostic uses

    ``rhs = p_parallel - B * (partial p_parallel / partial B)_psi``

    and ``error = p_perp - rhs``.  It does not flatten or globally sort spatial
    samples to manufacture a derivative.  An explicit zero derivative is
    required for constant-field isotropic data.  A sampled finite-difference
    derivative carries interpolation and sampling error, so a passing result is
    a local pressure-compatibility observation, not a spatial force-balance or
    global-stability proof.  All fields are returned in a
    ``scirel._result.Result`` mapping, which retains dictionary access and also
    exposes each field as an attribute.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.diagnostics.parallel_pressure_residual import compute_parallel_pressure_residual
    >>> r=compute_parallel_pressure_residual([3.,3.],[3.,3.],[2.,2.],dp_parallel_dB=0.)
    >>> assert isinstance(r, Result)
    >>> assert r.error is r['error']
    >>> np.testing.assert_array_equal(r['error'],[0.,0.])
    >>> assert r['passed']
    """
    p_parallel, p_perp, magnetic_field = (
        np.asarray(x, dtype=float) for x in (p_parallel, p_perp, magnetic_field)
    )
    if p_parallel.shape != p_perp.shape or p_parallel.shape != magnetic_field.shape:
        raise ValueError("p_parallel, p_perp, and magnetic_field must have the same shape")
    if p_parallel.size == 0:
        raise ValueError("parallel-pressure equilibrium requires at least one sample")
    if not np.all(np.isfinite(p_perp)):
        raise ValueError("pressures must be finite")
    if not np.isfinite(rtol) or not np.isfinite(atol) or rtol < 0 or atol <= 0:
        raise ValueError("rtol must be non-negative and atol must be positive finite values")
    derivative, method = fixed_flux_derivative(
        p_parallel, magnetic_field, derivative=dp_parallel_dB, field_axis=field_axis, psi=psi
    )
    rhs = p_parallel - magnetic_field * derivative
    error = p_perp - rhs
    relative_error = np.abs(error) / np.maximum(np.maximum(np.abs(p_perp), np.abs(rhs)), atol)
    if not all(np.all(np.isfinite(x)) for x in (rhs, error, relative_error)):
        raise FloatingPointError("parallel-pressure residual is not finite")
    maximum = float(np.max(relative_error))
    passed = bool(maximum <= rtol)
    if strict and not passed:
        raise ValueError("parallel equilibrium check failed")
    return Result(
        {
            "rhs": rhs,
            "error": error,
            "relative_error": relative_error,
            "max_relative_error": maximum,
            "mean_relative_error": float(np.mean(relative_error)),
            "passed": passed,
            "dp_parallel_dB": derivative,
            "derivative_method": method,
        }
    )


__all__ = ["compute_parallel_pressure_residual"]

"""Pointwise firehose margin and shared gyrotropic arithmetic kernels.

Single-sample and repeated/unsorted-field calls require no mirror derivative.
The combined diagnostic consumes the same validated arithmetic kernel.
"""

import numpy as np

from scirel._result import Result

MU0 = 4e-07 * np.pi


def _margin_kernel(magnetic_field, mu0, p_perp=0.0, p_parallel=0.0, derivative=None):
    """Evaluate the local relation without losing a cancellation residual.

    The vectorized path preserves normal float64 operation order. If opposing
    contributions reduce the result to at most half the largest contribution,
    at least one leading binary magnitude bit is lost: evaluate that sample as
    an exact rational expression, then round once. This arithmetic switch is
    not a physical tolerance, a clamp, or a zero-pressure special case.
    Intermediate overflow/underflow also takes the exact path; only a genuinely
    unrepresentable final result fails. Non-cancelling normal values retain
    their ordinary floating-point rounding.
    """
    from fractions import Fraction

    B, pt, pp = np.broadcast_arrays(magnetic_field, p_perp, p_parallel)
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        square = B * B
        magnetic = square / mu0
        if derivative is None:
            result = magnetic + pt - pp
            scale = np.maximum(np.abs(magnetic), np.maximum(np.abs(pt), np.abs(pp)))
            opposing = ((B != 0) | (pt > 0) | (pp < 0)) & ((pt < 0) | (pp > 0))
            product_range_loss = False
        else:
            product = B * derivative
            result = magnetic + product
            scale = np.maximum(np.abs(magnetic), np.abs(product))
            opposing = (B != 0) & (np.signbit(B) != np.signbit(derivative)) & (derivative != 0)
            product_range_loss = (
                (np.abs(product) < np.finfo(float).tiny) & (B != 0) & (derivative != 0)
            )
        cancellation = opposing & (np.abs(result) <= 0.5 * scale)
    exceptional = (
        ~np.isfinite(square)
        | ~np.isfinite(result)
        | ((np.abs(square) < np.finfo(float).tiny) & (B != 0))
        | ((np.abs(magnetic) < np.finfo(float).tiny) & (B != 0))
        | product_range_loss
        | cancellation
    )
    result = np.array(result, dtype=float, copy=True)
    if np.any(exceptional):
        d = None if derivative is None else np.broadcast_to(derivative, B.shape)
        permeability = Fraction.from_float(float(mu0))
        for index in zip(*np.nonzero(exceptional)) if B.ndim else [()]:
            if not exceptional[index]:
                continue
            field = Fraction.from_float(float(B[index]))
            exact = field * field / permeability
            if d is None:
                exact += Fraction.from_float(float(pt[index])) - Fraction.from_float(
                    float(pp[index])
                )
            else:
                exact += field * Fraction.from_float(float(d[index]))
            try:
                result[index] = float(exact)
            except OverflowError as exc:
                raise FloatingPointError(
                    "local pressure margin must be finite; exact result exceeds float64 range"
                ) from exc
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("local pressure margin must be finite")
    return result


def _firehose_kernel(p_parallel, p_perp, magnetic_field, mu0):
    """Shared local tension relation with finite-cancellation protection."""
    return _margin_kernel(magnetic_field, mu0, p_perp, p_parallel)


def _mirror_kernel(magnetic_field, derivative, mu0):
    """Fixed-flux total-pressure derivative with safe range and cancellation."""
    return _margin_kernel(magnetic_field, mu0, derivative=derivative)


def compute_pointwise_firehose_margin(p_parallel, p_perp, magnetic_field, mu0=MU0):
    """Compute the pointwise firehose pressure margin.

    Parameters
    ----------
    p_parallel : array_like, shape (...)
        Parallel pressure samples in ``[Pa]``.  Values must be finite and have
        exactly the same shape as ``p_perp`` and ``magnetic_field``.
    p_perp : array_like, shape (...)
        Perpendicular pressure samples in ``[Pa]``.  Values must be finite and
        have exactly the same shape as the other sample arrays.
    magnetic_field : array_like, shape (...)
        Magnetic-field samples in ``[T]`` used by the ``B**2 / mu0`` magnetic
        tension term.  Values must be finite and have exactly the same shape
        as the pressure arrays.
    mu0 : real scalar, optional
        Positive finite magnetic permeability in ``[H/m]``.  The default is
        ``4e-7 * pi``.  Non-scalar values are rejected rather than broadcast.

    Returns
    -------
    firehose_margin : ndarray of float64, same shape as inputs
        Field of the returned ``scirel._result.Result`` mapping containing
        ``B**2 / mu0 + p_perp - p_parallel`` in ``[Pa]``.  Scalar inputs
        produce a zero-dimensional float64 array.  The sign is not interpreted,
        clamped, or converted into a stability flag.

    Raises
    ------
    ValueError
        If the sample shapes differ, the sample set is empty, an input is
        nonfinite, ``mu0`` is not a positive finite scalar, or the final
        mathematical margin cannot be represented as finite float64.
    TypeError
        If an input or ``mu0`` has an element type that cannot be converted to
        float64.

    See Also
    --------
    scirel.diagnostics.compute_firehose_mirror_margins
        Combined diagnostic that adds a separately supplied fixed-flux mirror
        derivative and local stability flags.

    Notes
    -----
    The local relation is evaluated independently at every sample.  No sorting,
    derivative, minimum reduction, or aggregate stability decision is applied.
    The single ``firehose_margin`` field is returned in a
    ``scirel._result.Result`` mapping, which retains dictionary access and also
    exposes the field as an attribute.  Normal non-cancelling values retain
    their ordinary float64 operation order; dangerous cancellation or
    intermediate range loss evaluates the same binary-rational relation once
    before the final float64 rounding.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel._result import Result
    >>> from scirel.diagnostics import compute_pointwise_firehose_margin
    >>> mu0 = 4.0e-7 * np.pi
    >>> single = compute_pointwise_firehose_margin(810000.0, 740000.0, 0.93)
    >>> assert isinstance(single, Result)
    >>> assert single.firehose_margin is single['firehose_margin']
    >>> assert float(single['firehose_margin']) == 0.93 ** 2 / mu0 + 740000.0 - 810000.0
    >>> B = np.array([2.0, 1.0, 3.0, 1.5])
    >>> p_perp = 5.0 + 3.0 * B
    >>> result = compute_pointwise_firehose_margin(p_perp - 2.0, p_perp, B)
    >>> np.testing.assert_allclose(result.firehose_margin, B * B / mu0 + 2.0)
    >>> assert set(result.keys()) == {'firehose_margin'}
    >>> assert float(compute_pointwise_firehose_margin(1e100, 1e100, 1., mu0=1.).firehose_margin) == 1.
    """
    p_parallel = np.asarray(p_parallel, dtype=float)
    p_perp = np.asarray(p_perp, dtype=float)
    magnetic_field = np.asarray(magnetic_field, dtype=float)
    if p_parallel.shape != p_perp.shape or p_parallel.shape != magnetic_field.shape:
        raise ValueError("p_parallel, p_perp, and magnetic_field must have the same shape")
    if p_parallel.size == 0:
        raise ValueError("p_parallel, p_perp, and magnetic_field must be nonempty")
    if not all((np.all(np.isfinite(value)) for value in (p_parallel, p_perp, magnetic_field))):
        raise ValueError("p_parallel, p_perp, and magnetic_field must contain only finite values")
    if np.ndim(mu0) != 0 or isinstance(mu0, (list, tuple, np.ndarray)):
        raise ValueError("mu0 must be a scalar")
    if not np.isfinite(mu0) or mu0 <= 0.0:
        raise ValueError("mu0 must be positive and finite")
    try:
        firehose_margin = _firehose_kernel(p_parallel, p_perp, magnetic_field, float(mu0))
    except FloatingPointError as exc:
        raise ValueError(str(exc)) from exc
    return Result(firehose_margin=firehose_margin)


__all__ = ["compute_pointwise_firehose_margin", "MU0"]

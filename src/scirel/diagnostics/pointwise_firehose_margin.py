"""Pointwise firehose margin and shared gyrotropic arithmetic kernels.

Single-sample and repeated/unsorted-field calls require no mirror derivative.
The combined diagnostic consumes the same validated arithmetic kernel.
"""
import numpy as np
MU0 = 4e-07 * np.pi


def _margin_kernel(magnetic_field, mu0, p_perp=0., p_parallel=0., derivative=None):
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
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
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
            product_range_loss = (np.abs(product) < np.finfo(float).tiny) & (B != 0) & (derivative != 0)
        cancellation = opposing & (np.abs(result) <= 0.5 * scale)
    exceptional = (~np.isfinite(square) | ~np.isfinite(result) |
                   ((np.abs(square) < np.finfo(float).tiny) & (B != 0)) |
                   ((np.abs(magnetic) < np.finfo(float).tiny) & (B != 0)) |
                   product_range_loss | cancellation)
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
                exact += Fraction.from_float(float(pt[index])) - Fraction.from_float(float(pp[index]))
            else:
                exact += field * Fraction.from_float(float(d[index]))
            try:
                result[index] = float(exact)
            except OverflowError as exc:
                raise FloatingPointError('local pressure margin must be finite; exact result exceeds float64 range') from exc
    if not np.all(np.isfinite(result)):
        raise FloatingPointError('local pressure margin must be finite')
    return result


def _firehose_kernel(p_parallel, p_perp, magnetic_field, mu0):
    """Shared local tension relation with finite-cancellation protection."""
    return _margin_kernel(magnetic_field, mu0, p_perp, p_parallel)


def _mirror_kernel(magnetic_field, derivative, mu0):
    """Fixed-flux total-pressure derivative with safe range and cancellation."""
    return _margin_kernel(magnetic_field, mu0, derivative=derivative)


def compute_pointwise_firehose_margin(p_parallel, p_perp, magnetic_field, mu0=MU0):
    """Return the pointwise firehose margin B^2/mu0 + p_perp - p_parallel in Pa."""
    p_parallel = np.asarray(p_parallel, dtype=float)
    p_perp = np.asarray(p_perp, dtype=float)
    magnetic_field = np.asarray(magnetic_field, dtype=float)
    if p_parallel.shape != p_perp.shape or p_parallel.shape != magnetic_field.shape:
        raise ValueError('p_parallel, p_perp, and magnetic_field must have the same shape')
    if p_parallel.size == 0:
        raise ValueError('p_parallel, p_perp, and magnetic_field must be nonempty')
    if not all((np.all(np.isfinite(value)) for value in (p_parallel, p_perp, magnetic_field))):
        raise ValueError('p_parallel, p_perp, and magnetic_field must contain only finite values')
    if np.ndim(mu0) != 0 or isinstance(mu0, (list, tuple, np.ndarray)):
        raise ValueError('mu0 must be a scalar')
    if not np.isfinite(mu0) or mu0 <= 0.0:
        raise ValueError('mu0 must be positive and finite')
    try:
        firehose_margin = _firehose_kernel(p_parallel, p_perp, magnetic_field, float(mu0))
    except FloatingPointError as exc:
        raise ValueError(str(exc)) from exc
    return {'firehose_margin': firehose_margin}
__all__ = ['compute_pointwise_firehose_margin', 'MU0']

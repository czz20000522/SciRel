"""Shared mirror end-loss numerical kernel."""
import math
import numpy as np
from scirel._numerics import _scaled_difference

def _barrier_log_integral(a, b):
    """Log integral exp(-x-max(a*x+b,0)) dx on [0,infinity)."""
    if not math.isfinite(a) or not math.isfinite(b):
        raise FloatingPointError('dimensionless barrier must be finite')
    if a == 0.0:
        return -max(b, 0.0)
    if a > 0.0:
        if b >= 0.0:
            return -b - math.log1p(a)
        r = -b / a
        if math.isinf(r):
            return 0.0
        # Both terms positive; this retains the small result for large a,r~0.
        first = -math.expm1(-r)
        return float(np.logaddexp(math.log(first) if first else -math.inf,
                                 -r - math.log1p(a)))
    if b <= 0.0:
        return 0.0
    r = -b / a
    if math.isinf(r):
        return -b - math.log1p(a)
    if r == 0.0:
        # The cutoff is below the representable integration coordinate; its
        # contribution is below the binary64 rounding error of unit flux.
        return 0.0
    delta = abs((1.0 + a) * r)
    # Integral on [0,r] is a divided difference of exp(-b),exp(-r).
    factor = 1.0 if delta == 0.0 else -math.expm1(-delta) / delta
    first_log = -min(b, r) + math.log(r) + math.log(factor)
    return float(np.logaddexp(first_log, -r))


def _mirror_flux(density, mass, charge, t_parallel, t_perp, b_ref,
                 b_plug, phi_ref, phi_plug, refill, *, return_log=False):
    arrays = np.broadcast_arrays(*[np.asarray(x, dtype=float) for x in
        (density, mass, charge, t_parallel, t_perp, b_ref, b_plug,
         phi_ref, phi_plug, refill)])
    if not all(np.all(np.isfinite(a)) for a in arrays):
        raise ValueError('end-loss inputs must be finite')
    n, m, q, tp, tt, br, bp, pr, pp, fill = arrays
    if np.any(n < 0) or np.any(m <= 0) or np.any(tp <= 0) or np.any(tt <= 0) or np.any(br <= 0) or np.any(bp <= 0) or np.any(fill < 0) or np.any(fill > 1):
        raise ValueError('end-loss density, temperatures, fields or refill are invalid')
    result = np.empty(n.shape)
    for idx in np.ndindex(n.shape):
        if n[idx] == 0 or fill[idx] == 0:
            result[idx] = -math.inf
            continue
        a = float(tt[idx] / tp[idx]) * (float(bp[idx] / br[idx]) - 1.0)
        b = float(_scaled_difference(pp[idx],pr[idx],q[idx],tp[idx]))
        result[idx] = (math.log(float(n[idx])) + .5 * (math.log(float(tp[idx]))
            - math.log(2 * math.pi) - math.log(float(m[idx])))
            + math.log(float(fill[idx])) + _barrier_log_integral(a, b))
    if return_log:
        return result
    with np.errstate(over='ignore', under='ignore'):
        flux = np.exp(result)
    if not np.all(np.isfinite(flux)):
        raise FloatingPointError('end-loss flux exceeds the finite output range')
    return flux

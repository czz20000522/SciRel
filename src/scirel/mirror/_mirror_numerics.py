"""Private numerical kernels shared by the mirror modules."""

import math
import numpy as np
from scirel._numerics import _scaled_difference


def _barrier_log_integral(a, b):
    """Log integral exp(-x-max(a*x+b,0)) dx on [0,infinity)."""
    if not math.isfinite(a) or not math.isfinite(b):
        raise FloatingPointError("dimensionless barrier must be finite")
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
        return float(np.logaddexp(math.log(first) if first else -math.inf, -r - math.log1p(a)))
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


def _mirror_flux(
    density,
    mass,
    charge,
    t_parallel,
    t_perp,
    b_ref,
    b_plug,
    phi_ref,
    phi_plug,
    refill,
    *,
    return_log=False,
):
    arrays = np.broadcast_arrays(
        *[
            np.asarray(x, dtype=float)
            for x in (
                density,
                mass,
                charge,
                t_parallel,
                t_perp,
                b_ref,
                b_plug,
                phi_ref,
                phi_plug,
                refill,
            )
        ]
    )
    if not all(np.all(np.isfinite(a)) for a in arrays):
        raise ValueError("end-loss inputs must be finite")
    n, m, q, tp, tt, br, bp, pr, pp, fill = arrays
    if (
        np.any(n < 0)
        or np.any(m <= 0)
        or np.any(tp <= 0)
        or np.any(tt <= 0)
        or np.any(br <= 0)
        or np.any(bp <= 0)
        or np.any(fill < 0)
        or np.any(fill > 1)
    ):
        raise ValueError("end-loss density, temperatures, fields or refill are invalid")
    result = np.empty(n.shape)
    for idx in np.ndindex(n.shape):
        if n[idx] == 0 or fill[idx] == 0:
            result[idx] = -math.inf
            continue
        a = float(tt[idx] / tp[idx]) * (float(bp[idx] / br[idx]) - 1.0)
        b = float(_scaled_difference(pp[idx], pr[idx], q[idx], tp[idx]))
        result[idx] = (
            math.log(float(n[idx]))
            + 0.5 * (math.log(float(tp[idx])) - math.log(2 * math.pi) - math.log(float(m[idx])))
            + math.log(float(fill[idx]))
            + _barrier_log_integral(a, b)
        )
    if return_log:
        return result
    with np.errstate(over="ignore", under="ignore"):
        flux = np.exp(result)
    if not np.all(np.isfinite(flux)):
        raise FloatingPointError("end-loss flux exceeds the finite output range")
    return flux


def _trapped_fractions(a_left, b_left, a_right, b_right, order=32):
    """Return density, parallel and perpendicular fractions with error control.

    Integrals have absolute tolerance 2e-13 and relative tolerance 2e-11 in
    dimensionless fractions. The discarded x>40 tail is bounded by
    41*exp(-40)<1.75e-16 for all three moments. Order sets subdivision work;
    failure to meet the estimate raises rather than returning an unchecked
    fixed-node result. Magnetic-only barriers are integrated analytically.
    """
    fields = np.broadcast_arrays(
        *[np.asarray(x, dtype=float) for x in (a_left, b_left, a_right, b_right)]
    )
    if not all(np.all(np.isfinite(x)) for x in fields):
        raise FloatingPointError("dimensionless trapping barriers must be finite")
    answer = np.empty((3,) + fields[0].shape)
    cache = {}
    for idx in np.ndindex(fields[0].shape):
        key = tuple(float(x[idx]) for x in fields)
        if key not in cache:
            a, b, c, d = key
            if b == 0.0 and d == 0.0:
                alpha = min(a, c)
                xi = math.sqrt(alpha / (1 + alpha)) if alpha > 0 else 0.0
                values = np.array([xi, xi**3, 0.5 * xi * (3 - xi * xi)])
            else:
                # Keep the mirror namespace dependency-light until a plugged
                # profile actually needs incomplete-gamma quadrature.  The
                # magnetic-only branch above is analytic and must remain
                # usable without importing SciPy.
                from scipy.integrate import quad_vec
                from scipy.special import gammainc

                points = {0.0, 40.0}
                # Split at zeros, barrier intersections and the transition
                # scale of incomplete gamma, including narrow loss cones.
                for slope, intercept in [(a, b), (c, d)]:
                    if slope:
                        for target in (0.0, 1e-6, 0.01, 0.1, 1.0, 10.0, 40.0):
                            x = (target - intercept) / slope
                            if 0 < x < 40:
                                points.add(x)
                if a != c:
                    x = (d - b) / (a - c)
                    if 0 < x < 40:
                        points.add(x)
                roots = sorted(math.sqrt(x) for x in points)

                def integrand(t):
                    x = t * t
                    y = max(min(a * x + b, c * x + d), 0.0)
                    den = gammainc(0.5, y)
                    return (2 * t * math.exp(-x)) * np.array([den, gammainc(1.5, y), x * den])

                values, error, info = quad_vec(
                    integrand,
                    0.0,
                    math.sqrt(40.0),
                    points=roots[1:-1],
                    epsabs=2e-13,
                    epsrel=2e-11,
                    norm="max",
                    limit=max(256, 16 * int(order)),
                    full_output=True,
                )
                if (
                    not info.success
                    or not math.isfinite(error)
                    or error > max(2e-13, 2e-11 * float(np.max(np.abs(values))))
                ):
                    raise RuntimeError("trapped-moment quadrature did not meet its error bound")
                if (
                    not np.all(np.isfinite(values))
                    or np.any(values < 0)
                    or np.any(values > 1 + 2e-12)
                ):
                    raise FloatingPointError("invalid trapped-moment fractions")
            cache[key] = values
        answer[(slice(None),) + idx] = cache[key]
    return tuple(answer)


def _density_exponential(density, temperature_ratio, exponent):
    """Unclipped Boltzmann normalization with finite-output enforcement."""
    n, ratio, arg = np.broadcast_arrays(density, temperature_ratio, exponent)
    if (
        not all(np.all(np.isfinite(x)) for x in (n, ratio, arg))
        or np.any(n < 0)
        or np.any(ratio <= 0)
    ):
        raise FloatingPointError("distribution normalization is invalid or nonfinite")
    result = np.zeros(n.shape)
    active = n > 0
    with np.errstate(over="ignore", under="ignore"):
        result[active] = np.exp(np.log(n[active]) + np.log(ratio[active]) + arg[active])
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("distribution moments exceed the finite output range")
    return result


def _positive_product(*factors):
    """Multiply nonnegative finite factors without premature over/underflow."""
    arrays = np.broadcast_arrays(*[np.asarray(x, dtype=float) for x in factors])
    if any(not np.all(np.isfinite(x)) or np.any(x < 0) for x in arrays):
        raise FloatingPointError("moment factors must be finite and nonnegative")
    active = np.ones(arrays[0].shape, dtype=bool)
    for x in arrays:
        active &= x > 0
    logvalue = np.zeros(arrays[0].shape)
    for x in arrays:
        logvalue[active] += np.log(x[active])
    result = np.zeros(arrays[0].shape)
    with np.errstate(over="ignore", under="ignore"):
        result[active] = np.exp(logvalue[active])
    if not np.all(np.isfinite(result)):
        raise FloatingPointError("mirror moments exceed the finite output range")
    return result

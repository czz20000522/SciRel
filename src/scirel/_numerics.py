"""Private numerical kernels shared across scientific domains."""

from __future__ import annotations

import numpy as np


def stable_gradient(values, coordinates, axis):
    """Quadratic three-point derivative written as local value differences."""

    f = np.moveaxis(np.asarray(values, dtype=float), axis, -1)
    h = np.diff(np.asarray(coordinates, dtype=float))
    slopes = np.diff(f, axis=-1) / h
    result = np.empty_like(f)
    result[..., 1:-1] = (
        h[1:] * slopes[..., :-1] + h[:-1] * slopes[..., 1:]
    ) / (h[:-1] + h[1:])
    result[..., 0] = slopes[..., 0] - h[0] * (slopes[..., 1] - slopes[..., 0]) / (h[0] + h[1])
    result[..., -1] = slopes[..., -1] + h[-1] * (slopes[..., -1] - slopes[..., -2]) / (h[-2] + h[-1])
    return np.moveaxis(result, -1, axis)


def _potential_midpoint(left, right):
    """Finite binary64 midpoint, preserving a large common potential origin."""

    a, b = np.broadcast_arrays(np.asarray(left, dtype=float), np.asarray(right, dtype=float))
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise FloatingPointError("potential bracket endpoints must be finite")
    same = np.signbit(a) == np.signbit(b)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        value = np.asarray(np.where(same, a + (b - a) * 0.5, a * 0.5 + b * 0.5))
    tiny = np.maximum(abs(a), abs(b)) < 2 * np.finfo(float).tiny
    if np.any(tiny):
        from fractions import Fraction

        for idx in np.ndindex(value.shape):
            if tiny[idx]:
                value[idx] = float((Fraction(float(a[idx])) + Fraction(float(b[idx]))) / 2)
    return value


def _scaled_difference(left, right, multiplier, divisor):
    """Compute multiplier*(left-right)/divisor without absolute-origin loss."""

    a, b, q, t = np.broadcast_arrays(*[np.asarray(x, dtype=float) for x in (left, right, multiplier, divisor)])
    if not all(np.all(np.isfinite(x)) for x in (a, b, q, t)) or np.any(t <= 0.0):
        raise ValueError("scaled difference requires finite inputs and a positive divisor")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        delta = a - b
        wide = ~np.isfinite(delta)
        delta = np.where(wide, a * 0.5 - b * 0.5, delta)
        md, ed = np.frexp(delta)
        mq, eq = np.frexp(q)
        mt, et = np.frexp(t)
        value = np.asarray(np.ldexp(md * mq / mt, ed + wide.astype(np.int64) + eq - et))
    if not np.all(np.isfinite(value)):
        from fractions import Fraction

        for idx in np.ndindex(value.shape):
            if not np.isfinite(value[idx]):
                exact = Fraction(float(q[idx])) * (Fraction(float(a[idx])) - Fraction(float(b[idx]))) / Fraction(float(t[idx]))
                try:
                    value[idx] = float(exact)
                except OverflowError as exc:
                    raise FloatingPointError("scaled physical difference exceeds the finite range") from exc
        if not np.all(np.isfinite(value)):
            raise FloatingPointError("scaled physical difference exceeds the finite range")
    return value


__all__ = ["stable_gradient"]

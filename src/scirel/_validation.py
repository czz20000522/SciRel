"""Shared input checks with distinct required/default contracts."""

import numpy as np


def required_finite_scalar(value, name, *, positive=False, nonnegative=False):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a finite scalar")
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite scalar") from exc
    if array.ndim != 0 or not np.isrealobj(array) or (not bool(np.all(np.isfinite(array)))):
        raise ValueError(f"{name} must be a finite scalar")
    result = float(array)
    if positive and result <= 0.0:
        raise ValueError(f"{name} must be strictly positive")
    if nonnegative and result < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def required_integer_scalar(value, name, *, minimum):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer scalar")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return result


def finite_scalar(value, name, default):
    if value is None:
        value = default
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite scalar") from exc
    if array.ndim != 0 or not np.isrealobj(array) or (not bool(np.all(np.isfinite(array)))):
        raise ValueError(f"{name} must be a finite scalar")
    return float(array)


def integer_scalar(value, name, default, *, minimum):
    if value is None:
        value = default
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer scalar")
    result = int(value)
    if result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return result


def bool_scalar(value, name, default):
    if value is None:
        value = default
    if not isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a boolean scalar")
    return bool(value)

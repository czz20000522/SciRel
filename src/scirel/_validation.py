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


def finite_complex_array(value, name, *, asset_id):
    """Promote a nonempty unmasked numeric scalar/array to finite complex128."""
    legal = f"legal input: nonempty unmasked finite real/complex numbers; see {asset_id}"
    if np.ma.isMaskedArray(value):
        raise TypeError(f"{name} must be unmasked; received a masked array; {legal}")
    try:
        objects = np.asarray(value, dtype=object)
        raw = np.asarray(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(
            f"{name} must have a rectangular numeric shape; received unusable input; {legal}"
        ) from error
    received = f"received shape={raw.shape}, dtype={raw.dtype}"
    if (
        any(isinstance(item, (bool, np.bool_)) for item in objects.flat)
        or raw.dtype.kind not in "iufc"
    ):
        raise TypeError(
            f"{name} must contain real or complex numbers, without booleans or strings; {received}; {legal}"
        )
    if raw.size == 0:
        raise ValueError(f"{name} must be nonempty and finite; {received}; {legal}")
    try:
        with np.errstate(over="ignore", invalid="ignore"):
            result = np.asarray(value, dtype=np.complex128)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must fit finite complex128; {received}; {legal}") from error
    bad = np.count_nonzero(~np.isfinite(result))
    if bad:
        raise ValueError(
            f"{name} must be finite after complex128 conversion; {received}, nonfinite={bad}; {legal}"
        )
    return result

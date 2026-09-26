"""Shared input checks with distinct required/default contracts."""
import numpy as np

def required_finite_scalar(value, name, *, positive=False, nonnegative=False):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f'{name} must be a finite scalar')
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} must be a finite scalar') from exc
    if array.ndim != 0 or not np.isrealobj(array) or (not bool(np.all(np.isfinite(array)))):
        raise ValueError(f'{name} must be a finite scalar')
    result = float(array)
    if positive and result <= 0.0:
        raise ValueError(f'{name} must be strictly positive')
    if nonnegative and result < 0.0:
        raise ValueError(f'{name} must be nonnegative')
    return result

def required_integer_scalar(value, name, *, minimum):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f'{name} must be an integer scalar')
    result = int(value)
    if result < minimum:
        raise ValueError(f'{name} must be >= {minimum}')
    return result

def finite_scalar(value, name, default):
    if value is None:
        value = default
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} must be a finite scalar') from exc
    if array.ndim != 0 or not np.isrealobj(array) or (not bool(np.all(np.isfinite(array)))):
        raise ValueError(f'{name} must be a finite scalar')
    return float(array)

def integer_scalar(value, name, default, *, minimum):
    if value is None:
        value = default
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise ValueError(f'{name} must be an integer scalar')
    result = int(value)
    if result < minimum:
        raise ValueError(f'{name} must be >= {minimum}')
    return result

def bool_scalar(value, name, default):
    if value is None:
        value = default
    if not isinstance(value, (bool, np.bool_)):
        raise ValueError(f'{name} must be a boolean scalar')
    return bool(value)

JH_PAYLOAD_FIELDS = (
    'DKnot',
    'TKnot',
    'order',
    'LogR_BSCoef',
    'LogS_BSCoef',
    'LogAlpha_BSCoef',
    'A_Lyman',
    'A_Balmer',
)

def validate_jh_payload(jh_payload):
    """The saved ``_validate_payload`` contract, shared by the JH radiation graphs.

    Contract-identical to ``scirel.collisions.hydrogen_jh_s_coefficient``'s
    copy (both reproduce the saved formal implementation, messages included):
    an exact-field eight-field mapping, one-dimensional non-decreasing finite
    knots, the order field fixed at 4 -- consumed by FITPACK as the spline
    degree -- a knot geometry describing exactly 77 coefficients, and finite
    values in every field, including the fields a given radiation branch does
    not numerically consume.
    """
    if not isinstance(jh_payload, dict):
        raise ValueError('jh_payload must be a mapping')
    required = set(JH_PAYLOAD_FIELDS)
    if set(jh_payload) != required:
        raise ValueError('jh_payload fields are incomplete')
    density_knots = np.asarray(jh_payload['DKnot'], dtype=float)
    temperature_knots = np.asarray(jh_payload['TKnot'], dtype=float)
    order = int(jh_payload['order'])
    if density_knots.ndim != 1 or temperature_knots.ndim != 1 or order != 4:
        raise ValueError('jh_payload knots/order are invalid')
    if not np.all(np.diff(density_knots) >= 0.0) or not np.all(np.diff(temperature_knots) >= 0.0):
        raise ValueError('jh_payload knots must be non-decreasing')
    if (temperature_knots.size - order - 1) * (density_knots.size - order - 1) != 77:
        raise ValueError('jh_payload knot dimensions do not describe 77 coefficients')
    if not all(np.all(np.isfinite(np.asarray(jh_payload[name], dtype=float))) for name in required - {'order'}):
        raise ValueError('jh_payload must be finite')
    return density_knots, temperature_knots, order

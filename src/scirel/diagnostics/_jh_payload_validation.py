"""JH payload validation support for the hydrogen radiation diagnostics graphs.

This module exists outside ``scirel._validation`` because the historical
admission ledger content-locks that support module byte for byte; adding a
contract to it would break the recorded LF SHA-256 lock.  The contract below
reproduces the saved formal implementation's ``_validate_payload`` exactly
(the same contract the r57 ``hydrogen_jh_s_coefficient`` / ``_alpha`` assets
carry), messages included.  It is not an asset, is not exported from the
package, and serves only the internal import closure of the three JH
radiation task graphs.
"""
from __future__ import annotations

import numpy as np

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

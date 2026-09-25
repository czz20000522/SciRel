"""Atomic-hydrogen Johnson-Hinnov s-coefficient B-spline evaluation.

One leaf recovered from the saved KN1DPy ``原子氢JH-r系数B样条评价`` package
(source anchor ``KN1DPy/jh_related/jhs_coef.py:24-60`` with the payload
common-block anchor ``KN1DPy/common/JH_Coef.py:5-29``, both as recorded by
the saved bundle's own extraction report), integrated as
:func:`evaluate_h_jh_s_coefficient`:

the Johnson-Hinnov hydrogen s coefficient, evaluated as a cubic B-spline over
``(log Te, log n)`` with the caller-supplied explicit payload (knots, order
and the ``LogS_BSCoef`` coefficient vector) and the saved source's endpoint
clipping in both coordinates.

**The evaluation is the saved formal implementation's, exactly, and this
leaf consumes the caller's density.**  Unlike the sibling r and alpha
branches, the saved s branch evaluates the spline at the caller's clipped
``log`` density; the r and alpha branches overwrite that coordinate with the
source's ``1e32`` null sentinel.  The three branches are kept as separate
SciRel assets precisely because their density semantics differ.

**No repair is claimed for this leaf.**  The saved formal implementation
enforces its declared input contract (non-empty one-dimensional paired
arrays, finite and strictly positive density and temperature, an exact-field
read-only payload with one-dimensional non-decreasing finite knots, source
cubic order ``4``, a knot/field geometry describing exactly 77 coefficients,
and ``no_null == 1``); the contract is reproduced bit for bit, messages
included.

Evidence ceiling: this module establishes the B-spline evaluation against an
independent FITPACK evaluation of the same spline, the endpoint clipping,
the payload validation contract, the density dependence witness, and -- in
the environment-gated replay test -- exact agreement with the saved KN1DPy
implementation on the packaged coefficient payload.  The saved bundle's
strict D1 qualification has been withdrawn; that replay is historical
development evidence, not qualified-L1 provenance.  No test establishes the
coefficient table against an external atomic-physics reference: the saved
package records that residual as ``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import bisplev

__all__ = [
    "evaluate_h_jh_s_coefficient",
]

_PAYLOAD_FIELDS = (
    "DKnot",
    "TKnot",
    "order",
    "LogR_BSCoef",
    "LogS_BSCoef",
    "LogAlpha_BSCoef",
    "A_Lyman",
    "A_Balmer",
)


def _validate_profile(density_m3, temperature_ev):
    density = np.asarray(density_m3, dtype=float)
    temperature = np.asarray(temperature_ev, dtype=float)
    if (
        density.ndim != 1
        or temperature.ndim != 1
        or density.size == 0
        or density.shape != temperature.shape
        or not np.all(np.isfinite(density))
        or not np.all(np.isfinite(temperature))
        or np.any(density <= 0.0)
        or np.any(temperature <= 0.0)
    ):
        raise ValueError("density_m3 and temperature_ev must be finite positive same-shaped 1-D arrays")
    return density, temperature


def _validate_payload(jh_payload):
    if not isinstance(jh_payload, dict):
        raise ValueError("jh_payload must be a mapping")
    required = set(_PAYLOAD_FIELDS)
    if set(jh_payload) != required:
        raise ValueError("jh_payload fields are incomplete")
    density_knots = np.asarray(jh_payload["DKnot"], dtype=float)
    temperature_knots = np.asarray(jh_payload["TKnot"], dtype=float)
    order = int(jh_payload["order"])
    if density_knots.ndim != 1 or temperature_knots.ndim != 1 or order != 4:
        raise ValueError("jh_payload knots/order are invalid")
    if not np.all(np.diff(density_knots) >= 0.0) or not np.all(np.diff(temperature_knots) >= 0.0):
        raise ValueError("jh_payload knots must be non-decreasing")
    if (temperature_knots.size - order - 1) * (density_knots.size - order - 1) != 77:
        raise ValueError("jh_payload knot dimensions do not describe 77 coefficients")
    if not all(np.all(np.isfinite(np.asarray(jh_payload[name], dtype=float))) for name in required - {"order"}):
        raise ValueError("jh_payload must be finite")
    return density_knots, temperature_knots, order


def evaluate_h_jh_s_coefficient(density_m3, temperature_ev, jh_payload, no_null=1):
    """Return the source no_null=1 JH s coefficient branch.

    Parameters
    ----------
    density_m3
        Densities in ``m^-3`` as a non-empty one-dimensional array; must be
        finite and strictly positive.  The caller's values enter the spline
        after clipping to the density-knot range.
    temperature_ev
        Temperatures in eV, a one-dimensional array of the same shape; must
        be finite and strictly positive.  Values outside the knot range are
        clipped to it, the saved source's endpoint behavior.
    jh_payload
        The read-only Johnson-Hinnov coefficient payload mapping with the
        exact fields ``DKnot``, ``TKnot``, ``order``, ``LogR_BSCoef``,
        ``LogS_BSCoef``, ``LogAlpha_BSCoef``, ``A_Lyman``, ``A_Balmer``;
        validated for knot geometry (source cubic order 4 describing exactly
        77 coefficients) and finiteness.  The inputs are not mutated.
    no_null
        The source branch selector; only the source-complete ``no_null=1``
        branch is admitted.

    Returns
    -------
    numpy.ndarray
        s coefficients with the inputs' shape.  Finite and strictly positive
        for every accepted input.

    Raises
    ------
    ValueError
        If any input contract above is violated or the evaluation produces a
        non-finite value.
    """
    density, temperature = _validate_profile(density_m3, temperature_ev)
    if no_null != 1:
        raise ValueError("only the source-complete no_null=1 branch is admitted")
    knots = _validate_payload(jh_payload)
    coefficients = np.asarray(jh_payload["LogS_BSCoef"], dtype=float)
    if coefficients.shape != (77,):
        raise ValueError("JH profile coefficients must have shape (77,)")
    density_knots, temperature_knots, order = knots
    log_density = np.clip(np.log(density), density_knots[0], density_knots[-1])
    log_temperature = np.clip(np.log(temperature), temperature_knots[0], temperature_knots[-1])
    result = np.empty(density.shape, dtype=float)
    for index in range(density.size):
        result[index] = np.exp(
            float(
                bisplev(
                    float(log_temperature[index]),
                    float(log_density[index]),
                    (temperature_knots, density_knots, coefficients, order, order),
                    0,
                    0,
                )
            )
        )
    if not np.all(np.isfinite(result)):
        raise ValueError("JH profile evaluation produced non-finite output")
    return result

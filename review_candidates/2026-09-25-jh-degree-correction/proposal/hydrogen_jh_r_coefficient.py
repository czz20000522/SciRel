"""Atomic-hydrogen Johnson-Hinnov r-coefficient B-spline evaluation.

One leaf recovered from the saved KN1DPy ``原子氢JH-r系数B样条评价`` package
(source anchor ``KN1DPy/jh_related/jhr_coef.py:12-66`` with the payload
common-block anchor ``KN1DPy/common/JH_Coef.py:5-29``, both as recorded by the
saved bundle's own extraction report), integrated as
:func:`evaluate_h_jh_r_coefficient`:

the Johnson-Hinnov hydrogen r coefficient for principal levels 2-6, evaluated
as a tensor-product B-spline over ``(log Te, log n)`` with the caller-supplied
knots and coefficient tensor and the saved source's endpoint clipping in both
coordinates.

**Degree convention, stated precisely (r58 correction of the r57 wording).**
The ``spline_order`` argument is passed to scipy's FITPACK ``bisplev`` as
``kx=ky``, and scipy documents ``kx``/``ky`` as the spline *degree*, so the
admitted ``spline_order=4`` executes a degree-four (quartic) surface -- not
the cubic surface the saved source's own label describes.  The saved
coefficient-count contract closes only under that reading:
``(temperature_knots.size - 4 - 1) * (density_knots.size - 4 - 1)`` is
FITPACK's degree formula for the coefficient count.  The direct tests pin
the executed degree with an independent numpy Cox-de Boor evaluation.
Whether the saved label's intended degree-three surface should replace the
executed degree-four surface is an open expert-review question; no repair is
claimed and the executed arithmetic is preserved bit for bit.

**The evaluation is the saved formal implementation's, exactly, including one
observable source quirk.**  On the source-complete ``no_null=1`` branch the
saved implementation reproduces the raw source's ``result = Density;
result[:] = 1e32`` initialization (``jhr_coef.py:42-43``): the density
coordinate entering the spline is the ``1e32`` null sentinel, clipped to the
density-knot range, so within the admitted branch the output does **not**
depend on the caller's density values beyond shape and validation.  The
temperature coordinate is the caller's, clipped to the temperature-knot
range.  Whether this null-sentinel density overwrite is the intended
published contract or a source defect to repair is recorded as an open
expert-review question; no repair is claimed.

**No repair is claimed for this leaf.**  The saved formal implementation
enforces its declared input contract (non-empty one-dimensional paired
arrays, finite and strictly positive density and temperature, ``ion`` in
{0, 1}, ``principal_level`` an integer in [2, 6], non-decreasing finite
knots, a coefficient tensor consistent with the knots and spline order, and
``no_null == 1``); the contract is reproduced bit for bit, messages included.

Evidence ceiling: this module establishes the B-spline evaluation against an
independent FITPACK evaluation of the same spline, the endpoint clipping,
the ion/level channel selection, the density-independence witness, the input
and failure contracts, and -- in the environment-gated replay test -- exact
agreement with the saved KN1DPy implementation on synthetic payloads and on
the packaged coefficient payload.  The saved bundle's strict D1 qualification
has been withdrawn; that replay is historical development evidence, not
qualified-L1 provenance.  No test establishes the coefficient table against
an external atomic-physics reference: the saved package records that residual
as ``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import bisplev

__all__ = [
    "evaluate_h_jh_r_coefficient",
]

_SOURCE_NULL_DENSITY_M3 = 1.0e32


def evaluate_h_jh_r_coefficient(
    density_m3,
    temperature_ev,
    ion,
    principal_level,
    density_knots,
    temperature_knots,
    spline_order,
    log_r_bscoef,
    no_null=1,
):
    """Return the source jhr_coef ``no_null=1`` branch with explicit payload state.

    Parameters
    ----------
    density_m3
        Densities in ``m^-3`` as a non-empty one-dimensional array; must be
        finite and strictly positive.  On the admitted ``no_null=1`` branch
        the saved source overwrites the density coordinate with its ``1e32``
        null sentinel before the log-clipping, so the values only carry
        shape and validation.
    temperature_ev
        Temperatures in eV, a one-dimensional array of the same shape; must
        be finite and strictly positive.  Values outside the knot range are
        clipped to it, the saved source's endpoint behavior.
    ion
        The ion channel selector: the integer ``0`` (neutral target) or
        ``1`` (ion target), as saved.
    principal_level
        The atomic principal level: an integer in ``[2, 6]``, as saved.
    density_knots, temperature_knots
        The B-spline knot vectors: one-dimensional, finite, non-decreasing,
        at least two knots each.
    spline_order
        The B-spline order: a positive integer, consistent with the knots
        and the coefficient tensor.
    log_r_bscoef
        The log-space coefficient tensor of shape ``(n_coefficients, 2, 5)``
        and finite; ``n_coefficients`` must equal
        ``(temperature_knots.size - spline_order - 1) * (density_knots.size - spline_order - 1)``.
    no_null
        The source branch selector; only the source-complete ``no_null=1``
        branch is admitted.

    Returns
    -------
    numpy.ndarray
        r coefficients with the inputs' shape.  Finite and strictly positive
        for every accepted input.

    Raises
    ------
    ValueError
        If any input contract above is violated or the evaluation produces a
        non-finite value.
    """
    density = np.asarray(density_m3, dtype=float)
    temperature = np.asarray(temperature_ev, dtype=float)
    density_knot = np.asarray(density_knots, dtype=float)
    temperature_knot = np.asarray(temperature_knots, dtype=float)
    coefficients = np.asarray(log_r_bscoef, dtype=float)
    if density.ndim != 1 or temperature.ndim != 1 or density.size == 0 or density.shape != temperature.shape:
        raise ValueError("density_m3 and temperature_ev must be non-empty same-shaped 1-D arrays")
    if not np.all(np.isfinite(density)) or not np.all(np.isfinite(temperature)) or np.any(density <= 0.0) or np.any(temperature <= 0.0):
        raise ValueError("density_m3 and temperature_ev must be finite and positive")
    if not isinstance(ion, (int, np.integer)) or ion not in (0, 1):
        raise ValueError("ion must be 0 or 1")
    if not isinstance(principal_level, (int, np.integer)) or not 2 <= principal_level <= 6:
        raise ValueError("principal_level must be an integer in [2, 6]")
    if no_null != 1:
        raise ValueError("only the source-complete no_null=1 branch is admitted")
    if density_knot.ndim != 1 or temperature_knot.ndim != 1 or density_knot.size < 2 or temperature_knot.size < 2:
        raise ValueError("B-spline knots must be non-empty 1-D arrays")
    if not np.all(np.isfinite(density_knot)) or not np.all(np.isfinite(temperature_knot)) or np.any(np.diff(density_knot) < 0.0) or np.any(np.diff(temperature_knot) < 0.0):
        raise ValueError("B-spline knots must be finite and non-decreasing")
    if not isinstance(spline_order, (int, np.integer)) or spline_order < 1:
        raise ValueError("spline_order must be a positive integer")
    if coefficients.ndim != 3 or coefficients.shape[1:] != (2, 5) or not np.all(np.isfinite(coefficients)):
        raise ValueError("log_r_bscoef must have shape (n_coefficients, 2, 5) and be finite")
    expected_coefficients = (temperature_knot.size - spline_order - 1) * (density_knot.size - spline_order - 1)
    if expected_coefficients <= 0 or coefficients.shape[0] != expected_coefficients:
        raise ValueError("log_r_bscoef shape is inconsistent with knots and spline_order")

    # The source assigns ``result = Density`` and fills it with 1.0e32 before
    # taking the logarithm (jhr_coef.py:42-43).  Preserve that observable
    # no_null=1 behavior; within this branch the spline's density coordinate
    # is the clipped null sentinel, not the caller's values.
    source_density = np.full(density.shape, _SOURCE_NULL_DENSITY_M3, dtype=float)
    log_density = np.clip(np.log(source_density), density_knot[0], density_knot[-1])
    log_temperature = np.clip(np.log(temperature), temperature_knot[0], temperature_knot[-1])
    selected = coefficients[:, int(ion), int(principal_level) - 2]
    result = np.empty(density.shape, dtype=float)
    for index in range(density.size):
        result[index] = np.exp(
            float(
                bisplev(
                    float(log_temperature[index]),
                    float(log_density[index]),
                    (temperature_knot, density_knot, selected, int(spline_order), int(spline_order)),
                    0,
                    0,
                )
            )
        )
    if not np.all(np.isfinite(result)):
        raise ValueError("source B-spline evaluation produced non-finite output")
    return result

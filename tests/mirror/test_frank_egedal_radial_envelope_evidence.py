"""Independent evidence for the Frank--Egedal radial envelope.

Asset: ``scirel.mirror.frank-egedal-radial-envelope``.

The maintained tests check two hand-evaluated rows.  The envelope is a closed
form, so the evidence here is exact rational recomputation of that closed form
plus the algebraic identities it must satisfy.  The reference level is an
independent implementation of

``u = clip((psi - psi_axis)/(psi_edge - psi_axis), 0, 1)``, ``envelope = clip(1 - u, 0, inf)**alpha``

evaluated with ``fractions.Fraction`` where the grid is dyadic, and with 50-digit
mpmath where the exponent is not integral.  No tolerance is needed for the
identity statements; the fractional-exponent comparisons use a 64-eps budget
from the single ``pow`` call.

Statements, each of which a wrong implementation cannot pass:

1. **Exact values on a dyadic grid** for ``alpha = 1, 2, 3`` and for the clipped
   endpoints; a swapped numerator sign, a missing clip or an inverted
   ``1 - u`` changes them.
2. **The four analytic anchors**: ``u = 0`` gives exactly one, ``u = 1`` gives
   exactly zero, ``alpha = 0`` gives exactly one everywhere including the edge,
   and ``alpha = 1`` reproduces ``1 - u`` bit for bit on a dyadic grid.
3. **Reversal symmetry**: swapping ``psi_axis`` and ``psi_edge`` maps
   ``x -> 1 - x``, so the two envelopes must sum to exactly one at every sample.
4. **Exponent composition**: ``envelope(2 alpha)`` equals ``envelope(alpha)**2``
   within one squaring, which decides that the exponent multiplies the clipped
   base rather than, say, the flux coordinate.
5. **Monotonicity** along increasing normalization: the envelope is
   non-increasing between the reference levels.

Failure channels (contract ``failure_semantics``): a non-2D, empty or nonfinite
grid, a nonfinite reference or exponent, a negative exponent and a reference
interval below ``1e-30`` each raise ``ValueError``; a native conversion failure
raises ``TypeError``.  The contract declares no runtime-failure guard, so no
finite-output channel is asserted.
"""

from __future__ import annotations

import math
from fractions import Fraction

import mpmath
import numpy as np
import pytest

from scirel.mirror import evaluate_frank_egedal_radial_envelope

mpmath.mp.dps = 50

_EPS = math.ulp(1.0)
_POW_BUDGET = 64 * _EPS

# Dyadic flux grid spanning below, across and above the reference interval.
PSI = np.array([[-1.0, 0.0, 0.25], [0.5, 1.0, 2.0]])
PSI_AXIS = 0.0
PSI_EDGE = 1.0


def _reference(psi, axis, edge, alpha):
    u = min(
        max((Fraction(psi) - Fraction(axis)) / (Fraction(edge) - Fraction(axis)), Fraction(0)),
        Fraction(1),
    )
    base = max(Fraction(1) - u, Fraction(0))
    return base ** Fraction(alpha)


def test_exact_values_on_a_dyadic_grid():
    for alpha in (1, 2, 3):
        returned = evaluate_frank_egedal_radial_envelope(
            PSI, psi_axis=PSI_AXIS, psi_edge=PSI_EDGE, alpha=alpha
        )
        for node, observed in enumerate(returned.ravel()):
            expected = _reference(PSI.ravel()[node], PSI_AXIS, PSI_EDGE, alpha)
            assert float(observed) == float(expected), (
                alpha,
                node,
                float(observed),
                float(expected),
            )


def test_analytic_anchors():
    # u = 0 exactly one; u = 1 exactly zero.
    at_axis = evaluate_frank_egedal_radial_envelope(
        np.array([[PSI_AXIS]]), psi_axis=PSI_AXIS, psi_edge=PSI_EDGE, alpha=0.5
    )
    assert float(at_axis[0, 0]) == 1.0
    at_edge = evaluate_frank_egedal_radial_envelope(
        np.array([[PSI_EDGE]]), psi_axis=PSI_AXIS, psi_edge=PSI_EDGE, alpha=0.5
    )
    assert float(at_edge[0, 0]) == 0.0

    # alpha = 0 is one everywhere, including the outer endpoint.
    zero_exponent = evaluate_frank_egedal_radial_envelope(
        PSI, psi_axis=PSI_AXIS, psi_edge=PSI_EDGE, alpha=0.0
    )
    np.testing.assert_array_equal(zero_exponent, np.ones_like(PSI))

    # alpha = 1 reproduces 1 - u bit for bit on this dyadic grid.
    linear = evaluate_frank_egedal_radial_envelope(
        PSI, psi_axis=PSI_AXIS, psi_edge=PSI_EDGE, alpha=1.0
    )
    expected = np.array([[1.0, 1.0, 0.75], [0.5, 0.0, 0.0]])
    np.testing.assert_array_equal(linear, expected)


def test_reversing_the_reference_interval_maps_x_to_one_minus_x():
    forward = evaluate_frank_egedal_radial_envelope(
        PSI, psi_axis=PSI_AXIS, psi_edge=PSI_EDGE, alpha=1.0
    )
    reversed_interval = evaluate_frank_egedal_radial_envelope(
        PSI, psi_axis=PSI_EDGE, psi_edge=PSI_AXIS, alpha=1.0
    )
    np.testing.assert_array_equal(forward + reversed_interval, np.ones_like(PSI))


def test_the_exponent_acts_on_the_clipped_base():
    base = evaluate_frank_egedal_radial_envelope(
        PSI, psi_axis=PSI_AXIS, psi_edge=PSI_EDGE, alpha=0.5
    )
    squared = evaluate_frank_egedal_radial_envelope(
        PSI, psi_axis=PSI_AXIS, psi_edge=PSI_EDGE, alpha=1.0
    )
    mpmath.mp.dps = 50
    for observed, target in zip(base.ravel(), squared.ravel(), strict=True):
        expected = mpmath.mpf(float(target)) ** mpmath.mpf("0.5")
        assert abs(mpmath.mpf(float(observed)) - expected) <= _POW_BUDGET * abs(expected)


def test_the_envelope_is_non_increasing_between_the_reference_levels():
    ramp = np.linspace(PSI_AXIS, PSI_EDGE, 17).reshape(1, -1)
    for alpha in (0.5, 1.0, 2.5):
        returned = evaluate_frank_egedal_radial_envelope(
            ramp, psi_axis=PSI_AXIS, psi_edge=PSI_EDGE, alpha=alpha
        )
        assert np.all(np.diff(returned.ravel()) <= 0.0)
        assert returned[0, 0] == 1.0
        assert returned[0, -1] == 0.0


def test_default_reference_levels_are_the_grid_extrema():
    returned = evaluate_frank_egedal_radial_envelope(PSI, alpha=1.0)
    explicit = evaluate_frank_egedal_radial_envelope(
        PSI, psi_axis=float(np.min(PSI)), psi_edge=float(np.max(PSI)), alpha=1.0
    )
    np.testing.assert_array_equal(returned, explicit)


def test_invalid_input_channel_raises_value_error():
    with pytest.raises(ValueError, match="finite two-dimensional"):
        evaluate_frank_egedal_radial_envelope(np.array([1.0, 2.0]), alpha=1.0)
    with pytest.raises(ValueError, match="finite two-dimensional"):
        evaluate_frank_egedal_radial_envelope(np.zeros((0, 2)), alpha=1.0)
    with pytest.raises(ValueError, match="finite two-dimensional"):
        evaluate_frank_egedal_radial_envelope(np.array([[np.nan]]), alpha=1.0)
    with pytest.raises(ValueError, match="radial profile"):
        evaluate_frank_egedal_radial_envelope(PSI, psi_axis=np.inf, psi_edge=1.0)
    with pytest.raises(ValueError, match="radial profile"):
        evaluate_frank_egedal_radial_envelope(PSI, alpha=-0.5)
    with pytest.raises(ValueError, match="radial profile"):
        evaluate_frank_egedal_radial_envelope(PSI, psi_axis=1.0, psi_edge=1.0)
    with pytest.raises((TypeError, ValueError)):
        evaluate_frank_egedal_radial_envelope([["not a number"]], alpha=1.0)

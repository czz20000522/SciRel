"""Independent evidence for the three scalar/reduction diagnostics.

Assets: ``scirel.diagnostics.picard-flux-residual``,
``scirel.diagnostics.observation-residuals``,
``scirel.diagnostics.species-absorption-fraction``.

Evidence sources, all closed-form rather than "another library agrees":

1. **Exact rational recomputation.**  Each reduction is rebuilt here with
   ``fractions.Fraction`` from the original binary64 inputs and rounded once:
   the Picard ratio as an exact sum of squares, each normalized observation
   residual ``(prediction - observation) / sigma``, and the power shares
   ``100 p_i / sum p``.  A second arithmetic path, not a second call.
2. **Closed-form properties that any correct reduction must have.**  The Picard
   residual is invariant under scaling both fields, is exactly zero for equal
   fields, and depends only on the ratio through the declared ``1e-30`` floor;
   the observation residual vector is affine in the prediction with slope
   ``1/sigma`` and is exactly zero when prediction equals observation; the power
   shares sum to one hundred and are not clipped when the total is signed.
3. **Declared ordering and layout.**  The observation channel order is fixed
   (``flux_loops`` then ``density``, ``electron_temperature``, ``p_parallel``,
   ``p_perp``) and is checked against an input mapping whose insertion order is
   deliberately different, so a dict-order implementation fails.

Budgets, fixed before measurement: exact-rational comparisons use ``64 * eps``
of the local scale; the Picard ratio is compared through its exact rational
square (one square root cannot be compared exactly in binary64).  No tolerance
replaces a property; every property is an equality or a sign.

Not established here: statistical significance.  ``chi2`` is the declared
algebraic diagonal-weight sum; this file does not claim it is a goodness-of-fit
statistic, and the contract says the same.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
import pytest

from scirel import diagnostics as D

EPS = np.finfo(float).eps


def _exact_square_sum(values):
    return sum(Fraction.from_float(float(value)) ** 2 for value in np.asarray(values).ravel())


def test_picard_residual_equals_the_exact_rational_norm_ratio():
    """Evidence 1: the ratio of exact sums of squares."""
    previous = np.array([[1.0, 2.0], [3.0, 4.0]])
    following = np.array([[1.5, 2.0], [3.0, 5.0]])
    got = float(D.compute_picard_flux_residual(previous, following)["residual"])

    delta = _exact_square_sum(following - previous)
    base = _exact_square_sum(previous)
    assert got * got == pytest.approx(float(delta / base), rel=64.0 * EPS)


def test_picard_residual_is_scale_invariant_above_the_denominator_floor():
    """Evidence 2: only the ratio matters while both norms stay above ``1e-30``.

    The declared floor is part of the definition, so the invariance is a property
    of the region where it is inactive; the region below it is a separate test.
    """
    previous = np.array([[1.0, -2.0], [0.5, 4.0]])
    following = np.array([[1.25, -1.0], [0.5, 3.0]])
    base = float(D.compute_picard_flux_residual(previous, following)["residual"])

    for scale in (1e-8, 1e-3, 1e8, 1e200):
        scaled = float(
            D.compute_picard_flux_residual(scale * previous, scale * following)["residual"]
        )
        assert scaled == pytest.approx(base, rel=1e-12), scale


def test_picard_residual_of_equal_fields_is_exactly_zero():
    field = np.array([[1.0, 2.0], [3.0, -4.0]])
    assert float(D.compute_picard_flux_residual(field, field.copy())["residual"]) == 0.0


def test_picard_residual_uses_the_declared_denominator_floor():
    """Evidence 2: with a zero previous field the ``1e-30`` floor is the denominator."""
    previous = np.zeros((2, 2))
    following = np.full((2, 2), 0.3)
    got = float(D.compute_picard_flux_residual(previous, following)["residual"])
    expected = math.sqrt(float(_exact_square_sum(following))) / 1e-30
    assert got == pytest.approx(expected, rel=1e-12)


def test_picard_residual_floor_makes_small_fields_scale_dependent():
    """The same floor, seen from the other side: below it the ratio is *not* invariant.

    Scaling a field pair down until the previous-state norm falls under ``1e-30``
    replaces the denominator by the floor, so the residual grows by exactly the
    ratio of the two denominators.  Recording this prevents the floor from being
    mistaken for a numerical accident, and prevents a future "simplification" from
    silently dropping it.
    """
    previous = np.array([[1.0, -2.0], [0.5, 4.0]])
    following = np.array([[1.25, -1.0], [0.5, 3.0]])
    scale = 1e-200
    got = float(D.compute_picard_flux_residual(scale * previous, scale * following)["residual"])

    delta = _exact_square_sum(scale * (following - previous))
    expected = math.sqrt(float(delta)) / 1e-30
    assert got == pytest.approx(expected, rel=1e-12)
    # The unfloored formula would return the same ratio as at any other scale;
    # the floor instead divides by 1e-30, which is a ~1e-169 relative change here.
    unfloored = float(D.compute_picard_flux_residual(previous, following)["residual"])
    assert got < unfloored * 1e-100


def test_observation_residuals_follow_the_declared_order_and_formula():
    """Evidence 1 + 3: exact normalized residuals in the fixed channel order.

    The mapping is built with the channels inserted in reverse, so an
    implementation that walks the input mapping would produce a different vector.
    """
    observations = {
        "thomson": {
            "p_parallel": {"values": np.array([5.0])},
            "density": {"values": np.array([1.0, 2.0]), "sigma": 1.0},
            "electron_temperature": {"values": np.array([9.0]), "sigma": 3.0},
        },
        "flux_loops": {"values": np.array([0.0, 0.0]), "sigma": np.array([1.0, 2.0])},
    }
    predicted = {
        "flux_loops": np.array([1.0, 2.0]),
        "thomson": {
            "density": np.array([3.0, 4.0]),
            "electron_temperature": np.array([12.0]),
            "p_parallel": np.array([5.0]),
        },
    }
    result = D.reduce_observation_residuals(predicted=predicted, observations=observations)

    expected = np.array(
        [
            (1.0 - 0.0) / 1.0,
            (2.0 - 0.0) / 2.0,
            (3.0 - 1.0) / 1.0,
            (4.0 - 2.0) / 1.0,
            (12.0 - 9.0) / 3.0,
            (5.0 - 5.0) / 1.0,
        ]
    )
    got = np.asarray(result["residual_vector"])
    assert got.shape == expected.shape
    assert np.max(np.abs(got - expected)) <= 64.0 * EPS * np.max(np.abs(expected))
    assert float(result["chi2"]) == pytest.approx(float(np.sum(expected**2)), rel=64.0 * EPS)


def test_observation_residuals_are_affine_in_the_prediction_and_zero_at_agreement():
    observations = {"flux_loops": {"values": np.array([1.0, -2.0]), "sigma": np.array([0.5, 4.0])}}
    first = np.array([2.0, 0.0])
    second = np.array([1.5, 1.0])

    differed = np.asarray(
        D.reduce_observation_residuals(predicted={"flux_loops": first}, observations=observations)[
            "residual_vector"
        ]
    ) - np.asarray(
        D.reduce_observation_residuals(predicted={"flux_loops": second}, observations=observations)[
            "residual_vector"
        ]
    )
    expected = (first - second) / np.array([0.5, 4.0])
    assert np.max(np.abs(differed - expected)) <= 64.0 * EPS * np.max(np.abs(expected))

    agreed = D.reduce_observation_residuals(
        predicted={"flux_loops": np.array([1.0, -2.0])}, observations=observations
    )
    assert np.array_equal(np.asarray(agreed["residual_vector"]), np.zeros(2))
    assert float(agreed["chi2"]) == 0.0


def test_observation_units_are_checked_as_declared_labels():
    observations = {"flux_loops": {"values": np.array([0.0]), "unit": "Wb"}}
    with pytest.raises(ValueError) as caught:
        D.reduce_observation_residuals(
            predicted={"flux_loops": np.array([1.0])}, observations=observations
        )
    assert "unit" in str(caught.value)
    matched = D.reduce_observation_residuals(
        predicted={"flux_loops": np.array([1.0]), "units": {"flux_loops": "Wb"}},
        observations=observations,
    )
    assert float(np.asarray(matched["residual_vector"])[0]) == 1.0


def test_species_shares_match_exact_rational_percentages():
    """Evidence 1: ``100 p_i / sum p`` with one rounding, order preserved."""
    powers = np.array([1.0, 2.0, 3.0, 4.0])
    result = D.compute_species_absorption_fraction(powers)
    total = sum(Fraction.from_float(float(value)) for value in powers)
    expected = np.array([float(100 * Fraction.from_float(float(v)) / total) for v in powers])
    got = np.asarray(result["species_fraction_percent"])
    assert np.max(np.abs(got - expected)) <= 64.0 * EPS * np.max(np.abs(expected))
    assert float(result["total_power"]) == 10.0
    assert float(result["total_fraction_percent"]) == 100.0
    assert float(result["fraction_sum_residual_percent"]) == 0.0
    assert str(np.asarray(result["branch"])) == "nonzero_total"


def test_species_shares_are_not_clipped_when_the_total_is_signed():
    """Evidence 2: a signed ledger keeps negative shares instead of renormalizing."""
    powers = np.array([2.0, -1.0, 3.0, 4.0])
    result = D.compute_species_absorption_fraction(powers)
    total = sum(Fraction.from_float(float(value)) for value in powers)  # exactly 8
    expected = np.array([float(100 * Fraction.from_float(float(v)) / total) for v in powers])
    assert (
        np.max(np.abs(np.asarray(result["species_fraction_percent"]) - expected))
        <= 64.0 * EPS * 100.0
    )
    assert float(np.asarray(result["species_fraction_percent"])[1]) < 0.0
    assert float(result["total_power"]) == 8.0


def test_reduction_rejection_channels_are_bound_to_their_contract():
    field = np.array([[1.0, 2.0], [3.0, 4.0]])
    for call, expected_type, fragment in [
        (lambda: D.compute_picard_flux_residual(field[0], field[0]), ValueError, "two-dimensional"),
        (lambda: D.compute_picard_flux_residual(field, field[:1]), ValueError, "two-dimensional"),
        (
            lambda: D.compute_picard_flux_residual(np.array([[1.0, np.nan]]), field[:1]),
            ValueError,
            "finite",
        ),
        (lambda: D.compute_species_absorption_fraction([1.0, 2.0, 3.0]), ValueError, "length-four"),
        (
            lambda: D.compute_species_absorption_fraction([1.0, 2.0, 3.0, np.nan]),
            ValueError,
            "finite",
        ),
        (
            lambda: D.compute_species_absorption_fraction([0.0, 0.0, 0.0, 0.0]),
            ValueError,
            "zero total",
        ),
        (
            lambda: D.reduce_observation_residuals(predicted={}, observations={"unknown": {}}),
            ValueError,
            "unknown observation kinds",
        ),
        (
            lambda: D.reduce_observation_residuals(
                predicted={}, observations={"thomson": {"points": np.zeros((1, 2))}}
            ),
            ValueError,
            "at least one",
        ),
        (
            lambda: D.reduce_observation_residuals(
                predicted={"flux_loops": np.array([1.0])},
                observations={"flux_loops": {"values": np.array([1.0]), "sigma": 0.0}},
            ),
            ValueError,
            "positive",
        ),
        (
            lambda: D.reduce_observation_residuals(
                predicted={"flux_loops": np.array([1.0, 2.0])},
                observations={"flux_loops": {"values": np.array([1.0])}},
            ),
            ValueError,
            "shape",
        ),
    ]:
        with pytest.raises(expected_type) as caught:
            call()
        assert fragment in str(caught.value), (fragment, str(caught.value))

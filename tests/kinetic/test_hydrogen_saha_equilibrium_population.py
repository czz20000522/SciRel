"""Contract tests for atomic-hydrogen Saha equilibrium population."""

import numpy as np
import pytest

from scirel.kinetic import evaluate_h_saha_equilibrium_population


def _saha_population(density, temperature, level):
    level_squared = float(level * level)
    return (
        density
        * (3.310e-28 * density)
        * level_squared
        * np.exp(13.6057 / (level_squared * temperature))
        / temperature**1.5
    )


@pytest.mark.parametrize("level", [1, 2, 3])
def test_frozen_saha_relation_and_level_scaling(level):
    density = np.array([1.0e18, 1.0e19, 1.0e20])
    temperature = np.array([1.0, 2.0, 5.0])
    actual = evaluate_h_saha_equilibrium_population(density, temperature, level)
    np.testing.assert_allclose(
        actual,
        _saha_population(density, temperature, level),
        rtol=1e-15,
        atol=0.0,
    )
    assert actual.shape == density.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


@pytest.mark.parametrize("level", [2**53 + 1, 2**64])
def test_large_integral_level_is_not_rounded_before_square(level):
    density = np.array([1.0e18])
    temperature = np.array([2.0])
    actual = evaluate_h_saha_equilibrium_population(density, temperature, level)
    expected = _saha_population(density, temperature, level)
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize(
    "density,temperature,level,reason",
    [
        ([0.0], [1.0], 1, "scientific domain"),
        ([1.0e32], [1.0], 1, "scientific domain"),
        ([1.0e18], [0.0], 1, "scientific domain"),
        ([1.0e18], [1.0e32], 1, "scientific domain"),
        ([1.0e18, 2.0e18], [1.0], 1, "same shape"),
        ([[1.0e18]], [[1.0]], 1, "one-dimensional"),
        ([], [], 1, "one-dimensional"),
        ([1.0e18], [1.0], 0, "integer >= 1"),
        ([1.0e18], [1.0], 2.5, "integer >= 1"),
    ],
)
def test_invalid_domain_fails_closed(density, temperature, level, reason):
    with pytest.raises(ValueError, match=reason):
        evaluate_h_saha_equilibrium_population(density, temperature, level)


@pytest.mark.parametrize(
    "density,temperature,level",
    [
        ([True], [1.0], 1),
        (["1e18"], [1.0], 1),
        ([1.0e18], [True], 1),
        ([1.0e18], ["1.0"], 1),
        ([1.0e18], [1.0], True),
        ([1.0e18], [1.0], "2"),
    ],
)
def test_nonreal_coercions_are_rejected(density, temperature, level):
    with pytest.raises(ValueError):
        evaluate_h_saha_equilibrium_population(density, temperature, level)


def test_nonfinite_input_and_result_are_rejected():
    with pytest.raises(ValueError, match="finite"):
        evaluate_h_saha_equilibrium_population([1.0e18, np.nan], [1.0, 2.0], 1)
    with pytest.raises(ValueError, match="finite"):
        evaluate_h_saha_equilibrium_population([1.0e18], [np.inf], 1)
    with pytest.raises(ValueError, match="population"):
        evaluate_h_saha_equilibrium_population([1.0e31], [1.0e-12], 1)


def test_overflow_uses_public_failure_semantics_under_strict_numpy_errors():
    with np.errstate(all="raise"):
        with pytest.raises(ValueError, match="population"):
            evaluate_h_saha_equilibrium_population([1.0e31], [1.0e-12], 1)

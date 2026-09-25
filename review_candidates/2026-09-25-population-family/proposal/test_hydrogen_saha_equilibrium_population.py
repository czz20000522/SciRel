"""Direct contract tests for ``scirel.kinetic.hydrogen_saha_equilibrium_population``.

The saved KN1DPy leaf (source anchor ``KN1DPy/jh_related/nh_saha.py:25-46``)
computes the atomic-hydrogen Saha equilibrium population density: the source
fills a ``1e32`` sentinel on its non-scientific branches, and the saved formal
implementation exposes only the positive finite scientific branch, rejecting
inputs outside it so the sentinel is never promoted to data.  The saved
implementation already enforces its declared contract (non-empty
one-dimensional paired arrays, finite, strictly positive, level a scalar
integer >= 1, result finite and positive); the tests re-verify that contract
against an independent evaluation of the Saha formula, the principal-level
scaling, and the fail-closed rejections.  No repair is claimed for this leaf:
the saved implementation and its document already agree.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import evaluate_h_saha_equilibrium_population

SAHA_CONSTANT = 3.310e-28
IONIZATION_ENERGY_EV = 13.6057


def independent_oracle(density, temperature, level):
    level_squared = float(level * level)
    return (
        density
        * (SAHA_CONSTANT * density)
        * level_squared
        * np.exp(IONIZATION_ENERGY_EV / (level_squared * temperature))
        / (temperature**1.5)
    )


def test_population_matches_independent_oracle():
    density = np.array([1.0e18, 1.0e19, 1.0e20])
    temperature = np.array([1.0, 2.0, 5.0])
    actual = evaluate_h_saha_equilibrium_population(density, temperature, 1)
    np.testing.assert_allclose(actual, independent_oracle(density, temperature, 1), rtol=1e-15, atol=0.0)
    assert actual.shape == density.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_principal_level_scaling_matches_the_oracle():
    density = np.array([1.0e18, 1.0e19])
    temperature = np.array([1.0, 2.0])
    for level in (1, 2, 3):
        np.testing.assert_allclose(
            evaluate_h_saha_equilibrium_population(density, temperature, level),
            independent_oracle(density, temperature, level),
            rtol=1e-15,
            atol=0.0,
        )


def test_level_scaling_follows_the_expex_factor():
    """The level dependence is n_level^2 * exp(chi / (n_level^2 T)) / ...: on
    these cold inputs the exponential suppresses level 2 below level 1, and
    the direct test is the oracle equality above, not a monotonicity guess."""
    density = np.array([1.0e18, 1.0e19])
    temperature = np.array([1.0, 2.0])
    level1 = evaluate_h_saha_equilibrium_population(density, temperature, 1)
    level2 = evaluate_h_saha_equilibrium_population(density, temperature, 2)
    # cross-check both against the same frozen-constant relation, per element
    for level, actual in ((1, level1), (2, level2)):
        np.testing.assert_allclose(
            actual, independent_oracle(density, temperature, level), rtol=1e-15, atol=0.0
        )


def test_nonpositive_or_oversized_density_is_rejected():
    with pytest.raises(ValueError, match="scientific domain"):
        evaluate_h_saha_equilibrium_population(np.array([0.0, 1.0e18]), np.array([1.0, 2.0]), 1)
    with pytest.raises(ValueError, match="scientific domain"):
        evaluate_h_saha_equilibrium_population(np.array([1.0e32, 1.0e18]), np.array([1.0, 2.0]), 1)


def test_nonpositive_or_oversized_temperature_is_rejected():
    with pytest.raises(ValueError, match="scientific domain"):
        evaluate_h_saha_equilibrium_population(np.array([1.0e18]), np.array([0.0]), 1)
    with pytest.raises(ValueError, match="scientific domain"):
        evaluate_h_saha_equilibrium_population(np.array([1.0e18]), np.array([1.0e32]), 1)


def test_invalid_levels_fail_closed():
    with pytest.raises(ValueError, match="integer >= 1"):
        evaluate_h_saha_equilibrium_population(np.array([1.0e18]), np.array([1.0]), 0)
    with pytest.raises(ValueError, match="integer >= 1"):
        evaluate_h_saha_equilibrium_population(np.array([1.0e18]), np.array([1.0]), 2.5)
    with pytest.raises(ValueError, match="scalar integer"):
        evaluate_h_saha_equilibrium_population(np.array([1.0e18]), np.array([1.0]), True)


def test_shape_and_finiteness_fail_closed():
    with pytest.raises(ValueError, match="one-dimensional"):
        evaluate_h_saha_equilibrium_population(np.array([[1.0e18]]), np.array([[1.0]]), 1)
    with pytest.raises(ValueError, match="same shape"):
        evaluate_h_saha_equilibrium_population(np.array([1.0e18, 2.0e18]), np.array([1.0]), 1)
    with pytest.raises(ValueError, match="finite"):
        evaluate_h_saha_equilibrium_population(np.array([1.0e18, np.nan]), np.array([1.0, 2.0]), 1)

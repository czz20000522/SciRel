"""Direct contract tests for ``scirel.collisions.hydrogen2_hydrogen2_elastic_cross_section``.

The saved the neutral-transport formulation leaf fits the H2-on-H2 elastic
momentum-transfer cross section with a single logarithmic polynomial clipped
to ``[0.03, 1.01e4] eV``.  The saved implementation already validates the
``viscosity`` selector as a scalar boolean/integer, and its ``True`` branch is
the source's documented fallback that evaluates the same momentum-transfer
fit; both behaviors are asserted as the declared contract.  One documented
repair relative to the saved implementation is exercised: negative energies
are rejected (the saved document declares nonnegative energies but its
implementation silently clipped them to the lower endpoint).
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import evaluate_hydrogen2_hydrogen2_elastic_cross_section

COEFFICIENTS = np.array(
    [-3.430345e1, -2.960406e-1, -6.382532e-2, -7.557519e-3, 2.606259e-4],
    dtype=float,
)


def independent_fit(energy):
    clipped = np.clip(energy, 0.03, 1.01e4)
    return np.exp(np.polynomial.polynomial.polyval(np.log(clipped), COEFFICIENTS)) * 1.0e-4


def test_fit_matches_independent_evaluation():
    energy = np.array([0.03, 0.5, 1.0, 10.0, 100.0, 1.0e3, 1.01e4])
    actual = evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy)
    np.testing.assert_allclose(actual, independent_fit(energy), rtol=1e-15, atol=0.0)
    assert actual.shape == energy.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_viscosity_selector_is_the_declared_same_fit_fallback():
    energy = np.array([0.5, 10.0, 1.0e3])
    np.testing.assert_array_equal(
        evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy, viscosity=True),
        evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy),
    )


def test_scalar_selector_validation_is_preserved():
    energy = np.array([1.0, 10.0])
    with pytest.raises(ValueError, match="scalar boolean"):
        evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy, viscosity=np.ones((2, 2)))
    with pytest.raises(ValueError, match="scalar boolean"):
        evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy, viscosity=0.5)


def test_endpoint_clipping_is_preserved():
    result = evaluate_hydrogen2_hydrogen2_elastic_cross_section(
        np.array([0.01, 0.03, 2.0e4, 1.01e4])
    )
    assert result[0] == result[1]
    assert result[-1] == result[-2]


def test_negative_energy_is_rejected():
    """Documented repair: the saved implementation clipped negatives silently."""
    with pytest.raises(ValueError, match="nonnegative"):
        evaluate_hydrogen2_hydrogen2_elastic_cross_section(np.array([1.0, -0.5]))


def test_nonfinite_energy_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        evaluate_hydrogen2_hydrogen2_elastic_cross_section([1.0, np.nan])

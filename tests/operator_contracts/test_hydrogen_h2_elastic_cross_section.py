"""Direct contract tests for ``scirel.collisions.hydrogen_h2_elastic_cross_section``.

The saved the neutral-transport formulation leaf fits the H-on-H2 elastic
momentum-transfer cross section with a single logarithmic polynomial clipped
to ``[0.03, 1.01e4] eV``, preserving the source ``np.array([E])`` wrapper as
one extra leading singleton output axis.  One documented repair relative to
the saved implementation is exercised: negative energies are rejected (the
saved document declares nonnegative energies but its implementation silently
clipped them to the lower endpoint).
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import evaluate_hydrogen_h2_elastic_cross_section

COEFFICIENTS = np.array(
    [-3.495671e1, -4.062257e-1, -3.820531e-2, -9.404486e-3, 3.963723e-4],
    dtype=float,
)


def independent_fit(energy):
    clipped = np.clip(energy, 0.03, 1.01e4)
    return np.exp(np.polynomial.polynomial.polyval(np.log(clipped), COEFFICIENTS)) * 1.0e-4


def test_fit_matches_independent_evaluation():
    energy = np.array([0.03, 0.5, 1.0, 10.0, 100.0, 1.0e3, 1.01e4])
    actual = evaluate_hydrogen_h2_elastic_cross_section(energy)
    np.testing.assert_allclose(actual[0], independent_fit(energy), rtol=1e-15, atol=0.0)
    assert actual.shape == (1, energy.size)
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_leading_singleton_axis_is_preserved():
    """Declared source convention: the result carries one extra leading axis."""
    two_d = evaluate_hydrogen_h2_elastic_cross_section(np.array([[1.0, 100.0, 1.0e3]]))
    assert two_d.shape == (1, 1, 3)
    one_d = evaluate_hydrogen_h2_elastic_cross_section(np.array([1.0, 100.0, 1.0e3]))
    np.testing.assert_array_equal(two_d[0], one_d)


def test_endpoint_clipping_is_preserved():
    result = evaluate_hydrogen_h2_elastic_cross_section(np.array([0.01, 0.03, 2.0e4, 1.01e4]))
    assert result[0][0] == result[0][1]
    assert result[0][-1] == result[0][-2]


def test_negative_energy_is_rejected():
    """Documented repair: the saved implementation clipped negatives silently."""
    with pytest.raises(ValueError, match="nonnegative"):
        evaluate_hydrogen_h2_elastic_cross_section(np.array([1.0, -0.5]))


def test_nonfinite_energy_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        evaluate_hydrogen_h2_elastic_cross_section([1.0, np.nan])

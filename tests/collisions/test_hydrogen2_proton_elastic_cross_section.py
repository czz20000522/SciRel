"""Direct contract tests for ``scirel.collisions.hydrogen2_proton_elastic_cross_section``.

The saved the neutral-transport formulation leaf fits the H2-on-H+ elastic
momentum-transfer cross section with a single logarithmic polynomial clipped
to ``[0.03, 1.01e4] eV``.  One documented repair relative to the saved
implementation is exercised: negative energies are rejected (the saved
document declares nonnegative energies but its implementation silently clipped
them to the lower endpoint).
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import evaluate_hydrogen2_proton_elastic_cross_section

COEFFICIENTS = np.array(
    [-3.355719e1, -5.696568e-1, -4.089556e-2, -1.143513e-2, 5.926596e-4],
    dtype=float,
)


def independent_fit(energy):
    clipped = np.clip(energy, 0.03, 1.01e4)
    return np.exp(np.polynomial.polynomial.polyval(np.log(clipped), COEFFICIENTS)) * 1.0e-4


def test_fit_matches_independent_evaluation():
    energy = np.array([0.03, 0.5, 1.0, 10.0, 100.0, 1.0e3, 1.01e4])
    actual = evaluate_hydrogen2_proton_elastic_cross_section(energy)
    np.testing.assert_allclose(actual, independent_fit(energy), rtol=1e-15, atol=0.0)
    assert actual.shape == energy.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_holdout_grid_matches_independent_evaluation():
    energy = np.array([0.05, 7.0, 250.0, 8.0e3])
    np.testing.assert_allclose(
        evaluate_hydrogen2_proton_elastic_cross_section(energy),
        independent_fit(energy),
        rtol=1e-15,
        atol=0.0,
    )


def test_endpoint_clipping_is_preserved():
    result = evaluate_hydrogen2_proton_elastic_cross_section(np.array([0.01, 0.03, 2.0e4, 1.01e4]))
    assert result[0] == result[1]
    assert result[-1] == result[-2]


def test_scalar_input_returns_zero_dimensional_result():
    result = evaluate_hydrogen2_proton_elastic_cross_section(np.asarray(100.0))
    assert np.ndim(result) == 0
    assert np.isfinite(result) and result > 0.0


def test_negative_energy_is_rejected():
    """Documented repair: the saved implementation clipped negatives silently."""
    with pytest.raises(ValueError, match="nonnegative"):
        evaluate_hydrogen2_proton_elastic_cross_section(np.array([1.0, -0.5]))


def test_nonfinite_energy_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        evaluate_hydrogen2_proton_elastic_cross_section([1.0, np.nan])

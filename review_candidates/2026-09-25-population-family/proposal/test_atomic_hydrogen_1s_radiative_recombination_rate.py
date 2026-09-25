"""Direct contract tests for ``scirel.collisions.atomic_hydrogen_1s_radiative_recombination_rate``.

The saved KN1DPy leaf (source anchor ``KN1DPy/sigma/sigmav_rec_h1s.py:3-25`` with
caller evidence ``kinetic_h.py:862,867-881``) fits the H+ + e -> H(1s) + hv
radiative recombination rate coefficient with a Storey-type analytic form
whose constants are frozen at the saved source's values (Rydberg 13.58 eV,
``A_nl = 3.92``, ``x_nl = 0.35``, level ``n = 1``), evaluated on the
source-clipped domain ``[0.1, 2.01e4] eV`` and scaled to ``m^3/s``.  The tests
assert the closed form against an independent evaluation, the endpoint
clipping, and the fail-closed contracts.  One documented repair relative to
the saved implementation is exercised: a nonpositive temperature is rejected
(the saved document declares a positive temperature but its implementation
silently clipped it into the fit domain).
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import (
    evaluate_atomic_hydrogen_1s_radiative_recombination_rate,
)

RY_EV = 13.58
A_NL = 3.92
X_NL = 0.35


def independent_oracle(temperature):
    clipped = np.minimum(np.maximum(np.asarray(temperature, dtype=float), 0.1), 2.01e4)
    ionization_energy_ev = RY_EV / 1.0
    b_n = ionization_energy_ev / clipped
    return A_NL * 1.0e-14 * np.sqrt(ionization_energy_ev / RY_EV) * (b_n**1.5 / (b_n + X_NL)) * 1.0e-6


def test_fit_matches_independent_evaluation():
    temperature = np.array([0.1, 0.5, 1.0, 10.0, 100.0, 1.0e3, 2.01e4])
    actual = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)
    np.testing.assert_allclose(actual, independent_oracle(temperature), rtol=1e-15, atol=0.0)
    assert actual.shape == temperature.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_holdout_grid_matches_independent_evaluation():
    temperature = np.array([0.2, 2.0, 20.0, 200.0, 2000.0, 5000.0])
    np.testing.assert_allclose(
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature),
        independent_oracle(temperature),
        rtol=1e-15,
        atol=0.0,
    )


def test_domain_clipping_matches_the_oracle():
    temperature = np.array([0.01, 2.01e4, 5.0e4])
    actual = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(temperature)
    np.testing.assert_allclose(actual, independent_oracle(temperature), rtol=1e-15, atol=0.0)


def test_scalar_input_returns_zero_dimensional_result():
    result = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(np.asarray(12.5))
    assert np.ndim(result) == 0
    assert np.isfinite(result) and result > 0.0


def test_nonpositive_temperature_is_rejected():
    """Documented repair: the saved implementation clipped it into the fit domain."""
    with pytest.raises(ValueError, match="electron_temperature_ev"):
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate(np.array([1.0, -5.0]))
    with pytest.raises(ValueError, match="electron_temperature_ev"):
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate(np.array([1.0, 0.0]))


def test_nonfinite_temperature_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        evaluate_atomic_hydrogen_1s_radiative_recombination_rate([1.0, np.nan])

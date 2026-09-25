"""Direct contract tests for ``scirel.collisions.hydrogen2_h2p_h2s_dissociation_rate``.

The saved KN1DPy leaf (source anchor ```KN1DPy/sigma/sigmav_h2p_h2s_hh.py:5-35`；`KN1DPy/sigma/poly.py:3-10`；`KN1DPy/kinetic_h2.py:971`。``) fits the H2 + e -> H2+ + H(2s) channel
electron-impact rate coefficient as a temperature-only nine-coefficient
logarithmic polynomial, evaluated in the source's Horner order after clipping
the temperature to ``[0.1, 2.01e4] eV`` and scaling by ``1e-6`` to ``m^3/s``.
The tests assert the fit against an independent ``polyval`` evaluation, the
domain clipping, and the fail-closed contracts.  One documented repair
relative to the saved implementation is exercised: a nonpositive temperature
is rejected (the saved document declares a positive temperature but its
implementation silently clipped it into the fit domain).
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import evaluate_hydrogen2_h2p_h2s_dissociation_rate

COEFFICIENTS = np.array(
    [
    -47.94288960529,
    26.29649351119,
    -11.51117702256,
    2.99195488079,
    -0.4949305181578,
    0.05236320848415,
    -0.003433774290547,
    0.0001272097387363,
    -2.036079507592e-06,
],
    dtype=float,
)


def independent_oracle(temperature):
    clipped = np.minimum(np.maximum(np.asarray(temperature, dtype=float), 0.1), 2.01e4)
    return np.exp(
        np.polynomial.polynomial.polyval(np.log(clipped), COEFFICIENTS)
    ) * 1.0e-6


def test_fit_matches_independent_oracle():
    temperature = np.array([0.1, 0.5, 1.0, 10.0, 100.0, 1.0e3, 2.01e4, 5.0])
    actual = evaluate_hydrogen2_h2p_h2s_dissociation_rate(temperature)
    np.testing.assert_allclose(actual, independent_oracle(temperature), rtol=1e-12, atol=0.0)
    assert actual.shape == temperature.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_holdout_grid_matches_independent_oracle():
    temperature = np.array([0.2, 2.0, 20.0, 200.0, 2000.0, 5000.0])
    np.testing.assert_allclose(
        evaluate_hydrogen2_h2p_h2s_dissociation_rate(temperature),
        independent_oracle(temperature),
        rtol=1e-12,
        atol=0.0,
    )


def test_scalar_input_returns_zero_dimensional_result():
    result = evaluate_hydrogen2_h2p_h2s_dissociation_rate(np.asarray(12.5))
    assert np.ndim(result) == 0
    assert np.isfinite(result) and result > 0.0


def test_domain_clipping_matches_the_oracle():
    temperature = np.array([0.01, 2.01e4, 5.0e4])
    actual = evaluate_hydrogen2_h2p_h2s_dissociation_rate(temperature)
    np.testing.assert_allclose(actual, independent_oracle(temperature), rtol=1e-12, atol=0.0)


def test_nonpositive_temperature_is_rejected():
    """Documented repair: the saved implementation clipped it into the fit domain."""
    with pytest.raises(ValueError, match="temperature_ev"):
        evaluate_hydrogen2_h2p_h2s_dissociation_rate(np.array([1.0, -5.0]))
    with pytest.raises(ValueError, match="temperature_ev"):
        evaluate_hydrogen2_h2p_h2s_dissociation_rate(np.array([1.0, 0.0]))


def test_nonfinite_temperature_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        evaluate_hydrogen2_h2p_h2s_dissociation_rate([1.0, np.nan])

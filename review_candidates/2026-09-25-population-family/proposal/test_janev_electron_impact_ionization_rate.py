"""Direct contract tests for ``scirel.collisions.janev_electron_impact_ionization_rate``.

The saved KN1DPy leaf (source anchor ``KN1DPy/sigma/sigmav_ion_h0.py:1-22`` with
``sigmav_ion_hh.py:1-27`` and ``poly.py:1-10``) fits the Maxwellian
electron-impact ionization rate coefficient for two target species -- H and H2
-- as temperature-only nine-coefficient logarithmic polynomials evaluated on
the source-clipped domain ``[0.1, 2.01e4] eV`` and scaled by ``1e-6`` to
``m^3/s``.  The tests assert both species branches against independent
``polyval`` evaluations, the endpoint clipping, the species distinction, and
the fail-closed contracts.  One documented repair relative to the saved
implementation is exercised: a nonpositive temperature is rejected with a
message naming the quantity (the saved document declares a positive
temperature, but its implementation folded the temperature and species checks
into one generic error and silently clipped nonpositive values into the fit).
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import evaluate_janev_electron_impact_ionization_rate

H_COEFFICIENTS = np.array([-3.271396786375e1, 1.353655609057e1, -5.739328757388, 1.563154982022, -2.877056004391e-1, 3.482559773737e-2, -2.631976175590e-3, 1.119543953861e-4, -2.039149852002e-6])
H2_COEFFICIENTS = np.array([-3.568640293666e1, 1.733468989961e1, -7.767469363538, 2.211579405415, -4.169840174384e-1, 5.088289820867e-2, -3.832737518325e-3, 1.612863120371e-4, -2.893391904431e-6])


def independent_oracle(temperature, coefficients):
    clipped = np.clip(np.asarray(temperature, dtype=float), 0.1, 2.01e4)
    return np.exp(np.polynomial.polynomial.polyval(np.log(clipped), coefficients)) * 1.0e-6


def test_h_branch_matches_independent_oracle():
    temperature = np.array([0.1, 0.5, 1.0, 10.0, 100.0, 1.0e3, 2.01e4])
    actual = evaluate_janev_electron_impact_ionization_rate(temperature, "H")
    np.testing.assert_allclose(actual, independent_oracle(temperature, H_COEFFICIENTS), rtol=1e-12, atol=0.0)
    assert actual.shape == temperature.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_h2_branch_matches_independent_oracle():
    temperature = np.array([0.1, 0.5, 1.0, 10.0, 100.0, 1.0e3, 2.01e4])
    actual = evaluate_janev_electron_impact_ionization_rate(temperature, "H2")
    np.testing.assert_allclose(actual, independent_oracle(temperature, H2_COEFFICIENTS), rtol=1e-12, atol=0.0)
    assert np.all(actual > 0.0)


def test_species_branches_disagree():
    temperature = np.array([1.0, 10.0, 100.0, 1.0e3])
    h_rate = evaluate_janev_electron_impact_ionization_rate(temperature, "H")
    h2_rate = evaluate_janev_electron_impact_ionization_rate(temperature, "H2")
    assert not np.allclose(h_rate, h2_rate, rtol=1e-12, atol=0.0)


def test_domain_clipping_matches_the_oracle():
    temperature = np.array([0.01, 2.01e4, 5.0e4])
    actual = evaluate_janev_electron_impact_ionization_rate(temperature, "H")
    np.testing.assert_allclose(actual, independent_oracle(temperature, H_COEFFICIENTS), rtol=1e-12, atol=0.0)


def test_scalar_input_returns_zero_dimensional_result():
    result = evaluate_janev_electron_impact_ionization_rate(np.asarray(12.5), "H")
    assert np.ndim(result) == 0
    assert np.isfinite(result) and result > 0.0


def test_unknown_species_is_rejected():
    with pytest.raises(ValueError, match="H or H2"):
        evaluate_janev_electron_impact_ionization_rate(np.array([1.0]), "He")


def test_nonpositive_temperature_is_rejected():
    """Documented repair: the saved implementation clipped it into the fit domain."""
    with pytest.raises(ValueError, match="temperature"):
        evaluate_janev_electron_impact_ionization_rate(np.array([1.0, -5.0]), "H")
    with pytest.raises(ValueError, match="temperature"):
        evaluate_janev_electron_impact_ionization_rate(np.array([1.0, 0.0]), "H2")


def test_nonfinite_temperature_is_rejected():
    with pytest.raises(ValueError):
        evaluate_janev_electron_impact_ionization_rate([1.0, np.nan], "H")

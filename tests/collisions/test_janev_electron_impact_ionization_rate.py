"""Contract tests for the Janev H/H2 electron-impact ionization fits."""

import numpy as np
import pytest

from scirel.collisions import evaluate_janev_electron_impact_ionization_rate


@pytest.mark.parametrize("target_species,expected", [
    ("H", [
        1.1856109447898059e-60, 6.201607490833009e-21,
        5.172561712741314e-15, 3.082100081945778e-14,
        2.1276844012693452e-14, 6.035884712672147e-15,
    ]),
    ("H2", [
        5.781905261621736e-76, 3.173891860934189e-22,
        6.18461236890495e-15, 5.0280667977801184e-14,
        3.7022899041672964e-14, 1.2093423978250538e-14,
    ]),
])
def test_source_reference_values(target_species, expected):
    temperature = np.array([0.1, 1.0, 10.0, 100.0, 1000.0, 20100.0])
    result = evaluate_janev_electron_impact_ionization_rate(
        temperature, target_species,
    )
    np.testing.assert_allclose(result, expected, rtol=1e-14, atol=0.0)
    assert result.shape == temperature.shape
    assert np.all(np.isfinite(result)) and np.all(result > 0.0)


def test_species_distinction_clipping_and_scalar_shape():
    temperature = np.array([0.01, 10.0, 50000.0])
    endpoints = np.array([0.1, 10.0, 20100.0])
    for species in ("H", "H2"):
        np.testing.assert_array_equal(
            evaluate_janev_electron_impact_ionization_rate(temperature, species),
            evaluate_janev_electron_impact_ionization_rate(endpoints, species),
        )
        assert np.ndim(evaluate_janev_electron_impact_ionization_rate(10.0, species)) == 0
    h = evaluate_janev_electron_impact_ionization_rate(endpoints, "H")
    h2 = evaluate_janev_electron_impact_ionization_rate(endpoints, "H2")
    assert not np.allclose(h, h2, rtol=1e-12, atol=0.0)


@pytest.mark.parametrize("temperature", [
    0.0, -1.0, np.nan, np.inf, [1.0, np.inf],
])
def test_invalid_temperature_fails_closed(temperature):
    with pytest.raises(ValueError):
        evaluate_janev_electron_impact_ionization_rate(temperature, "H")


@pytest.mark.parametrize("temperature", [
    True, [True, 1.0], "10.0", ["1.0", "2.0"], 1.0 + 0j,
])
def test_nonreal_temperature_fails_closed(temperature):
    with pytest.raises(ValueError, match="real"):
        evaluate_janev_electron_impact_ionization_rate(temperature, "H")


@pytest.mark.parametrize("target_species", [
    "He", "h", "", None, True, ["H"], np.array(["H"]),
])
def test_invalid_target_fails_closed(target_species):
    with pytest.raises(ValueError, match="target_species"):
        evaluate_janev_electron_impact_ionization_rate(10.0, target_species)


def test_fit_peak_locations_are_documented_limitations():
    """AUDIT-D5: the fits have single maxima; pin their positions.

    Peak locations are fit properties, not independently validated thresholds.
    """
    temperature = np.geomspace(0.1, 2.01e4, 2000)
    for species, expected in (("H", 137.0), ("H2", 155.0)):
        rate = evaluate_janev_electron_impact_ionization_rate(temperature, species)
        peak = float(temperature[int(np.argmax(rate))])
        assert abs(peak - expected) <= 3.0
        assert np.count_nonzero(
            (rate[1:-1] > rate[:-2]) & (rate[1:-1] > rate[2:])) == 1

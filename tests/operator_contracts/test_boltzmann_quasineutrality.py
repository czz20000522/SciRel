import numpy as np
import pytest

from scirel.closures.boltzmann_quasineutrality import compute_boltzmann_electron_state, compute_boltzmann_electron_state as scientific_operator


def test_boltzmann_response_and_neutrality():
    result = scientific_operator(0.5, 2.0, 3.0, 0.0, 1.5, 2.0)
    expected = 3.0 * np.exp(1.602176634e-19 * 0.5 / 2.0)
    assert result["electron_density_m3"] == pytest.approx(expected)
    assert result["charge_residual_m3"] == pytest.approx(0.0)
    assert result["relative_charge_residual"] == pytest.approx(0.0)


def test_array_broadcast_and_zero_density_are_finite():
    result = scientific_operator(
        np.array([0.0, 1.0]), 2.0, np.array([0.0, 2.0]), 0.0, np.array([0.0, 1.0]), 1.0
    )
    assert np.all(np.isfinite(result["logarithmic_charge_residual"]))
    assert result["electron_density_m3"].shape == (2,)


@pytest.mark.parametrize("kwargs", [{"electron_temperature_j": 0.0}, {"ion_density_m3": -1.0}])
def test_invalid_domain_fails_closed(kwargs):
    base = dict(
        potential_v=0.0,
        electron_temperature_j=1.0,
        electron_density_ref_m3=1.0,
        electron_phi_ref_v=0.0,
        ion_density_m3=1.0,
        ion_charge_state=1.0,
    )
    base.update(kwargs)
    with pytest.raises(ValueError):
        scientific_operator(**base)


def test_reviewed_relation_example():
    from scirel.closures.boltzmann_quasineutrality import compute_boltzmann_electron_state
    import numpy as np

    e = 1.602176634e-19
    neutral = compute_boltzmann_electron_state(np.log(2.0), e, 3.0, 0.0, 3.0, 2.0)
    np.testing.assert_allclose(neutral["electron_density_m3"], 6.0)
    np.testing.assert_allclose(neutral["electron_pressure_pa"], 6.0 * e)
    np.testing.assert_allclose(neutral["logarithmic_charge_residual"], 0.0, atol=1e-14)

    offset = compute_boltzmann_electron_state(0.0, e, 3.0, 0.0, 3.0, 2.0)
    np.testing.assert_allclose(offset["logarithmic_charge_residual"], np.log(2.0))
    np.testing.assert_allclose(offset["charge_residual_m3"], 3.0)
    np.testing.assert_allclose(offset["relative_charge_residual"], 1.0 / 3.0)

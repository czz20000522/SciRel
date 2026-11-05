"""Direct contract tests for the atomic-H charge-exchange cross section."""

from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import evaluate_atomic_hydrogen_charge_exchange_cross_section

JANE_COEFFICIENTS = np.array(
    [
        -3.274123792568e1,
        -8.916456579806e-2,
        -3.016990732025e-2,
        9.205482406462e-3,
        2.400266568315e-3,
        -1.927122311323e-3,
        3.654750340106e-4,
        -2.788866460622e-5,
        7.422296363524e-7,
    ]
)
JOIN_EV = 1.267317514018116e4


def independent_janev(energy_ev):
    return np.exp(np.polynomial.polynomial.polyval(np.log(energy_ev), JANE_COEFFICIENTS)) * 1.0e-4


def independent_lindsay_stebbings(energy_ev):
    energy_kev = np.asarray(energy_ev, dtype=float) / 1000.0
    return (
        (4.15 - 0.531 * np.log(energy_kev)) ** 2
        * (1.0 - np.exp(-67.3 / energy_kev)) ** 4.5
        * 1.0e-20
    )


def independent_composite(energy_ev):
    energy = np.asarray(energy_ev, dtype=float)
    return np.where(
        energy <= JOIN_EV,
        independent_janev(energy),
        independent_lindsay_stebbings(energy),
    )


def independent_freeman(energy_ev):
    clipped = np.clip(energy_ev, 0.1, 1.0e5)
    return (
        1.0e-4
        * 0.6937e-14
        * (1.0 - 0.155 * np.log10(clipped)) ** 2
        / (1.0 + 0.1112e-14 * clipped**3.3)
    )


def test_default_composite_matches_independent_evaluation():
    energy = np.array(
        [0.1, 1.0, 100.0, 1.0e3, 1.0e4, JOIN_EV * 0.9, JOIN_EV, JOIN_EV * 1.1, 1.0e5, 2.5e5]
    )
    actual = evaluate_atomic_hydrogen_charge_exchange_cross_section(energy)
    np.testing.assert_allclose(actual, independent_composite(energy), rtol=1e-14, atol=0.0)
    assert actual.shape == energy.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_published_high_energy_values_are_inside_the_source_reliability():
    energy_kev = np.array([30.0, 50.0, 80.0, 100.0])
    expected = independent_lindsay_stebbings(energy_kev * 1000.0)
    actual = evaluate_atomic_hydrogen_charge_exchange_cross_section(energy_kev * 1000.0)
    np.testing.assert_allclose(actual, expected, rtol=0.11, atol=0.0)


def test_default_is_continuous_at_the_fit_crossing():
    below = evaluate_atomic_hydrogen_charge_exchange_cross_section(np.nextafter(JOIN_EV, 0.0))
    at = evaluate_atomic_hydrogen_charge_exchange_cross_section(JOIN_EV)
    above = evaluate_atomic_hydrogen_charge_exchange_cross_section(np.nextafter(JOIN_EV, np.inf))
    np.testing.assert_allclose([below, at, above], 7.675617010313647e-20, rtol=1e-12, atol=0.0)


def test_default_no_longer_repeats_the_20_kev_endpoint():
    high = evaluate_atomic_hydrogen_charge_exchange_cross_section(np.array([2.01e4, 3.0e4]))
    assert high[1] < high[0] / 1.4


def test_freeman_branch_matches_independent_evaluation_and_differs_from_default():
    energy = np.array([0.1, 1.0, 100.0, 1.0e4, 1.0e5])
    freeman = evaluate_atomic_hydrogen_charge_exchange_cross_section(energy, freeman=True)
    np.testing.assert_allclose(freeman, independent_freeman(energy), rtol=1e-15, atol=0.0)
    default = evaluate_atomic_hydrogen_charge_exchange_cross_section(energy)
    assert not np.allclose(default, freeman, rtol=1e-12, atol=0.0)


def test_endpoint_clipping_is_preserved_and_warned():
    with pytest.warns(RuntimeWarning, match="upper limit"):
        result = evaluate_atomic_hydrogen_charge_exchange_cross_section(
            np.array([0.01, 0.1, 2.5e5, 3.0e5])
        )
    assert result[0] == result[1]
    assert result[-1] == result[-2]
    with pytest.warns(RuntimeWarning, match="upper limit"):
        freeman = evaluate_atomic_hydrogen_charge_exchange_cross_section(
            np.array([0.01, 0.1, 1.0e5, 2.0e5]), freeman=True
        )
    assert freeman[0] == freeman[1]
    assert freeman[-1] == freeman[-2]


def test_scalar_input_returns_zero_dimensional_result():
    result = evaluate_atomic_hydrogen_charge_exchange_cross_section(np.asarray(100.0))
    assert np.ndim(result) == 0
    assert np.isfinite(result) and result > 0.0


def test_negative_energy_is_rejected():
    with pytest.raises(ValueError, match="nonnegative"):
        evaluate_atomic_hydrogen_charge_exchange_cross_section(np.array([1.0, -0.5]))


def test_nonfinite_energy_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        evaluate_atomic_hydrogen_charge_exchange_cross_section([1.0, np.nan])


def test_non_scalar_freeman_selector_is_rejected():
    with pytest.raises(ValueError, match="freeman"):
        evaluate_atomic_hydrogen_charge_exchange_cross_section(
            np.array([1.0, 10.0]), freeman=np.ones((2, 2, 1))
        )


def test_composition_with_maxwellian_rate_average():
    from scirel.collisions import average_cross_section_over_maxwellian

    dvr = 3.5 / 24
    dvx = 7.0 / 36
    vr = (np.arange(24) + 0.5) * dvr
    vx = (np.arange(36) + 0.5) * dvx - 3.5
    vth = np.sqrt(2.0 * 1.602177e-19 * 20.0 / (2.0 * 1.6726231e-27))
    volume = np.outer(vr * dvr, np.full(36, dvx)) * vth**3
    rate = average_cross_section_over_maxwellian(
        particle_energy_ev=np.array([10.0, 100.0, 1.0e3]),
        particle_mass_amu=1.0,
        target_temperature_ev=10.0,
        target_mass_amu=1.0,
        vx=vx,
        vr=vr,
        tnorm_ev=20.0,
        cylindrical_volume=volume,
        cross_section_m2=evaluate_atomic_hydrogen_charge_exchange_cross_section,
    )
    assert rate.shape == (3,)
    assert np.all(np.isfinite(rate)) and np.all(rate > 0.0)

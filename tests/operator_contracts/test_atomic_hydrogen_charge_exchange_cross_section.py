"""Direct contract tests for ``scirel.collisions.atomic_hydrogen_charge_exchange_cross_section``.

The saved KN1DPy leaf (source anchor ``KN1DPy/sigma/sigma_cx_h0.py:7-32`` with
``KN1DPy/poly.py:3-10``) is a source-free Janev logarithmic-polynomial fit for
the H + H+ charge-exchange cross section with an alternative Freeman--Jones
analytic branch, both source-clipped in energy.  The tests below assert the
clipped branches against an independent evaluation, the documented endpoint
clipping, and the fail-closed contracts.  Two documented repairs relative to
the saved implementation are exercised: negative energies are rejected (the
saved document declares nonnegative energies but its implementation silently
clipped them to the lower endpoint), and the branch selector is required to be
a scalar (the saved document declares a scalar but its implementation accepted
arrays through ``np.any``).
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import (
    evaluate_atomic_hydrogen_charge_exchange_cross_section,
)

JANE_COEFFICIENTS = np.array([
    -3.274123792568e1, -8.916456579806e-2, -3.016990732025e-2,
    9.205482406462e-3, 2.400266568315e-3, -1.927122311323e-3,
    3.654750340106e-4, -2.788866460622e-5, 7.422296363524e-7,
])


def independent_janev(energy):
    clipped = np.clip(energy, 0.1, 2.01e4)
    return np.exp(np.polynomial.polynomial.polyval(np.log(clipped), JANE_COEFFICIENTS)) * 1.0e-4


def independent_freeman(energy):
    clipped = np.clip(energy, 0.1, 1.0e5)
    return 1.0e-4 * 0.6937e-14 * (1.0 - 0.155 * np.log10(clipped)) ** 2 / (
        1.0 + 0.1112e-14 * clipped**3.3
    )


def test_janev_branch_matches_independent_evaluation():
    energy = np.array([0.1, 0.5, 1.0, 10.0, 100.0, 1.0e3, 1.0e4, 2.01e4])
    actual = evaluate_atomic_hydrogen_charge_exchange_cross_section(energy)
    np.testing.assert_allclose(actual, independent_janev(energy), rtol=1e-15, atol=0.0)
    assert actual.shape == energy.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_freeman_branch_matches_independent_evaluation_and_differs_from_janev():
    energy = np.array([0.1, 1.0, 100.0, 1.0e4, 1.0e5])
    freeman = evaluate_atomic_hydrogen_charge_exchange_cross_section(energy, freeman=True)
    np.testing.assert_allclose(freeman, independent_freeman(energy), rtol=1e-15, atol=0.0)
    janev = evaluate_atomic_hydrogen_charge_exchange_cross_section(energy)
    assert not np.allclose(janev, freeman, rtol=1e-12, atol=0.0)


def test_endpoint_clipping_is_preserved():
    energy = np.array([0.01, 0.1, 2.01e4, 3.0e4])
    result = evaluate_atomic_hydrogen_charge_exchange_cross_section(energy)
    assert result[0] == result[1]
    assert result[-1] == result[-2]
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
    """Documented repair: the saved implementation clipped negatives silently."""
    with pytest.raises(ValueError, match="nonnegative"):
        evaluate_atomic_hydrogen_charge_exchange_cross_section(np.array([1.0, -0.5]))


def test_nonfinite_energy_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        evaluate_atomic_hydrogen_charge_exchange_cross_section([1.0, np.nan])


def test_non_scalar_freeman_selector_is_rejected():
    """Documented repair: the saved implementation accepted arrays via np.any."""
    with pytest.raises(ValueError, match="freeman"):
        evaluate_atomic_hydrogen_charge_exchange_cross_section(
            np.array([1.0, 10.0]), freeman=np.ones((2, 2, 1))
        )


def test_composition_with_maxwellian_rate_average():
    """The cross section feeds the retained Maxwellian relative-speed average."""
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

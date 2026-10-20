"""Direct contract tests for ``scirel.collisions.molecular_hydrogen_charge_exchange_cross_section``.

The saved the neutral-transport formulation leaf is a source-free Janev logarithmic-polynomial
fit for the H2 + H2+ charge-exchange cross section, source-clipped in energy.
The tests assert the clipped branch against an independent evaluation, the
documented endpoint clipping, and the fail-closed contracts.  One documented
repair relative to the saved implementation is exercised: negative energies
are rejected (the saved document declares nonnegative energies but its
implementation silently clipped them to the lower endpoint).
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import (
    evaluate_molecular_hydrogen_charge_exchange_cross_section,
)

COEFFICIENTS = np.array([
    -3.427958758517e1,
    -7.121484125189e-2,
    4.690466187943e-2,
    -8.033946660540e-3,
    -2.265090924593e-3,
    -2.102414848737e-4,
    1.948869487515e-4,
    -2.208124950005e-5,
    7.262446915488e-7,
])


def independent_janev(energy):
    clipped = np.clip(energy, 0.1, 2.01e4)
    return np.exp(np.polynomial.polynomial.polyval(np.log(clipped), COEFFICIENTS)) * 1.0e-4


def test_branch_matches_independent_evaluation():
    energy = np.array([0.1, 0.5, 1.0, 10.0, 100.0, 1.0e3, 1.0e4, 2.01e4])
    actual = evaluate_molecular_hydrogen_charge_exchange_cross_section(energy)
    np.testing.assert_allclose(actual, independent_janev(energy), rtol=1e-15, atol=0.0)
    assert actual.shape == energy.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_holdout_grid_matches_independent_evaluation():
    energy = np.array([0.15, 3.0, 75.0, 900.0, 1.9e4])
    np.testing.assert_allclose(
        evaluate_molecular_hydrogen_charge_exchange_cross_section(energy),
        independent_janev(energy),
        rtol=1e-15,
        atol=0.0,
    )


def test_endpoint_clipping_is_preserved():
    result = evaluate_molecular_hydrogen_charge_exchange_cross_section(
        np.array([0.01, 0.1, 3.0e4, 2.01e4])
    )
    assert result[0] == result[1]
    assert result[-1] == result[-2]


def test_scalar_input_returns_zero_dimensional_result():
    result = evaluate_molecular_hydrogen_charge_exchange_cross_section(np.asarray(100.0))
    assert np.ndim(result) == 0
    assert np.isfinite(result) and result > 0.0


def test_differs_from_the_atomic_hydrogen_branch():
    """H2+ + H2 is a different physical system from H+ + H."""
    from scirel.collisions import evaluate_atomic_hydrogen_charge_exchange_cross_section

    energy = np.array([0.1, 1.0, 100.0, 1.0e3, 1.0e4])
    molecular = evaluate_molecular_hydrogen_charge_exchange_cross_section(energy)
    atomic = evaluate_atomic_hydrogen_charge_exchange_cross_section(energy)
    assert not np.allclose(molecular, atomic, rtol=1e-12, atol=0.0)


def test_negative_energy_is_rejected():
    """Documented repair: the saved implementation clipped negatives silently."""
    with pytest.raises(ValueError, match="nonnegative"):
        evaluate_molecular_hydrogen_charge_exchange_cross_section(np.array([1.0, -0.5]))


def test_nonfinite_energy_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        evaluate_molecular_hydrogen_charge_exchange_cross_section([1.0, np.nan])


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
        particle_mass_amu=2.0,
        target_temperature_ev=10.0,
        target_mass_amu=2.0,
        vx=vx,
        vr=vr,
        tnorm_ev=20.0,
        cylindrical_volume=volume,
        cross_section_m2=evaluate_molecular_hydrogen_charge_exchange_cross_section,
    )
    assert rate.shape == (3,)
    assert np.all(np.isfinite(rate)) and np.all(rate > 0.0)

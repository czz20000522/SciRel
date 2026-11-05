"""Direct contract tests for ``scirel.collisions.atomic_hydrogen_elastic_cross_section``.

The saved the neutral-transport formulation leaf carries two logarithmic-polynomial fits for
the H-on-H elastic cross section -- momentum transfer by default, viscosity
under the selector -- both source-clipped to ``[0.03, 1.01e4] eV``.  The tests
assert both branches against independent evaluations, the endpoint clipping,
and the fail-closed contracts.  Two documented repairs relative to the saved
implementation are exercised: negative energies are rejected (the saved
document declares nonnegative energies but its implementation silently clipped
them to the lower endpoint), and the ``viscosity`` selector must be a scalar
(the saved document declares a scalar but its implementation reduced arrays
with ``bool()``).
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import evaluate_atomic_hydrogen_elastic_cross_section

MOMENTUM_TRANSFER_COEFFICIENTS = np.array(
    [-3.330843e1, -5.738374e-1, -1.028610e-1, -3.920980e-3, 5.964135e-4],
    dtype=float,
)
VISCOSITY_COEFFICIENTS = np.array(
    [-3.344860e1, -4.238982e-1, -7.477873e-2, -7.915053e-3, -2.686129e-4],
    dtype=float,
)


def independent_fit(energy, coefficients):
    clipped = np.clip(energy, 0.03, 1.01e4)
    return np.exp(np.polynomial.polynomial.polyval(np.log(clipped), coefficients)) * 1.0e-4


def test_momentum_transfer_branch_matches_independent_evaluation():
    energy = np.array([0.03, 0.5, 1.0, 10.0, 100.0, 1.0e3, 1.01e4])
    actual = evaluate_atomic_hydrogen_elastic_cross_section(energy)
    np.testing.assert_allclose(
        actual, independent_fit(energy, MOMENTUM_TRANSFER_COEFFICIENTS), rtol=1e-15, atol=0.0
    )
    assert actual.shape == energy.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_viscosity_branch_matches_independent_evaluation_and_differs():
    energy = np.array([0.03, 1.0, 50.0, 1.0e3, 1.01e4])
    actual = evaluate_atomic_hydrogen_elastic_cross_section(energy, viscosity=True)
    np.testing.assert_allclose(
        actual, independent_fit(energy, VISCOSITY_COEFFICIENTS), rtol=1e-15, atol=0.0
    )
    momentum = evaluate_atomic_hydrogen_elastic_cross_section(energy)
    assert not np.allclose(momentum, actual, rtol=1e-12, atol=0.0)


def test_endpoint_clipping_is_preserved():
    result = evaluate_atomic_hydrogen_elastic_cross_section(np.array([0.01, 0.03, 2.0e4, 1.01e4]))
    assert result[0] == result[1]
    assert result[-1] == result[-2]


def test_scalar_input_returns_zero_dimensional_result():
    result = evaluate_atomic_hydrogen_elastic_cross_section(np.asarray(100.0))
    assert np.ndim(result) == 0
    assert np.isfinite(result) and result > 0.0


def test_negative_energy_is_rejected():
    """Documented repair: the saved implementation clipped negatives silently."""
    with pytest.raises(ValueError, match="nonnegative"):
        evaluate_atomic_hydrogen_elastic_cross_section(np.array([1.0, -0.5]))


def test_nonfinite_energy_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        evaluate_atomic_hydrogen_elastic_cross_section([1.0, np.nan])


def test_non_scalar_viscosity_selector_is_rejected():
    """Documented repair: the saved implementation relied on bool() coercion,
    which silently accepted 0-d/size-1 arrays and failed on multi-element
    arrays with NumPy's generic ambiguity error; the successor requires a
    0-d scalar and names the quantity."""
    with pytest.raises(ValueError, match="viscosity"):
        evaluate_atomic_hydrogen_elastic_cross_section(
            np.array([1.0, 10.0]), viscosity=np.ones((2, 2))
        )


def test_composition_with_maxwellian_rate_average():
    """The momentum-transfer fit feeds the retained Maxwellian relative-speed average."""
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
        cross_section_m2=evaluate_atomic_hydrogen_elastic_cross_section,
    )
    assert rate.shape == (3,)
    assert np.all(np.isfinite(rate)) and np.all(rate > 0.0)

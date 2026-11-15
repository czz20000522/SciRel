import warnings

import numpy as np
import pytest
from scipy.integrate import IntegrationWarning, quad

from scirel.plasma.fast_ion_heating import fast_ion_fractional_heating


def test_zero_birth_energy_is_finite_continuous_limit():
    assert fast_ion_fractional_heating(0.0, 10.0, 2.0) == 1.0
    np.testing.assert_array_equal(
        fast_ion_fractional_heating(np.array([0.0, 1e-3]), 10.0, 2.0)[0], 1.0
    )


def test_relation_matches_independent_direct_expression_away_from_boundary():
    E, Te, mass = 20.0, 4.0, 2.0
    x2 = E / (10.0 * mass * Te)
    x = np.sqrt(x2)
    expected = (
        2.0
        * (
            (1 / 6) * np.log((1 - x + x2) / (1 + 2 * x + x2))
            + (np.arctan((2 * x - 1) / np.sqrt(3)) + np.pi / 6) / np.sqrt(3)
        )
        / x2
    )
    assert np.isclose(fast_ion_fractional_heating(E, Te, mass), expected, rtol=1e-14, atol=1e-14)


def test_mixed_small_and_closed_form_entries_preserve_exact_values():
    E = np.array([0.0, 20.0])
    Te = 4.0
    mass = 2.0
    large_expected = fast_ion_fractional_heating(E[1], Te, mass)
    np.testing.assert_array_equal(
        fast_ion_fractional_heating(E, Te, mass),
        np.array([1.0, large_expected]),
    )


@pytest.mark.parametrize("args", [(-1.0, 10.0, 2.0), (1.0, 0.0, 2.0), (1.0, 10.0, 0.0)])
def test_invalid_domain_fails_closed(args):
    with pytest.raises(ValueError):
        fast_ion_fractional_heating(*args)


@pytest.mark.parametrize("parameter", range(3))
@pytest.mark.parametrize(
    "value",
    [
        20.0 + 7.0j,
        np.array([20.0 + 7.0j]),
        np.array([20.0 + 7.0j], dtype=object),
        np.ma.array([20.0], mask=[True]),
    ],
    ids=["complex-scalar", "complex-array", "complex-object", "masked"],
)
def test_rejects_nonreal_or_masked_physical_inputs(parameter, value):
    args = [20.0, 4.0, 2.0]
    args[parameter] = value
    with pytest.raises(ValueError, match="real|masked"):
        fast_ion_fractional_heating(*args)


def _bounded_integral_reference(x2):
    """Integrate the defining relation without using its production antiderivative."""
    x = np.sqrt(x2)
    options = dict(epsabs=2e-13, epsrel=2e-13, limit=100)
    with warnings.catch_warnings():
        warnings.simplefilter("error", IntegrationWarning)
        if x <= 1:
            # t = x*u avoids dividing two tiny independently rounded numbers.
            return quad(lambda u: 2 * u / (1 + (x * u) ** 3), 0.0, 1.0, **options)
        first, first_error = quad(lambda t: t / (1 + t**3), 0.0, 1.0, **options)
        # u = 1/t maps [1,x] to [1/x,1]; a huge direct interval can miss the peak.
        tail, tail_error = quad(lambda u: 1 / (1 + u**3), 1 / x, 1.0, **options)
    return 2 * (first + tail) / x2, 2 * (first_error + tail_error) / x2


@pytest.mark.parametrize(
    "x2",
    [1e-16, 1e-8, 0.009999, 0.01, 0.010001, 0.25, 1.0, 4.0, 100.0, 1e6, 1e12, 1e24],
)
def test_heating_matches_independent_bounded_integral(x2):
    reference, integration_error = _bounded_integral_reference(x2)
    # The independently requested quadrature error uses at most a quarter of
    # the 2e-12 comparison budget; no pre-existing tolerance is relaxed.
    assert integration_error <= 0.25 * 2e-12 * abs(reference)
    actual = fast_ion_fractional_heating(10 * x2, 1.0, 1.0)
    np.testing.assert_allclose(actual, reference, rtol=2e-12, atol=0)


def test_heating_fraction_bounds_and_monotonicity_follow_integral():
    x2 = np.r_[0.0, np.logspace(-16, 24, 161)]
    actual = fast_ion_fractional_heating(10 * x2, 1.0, 1.0)
    # f = integral_0^1 2*u/(1+x^3*u^3) du: it is positive, <=1, and decreasing.
    assert np.all((actual > 0) & (actual <= 1))
    assert np.all(np.diff(actual) <= 0)

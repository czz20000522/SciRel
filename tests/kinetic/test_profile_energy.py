"""Discrete conservation and boundary regressions for the the profile convention family."""

import numpy as np
import pytest

from scirel.source import gaussian_profile, exponential_profile
from scirel.physics import calculate_stored_thermal_energy


R = np.array([0.05, 0.2, 0.6, 0.9])
V = np.array([2.0, 3.0, 7.0, 11.0])
D = np.array([0.1, 0.2, 0.45, 0.25])


@pytest.mark.parametrize(
    "width",
    [1, np.int64(1), np.float32(0.2), 0.2, -1, -np.nextafter(0.0, 1.0), np.nextafter(0.0, 1.0)],
)
@pytest.mark.parametrize("kind", ["gaussian", "exponential"])
def test_signed_integer_tiny_width_discrete_conservation(width, kind):
    f = gaussian_profile if kind == "gaussian" else exponential_profile
    kw = {"center": 0.6} if kind == "gaussian" else {"decay_start": 0.8}
    result = f(R, V, D, width=width, total=17.0, **kw)
    assert result.shape == R.shape
    assert result.dtype == np.float64
    assert np.all(np.isfinite(result))
    assert np.sum(result * V * D) == pytest.approx(17.0, rel=2e-15)


@pytest.mark.parametrize("width", [0, -0.0, np.nan, np.inf, -np.inf])
def test_invalid_width_preserves_nan(width):
    assert np.all(np.isnan(gaussian_profile(R, V, D, center=0.5, width=width, total=1)))
    assert np.all(np.isnan(exponential_profile(R, V, D, decay_start=0.5, width=width, total=1)))


def test_nonuniform_gaussian_analytic_samples_and_sink():
    shape = np.exp(-((R - 0.4) ** 2) / (2 * 0.3**2))
    expected = -3 * shape / sum(shape * V * D)
    np.testing.assert_allclose(
        gaussian_profile(R, V, D, center=0.4, width=0.3, total=-3), expected, rtol=2e-15
    )


def test_exponential_start_cancels_and_negative_width_reverses():
    for w in [0.1, -0.1]:
        a = exponential_profile(R, V, D, decay_start=-1e300, width=w, total=3)
        b = exponential_profile(R, V, D, decay_start=1e300, width=w, total=3)
        np.testing.assert_array_equal(a, b)
        assert np.all(np.sign(np.diff(a)) == np.sign(w))


def test_thermal_independent_total_and_profile_composition():
    p = gaussian_profile(R, V, D, center=0.6, width=0.2, total=4.0)
    e = calculate_stored_thermal_energy(p, 2 * p, 7 * p, V, D)
    np.testing.assert_allclose(e, [6.0, 12.0, 42.0], rtol=2e-15)
    # No temperature/density conversion, closure, or forced total-pressure sum.
    np.testing.assert_allclose(
        calculate_stored_thermal_energy(np.ones(4) * 2, np.ones(4) * 3, np.ones(4) * 5, V, D),
        np.array([3.0, 4.5, 7.5]) * sum(V * D),
        rtol=2e-15,
    )


@pytest.mark.parametrize(
    "bad", [[], [1, 2], [[1, 2, 3, 4]], [0, 1, 1, 2], [True] * 4, [1, np.nan, 2, 3]]
)
def test_geometry_rejects_malformed_grid(bad):
    with pytest.raises(ValueError):
        gaussian_profile(bad, V, D, center=0.4, width=0.2, total=1)


@pytest.mark.parametrize("bad", [0, -1, np.inf, np.nan])
def test_weights_reject_invalid_values(bad):
    v = V.copy()
    v[0] = bad
    with pytest.raises(ValueError):
        gaussian_profile(R, v, D, center=0.4, width=0.2, total=1)
    with pytest.raises(ValueError):
        calculate_stored_thermal_energy(V, V, V, v, D)


@pytest.mark.parametrize("bad", [True, 1 + 0j, "1", [1], np.ma.array(1)])
def test_scalar_contract(bad):
    with pytest.raises(ValueError):
        gaussian_profile(R, V, D, center=0.4, width=bad, total=1)


def test_pressure_no_broadcast_and_signed_algebra():
    for p in [1.0, [1, 2], [1, np.inf, 3, 4]]:
        with pytest.raises(ValueError):
            calculate_stored_thermal_energy(p, V, V, V, D)
    assert calculate_stored_thermal_energy([-1, 2, 3, 4], V, V, V, D)[0] == pytest.approx(
        1.5 * np.dot([-1, 2, 3, 4], V * D)
    )


def test_large_width_flat_limit_and_extreme_center():
    p = gaussian_profile(R, V, D, center=0.5, width=np.finfo(float).max, total=3.0)
    np.testing.assert_allclose(p, np.ones(4) * 3 / sum(V * D), rtol=2e-15)
    p = gaussian_profile(R, V, D, center=1e300, width=0.2, total=3.0)
    assert np.all(np.isfinite(p))
    assert p[-1] * V[-1] * D[-1] == pytest.approx(3.0, rel=2e-15)


def test_unrepresentable_result_is_explicit():
    with pytest.raises(FloatingPointError):
        gaussian_profile(
            [0.5], [np.nextafter(0.0, 1.0)], [np.nextafter(0.0, 1.0)], center=0.5, width=1, total=1
        )
    with pytest.raises(FloatingPointError):
        calculate_stored_thermal_energy([1e308], [1e308], [1e308], [2], [1])


def test_underflow_does_not_erase_integral_or_reject_negligible_tails():
    with pytest.raises(FloatingPointError):
        gaussian_profile([0.5], [1e200], [1e200], center=0.5, width=1, total=1e-300)
    with pytest.raises(FloatingPointError):
        calculate_stored_thermal_energy([1e-300], [1e-300], [1e-300], [1e-200], [1e-200])
    p = gaussian_profile(R, V, D, center=0.6, width=0.01, total=1.0)
    assert np.sum(p * V * D) == pytest.approx(1.0, rel=2e-15)

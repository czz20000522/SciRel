"""Counterexamples retained before the bounded GPDF D2 numerical repair."""

import numpy as np
import pytest
from scipy.special import wofz
from scirel.kinetic import evaluate_cauchy_transform as cauchy
from scirel.kinetic import evaluate_maxwellian_electrostatic as response
from scirel.kinetic import solve_maxwellian_electrostatic_mode as solve


@pytest.mark.parametrize("k", [1e-5, 1e-7, 1e-9, 1e-10])
def test_small_k_dielectric_has_physical_cold_limit(k):
    # Gaussian moments: E[v^2]=1, E[v^4]=3, E[v^6]=15.
    expected = 0.75 - 3 * k * k / 16 - 15 * k**4 / 64
    assert abs(complex(response(2.0, k)["epsilon"]) - expected) < 1e-13


@pytest.mark.parametrize("k", [1e-5, 1e-7, 1e-9, 1e-10])
def test_small_k_root_does_not_accept_nonroot_seed(k):
    result = solve(k, 2.0)
    omega = result["omega"]
    independent_epsilon = 1 - 1 / omega**2 - 3 * k * k / omega**4 - 15 * k**4 / omega**6
    assert abs(independent_epsilon) < 1e-9
    assert abs(omega - 2) > 0.5


@pytest.mark.parametrize("center,width", [(10.0, 0.1), (100.0, 0.1), (100.0, 1.0)])
def test_shifted_gaussian_requires_explicit_feature_resolution(center, width):
    density = lambda v: np.exp(-(((v - center) / width) ** 2)) / (np.sqrt(np.pi) * width)
    # No finite sampling method can locate arbitrary hidden callback support.
    with pytest.raises(ValueError):
        cauchy(1j, density)
    mesh = center + width * np.linspace(-10, 10, 41)
    actual = cauchy(1j, density, integration_mesh=mesh)
    expected = 1j * np.sqrt(np.pi) * wofz((1j - center) / width) / width
    assert abs(actual["G"] - expected) < 1e-9
    assert np.all(actual["quadrature_error"] >= 0)


@pytest.mark.parametrize("value", [None, [], [1, 2], True, 0, np.inf])
def test_cauchy_invalid_tolerance_exception(value):
    with pytest.raises(ValueError):
        cauchy(1j, lambda v: np.exp(-v * v), bounds=(-10, 10), epsabs=value)


@pytest.mark.parametrize("k,seed", [(0.4, 1.45 - 0.1j), (0.1, 1.1 - 0.01j), (1e-9, 2.0)])
def test_successful_roots_pass_normalized_physical_residual(k, seed):
    result = solve(k, seed)
    assert result["normalized_residual"] <= 1e-9
    assert result["normalized_residual_error"] <= 1e-9 / 4
    with pytest.raises(RuntimeError):
        solve(k, seed, max_evaluations=1)


def test_finite_support_continuation_only_inside_support():
    density = lambda v: 1.0
    analytic = lambda z: 1.0
    # Outside the finite support, lower-half-plane evaluation remains the
    # real-contour Cauchy integral; continuation is only interior.
    z = 2.0 - 1j
    expected = np.log(1 - z) - np.log(-1 - z)
    actual = cauchy(z, density, bounds=(-1, 1), analytic_density=analytic)["G"]
    assert abs(actual - expected) < 1e-10


@pytest.mark.parametrize("x", [-2.0, -1.0, 0.0, 1.0, 2.0])
def test_finite_support_landau_continuation_crossing_policy(x):
    z = x - 1j
    reference = np.log(1 - z) - np.log(-1 - z)
    if -1 < x < 1:
        reference += 2j * np.pi
    actual = cauchy(z, lambda v: 1.0, bounds=(-1, 1), analytic_density=lambda z: 1.0)["G"]
    assert abs(actual - reference) < 1e-10


def test_cauchy_rejects_complex_or_boolean_mesh():
    with pytest.raises(ValueError):
        cauchy(1j, lambda v: 1.0, integration_mesh=np.array([-1 + 1j, 0, 1]))
    with pytest.raises(ValueError):
        cauchy(1j, lambda v: 1.0, integration_mesh=np.array([False, True]))


def test_cauchy_nonconvergence_fails_closed():
    with pytest.raises(RuntimeError):
        cauchy(1j, lambda v: np.sin(10000 * v), bounds=(-1, 1), limit=1)


def test_cauchy_whole_line_lower_continuation_with_mesh():
    density = lambda v: np.exp(-v * v) / np.sqrt(np.pi)
    extension = lambda z: np.exp(-z * z) / np.sqrt(np.pi)
    mesh = np.linspace(-8, 8, 65)
    result = cauchy(-0.3j, density, analytic_density=extension, integration_mesh=mesh)
    from scipy.special import wofz

    expected = 1j * np.sqrt(np.pi) * wofz(-0.3j)
    assert abs(result["G"] - expected) < 1e-9


def test_cauchy_rejects_complex_or_boolean_bounds():
    with pytest.raises(ValueError):
        cauchy(1j, lambda v: 1.0, bounds=np.array([-1 + 1j, 1]))
    with pytest.raises(ValueError):
        cauchy(1j, lambda v: 1.0, bounds=(False, 1))

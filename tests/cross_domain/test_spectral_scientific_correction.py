"""Independent identities for the 2026-10-12 spectral/diagnostic corrections."""

import math
import numpy as np
import pytest
from scirel.kinetic.loss_cone_spectrum import solve_loss_cone_spectrum
from scirel.kinetic.frank_egedal_source_projection import fractional_mode
from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments
from scirel.diagnostics.parallel_pressure_residual import compute_parallel_pressure_residual
from scirel.diagnostics.firehose_mirror_margins import compute_firehose_mirror_margins


@pytest.mark.parametrize("backend", ["truncated", "hypergeometric"])
def test_integer_ground_eigenmode_is_not_discarded(backend):
    result = solve_loss_cone_spectrum(1 / math.sqrt(3), 3, backend=backend)
    assert result["eigenvalues"][0] == pytest.approx(6.0, rel=1e-9)
    assert np.all(np.diff(result["eigenvalues"]) > 0)


@pytest.mark.parametrize("backend", ["truncated", "hypergeometric"])
def test_even_mode_is_regular_at_integer_degree_and_not_truncated(backend):
    x = np.linspace(-0.9, 0.9, 37)
    np.testing.assert_allclose(
        fractional_mode(2, x, 2, backend), 1 - 3 * x * x, rtol=2e-13, atol=2e-13
    )


def test_uniform_isotropic_parallel_state_with_explicit_derivative():
    result = compute_parallel_pressure_residual(
        np.full((3, 3), 2.0), np.full((3, 3), 2.0), np.ones((3, 3)), dp_parallel_dB=0.0
    )
    assert result["passed"]
    np.testing.assert_array_equal(result["error"], 0.0)


def test_fixed_flux_derivative_must_not_mix_flux_surfaces():
    B = np.array([[1.0, 1.3, 2.0], [1.0, 1.3, 2.0]])
    psi = np.array([[0.0, 0.0, 0.0], [3.0, 3.0, 3.0]])
    p = (psi + 1) * B * B
    result = compute_parallel_pressure_residual(p, -p, B, field_axis=1, psi=psi, rtol=1e-12)
    np.testing.assert_allclose(result["rhs"], -p, rtol=1e-12, atol=1e-12)
    assert result["passed"]


def test_missing_derivative_information_is_not_silently_zero():
    with pytest.raises(ValueError, match="derivative|fixed"):
        compute_parallel_pressure_residual(np.array([2.0, 3.0, 4.0]), np.zeros(3), np.ones(3))
    with pytest.raises(ValueError, match="derivative|fixed"):
        compute_firehose_mirror_margins(np.ones(3), np.array([1.0, 4.0, 9.0]), np.ones(3))


def test_invariant_bimaxwellian_mirror_threshold_has_positive_slope_sign():
    result = compute_firehose_mirror_margins(
        np.array([1.0]), np.array([2.0]), np.array([1.0]), mu0=1.0, dp_perp_dB=-4.0
    )
    np.testing.assert_array_equal(result["firehose_margin"], [2.0])
    np.testing.assert_array_equal(result["mirror_margin"], [-3.0])
    assert not result["mirror_stable"]


@pytest.mark.parametrize("lower", [0.0, 0.25, 0.8])
def test_same_population_tensor_uses_identical_velocity_domain(lower):
    constant = lambda degree, xi, terms: np.ones_like(xi)
    result = evaluate_frank_egedal_hot_ion_moments(
        [[1.0]],
        {
            "B0": 1.0,
            "mirror_ratio": 1e12,
            "vc_over_v0": 0.8,
            "beta_m": 0.0,
            "velocity_lower": lower,
            "velocity_nodes": 48,
            "pitch_nodes": 48,
        },
        [0.0],
        [1.0],
        15,
        constant,
    )
    xi2 = 1 - 1 / 1e12
    expected = (3 - xi2) / (2 * xi2)
    np.testing.assert_allclose(
        result["hot_perpendicular_shape"], [[expected]], rtol=2e-12, atol=2e-12
    )


def test_reference_population_below_reference_field_has_accessible_pitch_support():
    from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments

    b, mirror = 0.25, 4.0
    upper, lower = np.sqrt(1 - b / mirror), np.sqrt(1 - b)
    mid = np.sqrt(1 - 1 / mirror)
    got = evaluate_frank_egedal_hot_ion_moments(
        [[b]],
        {"B0": 1.0, "mirror_ratio": mirror, "beta_m": 0.0, "velocity_nodes": 48, "pitch_nodes": 48},
        [0.0],
        [1.0],
        2,
        lambda degree, x, n: np.ones_like(x),
    )
    np.testing.assert_allclose(got["hot_density_shape"], [[(upper - lower) / mid]], rtol=2e-12)
    np.testing.assert_allclose(
        got["hot_parallel_shape"], [[(upper**3 - lower**3) / mid**3]], rtol=2e-12
    )
    np.testing.assert_allclose(
        got["hot_perpendicular_shape"],
        [[1.5 * ((upper - lower) - (upper**3 - lower**3) / 3) / mid**3]],
        rtol=2e-12,
    )


def test_zero_critical_speed_zero_lower_density_is_not_normalizable():
    from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments

    with pytest.raises(ValueError, match="density"):
        evaluate_frank_egedal_hot_ion_moments(
            [[1.0]],
            {"B0": 1.0, "vc_over_v0": 0.0},
            [0.0],
            [1.0],
            2,
            lambda degree, x, n: np.ones_like(x),
        )


def test_zero_critical_speed_positive_lower_remains_integrable():
    from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments

    got = evaluate_frank_egedal_hot_ion_moments(
        [[1.0]],
        {"B0": 1.0, "mirror_ratio": 4.0, "vc_over_v0": 0.0, "velocity_lower": 0.2},
        [0.0],
        [1.0],
        2,
        lambda degree, x, n: np.ones_like(x),
    )
    np.testing.assert_allclose(got["hot_parallel_shape"], [[1.0]], atol=1e-14)
    np.testing.assert_allclose(got["hot_perpendicular_shape"], [[1.5]], atol=1e-14)


def test_nonintegrable_negative_beta_cannot_hide_behind_reference_normalization():
    from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments

    with pytest.raises(RuntimeError, match="quadrature"):
        evaluate_frank_egedal_hot_ion_moments(
            [[1.0]],
            {"B0": 1.0, "mirror_ratio": 1.5, "beta_m": -0.5, "max_quadrature_nodes": 192},
            [2.0],
            [1.0],
            2,
            lambda degree, x, n: 1 - 3 * x * x,
        )


def test_integrable_negative_beta_retains_finite_normalized_population():
    from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments

    got = evaluate_frank_egedal_hot_ion_moments(
        [[1.0]],
        {"B0": 1.0, "mirror_ratio": 1.5, "beta_m": -0.1},
        [2.0],
        [1.0],
        2,
        lambda degree, x, n: 1 - 3 * x * x,
    )
    np.testing.assert_allclose(got["hot_parallel_shape"], [[1.0]], rtol=1e-12)
    assert np.isfinite(got["hot_perpendicular_shape"]).all()


@pytest.mark.parametrize("backend", ["truncated", "hypergeometric"])
def test_high_integer_mode_matches_independent_legendre_polynomial(backend):
    from scipy.special import eval_legendre
    from scirel.kinetic.frank_egedal_source_projection import fractional_mode

    x = np.linspace(-0.974, 0.974, 121)
    expected = eval_legendre(30, x) / eval_legendre(30, 0.0)
    np.testing.assert_allclose(fractional_mode(30, x, 2, backend), expected, rtol=2e-10, atol=2e-10)


def test_narrow_loss_cone_high_degree_modes_respect_rayleigh_bounds():
    from scirel.kinetic.loss_cone_spectrum import solve_loss_cone_spectrum

    x = 1e-4
    got = solve_loss_cone_spectrum(x, 3)
    constant_p = ((np.arange(3) + 0.5) * np.pi / x) ** 2
    assert np.all(got["eigenvalues"] <= constant_p * (1 + 1e-12))
    assert np.all(got["eigenvalues"] >= constant_p * (1 - x * x) * (1 - 1e-12))
    assert np.max(abs(got["boundary_residuals"])) < 2e-8


@pytest.mark.parametrize("beta", [-0.3, -0.4, -0.4999])
def test_integrable_endpoint_singularity_remains_resolved(beta):
    from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments

    got = evaluate_frank_egedal_hot_ion_moments(
        [[0.9, 1.0, 1.2]],
        {"B0": 1.0, "mirror_ratio": 1.5, "beta_m": beta},
        [2.0],
        [1.0],
        2,
        lambda degree, x, n: 1 - 3 * x * x,
    )
    assert np.isfinite(got["hot_density_shape"]).all()
    assert got["quadrature_convergence"]["raw_moments_checked"]


def test_field_normalization_overflow_rejects_false_finite_population():
    from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments

    with np.errstate(over="ignore"), pytest.raises(ValueError, match="B/B0"):
        evaluate_frank_egedal_hot_ion_moments(
            [[1e308]], {"B0": 1e-308}, [0.0], [1.0], 2, lambda degree, x, n: np.ones_like(x)
        )

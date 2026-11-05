"""R1/R2 regressions from independent Gaussian/top-hat defining equations."""

import mpmath as mp
import numpy as np
import pytest
from scirel.kinetic.generalized_dispersion import (
    evaluate_generalized_dispersion,
    evaluate_generalized_hilbert,
)


def assert_components(actual, expected, rtol=5e-12):
    actual = complex(actual)
    expected = complex(expected)
    np.testing.assert_allclose(actual.real, expected.real, rtol=rtol, atol=0)
    np.testing.assert_allclose(actual.imag, expected.imag, rtol=rtol, atol=0)


def gaussian_reference(z):
    with mp.workdps(100):
        point = mp.mpc(complex(z))
        Z = mp.j * mp.sqrt(mp.pi) * mp.exp(-point * point) * mp.erfc(-mp.j * point)
        return complex(-2 * (1 + point * Z))


@pytest.mark.parametrize(
    "z",
    [
        1e8 + 1j,
        1e8 - 1j,
        1e8j,
        -20j,
        12 + 0j,
        11.999999 + 0j,
        12.000001 + 0j,
        12j,
        11.999999j,
        12.000001j,
        12 * np.exp(0.3j),
        12 * np.exp(1.2j),
        12 * np.exp(-0.3j),
        12 * np.exp(-1.2j),
        -12 * np.exp(0.3j),
        -12 * np.exp(-0.3j),
    ],
)
def test_r1_gaussian_derivative_high_precision_components(z):
    result = evaluate_generalized_dispersion(z, 0)["Zp"]
    assert_components(result, gaussian_reference(z))


def test_r1_gaussian_large_phase_independent_squared_kernel_integral():
    with mp.workdps(80):
        z = mp.mpc(1e8, 1)
        oracle = mp.quad(lambda v: mp.exp(-v * v) / (mp.sqrt(mp.pi) * (v - z) ** 2), [-12, 0, 12])
        actual = evaluate_generalized_dispersion(complex(z), 0)["Zp"]
        assert_components(actual, oracle, rtol=2e-14)
        # Omitted normalized Gaussian mass is below2e-64; squared kernel
        # is bounded by1/(1e8-12)^2 on the omitted central-tail comparison.
        assert abs(mp.erfc(12)) < mp.mpf("2e-64")


def top_hat_reference(z):
    with mp.workdps(200):
        point = mp.mpc(complex(z))
        derivative = 1 / (point * point - mp.mpf(".25"))
        if point.imag == 0:
            Z = mp.log(abs((point - mp.mpf(".5")) / (point + mp.mpf(".5"))))
            if abs(point.real) < mp.mpf(".5"):
                Z += mp.j * mp.pi
        else:
            Z = mp.log(mp.mpf(".5") - point) - mp.log(-mp.mpf(".5") - point)
        return complex(Z), complex(derivative)


@pytest.mark.parametrize(
    "z",
    [
        1e16 + 1j,
        1e16 - 1j,
        -1e16 + 1j,
        -1e16 - 1j,
        1e16 + 0j,
        -1e16 + 0j,
        1e16j,
        -1e16j,
        0.999999 + 0j,
        1.0 + 0j,
        1.000001 + 0j,
        0.999999 * np.exp(0.7j),
        np.exp(0.7j),
        1.000001 * np.exp(0.7j),
        np.exp(-0.7j),
        -np.exp(0.7j),
        -np.exp(-0.7j),
        0.5 + 1e-10j,
        0.5 - 1e-10j,
        -0.5 + 1e-10j,
        -0.5 - 1e-10j,
        0.5 + 1e-10,
        0.5 - 1e-10,
        -0.5 + 1e-10,
        -0.5 - 1e-10,
        0j,
    ],
)
def test_r2_top_hat_transform_derivative_branches(z):
    result = evaluate_generalized_dispersion(z, 2)
    Z, Zp = top_hat_reference(z)
    assert_components(result["Z"], Z, rtol=5e-12)
    assert_components(result["Zp"], Zp, rtol=5e-12)


def test_r2_far_top_hat_independent_integral_and_convergent_series():
    with mp.workdps(180):
        z = mp.mpc("1e16", 1)
        integral = mp.quad(lambda v: 1 / (v - z), [-mp.mpf(".5"), mp.mpf(".5")])
        derivative = mp.quad(lambda v: 1 / (v - z) ** 2, [-mp.mpf(".5"), mp.mpf(".5")])
        series = -sum(1 / (2 ** (2 * n) * (2 * n + 1) * z ** (2 * n + 1)) for n in range(4))
        assert abs(integral - series) < mp.mpf("1e-140")
        result = evaluate_generalized_dispersion(complex(z), 2)
        assert_components(result["Z"], integral, rtol=2e-14)
        assert_components(result["Zp"], derivative, rtol=2e-14)


def test_r1_r2_preserve_matrix_shape_and_endpoint_failures():
    z = np.array([[1e8 + 1j, 1e16 - 1j], [12 + 0.1j, -0.3 + 0.2j]])
    for selector in (0, 2):
        result = evaluate_generalized_dispersion(z, selector)
        assert result["Z"].shape == z.shape
        assert result["Zp"].shape == z.shape
        assert np.isfinite(result["Z"]).all() and np.isfinite(result["Zp"]).all()
    for point in (-0.5, 0.5):
        with pytest.raises(ValueError):
            evaluate_generalized_dispersion(point, 2)


@pytest.mark.parametrize(
    "z", [1.79e308 + 1.79e308j, -1.79e308 + 1.79e308j, 1e200 + 1e200j, 1e200 - 1j]
)
def test_r1_huge_finite_phase_norm_and_underflow(z):
    result = evaluate_generalized_dispersion(z, 0)
    assert np.isfinite(result["Z"]).all()
    assert result["Zp"] == 0  # Exact derivative magnitude is below float64 range.


def test_r1_lower_derivative_overflow_rejects_whole_call():
    # Z itself is finite here, while multiplication by phase in Zp is not.
    with pytest.raises(ValueError, match="derivative.*not representable"):
        evaluate_generalized_dispersion(-26.6j, 0)


@pytest.mark.parametrize(
    "z",
    [
        1e-16 + 0.1j,
        -1e-16 + 0.1j,
        1e-20 + 0.1j,
        -1e-20 - 0.1j,
        1e-20 + 0j,
        -1e-20 + 0j,
        0.75 + 1e-20j,
        0.75 - 1e-20j,
        -0.75 + 1e-20j,
        -0.75 - 1e-20j,
        0.249999999 + 0.1j,
        0.25 + 0.1j,
        0.250000001 + 0.1j,
        -0.249999999 + 0.1j,
        -0.25 + 0.1j,
        -0.250000001 + 0.1j,
        0.5 + 1e-16 + 1e-20j,
        0.5 - 1e-16 - 1e-20j,
    ],
)
def test_r2_near_center_and_small_height_components(z):
    result = evaluate_generalized_dispersion(z, 2)
    Z, Zp = top_hat_reference(z)
    assert_components(result["Z"], Z, rtol=5e-12)
    assert_components(result["Zp"], Zp, rtol=5e-12)


@pytest.mark.parametrize("z", [1e-40 + 0.1j, -1e-40 + 0.1j, 1e-100 + 0.1j, -1e-100 - 0.1j])
def test_r2_tiny_center_derivative_component(z):
    result = evaluate_generalized_dispersion(z, 2)
    Z, Zp = top_hat_reference(z)
    assert_components(result["Z"], Z, rtol=5e-12)
    assert_components(result["Zp"], Zp, rtol=5e-12)


@pytest.mark.parametrize("shift", [0.0, 2.0])
@pytest.mark.parametrize("z", [1e8 + 1j, 1e8 - 1j, 1e8 + 0j])
def test_r1_explicit_hilbert_gaussian_cold_derivative(shift, z):
    expression = f"exp(-(v-{shift})**2)/sqrt(pi)"
    result = evaluate_generalized_hilbert(z, expression, integration_mesh=[-12, -4, 0, 2, 4, 12])
    assert_components(result["Zp"], gaussian_reference(z - shift), rtol=5e-12)


@pytest.mark.parametrize("shift", [0.0, 2.0])
@pytest.mark.parametrize("radius", [11.999999, 12.0, 12.000001])
@pytest.mark.parametrize("angle", [0.4, -0.4, np.pi / 2])
def test_r1_explicit_hilbert_derivative_transition_and_branches(shift, radius, angle):
    z = 1j * radius if angle == np.pi / 2 else radius * np.exp(1j * angle)
    expression = f"exp(-(v-{shift})**2)/sqrt(pi)"
    result = evaluate_generalized_hilbert(z, expression, integration_mesh=[-12, -4, 0, 2, 4, 12])
    expected = gaussian_reference(z - shift)
    # The generic quadrature path has roundoff-scale symmetry residues;
    # this transition gate bounds the full complex error, atol remainszero.
    # Original tiny nonzero cold components retain separate strict gates.
    np.testing.assert_allclose(result["Zp"], expected, rtol=5e-12, atol=0)

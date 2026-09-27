import numpy as np
import pytest
from scipy.special import iv

from scirel.kinetic.bessel_gamma import evaluate_bessel_gamma


def test_analytic_definition_and_neighbour_derivative():
    order = np.arange(-3, 4)
    argument = np.array([0.01, 0.1, 0.5, 1.0, 2.0, 4.0, 8.0])
    result = evaluate_bessel_gamma(order, argument)
    expected = np.exp(-argument) * iv(order, argument)
    expected_prime = np.exp(-argument) * (
        (iv(order - 1, argument) + iv(order + 1, argument)) / 2 - iv(order, argument)
    )
    np.testing.assert_allclose(result["Gamma_n"], expected, rtol=2e-14, atol=1e-15)
    np.testing.assert_allclose(result["Gamma_prime_n"], expected_prime, rtol=2e-14, atol=1e-15)


def test_origin_and_complex_broadcast_preserve_shape_and_inputs():
    origin = evaluate_bessel_gamma(np.arange(-2, 3), 0.0)
    np.testing.assert_array_equal(origin["Gamma_n"], [0, 0, 1, 0, 0])
    np.testing.assert_array_equal(origin["Gamma_prime_n"], [0, 0.5, -1, 0.5, 0])
    order = np.array([[-1], [0], [1]])
    argument = np.array([[0.5 + 0.25j, 2.0 - 0.5j]])
    original = argument.copy()
    result = evaluate_bessel_gamma(order, argument)
    assert result["Gamma_n"].shape == (3, 2)
    assert result["Gamma_prime_n"].shape == (3, 2)
    assert result["Gamma_n"].dtype == np.complex128
    np.testing.assert_array_equal(argument, original)
    assert np.all(np.isfinite(result["Gamma_n"]))


def test_large_positive_argument_remains_representable():
    result = evaluate_bessel_gamma(0, 100.0)
    assert result["Gamma_n"].shape == ()
    assert result["Gamma_n"] == pytest.approx(0.03994437929909668, rel=1e-13)
    assert np.isfinite(result["Gamma_prime_n"])


@pytest.mark.parametrize(
    "order,argument",
    [
        (True, 1.0), (1.5, 1.0), (np.nan, 1.0), ("1", 1.0),
        (2**53 + 1, 1.0),
        (1, True), (1, "1"), (1, np.nan), (1, np.inf),
        ([], []), ([0, 1], [1.0, 2.0, 3.0]), (0, -1000.0),
    ],
)
def test_invalid_or_unrepresentable_values_fail_closed(order, argument):
    with pytest.raises(ValueError):
        evaluate_bessel_gamma(order, argument)

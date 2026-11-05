"""Independent function identities and regressions for retained GPDF variants."""

import numpy as np
import pytest
from scipy.special import wofz
from scirel.kinetic.faddeeva_variants import (
    evaluate_faddeeva_gpdf,
    evaluate_faddeeva_dr,
    evaluate_maxwellian_fft,
    evaluate_maxwellian_jpole,
)


@pytest.mark.parametrize("func,order", [(evaluate_faddeeva_gpdf, 32), (evaluate_faddeeva_dr, 16)])
def test_defaults_and_independent_complex_error_function(func, order):
    z = np.array([[0, 0.1 + 0.2j, 2 + 1j], [-2 - 0.5j, 1 - 2j, 40j]])
    result = func(z)
    assert result["order"] == order
    np.testing.assert_allclose(
        result["w"],
        wofz(z),
        rtol=1e-6 if order == 16 else 5e-13,
        atol=3e-7 if order == 16 else 5e-13,
    )
    assert result["w"].shape == z.shape


def test_imaginary_axis_overflow_regression():
    # Historical exp(y*y)*erfc(y) gives inf*0 for y=40, though w(40i) is finite.
    with np.errstate(over="ignore", invalid="ignore"):
        from scipy.special import erfc

        assert np.isnan(np.exp(40.0**2) * erfc(40.0))
    np.testing.assert_allclose(evaluate_faddeeva_gpdf(40j)["w"], wofz(40j), rtol=2e-15)


@pytest.mark.parametrize("order", [16, 32, 64])
def test_fft_normalization_and_reflection(order):
    z = np.array([0.2 + 1j, 2 - 1j, 1 + 0j])
    w = evaluate_faddeeva_gpdf(z, order=order)["w"]
    np.testing.assert_allclose(
        evaluate_maxwellian_fft(z, order=order)["Z"], 1j * np.sqrt(np.pi) * w
    )
    np.testing.assert_allclose(
        w + evaluate_faddeeva_gpdf(-z, order=order)["w"],
        2 * np.exp(-z * z),
        atol=5e-7 if order == 16 else 2e-12,
    )


@pytest.mark.parametrize("order", [8, 12, 16, 24])
def test_jpole_all_matrix_entries_and_scalar_reference(order):
    z = np.array([[0.1 + 0.2j, 1 + 1j, 2 - 0.1j], [3 + 0.5j, -2 + 0.1j, 5 + 2j]])
    whole = evaluate_maxwellian_jpole(z, order=order)["Z"]
    assert whole.shape == z.shape
    assert np.all(whole != 0)
    for ix in np.ndindex(z.shape):
        np.testing.assert_allclose(whole[ix], evaluate_maxwellian_jpole(z[ix], order=order)["Z"])
    # Fixed rational truncation accuracy; this is not a uniformly accurate entire function.
    np.testing.assert_allclose(whole, 1j * np.sqrt(np.pi) * wofz(z), rtol=5e-5, atol=5e-6)


@pytest.mark.parametrize(
    "func", [evaluate_faddeeva_gpdf, evaluate_faddeeva_dr, evaluate_maxwellian_fft]
)
@pytest.mark.parametrize("order", [0, True, 1.5, -2])
def test_invalid_truncation(func, order):
    with pytest.raises(ValueError):
        func(1j, order=order)


def test_explicit_empty_and_overflow():
    assert evaluate_faddeeva_gpdf(1j, order=None)["order"] == 32
    assert evaluate_faddeeva_dr(1j, order=None)["order"] == 16
    with pytest.raises(ValueError):
        evaluate_maxwellian_fft(1j, order=None)
    with pytest.raises(FloatingPointError):
        evaluate_faddeeva_gpdf(-40j)
    with pytest.raises(ValueError):
        evaluate_maxwellian_jpole(1, order=10)


@pytest.mark.parametrize(
    "z", [1e200 + 0.1j, 1e200 - 0.1j, 1e308 + 1j, 1e308 - 1j, 1.79e308 + 1j, 1.79e308 - 1j]
)
def test_large_real_finite_response(z):
    # Gaussian exponential underflows; the algebraic response remains finite.
    expected = 1j / np.sqrt(np.pi) / z
    np.testing.assert_allclose(evaluate_faddeeva_gpdf(z)["w"], expected, rtol=3e-15, atol=0)
    np.testing.assert_allclose(
        evaluate_maxwellian_jpole(z, order=8)["Z"], -1 / z, rtol=5e-12, atol=0
    )

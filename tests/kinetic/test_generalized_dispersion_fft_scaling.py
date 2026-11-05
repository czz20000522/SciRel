"""GPDF-R3: final Z scaling must respect finite output contract."""

import warnings
import numpy as np
import pytest
from scipy.special import wofz
from scirel.kinetic.faddeeva_variants import evaluate_faddeeva_gpdf, evaluate_maxwellian_fft


def test_r3_finite_w_does_not_imply_finite_scaled_response():
    z = -26.625j
    assert np.isfinite(evaluate_faddeeva_gpdf(z)["w"])
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        with pytest.raises(FloatingPointError):
            evaluate_maxwellian_fft(z)


@pytest.mark.parametrize("y", [-26.61, -26.60, -26.0, 0.0, 26.625])
@pytest.mark.parametrize("order", [16, 32])
def test_r3_representable_scaling_neighbors_and_default(y, order):
    r = evaluate_maxwellian_fft(1j * y, order=order)
    expected = (1j * np.sqrt(np.pi)) * wofz(1j * y)
    np.testing.assert_allclose(r["Z"], expected, rtol=3e-14, atol=0)
    assert np.isfinite(r["Z"])


def test_r3_mixed_matrix_no_partial_nonfinite_response():
    with pytest.raises(FloatingPointError):
        evaluate_maxwellian_fft([[0.2 + 0.3j, 1j], [-26.625j, 40j]])


def test_r3_math_threshold_both_sides():
    # erfcx(-y)=2exp(y²)-erfcx(y); the correction is negligible at this bound.
    threshold = np.sqrt(np.log(np.finfo(float).max) - np.log(2 * np.sqrt(np.pi)))
    below = threshold - 1e-6
    above = threshold + 1e-6
    assert np.isfinite(evaluate_maxwellian_fft(-1j * below)["Z"])
    assert np.isfinite(evaluate_faddeeva_gpdf(-1j * above)["w"])
    with pytest.raises(FloatingPointError):
        evaluate_maxwellian_fft(-1j * above)

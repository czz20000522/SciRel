import numpy as np
import pytest
from scipy.special import wofz

from scirel.kinetic import evaluate_plasma_dispersion


def test_origin_has_the_analytic_plasma_dispersion_value():
    result = evaluate_plasma_dispersion(0j)
    assert result["w"].shape == ()
    assert result["w"] == 1.0
    assert result["Z"] == pytest.approx(1j * np.sqrt(np.pi))


def test_complex_grid_preserves_shape_and_inputs():
    z = np.array([[0.5 + 0.5j, 2.0 - 0.8j], [1.5j, -2.0j]])
    original = z.copy()
    result = evaluate_plasma_dispersion(z)
    assert set(result) == {"w", "Z"}
    assert result["w"].shape == z.shape
    assert result["Z"].dtype == np.complex128
    np.testing.assert_array_equal(z, original)
    np.testing.assert_allclose(result["w"], wofz(z), rtol=0, atol=0)
    np.testing.assert_allclose(result["Z"], 1j * np.sqrt(np.pi) * result["w"])


def test_lower_half_plane_uses_analytic_continuation():
    z = np.array([0.3 - 0.7j, -2.1 - 1.3j, 5.0 - 2.0j])
    result = evaluate_plasma_dispersion(z)["w"]
    mirrored = evaluate_plasma_dispersion(np.conj(z))["w"]
    np.testing.assert_allclose(
        result, 2 * np.exp(-(z**2)) - np.conj(mirrored), rtol=2e-14, atol=2e-14
    )


def test_large_positive_imaginary_argument_remains_representable():
    result = evaluate_plasma_dispersion(30j)
    assert np.isfinite(result["w"])
    assert result["w"].real == pytest.approx(wofz(30j).real)
    assert result["Z"].imag > 0


@pytest.mark.parametrize("bad", [[], True, [1.0, False], "1", [1 + np.nan * 1j], [np.inf], [-30j]])
def test_invalid_or_unrepresentable_values_fail_closed(bad):
    with pytest.raises(ValueError):
        evaluate_plasma_dispersion(bad)

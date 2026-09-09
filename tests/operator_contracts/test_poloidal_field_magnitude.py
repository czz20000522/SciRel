import numpy as np
import pytest

from scirel.field.poloidal_field_magnitude import compute_poloidal_field_magnitude, compute_poloidal_field_magnitude as scientific_operator


def test_returns_poloidal_magnitude_and_zero_floor():
    result = scientific_operator([[3.0, 0.0]], [[4.0, 0.0]])
    np.testing.assert_allclose(result["B"], [[5.0, 1.0e-30]])
    assert result["B0_default"] == 2.5


def test_rejects_shape_mismatch():
    with pytest.raises(ValueError, match="same-shape"):
        scientific_operator([[1.0]], [[1.0, 2.0]])


def test_admitted_large_finite_median_does_not_overflow():
    result = scientific_operator([[1e308, 1e308]], [[0.0, 0.0]])
    np.testing.assert_array_equal(result["B"], [[1e308, 1e308]])
    assert result["B0_default"] == 1e308


def test_admitted_large_two_component_magnitude():
    import math
    result = scientific_operator([[1e200]], [[1e200]])
    assert result["B"][0, 0] == pytest.approx(math.hypot(1e200, 1e200))


def test_admitted_unrepresentable_magnitude_is_rejected():
    with pytest.raises(ValueError):
        scientific_operator([[1.7e308]], [[1.7e308]])


def test_admitted_empty_grid_has_no_reference_field():
    with pytest.raises(ValueError):
        scientific_operator(np.empty((0, 2)), np.empty((0, 2)))


def test_reviewed_relation_example():
    import numpy as np
    from scirel.field.poloidal_field_magnitude import compute_poloidal_field_magnitude

    br = np.array([[3.0, 0.0]])
    bz = np.array([[4.0, 0.0]])
    result = compute_poloidal_field_magnitude(br, bz)
    np.testing.assert_allclose(result["B"], [[5.0, 1.0e-30]])
    assert result["B0_default"] == np.nanmedian(result["B"])
    swapped = compute_poloidal_field_magnitude(-bz, br)
    np.testing.assert_allclose(swapped["B"], result["B"])
    large = compute_poloidal_field_magnitude([[1.0e308]], [[1.0e308]])
    assert np.isfinite(large["B"]).all()
    np.testing.assert_allclose(large["B"], [[np.sqrt(2.0) * 1.0e308]])

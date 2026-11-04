"""Scientific and failure contracts for neutral boundary and source normalization."""

import numpy as np
import pytest

from scirel.kinetic.incoming_boundary_flux_normalization import (
    normalize_incoming_neutral_boundary,
)
from scirel.kinetic.spatial_source_shape_normalization import (
    normalize_spatial_source_shape,
)


def test_boundary_scales_positive_half_to_requested_magnitude():
    shape = np.array([[2.0, 1.0, 3.0], [4.0, 2.0, 1.0]])
    vx = np.array([-1.0, 0.5, 2.0])
    volume = np.array([[1.0, 2.0, 0.5], [1.0, 1.0, 2.0]])
    incoming, scale, initial = normalize_incoming_neutral_boundary(
        shape, vx, volume, 3.0, -30.0
    )
    expected_initial = 3.0 * (2.0 * 1.0 * 0.5 + 0.5 * 3.0 * 2.0 + 1.0 * 2.0 * 0.5 + 2.0 * 1.0 * 2.0)
    assert initial == expected_initial
    assert scale == 30.0 / expected_initial
    np.testing.assert_array_equal(incoming[:, 0], [0.0, 0.0])
    np.testing.assert_array_equal(incoming[:, 1:], shape[:, 1:] * scale)
    assert 3.0 * np.sum(volume[:, 1:] * incoming[:, 1:] * vx[None, 1:]) == pytest.approx(30.0)


def test_zero_target_flux_returns_zero_boundary_and_scale():
    incoming, scale, initial = normalize_incoming_neutral_boundary(
        np.ones((2, 2)), np.array([-1.0, 1.0]), np.ones((2, 2)), 2.0, 0.0
    )
    assert initial == 4.0
    assert scale == 0.0
    np.testing.assert_array_equal(incoming, np.zeros((2, 2)))


@pytest.mark.parametrize(
    "field,value",
    [
        ("boundary_shape", np.array([[1.0, np.nan]])),
        ("vx", np.array([np.nan, 1.0])),
        ("cylindrical_volume", np.array([[1.0, np.nan]])),
        ("cylindrical_volume", np.array([[-1.0, 2.0]])),
        ("thermal_speed_m_s", np.nan),
        ("target_flux_m2_s", np.inf),
    ],
)
def test_boundary_rejects_invalid_field_values(field, value):
    args = dict(
        boundary_shape=np.ones((1, 2)),
        vx=np.array([-1.0, 1.0]),
        cylindrical_volume=np.ones((1, 2)),
        thermal_speed_m_s=2.0,
        target_flux_m2_s=1.0,
    )
    args[field] = value
    with pytest.raises(ValueError):
        normalize_incoming_neutral_boundary(**args)


@pytest.mark.parametrize(
    "field,value",
    [
        ("boundary_shape", [[True, 1.0]]),
        ("vx", ["-1", "1"]),
        ("cylindrical_volume", np.array([[1.0, 1.0]], dtype=bool)),
        ("thermal_speed_m_s", True),
        ("target_flux_m2_s", "1.0"),
        ("target_flux_m2_s", 1.0 + 0j),
    ],
)
def test_boundary_rejects_nonreal_or_coerced_values(field, value):
    args = dict(
        boundary_shape=np.ones((1, 2)),
        vx=np.array([-1.0, 1.0]),
        cylindrical_volume=np.ones((1, 2)),
        thermal_speed_m_s=2.0,
        target_flux_m2_s=1.0,
    )
    args[field] = value
    with pytest.raises(ValueError):
        normalize_incoming_neutral_boundary(**args)


def test_boundary_rejects_nonfinite_derived_flux():
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(ValueError, match="finite"):
            normalize_incoming_neutral_boundary(
                np.ones((1, 2)), [-1.0, 1.0], np.full((1, 2), 1e308), 1e308, 1.0
            )


def test_boundary_rejects_nonfinite_derived_scale():
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        with pytest.raises(ValueError, match="finite"):
            normalize_incoming_neutral_boundary(
                np.ones((1, 2)), [-1.0, 1.0], np.full((1, 2), 1e-308), 1.0, 1e308
            )


def test_boundary_rejects_zero_scale_from_nonzero_target():
    with pytest.raises(ValueError, match="scale"):
        normalize_incoming_neutral_boundary(
            np.ones((1, 2)), [-1.0, 1.0], np.full((1, 2), 1e300), 1.0, 1e-300
        )


def test_boundary_rejects_nonfinite_scaled_distribution():
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(ValueError, match="boundary must be finite"):
            normalize_incoming_neutral_boundary(
                np.full((1, 2), 1e308), [-1.0, 1.0], np.full((1, 2), 1e-300), 1.0, 1e308
            )


def test_source_shape_uses_trapezoidal_spatial_measure():
    source = np.array([1.0, 3.0, 2.0])
    x_m = np.array([0.0, 1.0, 3.0])
    result = normalize_spatial_source_shape(source, x_m)
    assert result["integral_source"] == 7.0
    np.testing.assert_array_equal(result["shape_m_inv"], source / 7.0)
    assert np.trapezoid(result["shape_m_inv"], x_m) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "source,x_m",
    [
        ([0.0, 0.0], [0.0, 1.0]),
        ([1.0, 1.0], [1.0, 0.0]),
        ([1.0], [0.0]),
        ([np.nan, 1.0], [0.0, 1.0]),
        ([1.0, -1.0], [0.0, 1.0]),
    ],
)
def test_source_shape_rejects_invalid_profiles(source, x_m):
    with pytest.raises(ValueError):
        normalize_spatial_source_shape(source, x_m)


@pytest.mark.parametrize(
    "source,x_m",
    [
        ([True, 1.0], [0.0, 1.0]),
        (["1", "2"], [0.0, 1.0]),
        ([1.0, 2.0], np.array([0.0, 1.0], dtype=bool)),
        ([1.0 + 0j, 2.0], [0.0, 1.0]),
    ],
)
def test_source_shape_rejects_nonreal_or_coerced_profiles(source, x_m):
    with pytest.raises(ValueError):
        normalize_spatial_source_shape(source, x_m)

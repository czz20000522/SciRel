"""Direct contract tests for ``scirel.kinetic.compute_thermal_speed_m_s`` and
``scirel.kinetic.reduce_generation_density``.

The saved KN1DPy packages (anchors ``KN1DPy/kinetic_h2.py:1360-1371`` for the
thermal-speed scale and ``KN1DPy/kinetic_h.py:1410-1424`` /
``kinetic_h2.py:1548-1573`` for the density reduction, as recorded by the
saved bundle's provenance) are reproduced bit for bit; no repair is claimed.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from scirel.kinetic import compute_thermal_speed_m_s, reduce_generation_density


def test_thermal_speed_matches_independent_frozen_constant_relation():
    result = compute_thermal_speed_m_s(1.0, 2.0)["thermal_speed_m_s"]
    expected = math.sqrt(2.0 * 1.602177e-19 / (2.0 * 1.6726231e-27))
    assert result == expected


def test_thermal_speed_decreases_with_mass_and_grows_with_temperature():
    assert compute_thermal_speed_m_s(2.0, 1.0)["thermal_speed_m_s"] > compute_thermal_speed_m_s(2.0, 2.0)["thermal_speed_m_s"]
    assert compute_thermal_speed_m_s(4.0, 1.0)["thermal_speed_m_s"] == 2.0 * compute_thermal_speed_m_s(1.0, 1.0)["thermal_speed_m_s"]


@pytest.mark.parametrize("temperature,mass", [(0.0, 1.0), (1.0, 0.0), (-1.0, 1.0), (float("nan"), 1.0), (1.0, float("inf"))])
def test_thermal_speed_invalid_inputs_fail_closed(temperature, mass):
    with pytest.raises(ValueError):
        compute_thermal_speed_m_s(temperature, mass)


def test_density_reduction_2d_weight_sums_over_both_velocity_axes():
    rng = np.random.default_rng(11)
    f = rng.random((4, 3, 5))
    w = rng.random((4, 3))
    dx = rng.random(3) + 0.1
    result = reduce_generation_density(f, w, dx)
    # the saved path multiplies all three fields per (vr,vx) cell and sums
    # over both axes in one reduction; replicate that exact operation order
    expected = np.sum(f * w[:, :, None] * dx[None, :, None], axis=(0, 1))
    np.testing.assert_array_equal(result, expected)
    assert result.shape == (5,)


def test_density_reduction_1d_radial_weight_uses_the_saved_projection_path():
    rng = np.random.default_rng(12)
    f = rng.random((4, 3, 5))
    w = rng.random(4)
    dx = rng.random(3) + 0.1
    result = reduce_generation_density(f, w, dx)
    expected = np.sum(w[:, None] * (np.moveaxis(f, 2, 1) @ dx), axis=0)
    np.testing.assert_array_equal(result, expected)


def test_density_reduction_uniform_radial_columns_match_the_full_weight_path():
    """The saved implementation routes a cylindrical weight whose columns are
    all equal onto the radial-projection path; both paths must agree there."""
    rng = np.random.default_rng(13)
    f = rng.random((4, 3, 5))
    w = rng.random(4)
    dx = rng.random(3) + 0.1
    uniform = np.repeat(w[:, None], 3, axis=1)
    np.testing.assert_array_equal(
        reduce_generation_density(f, uniform, dx),
        reduce_generation_density(f, w, dx),
    )


def test_density_reduction_rejects_misaligned_or_negative_quadrature():
    f = np.ones((2, 2, 2))
    with pytest.raises(ValueError, match="finite and aligned"):
        reduce_generation_density(f, np.ones((2, 2)), np.array([0.5, -1.0]))
    with pytest.raises(ValueError, match="radial quadrature must align"):
        reduce_generation_density(f, np.ones(3), np.array([0.5, 0.5]))
    with pytest.raises(ValueError, match="cylindrical weight must align"):
        reduce_generation_density(f, np.ones((3, 2)), np.array([0.5, 0.5]))

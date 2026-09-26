"""Direct contract tests for the small neutral-transport reduction assets:
``sum_elastic_frequency_channels``, ``normalize_incoming_neutral_boundary``,
``normalize_spatial_source_shape``, ``assemble_neutral_total_collision_frequency``.

The saved KN1DPy packages (anchors as recorded by the saved bundle's
provenance: kinetic_h.py:1297-1317 / kinetic_h2.py:1258-1297, kinetic_h.py:600-616
/ kinetic_h2.py:715-731, kn1d.py:520-577, kinetic_h.py:1089-1095 /
kinetic_h2.py:1151-1157) are reproduced bit for bit; no repair is claimed.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import (
    assemble_neutral_total_collision_frequency,
    normalize_incoming_neutral_boundary,
    normalize_spatial_source_shape,
    sum_elastic_frequency_channels,
)


def test_channel_sum_sums_each_channel_at_each_grid_point():
    result = sum_elastic_frequency_channels(
        [np.array([1.0, 2.0]), np.array([0.5, 1.0]), np.array([0.25, 0.5])]
    )
    np.testing.assert_array_equal(result["elastic_frequency_s_inv"], [1.75, 3.5])


def test_channel_sum_preserves_zero_channel_and_rejects_shape_violations():
    result = sum_elastic_frequency_channels([np.zeros(3), np.ones(3), np.full(3, 2.0)])
    np.testing.assert_array_equal(result["elastic_frequency_s_inv"], np.full(3, 3.0))
    with pytest.raises(ValueError, match="exactly three"):
        sum_elastic_frequency_channels([np.ones(3), np.ones(3)])
    with pytest.raises(ValueError, match="identical shapes"):
        sum_elastic_frequency_channels([np.ones(3), np.ones(4), np.ones(3)])
    with pytest.raises(ValueError, match="finite"):
        sum_elastic_frequency_channels([np.ones(3), np.full(3, np.nan), np.ones(3)])


def test_channel_sum_overflow_fails_closed():
    """Pre-review regression: the saved arm returns the overflow value inf for
    three near-maximum finite channels; this asset fail-closes instead, per
    the exact document's finite-output contract."""
    with pytest.raises(ValueError, match="not finite"):
        sum_elastic_frequency_channels(
            [np.array([1.0e308]), np.array([1.0e308]), np.array([1.0e308])]
        )


def test_boundary_normalization_scales_only_the_positive_vx_half():
    shape = np.ones((2, 3))
    volume = np.ones((2, 3))
    vx = np.array([-1.0, 0.5, 1.0])
    result, scale, initial = normalize_incoming_neutral_boundary(shape, vx, volume, 2.0, -12.0)
    assert initial == 6.0 and scale == 2.0
    assert np.all(result[:, 0] == 0.0)
    positive = vx > 0.0
    assert np.isclose(2.0 * np.sum(volume[:, positive] * result[:, positive] * vx[None, positive]), 12.0)


def test_boundary_normalization_fail_closed_contracts():
    volume = np.ones((2, 3))
    with pytest.raises(ValueError, match="positive incoming half"):
        normalize_incoming_neutral_boundary(
            np.ones((2, 3)), np.array([-1.0, -0.5, 0.0]), volume, 2.0, 12.0
        )
    with pytest.raises(ValueError, match="positive flux"):
        normalize_incoming_neutral_boundary(
            np.zeros((2, 3)), np.array([-1.0, 0.5, 1.0]), volume, 2.0, 12.0
        )
    with pytest.raises(ValueError, match="invalid"):
        normalize_incoming_neutral_boundary(
            np.ones((2, 3)), np.array([-1.0, 0.5, 1.0]), volume, 0.0, 12.0
        )
    with pytest.raises(ValueError, match="invalid"):
        normalize_incoming_neutral_boundary(
            -np.ones((2, 3)), np.array([-1.0, 0.5, 1.0]), volume, 2.0, 12.0
        )


def test_spatial_source_normalizes_with_independent_trapezoidal_measure():
    source = np.array([1.0, 2.0, 1.0])
    x_m = np.array([0.0, 1.0, 2.0])
    result = normalize_spatial_source_shape(source, x_m)
    assert result["integral_source"] == 3.0
    np.testing.assert_array_equal(result["shape_m_inv"], source / 3.0)
    assert np.trapezoid(result["shape_m_inv"], x_m) == 1.0


@pytest.mark.parametrize(
    "source,x_m",
    [
        ([0.0, 0.0], [0.0, 1.0]),
        ([1.0, 1.0], [1.0, 0.0]),
        ([1.0], [0.0]),
        ([float("nan"), 1.0], [0.0, 1.0]),
        ([1.0, -1.0], [0.0, 1.0]),
    ],
)
def test_spatial_source_fail_closed_contracts(source, x_m):
    with pytest.raises(ValueError):
        normalize_spatial_source_shape(source, x_m)


def test_total_frequency_assembles_saved_loss_terms_with_optional_wall_and_cx():
    result = assemble_neutral_total_collision_frequency(
        [1.0, 2.0], [-1.0, 1.0], [3.0, 4.0], [5.0, 6.0], [2.0, 0.0], np.ones((2, 2, 2))
    )
    # cell (vr=1, vx=*, x=0): base 3 + elastic 5 + wall 2*1/2 = 9; with CX 1 -> 10
    np.testing.assert_allclose(result[:, :, 0], [[10.0, 10.0], [11.0, 11.0]])
    # x=1 has zero pipe diameter: no wall loss; total = base + elastic + CX
    np.testing.assert_allclose(result[:, :, 1], [[11.0, 11.0], [11.0, 11.0]])
    # disabled CX skips the field: totals drop by 1
    disabled = assemble_neutral_total_collision_frequency(
        [1.0, 2.0], [-1.0, 1.0], [3.0, 4.0], [5.0, 6.0], [2.0, 0.0],
        charge_exchange_enabled=False,
    )
    np.testing.assert_allclose(disabled[:, :, 0], [[9.0, 9.0], [10.0, 10.0]])


def test_total_frequency_enabled_cx_requires_explicit_field():
    with pytest.raises(ValueError, match="charge exchange"):
        assemble_neutral_total_collision_frequency(
            [1.0], [1.0], [1.0], [1.0], [0.0]
        )


def test_total_frequency_profile_contracts_fail_closed():
    with pytest.raises(ValueError, match="invalid"):
        assemble_neutral_total_collision_frequency(
            [0.0, 2.0], [-1.0, 1.0], [3.0, 4.0], [5.0, 6.0], [2.0, 0.0]  # nonpositive vr
        )
    with pytest.raises(ValueError, match="invalid"):
        assemble_neutral_total_collision_frequency(
            [1.0, 2.0], [-1.0, 1.0], [3.0, -4.0], [5.0, 6.0], [2.0, 0.0]  # negative base
        )

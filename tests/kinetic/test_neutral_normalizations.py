"""Scientific and failure contracts for neutral boundary and source normalization."""

import math
from fractions import Fraction

import numpy as np
import pytest

from scirel.neutrals.incoming_boundary_flux_normalization import (
    normalize_incoming_neutral_boundary,
)
from scirel.neutrals.spatial_source_shape_normalization import (
    normalize_spatial_source_shape,
)


def test_boundary_scales_positive_half_to_requested_magnitude():
    shape = np.array([[2.0, 1.0, 3.0], [4.0, 2.0, 1.0]])
    vx = np.array([-1.0, 0.5, 2.0])
    volume = np.array([[1.0, 2.0, 0.5], [1.0, 1.0, 2.0]])
    incoming, scale, initial = normalize_incoming_neutral_boundary(shape, vx, volume, 3.0, -30.0)
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


@pytest.mark.parametrize("target_sign", [-1.0, 1.0])
@pytest.mark.parametrize("zero_volume_cell", [False, True])
def test_boundary_rejects_underflowed_flux_carrying_distribution(target_sign, zero_volume_cell):
    # Initial flux=2^-54 and scale=2^-1016 are representable. The only
    # flux-carrying returned cell would be 2^-1080, so it disappears.
    shape = [[float.fromhex("0x1p-64"), 1.0]] if zero_volume_cell else [[float.fromhex("0x1p-64")]]
    volume = [[1.0, 0.0]] if zero_volume_cell else [[1.0]]
    vx = [1.0, 1.0] if zero_volume_cell else [1.0]
    with pytest.raises(ValueError, match="underflow"):
        normalize_incoming_neutral_boundary(
            shape, vx, volume, 1024.0, target_sign * float.fromhex("0x1p-1070")
        )


def test_boundary_keeps_a_representable_subnormal_distribution():
    target = float.fromhex("0x1p-1060")
    incoming, _, _ = normalize_incoming_neutral_boundary(
        [[float.fromhex("0x1p-64")]], [1.0], [[1.0]], 1024.0, target
    )
    assert incoming[0, 0] == float.fromhex("0x1p-1070")
    assert Fraction.from_float(float(incoming[0, 0])) * 1024 == Fraction.from_float(target)


def test_boundary_allows_an_unrelated_small_cell_to_round_to_zero():
    target = float.fromhex("0x1p-1060")
    incoming, _, _ = normalize_incoming_neutral_boundary(
        [[float.fromhex("0x1p-64"), 1.0]], [1.0, 1.0], [[1.0, 1.0]], 1024.0, target
    )
    assert incoming[0, 0] == 0.0
    assert incoming[0, 1] == float.fromhex("0x1p-1070")
    assert Fraction.from_float(float(incoming[0, 1])) * 1024 == Fraction.from_float(target)


def test_boundary_does_not_reject_a_representable_result_for_a_reintegration_underflow():
    # Multiplying volume by the returned density first would underflow,
    # despite both the density and the exact flux being representable.
    volume, speed, target = (float.fromhex(value) for value in ("0x1p-400", "0x1p800", "0x1p-400"))
    incoming, _, _ = normalize_incoming_neutral_boundary([[1.0]], [1.0], [[volume]], speed, target)
    assert incoming[0, 0] == float.fromhex("0x1p-800")
    assert Fraction.from_float(float(incoming[0, 0])) * Fraction.from_float(
        volume
    ) * Fraction.from_float(speed) == Fraction.from_float(target)


def _exact_boundary_flux(distribution, vx, volume, speed):
    return Fraction.from_float(float(speed)) * sum(
        (
            Fraction.from_float(float(distribution[i, j]))
            * Fraction.from_float(float(volume[i][j]))
            * Fraction.from_float(float(vx[j]))
            for i in range(len(volume))
            for j in range(len(vx))
            if vx[j] > 0.0
        ),
        Fraction(0),
    )


@pytest.mark.parametrize("target_sign", [-1.0, 1.0])
@pytest.mark.parametrize("row", [[1.0, 2.0], [2.0, 1.0]])
@pytest.mark.parametrize("policy", ["raise", "warn", "ignore"])
def test_boundary_rejects_a_subnormal_scale_with_a_fifty_percent_relative_error(
    target_sign, row, policy
):
    target = target_sign * float.fromhex("0x1p-1063")
    exact_scale = abs(Fraction(target)) / 3072
    nearest_scale = float(exact_scale)
    assert abs(Fraction(nearest_scale) / exact_scale - 1) == Fraction(1, 2)
    with np.errstate(all=policy), pytest.raises(ValueError, match="scale.*represent"):
        normalize_incoming_neutral_boundary([row], [1.0, 1.0], [[1.0, 1.0]], 1024.0, target)


@pytest.mark.parametrize("target_sign", [-1.0, 1.0])
@pytest.mark.parametrize("row", [[1.0, 2.0], [2.0, 1.0]])
@pytest.mark.parametrize("policy", ["raise", "warn", "ignore"])
def test_boundary_keeps_an_exactly_representable_subnormal_scale(target_sign, row, policy):
    target = target_sign * 3 * float.fromhex("0x1p-1064")
    exact_scale = abs(Fraction(target)) / 3072
    assert exact_scale == Fraction(float.fromhex("0x1p-1074"))
    with np.errstate(all=policy):
        incoming, scale, initial = normalize_incoming_neutral_boundary(
            [row], [1.0, 1.0], [[1.0, 1.0]], 1024.0, target
        )
    assert Fraction(scale) == exact_scale
    assert Fraction(initial) == 3072
    actual = _exact_boundary_flux(incoming, [1.0, 1.0], [[1.0, 1.0]], 1024.0)
    assert actual == abs(Fraction(target))
    np.testing.assert_array_equal(incoming, np.asarray([row]) * scale)


@pytest.mark.parametrize("target", [0.0, 3 * float.fromhex("0x1p-1074")])
@pytest.mark.parametrize("policy", ["raise", "warn", "ignore"])
def test_boundary_rejects_a_pre_scale_flux_with_large_representation_error(target, policy):
    # Initial flux=1.5*MIN, so its nearest public float is 2*MIN (+1/3).
    exact_initial = Fraction(3, 2) * Fraction(float.fromhex("0x1p-1074"))
    assert abs(Fraction(float(exact_initial)) / exact_initial - 1) == Fraction(1, 3)
    with np.errstate(all=policy), pytest.raises(ValueError, match="flux.*represent"):
        normalize_incoming_neutral_boundary(
            [[1.0]], [1.0], [[float.fromhex("0x1p-1074")]], 1.5, target
        )


@pytest.mark.parametrize("target_sign", [-1.0, 1.0])
@pytest.mark.parametrize("policy", ["raise", "warn", "ignore"])
def test_boundary_rejects_a_nonzero_quantized_flux_that_cannot_meet_the_target(target_sign, policy):
    # The only active density would be 1.5*MIN. No single binary64 cell
    # carries this target: MIN gives -1/3 and 2*MIN gives +1/3 relative error.
    target = target_sign * 3.0 * float.fromhex("0x1p-1065")
    with np.errstate(all=policy), pytest.raises(ValueError, match="(scale|flux).*represent"):
        normalize_incoming_neutral_boundary([[1.0]], [1.0], [[1.0]], 1024.0, target)


@pytest.mark.parametrize("exponent", [-800, 800])
def test_boundary_preserves_a_compensated_initial_integral(exponent):
    value, speed = float.fromhex(f"0x1p{exponent}"), float.fromhex(f"0x1p{-exponent}")
    target = value if exponent < 0 else 1.0
    with np.errstate(all="raise"):
        incoming, scale, initial = normalize_incoming_neutral_boundary(
            [[value]], [1.0], [[value]], speed, target
        )
    assert initial == value
    assert scale == (1.0 if exponent < 0 else speed)
    assert incoming[0, 0] == (value if exponent < 0 else 1.0)
    assert _exact_boundary_flux(incoming, [1.0], [[value]], speed) == Fraction.from_float(target)


@pytest.mark.parametrize("nvr,nvx", [(3, 5), (17, 31)])
def test_boundary_normalization_budget_on_nonuniform_multicell_inputs(nvr, nvx):
    index = np.arange(nvr * nvx).reshape(nvr, nvx)
    shape = (index + 1.0) / 16.0
    volume = 1.0 + (index % 7) / 8.0
    vx = np.arange(nvx, dtype=float) - nvx // 2
    saved = [a.copy() for a in (shape, volume, vx)]
    target = -2.75
    incoming, scale, initial = normalize_incoming_neutral_boundary(shape, vx, volume, 2.0, target)
    exact_initial = _exact_boundary_flux(shape, vx, volume, 2.0)
    exact_returned = _exact_boundary_flux(incoming, vx, volume, 2.0)
    assert abs(Fraction(initial) / exact_initial - 1) <= Fraction.from_float(1e-13)
    assert abs(exact_returned / Fraction(abs(target)) - 1) <= Fraction.from_float(1e-13)
    assert scale == abs(target) / initial
    np.testing.assert_array_equal(incoming[:, vx > 0], shape[:, vx > 0] * scale)
    np.testing.assert_array_equal(incoming[:, vx <= 0], 0.0)
    for original, before in zip((shape, volume, vx), saved, strict=True):
        np.testing.assert_array_equal(original, before)


@pytest.mark.parametrize("bits,accepted", [(40, False), (48, True)])
def test_boundary_relative_budget_distinguishes_subnormal_quantization(bits, accepted):
    # Exact density=(2**bits+1/3)*MIN. The rounding error is harmless for
    # bits=48 but exceeds the frozen 1e-13 target budget for bits=40.
    target = (3 * 2**bits + 1) * float.fromhex("0x1p-1074")
    if not accepted:
        with pytest.raises(ValueError, match="(scale|flux).*represent"):
            normalize_incoming_neutral_boundary([[1.0]], [1.0], [[1.0]], 3.0, target)
    else:
        incoming, _, _ = normalize_incoming_neutral_boundary([[1.0]], [1.0], [[1.0]], 3.0, target)
        actual = _exact_boundary_flux(incoming, [1.0], [[1.0]], 3.0)
        assert abs(actual / Fraction(target) - 1) <= Fraction.from_float(1e-13)


def test_source_shape_uses_trapezoidal_spatial_measure():
    source = np.array([1.0, 3.0, 2.0])
    x_m = np.array([0.0, 1.0, 3.0])
    result = normalize_spatial_source_shape(source, x_m)
    assert result["integral_source"] == 7.0
    np.testing.assert_array_equal(result["shape_m_inv"], source / 7.0)
    shape = result["shape_m_inv"]
    independent_integral = math.fsum(
        float((shape[i] + shape[i + 1]) * (x_m[i + 1] - x_m[i]) / 2) for i in range(len(x_m) - 1)
    )
    assert independent_integral == pytest.approx(1.0)


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

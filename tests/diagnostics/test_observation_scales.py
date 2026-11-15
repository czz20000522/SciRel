"""Raw-input algebraic references for bounded observation scale arithmetic.

Fraction consumes original binary64 inputs, never SciRel intermediate values.
The nonzero relative budget is fixed at 1e-13 with no absolute allowance.
These checks concern the declared diagonal algebra, not fit significance.
"""

from copy import deepcopy
from fractions import Fraction

import numpy as np
import pytest

from scirel._result import Result
from scirel.diagnostics import reduce_observation_residuals

RTOL = Fraction.from_float(1e-13)
CHANNELS = ("density", "electron_temperature", "p_parallel", "p_perp")


def _fraction(value):
    return Fraction.from_float(float(value))


def _reference(prediction, observation, sigma):
    p, o, s = np.broadcast_arrays(prediction, observation, sigma)
    residuals = [
        (_fraction(pv) - _fraction(ov)) / _fraction(sv)
        for pv, ov, sv in zip(p.flat, o.flat, s.flat)
    ]
    return [float(value) for value in residuals], float(
        sum((value * value for value in residuals), Fraction())
    )


def _close(actual, expected):
    assert np.isfinite(actual)
    if expected == 0.0:
        assert actual == 0.0
    else:
        assert abs(_fraction(actual) - _fraction(expected)) <= RTOL * abs(_fraction(expected)), (
            actual,
            expected,
        )


def _call(prediction, observation, sigma=1.0):
    return reduce_observation_residuals(
        predicted={"flux_loops": prediction},
        observations={"flux_loops": {"values": observation, "sigma": sigma}},
    )


@pytest.mark.parametrize("power", [0, 1023])
@pytest.mark.parametrize("sign", [-1.0, 1.0])
def test_normalize_complete_difference_before_rejecting_intermediate_overflow(power, sign):
    value = sign * 2.0**power
    expected, chi2 = _reference([value], [-value], [abs(value)])
    assert expected == [sign * 2.0] and chi2 == 4.0
    result = _call([value], [-value], [abs(value)])
    np.testing.assert_array_equal(result.residual_vector, expected)
    assert result.chi2 == chi2


@pytest.mark.parametrize("power", [-538, -537])
@pytest.mark.parametrize("count", [4, 7, 16])
def test_complete_squared_sum_retains_compensating_subnormal_total(power, count):
    value = 2.0**power
    prediction = [value] * count
    expected, chi2 = _reference(prediction, [0.0] * count, 1.0)
    assert chi2 > 0.0
    result = _call(prediction, [0.0] * count)
    np.testing.assert_array_equal(result.residual_vector, expected)
    _close(result.chi2, chi2)
    if power == -538 and count == 4:
        assert chi2 == float.fromhex("0x0.0000000000001p-1022")


@pytest.mark.parametrize("count", [1, 7, 8, 9, 16])
def test_final_subnormal_rounding_is_distinct_from_premature_squared_zero(count):
    # Each square is 2^-1078. Eight terms are exactly half a minimum
    # subnormal (round-to-even zero); nine round to the minimum subnormal.
    value = 2.0**-539
    prediction = [value] * count
    expected, chi2 = _reference(prediction, [0.0] * count, 1.0)
    result = _call(prediction, [0.0] * count)
    np.testing.assert_array_equal(result.residual_vector, expected)
    _close(result.chi2, chi2)


@pytest.mark.parametrize("power", [-530, -512, -200, 0, 200, 500])
def test_signed_ordinary_and_extreme_vectors_keep_the_same_diagonal_relation(power):
    scale = 2.0**power
    prediction = scale * np.array([1.0, -2.0, 3.0, -4.0])
    observation = scale * np.array([0.5, -1.0, 2.0, -2.0])
    sigma = np.array([1.0, 2.0, 0.5, 4.0])
    expected, chi2 = _reference(prediction, observation, sigma)
    result = _call(prediction, observation, sigma)
    for actual, reference in zip(result.residual_vector, expected):
        _close(actual, reference)
    _close(result.chi2, chi2)


@pytest.mark.parametrize("power", [-1022, -900, 0, 900, 1023])
def test_near_cancellation_keeps_the_raw_difference_before_normalization(power):
    prediction = 2.0**power
    observation = np.nextafter(prediction, 0.0)
    sigma = 2.0 ** (power - 52)
    expected, chi2 = _reference(prediction, observation, sigma)
    result = _call(prediction, observation, sigma)
    assert result.residual_vector.shape == (1,)
    _close(result.residual_vector[0], expected[0])
    _close(result.chi2, chi2)


def test_equal_huge_inputs_have_exact_zero_even_with_tiny_sigma():
    value = 2.0**1023
    tiny = float.fromhex("0x0.0000000000001p-1022")
    result = _call([value, -value], [value, -value], tiny)
    np.testing.assert_array_equal(result.residual_vector, [0.0, 0.0])
    assert result.chi2 == 0.0


def test_scalar_overflowing_difference_keeps_one_residual_entry():
    value = 2.0**1023
    result = _call(value, -value, value)
    np.testing.assert_array_equal(result.residual_vector, [2.0])
    assert result.chi2 == 4.0


@pytest.mark.parametrize(
    "prediction",
    [
        [2.0**511] * 3,
        [np.nextafter(2.0**512, 0.0)],
        [2.0**511] * 3 + [2.0**-538],
    ],
)
def test_large_finite_squared_sum_is_not_rejected_as_final_overflow(prediction):
    expected, chi2 = _reference(prediction, [0.0] * len(prediction), 1.0)
    assert np.isfinite(chi2) and chi2 > np.finfo(float).max / 2.0
    result = _call(prediction, [0.0] * len(prediction))
    np.testing.assert_array_equal(result.residual_vector, expected)
    _close(result.chi2, chi2)


def test_large_scales_preserve_every_channel_c_order_shape_units_and_inputs():
    value = 2.0**1023
    pattern = value * np.array([[1.0, -1.0], [-1.0, 1.0]])
    predicted = {
        "thomson": {name: pattern.copy() for name in reversed(CHANNELS)},
        "flux_loops": pattern.copy(),
        "units": {
            "flux_loops": "Wb",
            "thomson": {name: "declared-profile-unit" for name in CHANNELS},
        },
    }
    observations = {
        "thomson": {
            name: {
                "values": -pattern.copy(),
                "sigma": [[value / 2 ** (CHANNELS.index(name) + 1)]] * 2,
                "unit": "declared-profile-unit",
            }
            for name in reversed(CHANNELS)
        },
        "flux_loops": {"values": -pattern.copy(), "sigma": value, "unit": "Wb"},
    }
    before = deepcopy((predicted, observations))
    result = reduce_observation_residuals(predicted=predicted, observations=observations)
    assert isinstance(result, Result)
    assert list(result) == ["residual_vector", "chi2"]
    assert result.residual_vector is result["residual_vector"]
    assert result.residual_vector.dtype == np.dtype("float64")
    expected = [
        entry
        for amplitude in [2.0, 4.0, 8.0, 16.0, 32.0]
        for entry in [amplitude, -amplitude, -amplitude, amplitude]
    ]
    np.testing.assert_array_equal(result.residual_vector, expected)
    assert result.chi2 == result["chi2"] == 5456.0
    for name in CHANNELS:
        np.testing.assert_array_equal(predicted["thomson"][name], before[0]["thomson"][name])
        np.testing.assert_array_equal(
            observations["thomson"][name]["values"], before[1]["thomson"][name]["values"]
        )
        assert observations["thomson"][name]["sigma"] == before[1]["thomson"][name]["sigma"]
    np.testing.assert_array_equal(predicted["flux_loops"], before[0]["flux_loops"])
    np.testing.assert_array_equal(
        observations["flux_loops"]["values"], before[1]["flux_loops"]["values"]
    )
    assert predicted["units"] == before[0]["units"]


def test_squared_sum_combines_requested_channels_before_final_rounding():
    value = 2.0**-538
    result = reduce_observation_residuals(
        predicted={"flux_loops": [0.0], "thomson": {name: value for name in CHANNELS}},
        observations={
            "thomson": {name: {"values": 0.0} for name in reversed(CHANNELS)},
            "flux_loops": {"values": [0.0]},
        },
    )
    np.testing.assert_array_equal(result.residual_vector, [0.0, value, value, value, value])
    assert result.chi2 == float.fromhex("0x0.0000000000001p-1022")


@pytest.mark.parametrize(
    ("prediction", "observation", "sigma", "message"),
    [
        ([2.0**1023], [-(2.0**1023)], 1.0, "normalized residual"),
        ([2.0**1023], [0.0], 2.0**-1000, "normalized residual"),
        ([2.0**600], [0.0], 1.0, "chi2"),
        ([2.0**511] * 4, [0.0] * 4, 1.0, "chi2"),
    ],
)
def test_genuine_final_overflow_still_rejects_without_partial_result(
    prediction, observation, sigma, message
):
    with pytest.raises(ValueError, match=message):
        _call(prediction, observation, sigma)


def test_large_scale_does_not_relax_unit_or_exact_shape_matching():
    value = 2.0**1023
    with pytest.raises(ValueError, match="unit must match"):
        reduce_observation_residuals(
            predicted={"flux_loops": [value], "units": {"flux_loops": "Wb/rad"}},
            observations={"flux_loops": {"values": [-value], "sigma": value, "unit": "Wb"}},
        )
    with pytest.raises(ValueError, match="exact same shape"):
        _call([value] * 4, [[-value] * 2] * 2, value)
    with pytest.raises(ValueError, match="every requested usable signal"):
        reduce_observation_residuals(
            predicted={"flux_loops": [0.0]},
            observations={
                "flux_loops": {"values": [0.0]},
                "thomson": {"density": {"values": [0.0]}},
            },
        )


@pytest.mark.parametrize("head_factor", [1.0, 2.0, 1.0 + 2.0**-10])
@pytest.mark.parametrize("count", [1024, 4096, 8192])
def test_complete_normal_squared_sum_retains_individually_unrepresentable_tail(head_factor, count):
    prediction = [head_factor * 2.0**-511] + [2.0**-538] * count
    exact = _fraction(prediction[0]) ** 2 + count * Fraction(1, 2**1076)
    expected_chi2 = float(exact)
    assert expected_chi2 >= np.finfo(float).tiny
    result = _call(prediction, [0.0] * len(prediction))
    np.testing.assert_array_equal(result.residual_vector, prediction)
    _close(result.chi2, expected_chi2)


@pytest.mark.parametrize("sign", [-1.0, 1.0])
@pytest.mark.parametrize("observation_step", [-1, 0, 1])
def test_finite_normalized_difference_is_rounded_only_after_complete_division(
    sign, observation_step
):
    predecessor = np.nextafter(2.0**-52, 0.0)
    if observation_step == -1:
        magnitude = np.nextafter(predecessor, 0.0)
    elif observation_step == 1:
        magnitude = 2.0**-52
    else:
        magnitude = predecessor
    prediction, observation, sigma = sign * 2.0**-51, -sign * magnitude, 2.0**1023
    exact = (_fraction(prediction) - _fraction(observation)) / _fraction(sigma)
    expected = float(exact)
    if observation_step == 0:
        assert abs(expected) == float.fromhex("0x0.0000000000001p-1022")
    result = _call(prediction, observation, sigma)
    np.testing.assert_array_equal(result.residual_vector, [expected])
    # The public vector and its squared sum are separate obligations: chi2
    # legitimately rounds to zero here, even when the vector was wrong.
    assert result.chi2 == float(_fraction(expected) ** 2) == 0.0


@pytest.mark.parametrize("sign", [-1.0, 1.0])
@pytest.mark.parametrize("count", [1024, 4096, 8192])
def test_complete_normal_sum_retains_low_bits_of_subnormal_products(sign, count):
    residual = sign * (1.0 + 2.0**-21) * 2.0**-517
    exact = count * _fraction(residual) ** 2
    expected_chi2 = float(exact)
    if count == 4096:
        assert expected_chi2 == float.fromhex("0x1.0000100000400p-1022")
    result = _call([residual] * count, [0.0] * count)
    np.testing.assert_array_equal(result.residual_vector, [residual] * count)
    _close(result.chi2, expected_chi2)


def test_exact_zero_difference_keeps_the_existing_ieee_zero_signs():
    prediction = np.array([-0.0, -0.0, 0.0, 0.0])
    observation = np.array([0.0, -0.0, 0.0, -0.0])
    expected_signs = np.signbit(prediction - observation)
    result = _call(prediction, observation)
    np.testing.assert_array_equal(np.signbit(result.residual_vector), expected_signs)
    assert result.chi2 == 0.0


def test_chi2_squares_the_returned_rounded_vector_not_the_unrounded_ratio():
    exact_ratio = Fraction(1, 10)
    expected_residual = float(exact_ratio)
    expected_chi2 = float(_fraction(expected_residual) ** 2)
    assert expected_chi2 != float(exact_ratio**2)
    result = _call(1.0, 0.0, 10.0)
    np.testing.assert_array_equal(result.residual_vector, [expected_residual])
    assert result.chi2 == expected_chi2

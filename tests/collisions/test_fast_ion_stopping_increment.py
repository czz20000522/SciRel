"""Direct checks of the fixed empirical expression, not physical calibration."""

from __future__ import annotations

import json
from pathlib import Path
import struct
import warnings

import mpmath as mp
import numpy as np
import pytest

from scirel.collisions import evaluate_fast_ion_stopping_increment

_FIXTURE = json.loads(
    (Path(__file__).parents[1] / "fixtures/collisions/fast_ion_stopping_increment.json").read_text(
        encoding="utf-8"
    )
)


def _inputs(case):
    return {
        name: np.asarray(
            [
                np.nan
                if value["classification"] == "nan"
                else struct.unpack(">d", bytes.fromhex(value["ieee754_binary64_be_hex"]))[0]
                for value in item["values"]
            ],
            dtype=np.float64,
        ).reshape(item["shape"], order="F")
        for name, item in case["inputs"].items()
    }


@pytest.mark.parametrize("case", _FIXTURE["cases"], ids=lambda case: case["id"])
def test_frozen_independent_engine_observations(case):
    """Keep all 56 cases and the original finite/nonfinite comparison rules."""
    inputs = _inputs(case)
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always", RuntimeWarning)
        if case["expected_status"] != "returned":
            with pytest.raises(ValueError):
                evaluate_fast_ion_stopping_increment(**inputs)
            return
        actual = evaluate_fast_ion_stopping_increment(**inputs)
    expected = case["expected_output"]
    assert list(actual.shape) == expected["shape"]
    assert actual.dtype in (np.dtype("float64"), np.dtype("complex128"))
    for channel in ("real", "imag"):
        observed = getattr(actual, channel).ravel(order="F")
        reference = np.asarray([float(value) for value in expected[channel]])
        np.testing.assert_array_equal(np.isnan(observed), np.isnan(reference))
        np.testing.assert_array_equal(np.isposinf(observed), np.isposinf(reference))
        np.testing.assert_array_equal(np.isneginf(observed), np.isneginf(reference))
        finite = np.isfinite(reference)
        assert np.isfinite(observed[finite]).all()
        np.testing.assert_allclose(
            observed[finite],
            reference[finite],
            rtol=_FIXTURE["rules"]["finite_rtol"],
            atol=_FIXTURE["rules"]["finite_atol"],
        )


def test_frozen_denominator_and_criteria_are_not_reduced():
    cases = _FIXTURE["cases"]
    assert len(cases) == len({case["id"] for case in cases}) == 56
    rows = {row for case in cases for row in case["rows"]}
    assert len(rows) == 37 and rows == set(_FIXTURE["row_ids"])
    assert sum(case["expected_status"] == "returned" for case in cases) == 55
    assert [case["id"] for case in cases if case["expected_status"] != "returned"] == ["bad_shape"]
    assert _FIXTURE["rules"]["finite_rtol"] == 5e-12
    assert _FIXTURE["rules"]["finite_atol"] == 1e-300


def _call(**changes):
    parameters = dict(
        beam_mass_number=1,
        beam_energy_ev=100000,
        birth_pitch_cosine=0.5,
        electron_density_m3=1e18,
        electron_temperature_ev=10000,
        power_density_w_m3=1000000,
        electron_slowing_time_s=1,
    )
    parameters.update(changes)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return evaluate_fast_ion_stopping_increment(**parameters)


def test_pitch_absolute_value_and_cap():
    np.testing.assert_array_equal(_call(birth_pitch_cosine=-0.5), _call(birth_pitch_cosine=0.5))
    np.testing.assert_array_equal(_call(birth_pitch_cosine=-2), _call(birth_pitch_cosine=1))
    np.testing.assert_array_equal(_call(birth_pitch_cosine=2), _call(birth_pitch_cosine=1))


def test_strict_cutoff_preserves_finite_zero():
    result = _call(beam_energy_ev=(np.pi + 8 * np.spacing(np.pi)) * 1e6)
    np.testing.assert_array_equal(result, np.zeros((1, 1)))
    assert not np.array_equal(_call(beam_energy_ev=np.pi * 1e6), result)


def test_row_column_and_nd_axes():
    assert _call(beam_energy_ev=[100000, 500000]).shape == (1, 2)
    assert _call(beam_energy_ev=[[100000], [500000]]).shape == (2, 1)
    assert _call(
        beam_energy_ev=np.ones((1, 1, 2)) * 100000,
        birth_pitch_cosine=[[0.5], [1]],
    ).shape == (2, 1, 2)


def test_zero_power_does_not_bypass_energy_division():
    assert np.isnan(_call(beam_energy_ev=0, power_density_w_m3=0)).all()


def test_negative_temperature_is_not_silently_real():
    value = _call(electron_temperature_ev=-10000)
    assert np.iscomplexobj(value)
    assert np.any(value.imag != 0)


def test_no_hidden_time_state_or_input_mutation():
    energy = np.array([[100000.0, 500000.0]])
    original = energy.copy()
    first = _call(beam_energy_ev=energy)
    second = _call(beam_energy_ev=energy)
    np.testing.assert_array_equal(energy, original)
    np.testing.assert_array_equal(first, second)


def test_empty_and_incompatible_axes():
    assert _call(beam_energy_ev=np.empty((0, 0))).shape == (0, 0)
    with pytest.raises(ValueError):
        _call(beam_energy_ev=[[100000, 500000]], beam_mass_number=[[1, 2, 3]])


@pytest.mark.parametrize("temperature", [7000, 10000, 23000])
def test_declared_expression_against_high_precision_evaluation(temperature):
    """Independent arithmetic of the declared fit, not a physical accuracy test."""
    with mp.workdps(70):
        theta = mp.mpf(temperature) / 10000
        ratio = mp.mpf("0.1") / theta
        pitch = mp.mpf("0.5")
        energy_coefficients = (
            "0.57658",
            "1.6432",
            "-4.8886",
            "5.3932",
            "-2.9226",
            "0.77156",
            "-0.079095",
        )
        pitch_coefficients = ("0.30812", "11.992", "-68.971", "165.94", "-177.33", "69.833")
        energy_fit = mp.fsum(
            mp.mpf(value) * ratio**power for power, value in enumerate(energy_coefficients)
        )
        pitch_fit = mp.fsum(
            mp.mpf(value) * pitch**power for power, value in enumerate(pitch_coefficients, 1)
        )
        population = mp.mpf(1000000) / (mp.mpf(100000) * mp.mpf("1.602176462e-19")) / mp.mpf("1e18")
        reference = float(
            population * theta ** mp.mpf("-0.9027") * energy_fit * pitch_fit * mp.mpf("1e-19")
        )
    np.testing.assert_allclose(
        _call(electron_temperature_ev=temperature), [[reference]], rtol=5e-12, atol=1e-300
    )


def test_supplied_power_time_density_scaling():
    baseline = _call()
    for changes in ({"power_density_w_m3": 2000000}, {"electron_slowing_time_s": 2}):
        np.testing.assert_allclose(_call(**changes), 2 * baseline, rtol=5e-12, atol=1e-300)
    np.testing.assert_allclose(
        _call(electron_density_m3=2e18), baseline / 2, rtol=5e-12, atol=1e-300
    )


def test_complex_input_is_outside_real_input_contract():
    with pytest.raises(TypeError, match="real"):
        _call(birth_pitch_cosine=0.5 + 0j)


def test_finite_extremes_do_not_imply_finite_output():
    assert np.isinf(_call(beam_energy_ev=np.finfo(np.float64).tiny)).all()

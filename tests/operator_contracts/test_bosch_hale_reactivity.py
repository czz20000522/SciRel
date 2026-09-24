import math

import numpy as np
import pytest

from scirel.fusion import evaluate_bosch_hale_reactivity


@pytest.mark.parametrize(
    ("reaction", "temperature_kev", "expected_m3_s"),
    [
        ("DT", 0.1, 2.723605684273298e-36),
        ("DT", 1.0, 6.8568842495932803e-27),
        ("DT", 10.0, 1.1361654705836232e-22),
        ("DT", 100.0, 8.4476624586658349e-22),
        ("DHe3", 10.0, 2.1260732682232565e-25),
        ("DHe3", 200.0, 2.7589517827340805e-22),
        ("DD_Tp", 50.0, 9.8383256163410802e-24),
        ("DD_He3n", 200.0, 5.4139118283507161e-23),
    ],
)
def test_bosch_hale_channels_match_saved_compiled_source_values(
    reaction, temperature_kev, expected_m3_s
):
    result = evaluate_bosch_hale_reactivity(temperature_kev, reaction=reaction)
    assert isinstance(result, float)
    assert result == pytest.approx(expected_m3_s, rel=1e-11)


def test_profile_preserves_shape_and_does_not_modify_input():
    temperatures = np.array([[1.0, 10.0], [50.0, 100.0]])
    original = temperatures.copy()
    result = evaluate_bosch_hale_reactivity(temperatures, reaction="DT")
    assert result.shape == temperatures.shape
    np.testing.assert_array_equal(temperatures, original)
    for index, temperature in np.ndenumerate(temperatures):
        assert result[index] == pytest.approx(
            evaluate_bosch_hale_reactivity(float(temperature), reaction="DT"),
            rel=1e-14,
        )


def test_dt_fit_matches_independently_rearranged_analytic_form():
    bg = 34.3827
    mrc2 = 1124656
    source_c1 = 1.17302e-9
    k = (bg * bg / 4.0) ** (1.0 / 3.0)
    c0 = source_c1 * 1e-6 / (math.sqrt(mrc2) * k ** 1.5)
    for temperature in (0.2, 1.0, 10.0, 100.0, 200.0):
        zeta = 1.0 - (
            1.51361e-2 * temperature
            + 4.60643e-3 * temperature**2
            - 1.06750e-4 * temperature**3
        ) / (
            1.0 + 7.51886e-2 * temperature
            + 1.35000e-2 * temperature**2
            + 1.36600e-5 * temperature**3
        )
        xi = k * (zeta / temperature) ** (1.0 / 3.0)
        expected = c0 * zeta ** (-5.0 / 6.0) * xi**2 * math.exp(-3.0 * xi)
        actual = evaluate_bosch_hale_reactivity(temperature)
        assert actual == pytest.approx(expected, rel=2e-14)


def test_no_implicit_low_temperature_clip_and_unrepresentable_fit_fails():
    assert evaluate_bosch_hale_reactivity(0.1) < evaluate_bosch_hale_reactivity(0.2)
    with pytest.raises(ValueError, match="not representable"):
        evaluate_bosch_hale_reactivity(1e308)


@pytest.mark.parametrize("temperature", [0.0, -1.0, np.nan, np.inf, True, "10", [], [10.0, False], [1j]])
def test_invalid_temperature_fails_closed(temperature):
    with pytest.raises(ValueError):
        evaluate_bosch_hale_reactivity(temperature)


def test_unknown_reaction_fails_closed():
    with pytest.raises(ValueError, match="reaction"):
        evaluate_bosch_hale_reactivity(10.0, reaction="pB11")

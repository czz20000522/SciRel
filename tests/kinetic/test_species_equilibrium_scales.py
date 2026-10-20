import numpy as np
import pytest

from scirel.kinetic.species_equilibrium_scales import derive_species_equilibrium_scales


ELECTRON = dict(
    ms=[9.1094e-31],
    qs=[-1.60217662e-19],
    ns_unit=[1.0],
    Ts_unit=[1.0],
    B0=1.0,
    n00=6.075e19,
    T00=1e3,
)


def test_thermal_and_gyroradius_conventions_are_distinct():
    result = derive_species_equilibrium_scales(**ELECTRON)
    thermal = np.sqrt(2.0 * result["kB"] * result["Ts0"] / ELECTRON["ms"])
    np.testing.assert_array_equal(result["vts"], thermal)
    np.testing.assert_allclose(
        result["rhocs"], result["vts"] / (np.sqrt(2.0) * result["wcs"]), rtol=2e-16
    )
    assert result["wcs"][0] < 0
    assert result["rhocs"][0] < 0
    assert result["sgns"][0] == -1
    assert result["wn"] == result["wcn"]
    assert result["kn"] == 1.0 / result["rhocn"]


def test_two_species_axes_and_input_ownership():
    case = dict(ELECTRON)
    case["ms"] = np.array([9.1094e-31, 2 * 1.6726219e-27])
    case["qs"] = np.array([-1.0, 1.0]) * 1.60217662e-19
    case["ns_unit"] = np.array([1.0, 1.0])
    case["Ts_unit"] = np.array([1.0, 1.0])
    original = {name: case[name].copy() for name in ("ms", "qs", "ns_unit", "Ts_unit")}
    result = derive_species_equilibrium_scales(**case)
    for name, values in original.items():
        np.testing.assert_array_equal(case[name], values)
    for name in ("ns0", "Ts0", "vts", "wcs", "wps2", "rhocs", "lambdaDs"):
        assert result[name].shape == (2,)
        assert np.all(np.isfinite(result[name]))
    assert result["wcs"][0] < 0 < result["wcs"][1]
    np.testing.assert_array_equal(result["absrhocs"], np.abs(result["rhocs"]))
    np.testing.assert_array_equal(result["sgns"], np.sign(result["rhocs"]))
    np.testing.assert_array_equal(result["kDs"], 1.0 / result["lambdaDs"])


@pytest.mark.parametrize(
    "change",
    [
        {"ms": []}, {"ms": [[1.0]]}, {"qs": [1.0, -1.0]},
        {"ms": [0.0]}, {"qs": [0.0]}, {"ns_unit": [0.0]},
        {"Ts_unit": [-1.0]}, {"B0": 0.0}, {"n00": 0.0},
        {"T00": -1.0}, {"n00": np.inf}, {"Ts_unit": [np.nan]},
        {"ms": [True]}, {"B0": True}, {"ms": ["1"]},
        {"B0": "1"}, {"n00": [1.0]},
    ],
)
def test_invalid_case_fails_closed(change):
    with pytest.raises(ValueError):
        derive_species_equilibrium_scales(**{**ELECTRON, **change})


def test_unrepresentable_derived_scale_fails_closed():
    with pytest.raises(ValueError):
        derive_species_equilibrium_scales(**{**ELECTRON, "n00": 1e308})

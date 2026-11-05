import pytest
from scirel.kinetic.frank_egedal_pressure_state import (
    assemble_frank_egedal_pressure,
    assemble_frank_egedal_pressure as scientific_function,
)


def test_rejects_incomplete_pressure_state():
    with pytest.raises((KeyError, ValueError, TypeError)):
        scientific_function({})


def test_reviewed_relation_example():
    import numpy as np

    psi = np.zeros((2, 2))
    radial = np.array([[1.0, 0.5], [0.25, 0.0]])
    hpar = np.full((2, 2), 2.0)
    hperp = np.full((2, 2), 3.0)
    hdensity = np.full((2, 2), 4.0)
    result = assemble_frank_egedal_pressure(
        psi,
        radial,
        hpar,
        hperp,
        hdensity,
        {
            "hot_pressure_scale": 5.0,
            "gas_dynamic_pressure": 7.0,
            "gas_dynamic_density": 11.0,
            "hot_density_scale": 13.0,
            "electron_temperature": 17.0,
        },
    )
    density = 11.0 * radial + 13.0 * radial * hdensity
    electron = density * 17.0
    expected_parallel = 7.0 * radial + electron + 5.0 * radial * hpar
    expected_perp = 7.0 * radial + electron + 5.0 * radial * hperp
    assert np.allclose(result["density"], density)
    assert np.allclose(result["p_parallel"], expected_parallel)
    assert np.allclose(result["p_perp"], expected_perp)
    assert np.allclose(result["p_perp"] - result["p_parallel"], 5.0 * radial * (hperp - hpar))

    # 没有任何密度尺度时，density 为 None；电子温度仍返回，但不产生电子压强。
    no_density = assemble_frank_egedal_pressure(
        psi,
        radial,
        hpar,
        hperp,
        hdensity,
        {"hot_pressure_scale": 5.0, "gas_dynamic_pressure": 7.0, "electron_temperature": 17.0},
    )
    assert no_density["density"] is None
    assert np.allclose(no_density["electron_temperature"], 17.0)
    assert np.allclose(no_density["p_parallel"], 7.0 * radial + 5.0 * radial * hpar)
    assert np.allclose(no_density["p_perp"], 7.0 * radial + 5.0 * radial * hperp)

    bad_psi = psi.copy()
    bad_psi[0, 0] = np.nan
    try:
        assemble_frank_egedal_pressure(bad_psi, radial, hpar, hperp, hdensity, {})
    except ValueError as exc:
        assert "finite two-dimensional" in str(exc)
    else:
        raise AssertionError("非有限磁通 shape 载体必须失败关闭")
    try:
        assemble_frank_egedal_pressure(
            psi, radial, hpar, hperp, hdensity, {"gas_dynamic_pressure": -1.0}
        )
    except ValueError as exc:
        assert "finite and nonnegative" in str(exc)
    else:
        raise AssertionError("负压力尺度必须失败关闭")

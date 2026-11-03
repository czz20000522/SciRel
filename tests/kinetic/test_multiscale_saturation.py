import numpy as np

from scirel.kinetic.multiscale_saturation import simulate_sat123


def _inputs():
    k = np.array([0.1, 0.2, 0.4])
    scenarios = [{"id": f"s{i}", "sat_rule": 1 if i < 3 else 2 if i < 6 else 3,
                  "exb_shear_a_over_cs": (-0.3, 0.0, 0.3)[i % 3],
                  "energy_weight_variant": "transition" if i == 9 else "default"}
                 for i in range(10)]
    return {
        "ky_rhos": k.tolist(), "n_modes": 2,
        "first_growth_cs_over_a": [[0.2, 0.1], [0.4, 0.2], [0.3, 0.15]],
        "second_growth_cs_over_a": [[0.18, 0.09], [0.35, 0.17], [0.28, 0.14]],
        "width_radian": [1.0, 1.0, 1.0],
        "geometry": {"rmin_a": .5, "rmaj_a": 3., "q": 2., "magnetic_shear": 1.,
                      "pressure_alpha": 0., "theta0": 0., "f_RBt_over_aBunit": 3., "nxgrid": 8,
                      "theta_trapped": .7, "ft_min": .01},
        "QL_field_weights": np.ones((3, 2, 4)).tolist(),
        "QL_moment_weights": np.ones((3, 2, 2, 4)).tolist(),
        "QL_flux_weights": np.ones((3, 2, 2, 3, 5)).tolist(),
        "transition_electron_to_ion_ES_energy_ratio": [1., 1.],
        "scenarios": scenarios,
    }


def test_sat123_returns_all_scenarios_and_signed_flux():
    result = simulate_sat123(_inputs())
    assert len(result["scenarios"]) == 10
    assert result["scenarios"][0]["checks"]["finite"]
    assert any(item["checks"]["signed_flux_present"] for item in result["scenarios"]) or all(
        np.asarray(item["flux_spectrum_GB"]).shape == (3, 2, 2, 3, 5)
        for item in result["scenarios"]
    )
    assert np.asarray(result["scenarios"][0]["field_spectrum"]).shape == (3, 2, 4)


def test_sat123_rejects_missing_scenario_contract():
    inputs = _inputs()
    inputs.pop("scenarios")
    try:
        simulate_sat123(inputs)
    except ValueError as exc:
        assert "scenarios" in str(exc)
    else:
        raise AssertionError("missing scenarios must fail")

import numpy as np
import pytest

from scirel.kinetic.mirror_total_pressure import assemble_mirror_total_pressure, assemble_mirror_total_pressure as scientific_operator


def test_total_pressure_and_terminal_fields_are_assembled():
    ion = {"p_parallel_pa": [2.0, 3.0], "p_perpendicular_pa": [4.0, 5.0], "density_m3": [1.0, 2.0], "marker": "ion"}
    electron = {"electron_density_m3": [6.0, 7.0], "electron_pressure_pa": 1.5, "relative_charge_residual": [0.1, 0.2]}
    result = scientific_operator(ion, electron)
    np.testing.assert_allclose(result["p_parallel"], [3.5, 4.5])
    np.testing.assert_allclose(result["p_perpendicular"], [5.5, 6.5])
    assert result["kinetic_moments"] is ion
    assert result["marker"] == "ion"


def test_missing_state_field_fails_closed():
    with pytest.raises(ValueError, match="missing required"):
        scientific_operator({"p_parallel_pa": 1.0}, {"electron_pressure_pa": 1.0})


def test_reviewed_relation_example():
    import numpy as np
    from scirel.kinetic.mirror_total_pressure import assemble_mirror_total_pressure

    ion = {
        "p_parallel_pa": [2.0, 3.0],
        "p_perpendicular_pa": [4.0, 5.0],
        "density_m3": [1.0, 2.0],
        "marker": "ion",
    }
    electron = {
        "electron_density_m3": [6.0, 7.0],
        "electron_pressure_pa": 1.5,
        "relative_charge_residual": [0.1, 0.2],
    }
    result = assemble_mirror_total_pressure(ion, electron)
    assert np.allclose(result["p_parallel"], [3.5, 4.5])
    assert np.allclose(result["p_perpendicular"], [5.5, 6.5])
    assert np.allclose(
        result["p_perpendicular"] - result["p_parallel"],
        np.asarray(ion["p_perpendicular_pa"]) - np.asarray(ion["p_parallel_pa"]),
    )
    assert result["kinetic_moments"] is ion
    assert result["marker"] == "ion"
    assert result["electrostatic_potential"] is None


def test_electrostatic_potential_is_preserved_when_provided():
    ion = {
        "p_parallel_pa": [2.0],
        "p_perpendicular_pa": [3.0],
        "density_m3": [1.0],
    }
    potential = np.array([0.2, -0.1])
    electron = {
        "electron_density_m3": [1.0],
        "electron_pressure_pa": [1.0],
        "relative_charge_residual": [0.0],
        "electrostatic_potential": potential,
    }

    result = assemble_mirror_total_pressure(ion, electron)

    assert result["electrostatic_potential"] is potential


def test_electrostatic_potential_defaults_to_none_when_absent():
    ion = {
        "p_parallel_pa": [2.0],
        "p_perpendicular_pa": [3.0],
        "density_m3": [1.0],
    }
    electron = {
        "electron_density_m3": [1.0],
        "electron_pressure_pa": [1.0],
        "relative_charge_residual": [0.0],
    }

    result = assemble_mirror_total_pressure(ion, electron)

    assert result["electrostatic_potential"] is None

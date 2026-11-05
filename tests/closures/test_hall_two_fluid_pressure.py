import numpy as np
import pytest

from scirel.closures.hall_two_fluid_pressure import (
    close_hall_two_fluid_pressure,
    close_hall_two_fluid_pressure as scientific_function,
)


def _law(b, psi):
    return {"p_parallel": 5.0 + b + psi, "p_perpendicular": 4.0 + b + 2.0 * psi}


def test_callable_profiles_and_default_ion_pressure_decomposition():
    b = np.array([[1.0, 2.0]])
    psi = np.array([[0.2, 0.4]])
    result = scientific_function(
        b, psi, _law, lambda b, psi: 1.0e18 + psi, lambda b, psi: 1.0 + psi, 3.0
    )
    np.testing.assert_allclose(result["electron_density"], result["ion_density"])
    np.testing.assert_allclose(
        result["ion_p_parallel"], result["p_parallel"] - result["electron_pressure"]
    )
    np.testing.assert_allclose(result["electron_p_perpendicular"], result["electron_pressure"])


def test_negative_derived_ion_moment_fails_closed():
    with pytest.raises(ValueError, match="negative moment"):
        scientific_function(np.ones((1, 2)), np.zeros((1, 2)), _law, 1.0, 100.0, 0.0)


def test_reviewed_relation_example():
    import numpy as np

    def law(b, psi):
        return {"p_parallel": 5.0 + b + psi, "p_perpendicular": 4.0 + b + 2.0 * psi}

    b = np.array([[1.0, 2.0]])
    psi = np.array([[0.2, 0.4]])
    result = close_hall_two_fluid_pressure(b, psi, law, 1.0e18 + psi, 1.0 + psi, 3.0)
    np.testing.assert_allclose(result["p_parallel"], [[6.2, 7.4]])
    np.testing.assert_allclose(result["p_perpendicular"], [[5.4, 6.8]])
    np.testing.assert_allclose(result["electron_density"], result["ion_density"])
    np.testing.assert_allclose(
        result["ion_p_parallel"] + result["electron_p_parallel"], result["p_parallel"]
    )
    np.testing.assert_allclose(
        result["ion_p_perpendicular"] + result["electron_p_perpendicular"],
        result["p_perpendicular"],
    )

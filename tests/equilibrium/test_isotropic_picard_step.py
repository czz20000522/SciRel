import pytest
from scirel.equilibrium.isotropic_picard_step import (
    pressure_flux_picard_step,
    pressure_flux_picard_step as scientific_function,
)


def test_rejects_incomplete_picard_state():
    with pytest.raises((KeyError, ValueError, TypeError)):
        scientific_function({})


def test_reviewed_relation_example():
    import numpy as np

    r_grid, z_grid = np.meshgrid([1.0, 2.0], [-1.0, 1.0])
    pressure_derivative = np.array([1.0, 2.0, 3.0, 4.0])
    currents_old = np.array([10.0, 20.0, 30.0, 40.0])
    relax = 0.25
    psi_state = np.zeros_like(r_grid)
    psi_vac = np.ones_like(r_grid)
    result = pressure_flux_picard_step(
        r_grid,
        z_grid,
        psi_state,
        psi_vac,
        np.eye(r_grid.size),
        pressure_derivative,
        2.0,
        currents_old,
        relax,
    )
    d_area = 2.0
    expected_current = (
        1.0 - relax
    ) * r_grid.ravel() * pressure_derivative * d_area + relax * currents_old
    expected_flux = (expected_current + psi_vac.ravel()).reshape(r_grid.shape)
    np.testing.assert_allclose(result["plasma_currents"], expected_current)
    np.testing.assert_allclose(result["psi_next"], expected_flux)
    assert np.isclose(result["residual"], np.linalg.norm(expected_flux) / 2.0)

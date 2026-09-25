import numpy as np
import pytest

from scirel.equilibrium.axisymmetric_picard_update import update_axisymmetric_picard_flux, update_axisymmetric_picard_flux as scientific_operator
from scirel.field.circular_filament_green import circular_filament_green_response
from scirel.field.mirror_plasma_green import build_mirror_plasma_flux_green
from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux


def _inputs(**overrides):
    r_grid, z_grid = np.meshgrid(np.array([0.0, 0.5, 1.0]), np.array([-0.5, 0.0, 0.5]))
    values = dict(r_grid=r_grid, z_grid=z_grid, j_phi=np.ones((3, 3)), psi_state=np.zeros((3, 3)), psi_vac=np.ones((3, 3)), g_psi=np.eye(9), relax=0.25)
    values.update(overrides)
    return values


def test_flux_relaxation_and_cell_area_follow_declared_source_order():
    result = scientific_operator(**_inputs())
    np.testing.assert_allclose(result["plasma_cell_currents"], 0.25)
    np.testing.assert_allclose(result["psi_next"], 0.9375)
    assert result["relative_current_change"] == 0.75


def test_relax_one_is_rejected():
    with pytest.raises(ValueError, match="relax"):
        scientific_operator(**_inputs(relax=1.0))


def test_vacuum_and_mirror_green_picard_flux_recovers_filament_field():
    radial = np.linspace(0.1, 0.5, 17)
    axial = np.linspace(-0.2, 0.2, 17)
    r_grid, z_grid = np.meshgrid(radial, axial)
    points = np.column_stack((r_grid.ravel(), z_grid.ravel()))
    vacuum_source = [0.7, 0.0, 3.0]
    psi_vac = circular_filament_green_response([vacuum_source], points)["gpsi"].reshape(r_grid.shape)
    g_psi = build_mirror_plasma_flux_green(r_grid, z_grid)["g_psi"]
    source_index = (8, 12)
    j_phi = np.zeros_like(r_grid)
    j_phi[source_index] = 1.0 / ((radial[1] - radial[0]) * (axial[1] - axial[0]))

    state = scientific_operator(r_grid, z_grid, j_phi, psi_vac, psi_vac, g_psi, 0.0)
    field = poloidal_field_from_flux(r_grid, z_grid, state["psi_next"])
    target_index = (12, 4)
    target = points[np.ravel_multi_index(target_index, r_grid.shape)]
    plasma_source = [r_grid[source_index], z_grid[source_index], 1.0]
    direct = circular_filament_green_response([vacuum_source, plasma_source], [target])
    np.testing.assert_allclose(state["plasma_cell_currents"][source_index], 1.0)
    np.testing.assert_allclose(field["B_R"][target_index], direct["gBR"][0], rtol=0.02, atol=0.0)
    np.testing.assert_allclose(field["B_Z"][target_index], direct["gBZ"][0], rtol=0.02, atol=0.0)
    assert not np.isclose(2 * np.pi * field["B_Z"][target_index], direct["gBZ"][0], rtol=0.1, atol=0.0)


def test_reviewed_relation_example():
    import numpy as np
    from scirel.equilibrium.axisymmetric_picard_update import update_axisymmetric_picard_flux

    r_grid, z_grid = np.meshgrid([0.0, 0.5, 1.0], [-0.5, 0.0, 0.5])
    j_phi = np.arange(1.0, 10.0).reshape(3, 3)
    g_psi = np.diag(np.arange(1.0, 10.0))
    psi_state = np.full((3, 3), 2.0)
    psi_vac = np.ones((3, 3))
    relax = 0.25
    result = update_axisymmetric_picard_flux(
        r_grid,
        z_grid,
        j_phi,
        psi_state,
        psi_vac,
        g_psi,
        relax,
    )
    cell_currents = 0.25 * j_phi
    candidate = psi_vac + (g_psi @ cell_currents.ravel()).reshape(3, 3)
    expected = relax * psi_state + (1.0 - relax) * candidate
    np.testing.assert_allclose(result["plasma_cell_currents"], cell_currents)
    np.testing.assert_allclose(result["psi_next"], expected)
    assert np.isclose(result["relative_current_change"], 1.0)
    expected_relative_psi = np.linalg.norm(expected - psi_state) / max(
        np.linalg.norm(expected), np.linalg.norm(psi_vac), np.finfo(float).tiny
    )
    assert np.isclose(result["relative_psi_change"], expected_relative_psi)
    assert set(result) == {
        "psi_next",
        "plasma_cell_currents",
        "relative_psi_change",
        "relative_current_change",
    }
    negative_r_grid, negative_z_grid = np.meshgrid([-1.0, -0.5, 0.0], [-0.5, 0.0, 0.5])
    try:
        update_axisymmetric_picard_flux(
            negative_r_grid,
            negative_z_grid,
            np.ones((3, 3)),
            np.zeros((3, 3)),
            np.zeros((3, 3)),
            np.eye(9),
            0.25,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("negative cylindrical radius must be rejected")

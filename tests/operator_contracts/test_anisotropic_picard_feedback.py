import numpy as np
import pytest

from scirel.equilibrium.anisotropic_picard_feedback import update_anisotropic_picard_flux, update_anisotropic_picard_flux as scientific_operator
from scirel.field.circular_filament_green import circular_filament_green_response
from scirel.field.dense_axisymmetric_green import dense_axisymmetric_green_response


def _inputs(**overrides):
    r, z = np.meshgrid([0.2, 0.4], [-0.1, 0.1])
    values = dict(j_phi=np.ones((2, 2)), r_grid=r, z_grid=z, plasma_mask=None, currents_old=np.zeros(4), relax=0.0, g_psi=np.zeros((4, 4)), g_br=None, g_bz=None, psi_vac=r, br_vac=np.zeros_like(r), bz_vac=np.ones_like(r))
    values.update(overrides)
    return values


def test_zero_green_keeps_vacuum_field_and_emits_cell_current():
    result = scientific_operator(**_inputs())
    np.testing.assert_allclose(result["psi"], _inputs()["psi_vac"])
    np.testing.assert_allclose(result["plasma_currents"], 0.04)


def test_per_radian_green_projection_matches_direct_filament_field():
    r_grid, z_grid = np.meshgrid(np.linspace(0.1, 0.5, 5), np.linspace(-0.2, 0.2, 5))
    points = np.column_stack((r_grid.ravel(), z_grid.ravel()))
    sources = np.column_stack((points, np.ones(points.shape[0])))
    green = dense_axisymmetric_green_response(points, sources)
    vacuum_source = [0.7, 0.0, 1e6]
    vacuum = circular_filament_green_response([vacuum_source], points)
    shape = r_grid.shape
    j_phi = np.zeros(shape)
    source_index = (2, 3)
    j_phi[source_index] = 200.0

    result = update_anisotropic_picard_flux(
        j_phi, r_grid, z_grid, None, None, 0.0,
        green['gpsi'], green['gBR'], green['gBZ'],
        vacuum['gpsi'].reshape(shape), vacuum['gBR'].reshape(shape), vacuum['gBZ'].reshape(shape),
    )

    cell_current = j_phi[source_index] * (r_grid[0, 1] - r_grid[0, 0]) * (z_grid[1, 0] - z_grid[0, 0])
    target_index = (4, 1)
    target = points[np.ravel_multi_index(target_index, shape)]
    plasma_source = [r_grid[source_index], z_grid[source_index], cell_current]
    direct = circular_filament_green_response([vacuum_source, plasma_source], [target])
    assert abs(result['psi'][target_index] - vacuum['gpsi'].reshape(shape)[target_index]) > 1e-9
    np.testing.assert_allclose(result['psi'][target_index], direct['gpsi'][0], rtol=1e-10)
    np.testing.assert_allclose(result['BR'][target_index], direct['gBR'][0], rtol=1e-10)
    np.testing.assert_allclose(result['BZ'][target_index], direct['gBZ'][0], rtol=1e-10)


def test_rejects_unpaired_field_green_matrices():
    with pytest.raises(ValueError, match="provided together"):
        scientific_operator(**_inputs(g_br=np.eye(4)))


def test_reviewed_relation_example():
    import numpy as np
    from scirel.equilibrium.anisotropic_picard_feedback import update_anisotropic_picard_flux

    r_grid, z_grid = np.meshgrid([0.2, 0.4], [-0.1, 0.1])
    j_phi = np.array([[1.0, 2.0], [3.0, 4.0]])
    mask = np.array([[True, False], [False, True]])
    old = np.array([0.2, 0.3, 0.4, 0.5])
    relax = 0.25
    result = update_anisotropic_picard_flux(
        j_phi,
        r_grid,
        z_grid,
        mask,
        old,
        relax,
        np.eye(4),
        2.0 * np.eye(4),
        -np.eye(4),
        np.zeros((2, 2)),
        np.ones((2, 2)),
        2.0 * np.ones((2, 2)),
    )
    kept = np.array([[1.0, 0.0], [0.0, 4.0]])
    raw = kept.ravel() * 0.04
    relaxed = (1.0 - relax) * raw + relax * old
    np.testing.assert_allclose(result["j_phi"], kept)
    np.testing.assert_allclose(result["plasma_currents"], raw.reshape(2, 2))
    np.testing.assert_allclose(result["picard_current_state"], relaxed)
    np.testing.assert_allclose(result["psi"], relaxed.reshape(2, 2))
    np.testing.assert_allclose(result["BR"], 1.0 + 2.0 * relaxed.reshape(2, 2))
    np.testing.assert_allclose(result["BZ"], 2.0 - relaxed.reshape(2, 2))


def test_review_gate_rejects_a_grid_without_a_cell_area():
    import pytest

    with pytest.raises(ValueError, match="at least two points per axis"):
        update_anisotropic_picard_flux(
            np.ones((1, 2)),
            np.array([[0.2, 0.4]]),
            np.array([[0.0, 0.0]]),
            None,
            None,
            0.0,
            np.eye(2),
            None,
            None,
            np.zeros((1, 2)),
            np.zeros((1, 2)),
            np.ones((1, 2)),
        )


@pytest.mark.parametrize("axis", [[0.2, 0.2, 0.6], [0.2, 0.4, 0.8], [0.6, 0.2, 0.4]])
def test_rejects_grids_where_one_cell_area_cannot_represent_all_cells(axis):
    r, z = np.meshgrid(axis, [-0.1, 0.1])
    shape, size = r.shape, r.size
    with pytest.raises(ValueError, match="uniform nonzero spacing"):
        scientific_operator(**_inputs(r_grid=r, z_grid=z, j_phi=np.ones(shape),
            currents_old=np.zeros(size), g_psi=np.eye(size), psi_vac=np.zeros(shape),
            br_vac=np.zeros(shape), bz_vac=np.ones(shape)))


@pytest.mark.parametrize("mask", [True, [True, False], [[1, 0], [0, 1]]])
def test_rejects_broadcast_or_nonboolean_plasma_masks(mask):
    with pytest.raises(ValueError, match="boolean.*shape"):
        scientific_operator(**_inputs(plasma_mask=mask))


def test_descending_uniform_axes_preserve_positive_cell_area():
    r, z = np.meshgrid([0.4, 0.2], [0.1, -0.1])
    result = scientific_operator(**_inputs(r_grid=r, z_grid=z))
    np.testing.assert_allclose(result["plasma_currents"], 0.04)

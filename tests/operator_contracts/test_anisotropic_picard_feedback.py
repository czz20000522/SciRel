# Historical failing-node names are retained for traceability. Expectations below
# follow the corrected nodal-domain quadrature, not the superseded full-cell rule.
import numpy as np
import pytest

from scirel.equilibrium.anisotropic_picard_feedback import update_anisotropic_picard_flux, update_anisotropic_picard_flux as scientific_operator


def _inputs(**overrides):
    r, z = np.meshgrid([0.2, 0.4], [-0.1, 0.1])
    values = dict(j_phi=np.ones((2, 2)), r_grid=r, z_grid=z, plasma_mask=None, currents_old=np.zeros(4), relax=0.0, g_psi=np.zeros((4, 4)), g_br=None, g_bz=None, psi_vac=r, br_vac=np.zeros_like(r), bz_vac=np.ones_like(r))
    values.update(overrides)
    return values


def test_zero_green_keeps_vacuum_field_and_emits_cell_current():
    result = scientific_operator(**_inputs())
    np.testing.assert_allclose(result["psi"], _inputs()["psi_vac"])
    np.testing.assert_allclose(result["plasma_currents"], 0.01)


def test_rejects_unpaired_field_green_matrices():
    with pytest.raises(ValueError, match="provided together"):
        scientific_operator(**_inputs(g_br=np.eye(4)))


def test_full_old_state_retention_and_zero_initialization():
    old = np.array([0.2, 0.3, 0.4, 0.5])
    retained = scientific_operator(**_inputs(currents_old=old, relax=1.0, g_psi=np.eye(4)))
    np.testing.assert_allclose(retained["picard_current_state"], old)
    np.testing.assert_allclose(retained["plasma_currents"], 0.01)
    np.testing.assert_allclose(retained["psi"], _inputs()["psi_vac"] + old.reshape(2, 2))
    np.testing.assert_array_equal(retained["initial_picard_current_state"], np.zeros(4))

    initialized = scientific_operator(**_inputs(currents_old=None, relax=1.0))
    np.testing.assert_array_equal(initialized["picard_current_state"], np.zeros(4))
    np.testing.assert_allclose(initialized["plasma_currents"], 0.01)


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
    raw = kept.ravel() * 0.01
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
    values = _inputs(r_grid=r, z_grid=z, j_phi=np.ones(shape),
        currents_old=np.zeros(size), g_psi=np.eye(size), psi_vac=np.zeros(shape),
        br_vac=np.zeros(shape), bz_vac=np.ones(shape))
    if axis == [0.2, 0.4, 0.8]:
        # A nonuniform monotone axis is valid: trapezoid weights integrate
        # precisely the rectangle of width .6 and height .2, not .2*3*.2*2.
        result = scientific_operator(**values)
        np.testing.assert_allclose(result["plasma_currents"],
            [[.01, .03, .02], [.01, .03, .02]])
        np.testing.assert_allclose(np.sum(result["plasma_currents"]), .12)
    else:
        with pytest.raises(ValueError, match="strictly monotone"):
            scientific_operator(**values)


@pytest.mark.parametrize("mask", [True, [True, False], [[1, 0], [0, 1]]])
def test_rejects_broadcast_or_nonboolean_plasma_masks(mask):
    with pytest.raises(ValueError, match="boolean.*shape"):
        scientific_operator(**_inputs(plasma_mask=mask))


def test_descending_uniform_axes_preserve_positive_cell_area():
    r, z = np.meshgrid([0.4, 0.2], [0.1, -0.1])
    result = scientific_operator(**_inputs(r_grid=r, z_grid=z))
    np.testing.assert_allclose(result["plasma_currents"], 0.01)

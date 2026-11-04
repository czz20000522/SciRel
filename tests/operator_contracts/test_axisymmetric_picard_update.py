import numpy as np
import pytest

from scirel.equilibrium.axisymmetric_picard_update import update_axisymmetric_picard_flux, update_axisymmetric_picard_flux as scientific_operator


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


def test_nonuniform_grid_uses_first_spacings_for_every_cell_current():
    r_grid, z_grid = np.meshgrid([0.0, 0.2, 0.7], [-0.5, -0.2, 0.6])
    result = scientific_operator(
        r_grid, z_grid, np.ones((3, 3)), np.zeros((3, 3)),
        np.zeros((3, 3)), np.eye(9), 0.0,
    )
    np.testing.assert_allclose(result["plasma_cell_currents"], 0.06)
    np.testing.assert_allclose(result["psi_next"], 0.06)


def test_previous_currents_change_only_the_current_diagnostic():
    inputs = _inputs()
    baseline = scientific_operator(**inputs)
    repeated = scientific_operator(**inputs, previous_cell_currents=np.full((3, 3), 0.25))
    for key in ("psi_next", "plasma_cell_currents", "relative_psi_change"):
        np.testing.assert_allclose(repeated[key], baseline[key])
    assert repeated["relative_current_change"] == 0.0
    assert baseline["relative_current_change"] == 0.75


def test_relax_one_is_rejected():
    with pytest.raises(ValueError, match="relax"):
        scientific_operator(**_inputs(relax=1.0))


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

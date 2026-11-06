# Historical node IDs are retained. A current density at nodes owns its
# trapezoid weight; first-spacing/full-cell assumptions are superseded.
import numpy as np
import pytest

from scirel._result import Result
from scirel.equilibrium.axisymmetric_picard_update import (
    update_axisymmetric_picard_flux,
    update_axisymmetric_picard_flux as scientific_function,
)


def _inputs(**overrides):
    r_grid, z_grid = np.meshgrid(np.array([0.0, 0.5, 1.0]), np.array([-0.5, 0.0, 0.5]))
    values = dict(
        r_grid=r_grid,
        z_grid=z_grid,
        j_phi=np.ones((3, 3)),
        psi_state=np.zeros((3, 3)),
        psi_vac=np.ones((3, 3)),
        g_psi=np.eye(9),
        relax=0.25,
    )
    values.update(overrides)
    return values


def test_flux_relaxation_and_cell_area_follow_declared_source_order():
    result = scientific_function(**_inputs())
    assert isinstance(result, Result)
    assert list(result) == [
        "psi_next",
        "plasma_cell_currents",
        "relative_psi_change",
        "relative_current_change",
        "fixed_point_residual",
    ]
    for key in result:
        assert getattr(result, key) is result[key]
    weights = np.outer([0.25, 0.5, 0.25], [0.25, 0.5, 0.25])
    np.testing.assert_allclose(result["plasma_cell_currents"], weights)
    np.testing.assert_allclose(result["psi_next"], 0.75 * (1.0 + weights))
    assert result["relative_current_change"] == 0.375


def test_nonuniform_grid_uses_first_spacings_for_every_cell_current():
    r_grid, z_grid = np.meshgrid([0.0, 0.2, 0.7], [-0.5, -0.2, 0.6])
    result = scientific_function(
        r_grid,
        z_grid,
        np.ones((3, 3)),
        np.zeros((3, 3)),
        np.zeros((3, 3)),
        np.eye(9),
        0.0,
    )
    weights = np.outer([0.15, 0.55, 0.4], [0.1, 0.35, 0.25])
    np.testing.assert_allclose(result["plasma_cell_currents"], weights)
    np.testing.assert_allclose(result["psi_next"], weights)
    np.testing.assert_allclose(np.sum(result["plasma_cell_currents"]), 0.7 * 1.1)


def test_previous_currents_change_only_the_current_diagnostic():
    inputs = _inputs()
    baseline = scientific_function(**inputs)
    repeated = scientific_function(
        **inputs, previous_cell_currents=np.outer([0.25, 0.5, 0.25], [0.25, 0.5, 0.25])
    )
    for key in ("psi_next", "plasma_cell_currents", "relative_psi_change"):
        np.testing.assert_allclose(repeated[key], baseline[key])
    assert repeated["relative_current_change"] == 0.0
    assert baseline["relative_current_change"] == 0.375


def test_relax_one_is_rejected():
    with pytest.raises(ValueError, match="relax"):
        scientific_function(**_inputs(relax=1.0))


def test_reviewed_relation_example():
    import numpy as np

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
    cell_currents = np.outer([0.25, 0.5, 0.25], [0.25, 0.5, 0.25]) * j_phi
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
        "fixed_point_residual",
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

import numpy as np
import pytest

from scirel.field.filament_vacuum_field import integrate_filament_vacuum_field, integrate_filament_vacuum_field as scientific_operator
from scirel.field.circular_filament_green import circular_filament_green_response


def _grid():
    return np.meshgrid(np.linspace(0.0, 0.3, 5), np.linspace(-0.2, 0.2, 4))


def test_superposition_and_axis_boundary():
    r_grid, z_grid = _grid()
    left = scientific_operator(r_grid, z_grid, np.array([[0.45, -0.1, 1500.0]]))
    right = scientific_operator(r_grid, z_grid, np.array([[0.55, 0.15, -800.0]]))
    combined = scientific_operator(r_grid, z_grid, np.array([[0.45, -0.1, 1500.0], [0.55, 0.15, -800.0]]))
    for name in ("psi", "b_r", "b_z"):
        np.testing.assert_allclose(combined[name], left[name] + right[name], rtol=2.0e-14, atol=1.0e-300)
    np.testing.assert_allclose(combined["b_r"][:, 0], 0.0, atol=0.0)
    np.testing.assert_allclose(combined["psi"][:, 0], 0.0, atol=0.0)


def test_axis_field_matches_circular_filament_analytic_limit():
    r_grid, z_grid = _grid()
    source_r, source_z, current_a = 0.45, -0.10, 1500.0
    result = scientific_operator(r_grid, z_grid, np.array([[source_r, source_z, current_a]]))
    z_axis = z_grid[:, 0]
    expected_b_z = (
        4.0
        * np.pi
        * 1.0e-7
        * current_a
        * source_r**2
        / (2.0 * (source_r**2 + (z_axis - source_z) ** 2) ** 1.5)
    )
    np.testing.assert_allclose(result["b_z"][:, 0], expected_b_z, rtol=2.0e-14, atol=1.0e-300)


def test_radial_flux_matches_psi_ra_phi_with_first_radius_reference():
    radial = np.linspace(0.0, 0.3, 301)
    r_grid, z_grid = np.meshgrid(radial, [-0.12, 0.08])
    source_r, source_z, current_a = 0.45, -0.02, 1200.0
    result = scientific_operator(r_grid, z_grid, [[source_r, source_z, current_a]])
    point_green = circular_filament_green_response(
        [[source_r, source_z, 1.0]],
        np.column_stack((r_grid.ravel(), z_grid.ravel())),
    )["gpsi"].reshape(r_grid.shape) * current_a
    expected = point_green - point_green[:, :1]
    np.testing.assert_allclose(result["psi"], expected, rtol=3e-5, atol=3e-9)


def test_accepts_transposed_rectilinear_layout():
    r_grid, z_grid = _grid()
    result = scientific_operator(r_grid.T, z_grid.T, np.array([[0.45, 0.0, 1000.0]]))
    assert result["psi"].shape == r_grid.T.shape
    assert np.all(np.isfinite(result["b_z"]))


def test_rejects_non_rectilinear_radial_grid():
    r_grid, z_grid = _grid()
    r_grid = r_grid.copy()
    r_grid[1, 2] += 0.01
    with pytest.raises(ValueError, match="rectilinear radial"):
        scientific_operator(r_grid, z_grid, np.array([[0.45, 0.0, 1000.0]]))


def test_reviewed_relation_example():
    import numpy as np
    from scirel.field.filament_vacuum_field import integrate_filament_vacuum_field

    r_grid, z_grid = np.meshgrid(np.linspace(0.0, 0.3, 5), np.linspace(-0.2, 0.2, 4))
    left_filament = np.array([[0.45, -0.1, 1500.0]])
    right_filament = np.array([[0.55, 0.15, -800.0]])
    left = integrate_filament_vacuum_field(r_grid, z_grid, left_filament)
    right = integrate_filament_vacuum_field(r_grid, z_grid, right_filament)
    total = integrate_filament_vacuum_field(
        r_grid, z_grid, np.vstack([left_filament, right_filament])
    )
    empty = integrate_filament_vacuum_field(r_grid, z_grid, [])
    for name in ("psi", "b_r", "b_z"):
        np.testing.assert_allclose(total[name], left[name] + right[name], rtol=2.0e-14, atol=1.0e-300)
        np.testing.assert_allclose(empty[name], np.zeros_like(r_grid))
    source_r, source_z, current = left_filament[0]
    expected_axis_bz = (
        4.0 * np.pi * 1.0e-7 * current * source_r**2
        / (2.0 * (source_r**2 + (z_grid[:, 0] - source_z) ** 2) ** 1.5)
    )
    np.testing.assert_allclose(left["b_z"][:, 0], expected_axis_bz, rtol=2.0e-14)
    h = r_grid[0, 1] - r_grid[0, 0]
    expected_increment = 0.5 * h * (
        r_grid[:, :-1] * left["b_z"][:, :-1]
        + r_grid[:, 1:] * left["b_z"][:, 1:]
    )
    np.testing.assert_allclose(np.diff(left["psi"], axis=1), expected_increment)

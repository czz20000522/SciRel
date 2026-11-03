import numpy as np
import pytest
import mpmath as mp

from scirel.field.mirror_plasma_green import build_mirror_plasma_flux_green, build_mirror_plasma_flux_green as scientific_function
from scirel.field.dense_axisymmetric_green import dense_axisymmetric_green_response


def _grid():
    radial = np.linspace(0.0, 0.3, 4)
    axial = np.linspace(-0.4, 0.4, 3)
    return np.meshgrid(radial, axial)


def _direct_first_plane_response(r_grid, z_grid, source_r):
    # The original binary64 K/E subtraction cancels at small m, exceeding
    # this test's unchanged 2e-14 gate. Evaluate the independent formula at
    # 80 digits using exact binary64 fixture values; do not weaken tolerances.
    result = np.zeros(r_grid.size)
    with mp.workdps(80):
        a,z0 = mp.mpf(float(source_r)),mp.mpf(float(z_grid[0,0]))
        for i,(r,z) in enumerate(zip(r_grid.ravel(),z_grid.ravel())):
            r,z = mp.mpf(float(r)),mp.mpf(float(z))
            if r==0 or (r==a and z==z0):
                continue
            d=mp.sqrt((r+a)**2+(z-z0)**2)
            m=4*r*a/d**2
            result[i]=float(mp.mpf('1e-7')*d*((2-m)*mp.ellipk(m)-2*mp.ellipe(m)))
    return result


def test_first_source_plane_matches_independent_circular_filament_formula():
    r_grid, z_grid = _grid()
    result = scientific_function(r_grid, z_grid)["g_psi"]
    for source_index, source_r in enumerate(r_grid[0]):
        expected = (
            np.zeros(r_grid.size)
            if source_index == 0
            else _direct_first_plane_response(r_grid, z_grid, source_r)
        )
        np.testing.assert_allclose(result[:, source_index], expected, rtol=2.0e-14, atol=1.0e-300)


def test_shape_finiteness_and_axis_source_columns_follow_source_convention():
    r_grid, z_grid = _grid()
    result = scientific_function(r_grid, z_grid)["g_psi"]
    assert result.shape == (r_grid.size, r_grid.size)
    assert np.all(np.isfinite(result))
    for source_plane in range(r_grid.shape[0]):
        np.testing.assert_allclose(result[:, source_plane * r_grid.shape[1]], 0.0, atol=0.0)


def test_reflected_matrix_matches_direct_filament_columns_on_symmetric_grid():
    r_grid, z_grid = _grid()
    points = np.column_stack((r_grid.ravel(), z_grid.ravel()))
    sources = np.column_stack((points, np.ones(points.shape[0])))
    direct = dense_axisymmetric_green_response(points, sources)["gpsi"]
    reflected = scientific_function(r_grid, z_grid)["g_psi"]
    np.testing.assert_allclose(reflected, direct, rtol=2e-14, atol=1e-30)


def test_rejects_non_symmetric_axial_grid():
    r_grid, z_grid = _grid()
    z_grid = z_grid.copy()
    z_grid[-1, :] = 0.5
    with pytest.raises(ValueError, match="axis-reflection-symmetric"):
        scientific_function(r_grid, z_grid)


def test_reviewed_relation_example():
    import numpy as np
    from scirel.field.mirror_plasma_green import build_mirror_plasma_flux_green

    r_grid, z_grid = np.meshgrid(
        np.linspace(0.0, 0.3, 4),
        np.linspace(-0.4, 0.4, 3),
    )
    g_psi = build_mirror_plasma_flux_green(r_grid, z_grid)["g_psi"]
    n_z, n_r = r_grid.shape
    assert g_psi.shape == (r_grid.size, r_grid.size)
    for source_plane in range(n_z):
        np.testing.assert_allclose(g_psi[:, source_plane * n_r], 0.0)
    for target_plane in range(n_z):
        for source_plane in range(n_z):
            block = g_psi[
                target_plane * n_r : (target_plane + 1) * n_r,
                source_plane * n_r : (source_plane + 1) * n_r,
            ]
            separation = abs(target_plane - source_plane)
            reference = g_psi[
                separation * n_r : (separation + 1) * n_r,
                :n_r,
            ]
            np.testing.assert_allclose(block, reference)

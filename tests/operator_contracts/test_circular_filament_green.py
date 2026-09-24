import numpy as np

from scirel.field.circular_filament_green import circular_filament_green_response, circular_filament_green_response as scientific_operator
from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux


# 验证：轴上的 source filament 必须依源码约定跳过，且不污染其他有限响应。
def test_skips_axis_filament_and_returns_finite_response():
    points = np.array([[0.2, -0.1], [0.3, 0.0], [0.4, 0.1]])
    result = scientific_operator(np.array([[0.0, 0.0, 9.0], [0.25, 0.0, 1.0]]), points)
    reference = scientific_operator(np.array([[0.25, 0.0, 1.0]]), points)
    for key in ("gpsi", "gBR", "gBZ"):
        assert result[key].shape == (3,)
        assert np.all(np.isfinite(result[key]))
        assert np.allclose(result[key], reference[key])


# 验证：线性 Green 响应必须满足独立电流丝贡献的加和。
def test_weighted_filament_response_is_linear():
    points = np.array([[0.2, -0.1], [0.3, 0.1]])
    left = scientific_operator(np.array([[0.25, 0.0, 2.0]]), points)
    right = scientific_operator(np.array([[0.35, 0.05, -0.5]]), points)
    total = scientific_operator(np.array([[0.25, 0.0, 2.0], [0.35, 0.05, -0.5]]), points)
    for key in ("gpsi", "gBR", "gBZ"):
        assert np.allclose(total[key], left[key] + right[key])


def test_flux_normalization_recovers_direct_green_field():
    r = np.linspace(0.2, 0.6, 41)
    z = np.linspace(-0.2, 0.2, 41)
    r_grid, z_grid = np.meshgrid(r, z)
    points = np.column_stack((r_grid.ravel(), z_grid.ravel()))
    green = circular_filament_green_response([[0.8, 0.0, 1.0]], points)
    flux = green["gpsi"].reshape(r_grid.shape)
    reconstructed = poloidal_field_from_flux(r_grid, z_grid, flux)
    full_linked_flux = poloidal_field_from_flux(r_grid, z_grid, 2.0 * np.pi * flux)
    interior = (slice(4, -4), slice(4, -4))

    for field_name, green_name in (("B_R", "gBR"), ("B_Z", "gBZ")):
        direct = green[green_name].reshape(r_grid.shape)[interior]
        error = np.max(np.abs(reconstructed[field_name][interior] - direct))
        assert error / np.max(np.abs(direct)) < 2.0e-3
        full_flux_error = np.max(np.abs(full_linked_flux[field_name][interior] - direct))
        assert full_flux_error / np.max(np.abs(direct)) > 1.0


def test_reviewed_relation_example():
    import numpy as np
    from scirel.field.circular_filament_green import circular_filament_green_response

    source_r = 0.35
    source_z = 0.0
    points = np.array([
        [0.0, -0.2],
        [0.0, 0.2],
        [0.2, -0.1],
        [0.2, 0.1],
    ])
    unit = circular_filament_green_response([[source_r, source_z, 1.0]], points)
    weighted = circular_filament_green_response([[source_r, source_z, 2.5]], points)
    for name in ("gpsi", "gBR", "gBZ"):
        assert unit[name].shape == (points.shape[0],)
        np.testing.assert_allclose(weighted[name], 2.5 * unit[name])
        np.testing.assert_allclose(
            circular_filament_green_response([], points)[name],
            np.zeros(points.shape[0]),
        )
    np.testing.assert_allclose(unit["gBR"][2], -unit["gBR"][3])
    np.testing.assert_allclose(unit["gBZ"][2], unit["gBZ"][3])
    np.testing.assert_allclose(unit["gpsi"][2], unit["gpsi"][3])
    expected_axis_bz = 4.0 * np.pi * 1.0e-7 * source_r**2 / (
        2.0 * (source_r**2 + 0.2**2) ** 1.5
    )
    np.testing.assert_allclose(unit["gBZ"][:2], expected_axis_bz, rtol=1.0e-13)
    np.testing.assert_allclose(unit["gpsi"][:2], 0.0)
    np.testing.assert_allclose(unit["gBR"][:2], 0.0)

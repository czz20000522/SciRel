import numpy as np

from scirel.field.poloidal_field_from_flux import _source_hypot, poloidal_field_from_flux, poloidal_field_from_flux as scientific_operator


def test_uniform_axial_field_and_axis_regularization():
    r, z = np.linspace(0., .4, 7), np.linspace(-.5, .5, 9)
    R, Z = np.meshgrid(r, z)
    result = scientific_operator(R, Z, .5 * 2.0 * R**2)
    np.testing.assert_allclose(result['B_R'], 0.0, atol=1e-12)
    np.testing.assert_allclose(result['B_Z'], 2.0, atol=1e-12)


def test_nonrectilinear_grid_is_rejected():
    r, z = np.linspace(0., .4, 4), np.linspace(-.5, .5, 4)
    R, Z = np.meshgrid(r, z)
    R[1, 1] += .01
    try:
        scientific_operator(R, Z, np.zeros_like(R))
    except ValueError:
        return
    raise AssertionError('expected invalid mesh failure')


def test_source_hypot_preserves_finite_subnormal_and_large_results():
    result = _source_hypot(np.array([1.0e-308, 1.0e308]), np.array([1.0e-308, 1.0e308]))
    assert result[0] != 0.0
    assert np.isfinite(result[0]) and np.isfinite(result[1])
    np.testing.assert_array_equal(result, np.array([1.414213562373095e-308, 1.4142135623730951e308]))


def test_reviewed_relation_example():
    import numpy as np
    from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux

    r_axis = np.linspace(0.0, 0.4, 7)
    z_axis = np.linspace(-0.5, 0.5, 9)
    r_grid, z_grid = np.meshgrid(r_axis, z_axis)
    profile = 2.0 + z_grid
    psi = 0.5 * r_grid**2 * profile
    result = poloidal_field_from_flux(r_grid, z_grid, psi)
    np.testing.assert_allclose(result["B_Z"], profile, atol=1.0e-12)
    np.testing.assert_allclose(result["B_R"], -0.5 * r_grid, atol=1.0e-12)
    np.testing.assert_allclose(
        result["B"],
        np.hypot(result["B_R"], result["B_Z"]),
    )
    bad_r = r_grid.copy()
    bad_r[0, 0] = np.nan
    try:
        poloidal_field_from_flux(bad_r, z_grid, psi)
    except ValueError:
        pass
    else:
        raise AssertionError("non-finite grid coordinates must be rejected")

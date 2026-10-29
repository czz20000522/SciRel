import numpy as np
import pytest

from scirel.equilibrium import (
    bilinear_interpolate,
    find_critical_points,
    refine_limiter_polygon,
    solve_limited_boundary,
    trace_flux_boundary,
)


def _case():
    r = 0.5 + 7 * np.arange(65) / 320
    z = -1.0 + np.arange(85) / 40
    R, Z = np.meshgrid(r, z, indexing="ij")
    psi = 0.05 - 0.02 * (((R - 1.2) / 0.4) ** 2 + ((Z - 0.1) / 0.65) ** 2)
    limiter = np.array([[.85, -.63], [1.68, -.63], [1.68, .72], [.85, .72], [.85, -.63]])
    return r, z, psi, limiter


def test_finite_difference_axis_and_limiter_boundary():
    r, z, psi, limiter = _case()
    result = solve_limited_boundary(r, z, psi, limiter)
    np.testing.assert_allclose(result["opoints_RZpsi"][0], [1.2, .1, .05], atol=1e-14)
    assert result["xpoints_RZpsi"].shape == (0, 3)
    np.testing.assert_allclose(result["boundary_psi"], .0346875, atol=1e-14)
    assert result["closed_boundary_RZ"].shape == (81, 2)
    np.testing.assert_array_equal(result["closed_boundary_RZ"][0], result["closed_boundary_RZ"][-1])


def test_refinement_and_bilinear_lower_upper_points():
    r, z, psi, limiter = _case()
    refined = refine_limiter_polygon(r, z, limiter)
    assert refined.shape[0] > limiter.shape[0]
    got = bilinear_interpolate(r, z, psi, np.array([[r[0], z[0]], [r[-1], z[-1]]]))
    np.testing.assert_allclose(got, [psi[0, 0], psi[-1, -1]])


def test_malformed_and_degenerate_inputs_fail_closed():
    r, z, psi, limiter = _case()
    with pytest.raises(ValueError):
        find_critical_points(r, z, psi[:, :-1])
    with pytest.raises(ValueError):
        refine_limiter_polygon(r, z, np.zeros((4, 2)))
    with pytest.raises(ValueError):
        bilinear_interpolate(r, z, psi, np.array([[r[0] - 1, z[0]]]))
    with pytest.raises(ValueError):
        trace_flux_boundary(r, z, psi, np.array([1.2, .1, .05]), .05)

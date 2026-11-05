"""Independent meridional vector projection and roundtrip gates."""

import numpy as np
import pytest
from scirel.geometry import sampling as m


def test_polar_position_and_vector_independent_projection():
    rho = np.array([0.2, 0.7, 1.4, 2.1, 0.0])
    z = np.array([0.7, -0.3, 0.0, 1.2, -0.8])
    u = np.array([0.3, -0.1, 0.9, 0.5, 0.4])
    v = np.array([-0.4, 0.6, 0.2, -0.1, 0.7])
    r, t, ur, ut = m.transform_to_rtheta(rho, z, u, v)
    expected_r = np.sqrt(rho * rho + z * z)
    np.testing.assert_allclose(r, expected_r, rtol=0, atol=1e-14)
    np.testing.assert_allclose(np.sin(t), rho / expected_r, rtol=0, atol=3e-15)
    np.testing.assert_allclose(np.cos(t), z / expected_r, rtol=0, atol=3e-15)
    np.testing.assert_allclose(ur, (u * rho + v * z) / expected_r, rtol=0, atol=3e-15)
    np.testing.assert_allclose(ut, (u * z - v * rho) / expected_r, rtol=0, atol=3e-15)
    np.testing.assert_allclose(ur * ur + ut * ut, u * u + v * v, rtol=0, atol=3e-15)


def test_polar_inverse_roundtrip_positions_and_vector_components():
    rho = np.array([0.2, 0.7, 1.4, 2.1, 0.0])
    z = np.array([0.7, -0.3, 0.0, 1.2, -0.8])
    u = np.array([0.3, -0.1, 0.9, 0.5, 0.4])
    v = np.array([-0.4, 0.6, 0.2, -0.1, 0.7])
    got = m.transform_to_rhoz(*m.transform_to_rtheta(rho, z, u, v))
    for actual, expected in zip(got, [rho, z, u, v]):
        np.testing.assert_allclose(actual, expected, rtol=0, atol=3e-15)


def test_origin_polar_basis_rejected():
    with pytest.raises(ValueError, match="origin|undefined"):
        m.transform_to_rtheta(0.0, 0.0, 1.0, 2.0)
    with pytest.raises(ValueError, match="origin|positive|undefined"):
        m.transform_to_rhoz(0.0, 0.0, 1.0, 2.0)

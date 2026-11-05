"""Ordered per-filament response, including the explicit discrete self rule."""

import numpy as np
import pytest
from scipy.integrate import quad

from scirel.electromagnetism import green_response_matrices


def loop_integrals(a, z0, r, z):
    h = z - z0
    distance = lambda phi: np.sqrt(r * r + a * a - 2 * r * a * np.cos(phi) + h * h)
    psi = (
        1e-7
        * a
        * r
        * quad(lambda p: np.cos(p) / distance(p), 0, 2 * np.pi, epsabs=1e-12, epsrel=1e-12)[0]
    )
    br = (
        1e-7
        * a
        * h
        * quad(lambda p: np.cos(p) / distance(p) ** 3, 0, 2 * np.pi, epsabs=1e-12, epsrel=1e-12)[0]
    )
    bz = (
        1e-7
        * a
        * quad(
            lambda p: (a - r * np.cos(p)) / distance(p) ** 3,
            0,
            2 * np.pi,
            epsabs=1e-12,
            epsrel=1e-12,
        )[0]
    )
    return np.array([psi, br, bz])


def test_signed_ordered_response_and_current_contraction():
    targets = np.array([[0.24, -0.71], [0.0, 0.35], [1.42, 0.63], [0.73, -0.08]])
    sources = np.array([[0.51, 0.17, -2.0], [1.18, -0.42, 0.7], [0.36, 1.1, 3.0]])
    expected = np.empty((3, 4, 3))
    for i, (r, z) in enumerate(targets):
        for j, (a, h, w) in enumerate(sources):
            expected[:, i, j] = w * loop_integrals(a, h, r, z)
    response = np.array(green_response_matrices(targets, sources))
    assert response.shape == (3, 4, 3)
    np.testing.assert_allclose(response, expected, rtol=1e-11, atol=1e-18)
    currents = np.array([4.0, -3.0, 0.5])
    np.testing.assert_allclose(response @ currents, expected @ currents, rtol=1e-11, atol=1e-18)
    np.testing.assert_allclose(
        green_response_matrices(targets[[2, 0, 3, 1]], sources[[1, 2, 0]]),
        response[:, [2, 0, 3, 1]][:, :, [1, 2, 0]],
        rtol=0,
        atol=0,
    )


def test_default_unit_sources_discrete_self_axis_and_zero_weight():
    targets = np.array([[0.0, 0.7], [0.6, -0.3], [1.1, 0.4]])
    matrices = np.array(green_response_matrices(targets))
    assert matrices.shape == (3, 3, 3)
    np.testing.assert_array_equal(matrices[:, np.arange(3), np.arange(3)], 0.0)
    np.testing.assert_array_equal(matrices[:, :, 0], 0.0)
    explicit = np.column_stack((targets, np.ones(3)))
    np.testing.assert_array_equal(matrices, green_response_matrices(targets, explicit))
    np.testing.assert_array_equal(green_response_matrices(targets, [[0.6, -0.3, 0.0]]), 0.0)
    np.testing.assert_allclose(
        matrices[:, 0, 1], loop_integrals(0.6, -0.3, 0.0, 0.7), rtol=1e-12, atol=1e-18
    )


@pytest.mark.parametrize(
    "sources", [[[0.2, 0, np.nan]], [[-0.2, 0, 1]], [[0.2, 0, 1, 2]], [[0.2 + 1j, 0, 1]]]
)
def test_malformed_sources_fail_closed(sources):
    with pytest.raises(ValueError):
        green_response_matrices([[0.3, 0.4]], sources)

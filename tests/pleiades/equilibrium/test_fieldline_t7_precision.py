"""Original full-core T7 calibration gates retained as failing regressions.

D2 successor: same domains, 40/80/160 spatial grids, 401 line vertices,
4e-9 affine tolerance, >3.4 refinement ratios, and .004 final accuracy.
"""
import numpy as np
import pytest
from scirel.fieldline import FieldLine, HelperFieldLine


@pytest.mark.parametrize("klass", [FieldLine, HelperFieldLine])
def test_t7_default_cubic_affine_gradient(klass):
    vertices = np.c_[np.linspace(1.1, 2.7, 9), np.full(9, -.2)]
    line = klass(.7, vertices, **({"npts": 73} if klass is FieldLine else {}))
    r, z = np.meshgrid(np.linspace(1, 2.8, 13), np.linspace(-.6, .2, 9))
    gr, gz = line.get_gradpsi(r, z, .3*np.ones_like(r), .8*np.ones_like(r))
    assert np.max(np.abs(gr - .8*line.verts[:, 0])) <= 4e-9
    assert np.max(np.abs(gz + .3*line.verts[:, 0])) <= 4e-9


def test_helper_gradient_honors_linear_method():
    vertices = np.c_[np.linspace(1.1, 2.7, 9), np.full(9, -.2)]
    line = HelperFieldLine(.7, vertices)
    r, z = np.meshgrid(np.linspace(1, 2.8, 13), np.linspace(-.6, .2, 9))
    br, bz = .3 + z*z, .8 + r*r
    actual = line.get_gradpsi(r, z, br, bz, method="linear")
    expected = (line.interpolate_onto(r, z, r*bz, method="linear"),
                -line.interpolate_onto(r, z, r*br, method="linear"))
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("klass", [FieldLine, HelperFieldLine])
def test_t7_field_curvature_spatial_refinement(klass):
    theta = np.linspace(.3, 2.6, 401)
    line = klass.__new__(klass)
    line.verts = np.c_[1.5+.4*np.cos(theta), .1+.4*np.sin(theta)]
    expected = -np.c_[np.cos(theta), np.sin(theta)]/.4
    errors = []
    for n in [40, 80, 160]:
        r, z = np.meshgrid(np.linspace(.7, 2.3, n), np.linspace(-.7, .9, n))
        br, bz = -(z-.1)/r, (r-1.5)/r
        value = line.get_kappa_n(r, z, br, bz, method="cubic")
        reverse = line.get_kappa_n(r, z, -br, -bz, method="cubic")
        if klass is HelperFieldLine:
            value, reverse = np.array(value).T, np.array(reverse).T
        np.testing.assert_allclose(reverse, value, rtol=0, atol=2e-13)
        errors.append(float(np.max(np.linalg.norm(value-expected, axis=1))))
    assert errors[1] < errors[0]/3.4, errors
    assert errors[2] < errors[1]/3.4, errors
    assert errors[-1] < .004, errors


@pytest.mark.parametrize("klass", [FieldLine, HelperFieldLine])
@pytest.mark.parametrize("scale", [1e-180, 1e180])
def test_curvature_constant_field_scale_does_not_create_a_null(klass, scale):
    r, z = np.meshgrid(np.linspace(1, 3, 5), np.linspace(-1, 1, 5))
    line = klass.__new__(klass)
    line.verts = np.c_[np.linspace(1.2, 2.8, 7), np.zeros(7)]
    got = line.get_kappa_n(r, z, np.full_like(r, scale), np.zeros_like(r))
    np.testing.assert_allclose(got, 0, rtol=0, atol=1e-13)

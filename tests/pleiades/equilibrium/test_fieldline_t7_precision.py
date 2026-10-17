"""Original full-core T7 calibration gates retained as failing regressions.

D2 successor: same domains, 40/80/160 spatial grids, 401 line vertices,
4e-9 affine tolerance, >3.4 refinement ratios, and .004 final accuracy.
"""
import numpy as np
import pytest
from scirel.geometry.fieldline import FieldLine, HelperFieldLine, _curve_curvature


def _scalar_curvature_oracle(vertices, br, bz):
    """Independent scalar-stencil oracle for the batched curvature path."""
    p = np.asarray(vertices, dtype=float)
    field = np.column_stack((br, bz))
    magnitude = np.hypot(field[:, 0], field[:, 1])
    ds = np.linalg.norm(np.diff(p, axis=0), axis=1)
    t = np.r_[0.0, np.cumsum(ds)]
    b = field / magnitude[:, None]
    values = np.column_stack((p, b))
    derivative = np.empty_like(values)
    width = min(5, len(p))
    for i in range(len(p)):
        start = min(max(i - width // 2, 0), len(p) - width)
        local = t[start:start + width] - t[i]
        scale = np.max(np.abs(local))
        x = local / scale
        moments = np.zeros(width)
        moments[1] = 1.0
        weights = np.linalg.solve(
            np.vander(x, N=width, increasing=True).T, moments
        ) / scale
        derivative[i] = weights @ (values[start:start + width] - values[i])
    tangent, db = derivative[:, :2], derivative[:, 2:]
    speed = np.linalg.norm(tangent, axis=1)
    direction = np.sign(np.sum(tangent * b, axis=1))
    return direction[:, None] * db / speed[:, None]


@pytest.mark.parametrize("n", [3, 4, 5, 17])
@pytest.mark.parametrize("reverse", [False, True])
def test_batched_curvature_matches_scalar_nonuniform_oracle(n, reverse):
    s = np.array([0.0, .03, .09, .22, .5, 1.0, 1.8, 2.9, 4.3, 5.2,
                  6.7, 8.1, 9.0, 10.4, 11.8, 13.1, 14.7])[:n]
    vertices = np.column_stack((s, .08 * s * s + .01 * np.cos(s)))
    tangent = np.column_stack((np.ones(n), .16 * s - .01 * np.sin(s)))
    if reverse:
        vertices = vertices[::-1]
        tangent = -tangent[::-1]
    expected = _scalar_curvature_oracle(vertices, tangent[:, 0], tangent[:, 1])
    actual = _curve_curvature(vertices, tangent[:, 0], tangent[:, 1])
    np.testing.assert_allclose(actual, expected, rtol=3e-13, atol=3e-12)


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

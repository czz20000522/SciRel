"""Independent analytic gates for spline, field-line and parsing contracts."""

import inspect
import numpy as np
import pytest

from scirel.geometry import basis
from scirel.geometry import fieldline as fl
from scirel.geometry import sampling as helpers


def test_clamped_unequal_knots_reproduces_cubic():
    x = np.array([0.0, 0.11, 0.39, 0.94, 1.8])
    p = lambda q: q**3 - 2 * q * q + 0.7 * q - 0.3
    dp = lambda q: 3 * q * q - 4 * q + 0.7
    fit = basis.ClampedCubicSpline(x, p(x), yp=[dp(x[0]), dp(x[-1])])
    q = np.linspace(x[0], x[-1], 73)
    np.testing.assert_allclose(fit(q), p(q), rtol=0, atol=2e-13)
    np.testing.assert_allclose(fit(q, deriv=1), dp(q), rtol=0, atol=2e-13)
    np.testing.assert_allclose(fit(q, deriv=2), 6 * q - 4, rtol=0, atol=2e-12)


def test_first_clamped_second_derivative_continuity_and_robin():
    x = np.array([0.13, 0.31, 0.8, 1.2, 1.9])
    y = np.array([0.2, -0.1, 0.4, 0.7, 0.3])
    fit = basis.FirstClampedCubicSpline(x, y, yp=0.6, m=2)
    slopes = np.asarray(fit.k).ravel()
    h = np.diff(x)
    dy = np.diff(y)
    # d2 at right of segment i and left of segment i+1, separately derived.
    left = (2 * slopes[:-1] + 4 * slopes[1:]) / h - 6 * dy / h**2
    right = 6 * dy / h**2 - (4 * slopes[:-1] + 2 * slopes[1:]) / h
    np.testing.assert_allclose(left[:-1], right[1:], rtol=0, atol=5e-12)
    assert abs(slopes[0] - 0.6) < 1e-14
    assert abs(left[-1] + slopes[-1] / x[-1] - 4 * y[-1] / x[-1] ** 2) < 5e-12


def test_first_clamped_spline_public_docstring_declares_contract():
    doc = inspect.getdoc(basis.FirstClampedCubicSpline)
    assert doc is not None
    assert "Parameters" in doc
    assert "Returns" in doc
    assert "Raises" in doc
    assert "left endpoint" in doc
    assert "physical qualification" in doc


@pytest.mark.parametrize("which", ["helper", "fltools"])
def test_line_derivative_uses_actual_nonuniform_arclength(which):
    klass = (
        fl.HelperFieldLine
        if which == "helper"
        else (fl.HelperFieldLine if which == "helper" else fl.FieldLine)
    )
    line = klass.__new__(klass)
    x = np.array([0.2, 0.27, 0.5, 0.82, 1.4, 1.9])
    line.verts = np.column_stack([x, np.zeros_like(x)])
    s = x - x[0]
    np.testing.assert_allclose(line.d_ds(3 * s * s - 2 * s + 0.4), 6 * s - 2, rtol=0, atol=3e-13)


@pytest.mark.parametrize("which", ["helper", "fltools"])
@pytest.mark.parametrize("reverse", [False, True])
def test_curvature_is_translation_and_field_reversal_invariant(which, reverse):
    klass = (
        fl.HelperFieldLine
        if which == "helper"
        else (fl.HelperFieldLine if which == "helper" else fl.FieldLine)
    )
    line = klass.__new__(klass)
    theta = np.linspace(0.23, 2.5, 257)
    radius = 0.7
    line.verts = np.column_stack([2.1 + radius * np.cos(theta), -0.3 + radius * np.sin(theta)])
    b = np.column_stack([-np.sin(theta), np.cos(theta)])
    if reverse:
        b = -b
    # Isolate curvature from scattered interpolation: return exact analytic b.
    # unit modB on a distinct artificial 1x1 input for source call identity.
    br, bz = np.array([[1.0]]), np.array([[0.0]])

    # Source normalizes these into new arrays, so choose by their value.
    def interp(R, Z, Q, method="cubic"):
        return b[:, 0] if np.all(Q == 1) else b[:, 1]

    line.interpolate_onto = interp
    got = line.get_kappa_n(np.array([[1.0]]), np.array([[0.0]]), br, bz)
    if which == "helper":
        got = np.column_stack(got)
    expected = -np.column_stack([np.cos(theta), np.sin(theta)]) / radius
    np.testing.assert_allclose(got, expected, rtol=0, atol=6e-5)


def test_parse_segment_preserves_default_and_requested_last_vertex():
    p = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]])  # clockwise
    np.testing.assert_array_equal(helpers.parse_segment(p), p)
    np.testing.assert_array_equal(helpers.parse_segment(p, end_coord=(1, 0)), p)


@pytest.mark.parametrize(
    ("clockwise", "expected"),
    [
        (True, np.array([[0.0, 1.0], [1.0, 1.0], [1.0, 0.0]])),
        (False, np.array([[0.0, 1.0], [0.0, 0.0], [1.0, 0.0]])),
    ],
)
def test_parse_segment_preserves_requested_start_direction_and_endpoint(clockwise, expected):
    p = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]])
    got = helpers.parse_segment(
        p,
        start_coord=(0.1, 0.9),
        end_coord=(0.9, 0.1),
        clockwise=clockwise,
    )
    np.testing.assert_array_equal(got, expected)


def test_parse_segment_keeps_first_nearest_vertex_on_ties():
    p = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0]])
    got = helpers.parse_segment(p, start_coord=(0.5, 0.5), end_coord=(0.5, 0.5))
    np.testing.assert_array_equal(got, p[:1])


def test_parse_segment_public_docstring_declares_contract():
    doc = inspect.getdoc(helpers.parse_segment)
    assert doc is not None
    assert "Parameters" in doc
    assert "Returns" in doc
    assert "Raises" in doc
    assert "terminal vertex" in doc


@pytest.mark.parametrize("endpoint", [0, 1])
@pytest.mark.parametrize("invalid_slope", [np.nan, np.inf, -np.inf])
def test_clamped_spline_rejects_nonfinite_endpoint_slopes(endpoint, invalid_slope):
    slopes = [0.0, 0.0]
    slopes[endpoint] = invalid_slope
    with pytest.raises(ValueError, match="yp.*finite"):
        basis.ClampedCubicSpline([0.0, 0.3, 1.0], [0.0, 0.2, 1.0], yp=slopes)


@pytest.mark.parametrize("invalid_coefficient", [np.nan, np.inf, -np.inf])
def test_second_clamped_spline_rejects_nonfinite_robin_coefficient(invalid_coefficient):
    with pytest.raises(ValueError, match="m.*finite"):
        basis.SecondClampedCubicSpline([0.0, 0.3, 1.0], [0.0, 0.2, 1.0], m=invalid_coefficient)

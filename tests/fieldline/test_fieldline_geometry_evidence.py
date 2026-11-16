"""Independent evidence for the field-line geometry primitives.

Assets: ``scirel.fieldline.arclength-derivative``, ``scirel.fieldline.boundary``,
``scirel.fieldline.fieldline`` and ``scirel.fieldline.helper-fieldline``.

The maintained tests pin shapes, ordering, repair behaviour and refinement
ratios against *the implementation's own* interpolated field.  They do not
confront a statement with an outside calculation.  This module does, on
analytic objects only:

* **Exact rational recomputation of the arclength stencil.**
  ``d_ds_arclength`` is a three-point Lagrange derivative on unequal nodes with
  one-sided quadratic stencils at the ends.  A polynomial of degree <= 2 is
  reproduced *exactly* by such a stencil, so for quadratic data the returned
  derivative must equal the analytic derivative to rounding; for cubic data the
  same stencil is only second-order, and the measured refinement ratio must be
  four per halving.  Both statements together pin the stencil's weights and its
  order without reference to the implementation's formula.
* **Exact reproduction of a linear field.**  ``get_gradpsi`` returns
  ``(R BZ, -R BR)`` interpolated onto the fitted vertices; with a constant
  field and a cubic separable grid the interpolation is exact, so the identity
  is decisive at the level of rounding.
* **Analytic curvature of a circle.**  For the flux
  ``psi = ((R - R0)^2 + Z^2) / 2`` every level set is a circle, so
  ``get_kappa_n_2`` must return a vector of magnitude ``1/r`` pointing at the
  centre on a vertex ring of radius ``r``.
* **Analytic length and boundary geometry.**  A circle of radius ``a`` has
  length ``2 pi a``, and a ``Boundary`` fitted to a sampled circle must return
  to radius ``a`` at its 200 stored samples.  Both are measured over halvings
  of the vertex spacing, and the measured ratios are reported.

Order claims are made **only for the configurations measured here**: a periodic
quadratic spline on a smooth closed circle and a nonperiodic quadratic spline on
a smooth boundary.  No general order statement is made.

Budgets, fixed before the comparison ran: eight roundings (``8 eps``) for a
statement that is exact in exact arithmetic; a measured ratio of at least 3.0
per halving for a second-order quantity and at least 8.0 for the spline
interpolation of a circle (which is O(h^3) for a quadratic fit on smooth data);
and a final relative error below ``1e-6`` on the finest measured sampling.  The
sampling floor of ``get_length`` is the polyline of the fitted samples: with
``npts = 4000`` over a circumference of about ``2 pi`` its own length error is
about ``1e-7``, which is why the last measured ratio is smaller than the first
two.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel.geometry import Boundary, FieldLine, HelperFieldLine
from scirel.geometry.fieldline import d_ds_arclength

EXACT_BUDGET = 8 * 2**-52
SECOND_ORDER_RATIO = 3.0
SPLINE_RATIO = 8.0
FINAL_RELATIVE = 1e-6
CIRCUMFERENCE_NPTS = 4000


def _circle(vertices, radius=1.0, centre=(0.0, 0.0)):
    """Return ``vertices`` equally spaced points of a closed circle.

    The last point is set equal to the first by assignment rather than by
    evaluating ``2 pi``: ``sin(2 pi)`` is not exactly zero in binary64, and
    the documented ``is_closed`` test is an exact equality, so the closure has
    to be built with the same exact equality.
    """
    angles = np.linspace(0.0, 2 * np.pi, vertices)
    points = np.column_stack(
        (centre[0] + radius * np.cos(angles), centre[1] + radius * np.sin(angles))
    )
    points[-1] = points[0]
    return points


def _arc(vertices, radius, centre, start, stop):
    """Return an open circular arc."""
    angles = np.linspace(start, stop, vertices)
    return np.column_stack(
        (centre[0] + radius * np.cos(angles), centre[1] + radius * np.sin(angles))
    )


# ------------------------------------------------------- arclength derivative
def test_derivative_is_exact_for_polynomials_of_degree_two():
    """Exact recomputation: a three-point stencil reproduces a quadratic."""
    x = np.array([0.0, 0.3, 1.1, 1.9, 2.4, 3.3])
    points = np.column_stack((x, np.zeros_like(x)))
    got = d_ds_arclength(points, x**2)
    want = 2.0 * x
    scale = np.maximum(np.abs(want), 1.0)
    assert np.all(np.abs(got - want) <= EXACT_BUDGET * scale), (got, want)
    # A linear function is the same statement with the endpoints included.
    np.testing.assert_allclose(
        d_ds_arclength(points, 3.0 * x + 1.0), np.full(x.size, 3.0), rtol=EXACT_BUDGET, atol=0.0
    )
    # A constant, which also pins that the stencil weights sum to zero.  The
    # rounding of that sum scales with the magnitude of the data, so the bound
    # is the same eight roundings of ``max|value|`` rather than of one.
    constant = np.full(x.size, 5.0)
    np.testing.assert_allclose(
        d_ds_arclength(points, constant),
        0.0,
        rtol=0.0,
        atol=EXACT_BUDGET * np.max(np.abs(constant)),
    )


def test_derivative_is_second_order_on_cubic_data():
    """Measured order: the same stencil is O(h^2) for a cubic, ratio four."""
    errors = []
    for count in (9, 17, 33, 65):
        x = np.linspace(0.0, 1.0, count)
        points = np.column_stack((x, np.zeros_like(x)))
        errors.append(np.max(np.abs(d_ds_arclength(points, x**3) - 3.0 * x**2)))
    ratios = [errors[index] / errors[index + 1] for index in range(len(errors) - 1)]
    assert all(ratio > SECOND_ORDER_RATIO for ratio in ratios), (ratios, errors)
    # The stencil is not accidentally exact for cubics: the first error is far
    # above the rounding level of the data.
    assert errors[0] > 1e-3


def test_derivative_uses_the_true_arclength_not_the_index():
    """A nonuniform straight path differentiates with respect to arclength."""
    x = np.array([0.0, 0.05, 0.6, 0.7, 1.9])
    points = np.column_stack((x, np.zeros_like(x)))
    # x as a function of arclength is the identity on a straight segment.
    np.testing.assert_allclose(
        d_ds_arclength(points, x), np.ones(x.size), rtol=EXACT_BUDGET, atol=0.0
    )


def test_derivative_rejection_channels():
    """Failure matrix: shapes, sample count, nonfinite values, duplicates."""
    good = np.array([[0.0, 0.0], [0.5, 0.0], [1.0, 0.0]])
    values = np.array([0.0, 1.0, 2.0])
    with pytest.raises(ValueError, match=r"vertices must be \(N,2\)"):
        d_ds_arclength(np.zeros((3, 3)), values)
    with pytest.raises(ValueError, match=r"vertices must be \(N,2\)"):
        d_ds_arclength(good[:2], values[:2])
    with pytest.raises(ValueError, match="vertices and values must be finite"):
        d_ds_arclength(np.array([[0.0, 0.0], [0.5, np.nan], [1.0, 0.0]]), values)
    with pytest.raises(ValueError, match="adjacent vertices must be distinct"):
        d_ds_arclength(np.array([[0.0, 0.0], [0.0, 0.0], [1.0, 0.0]]), values)


# ------------------------------------------------------------------- boundary
def test_boundary_fit_reproduces_its_own_nodes_and_the_circle():
    """Analytic geometry: endpoints exactly, circle radius with measured ratios."""
    errors = []
    for count in (17, 33, 65, 129):
        boundary = Boundary(_circle(count))
        assert boundary.verts.shape == (200, 2)
        first = boundary.verts[0]
        last = boundary.verts[-1]
        np.testing.assert_allclose(first, [1.0, 0.0], rtol=0.0, atol=EXACT_BUDGET)
        np.testing.assert_allclose(
            last, [np.cos(2 * np.pi), np.sin(2 * np.pi)], rtol=0.0, atol=1e-12
        )
        radii = np.hypot(boundary.verts[:, 0], boundary.verts[:, 1])
        errors.append(np.max(np.abs(radii - 1.0)))
    ratios = [errors[index] / errors[index + 1] for index in range(len(errors) - 1)]
    assert all(ratio > SPLINE_RATIO for ratio in ratios), (ratios, errors)
    assert errors[-1] < FINAL_RELATIVE, errors[-1]
    # The interpolation of a scalar parameter returns one point, not a pair of
    # arrays: the fitted representation is used, not a re-fit.
    single = Boundary(_circle(17))
    x_value, y_value = (float(value) for value in single.interpolate(0.0))
    assert abs(x_value - 1.0) <= EXACT_BUDGET
    assert abs(y_value) <= EXACT_BUDGET


# --------------------------------------------------------- line length, curves
def test_closed_circle_length_converges_to_the_analytic_circumference():
    """Analytic length: 2 pi a with a measured refinement ratio."""
    errors = []
    for count in (17, 33, 65, 129):
        line = FieldLine(0.1, _circle(count), npts=CIRCUMFERENCE_NPTS)
        assert line.is_closed()
        errors.append(abs(line.get_length() - 2 * np.pi))
    ratios = [errors[index] / errors[index + 1] for index in range(len(errors) - 1)]
    # The first two halvings are still limited by the vertex spacing; the last
    # is limited by the 4000-point sampling floor declared in the module.
    assert all(ratio > SECOND_ORDER_RATIO for ratio in ratios[:2]), (ratios, errors)
    assert errors[-1] / (2 * np.pi) < FINAL_RELATIVE, errors[-1]
    # The length is not the vertex polyline length of the input: the fit adds
    # samples, so the two differ.
    line = FieldLine(0.1, _circle(17), npts=CIRCUMFERENCE_NPTS)
    input_polyline = np.sum(np.linalg.norm(np.diff(_circle(17), axis=0), axis=1))
    assert abs(line.get_length() - input_polyline) > 0.0


def test_flux_gradient_curvature_of_a_circle_is_analytic():
    """Analytic curvature: a quadratic flux has circular level sets, kappa = 1/r."""
    centre, radius = 1.2, 0.4
    grid_r, grid_z = np.meshgrid(np.linspace(0.3, 2.2, 81), np.linspace(-1.2, 1.2, 61))
    flux = 0.5 * ((grid_r - centre) ** 2 + grid_z**2)
    line = FieldLine(0.2, _arc(49, radius, (centre, 0.0), 0.3, 2.6))
    curvature = line.get_kappa_n_2(grid_r, grid_z, flux)
    magnitude = np.linalg.norm(curvature, axis=1)
    assert np.all(np.abs(magnitude - 1.0 / radius) <= 0.01 / radius), (
        float(np.max(np.abs(magnitude - 1.0 / radius))),
    )
    # The direction points at the centre: the projection of the curvature
    # vector onto the outward radial direction is negative on every vertex,
    # whatever the angular position of the vertex.
    outward = line.verts - np.array([centre, 0.0])
    assert np.all(np.sum(curvature * outward, axis=1) < 0.0)


def test_linear_field_gradient_identity_is_exact():
    """Exact reproduction: a constant field interpolates exactly onto the line."""
    line = FieldLine(0.2, _arc(49, 0.4, (1.2, 0.0), 0.3, 2.6))
    grid_r, grid_z = np.meshgrid(np.linspace(0.3, 2.2, 81), np.linspace(-1.2, 1.2, 61))
    grad_r, grad_z = line.get_gradpsi(
        grid_r, grid_z, 0.3 * np.ones_like(grid_r), 0.8 * np.ones_like(grid_r)
    )
    radius = line.verts[:, 0]
    scale = np.maximum(np.abs(0.8 * radius), 1.0)
    assert np.all(np.abs(grad_r - 0.8 * radius) <= EXACT_BUDGET * scale)
    assert np.all(np.abs(grad_z + 0.3 * radius) <= EXACT_BUDGET * scale)


def test_curvature_of_a_constant_field_is_zero():
    """Boundary case: a straight field has no curvature along any line."""
    line = FieldLine(0.2, np.array([[0.2, 0.0], [0.7, 0.0], [1.2, 0.0]]))
    grid_r, grid_z = np.meshgrid(np.linspace(0.1, 1.4, 9), np.linspace(-0.3, 0.3, 9))
    curvature = line.get_kappa_n(grid_r, grid_z, np.ones_like(grid_r), np.zeros_like(grid_r))
    np.testing.assert_allclose(curvature, 0.0, rtol=0.0, atol=1e-10)


# ---------------------------------------------------------------- intersections
def test_intersection_lands_on_the_boundary():
    """Analytic crossing: the returned parameter reproduces the boundary point."""
    line = FieldLine(0.2, np.array([[0.2, 0.0], [1.5, 0.0], [2.8, 0.0]]))
    vertical = Boundary(np.column_stack((np.full(7, 1.0), np.linspace(-1.0, 1.0, 7))))
    parameter = line.intersection(vertical)
    radius, height = line.interpolate(parameter)
    # The crossing is at R = 1 exactly (the boundary is a straight vertical
    # line), so the residual is a statement about the returned parameter.
    assert float(radius) == pytest.approx(1.0, abs=1e-9)
    assert float(height) == pytest.approx(0.0, abs=1e-9)
    # Bounding the line with two crossings samples between them, and the
    # stored parameters are ordered.
    line.apply_boundary(
        vertical, Boundary(np.column_stack((np.full(7, 2.0), np.linspace(-1.0, 1.0, 7))))
    )
    assert line.ubound1 > line.ubound0
    bounded = np.asarray(line.get_bounded_fl(11))
    assert bounded.shape == (2, 11)
    np.testing.assert_allclose(bounded[0][[0, -1]], [1.0, 2.0], atol=1e-9)
    with pytest.raises(ValueError, match="no intersection found"):
        line.intersection(Boundary(np.column_stack((np.full(7, 9.0), np.linspace(-1.0, 1.0, 7)))))


def test_helper_line_matches_the_same_analytic_facts():
    """The helper class reproduces the derivative and the circle length."""
    line = HelperFieldLine(0.1, _circle(65))
    assert line.is_closed()
    assert line.verts.shape == (1000, 2)
    # On a straight segment the arclength derivative of the coordinate is one.
    straight = HelperFieldLine(0.1, np.array([[0.0, 0.0], [0.5, 0.0], [1.0, 0.0]]))
    np.testing.assert_allclose(straight.d_ds(straight.verts[:, 0]), 1.0, rtol=0.0, atol=1e-12)
    # On the circle the coordinate R = a cos(theta) satisfies dR/ds = -sin(theta)
    # with s = a theta, so the fitted derivative must follow that closed form.
    # The bound covers the polyline sampling of the fitted curve (spacing
    # 2 pi / 1000 gives a local chord-slope error of about 6e-6) and the
    # quadratic fit of the 65-node circle, not an arbitrary tolerance.
    radius = line.verts[:, 0]
    height = line.verts[:, 1]
    angle = np.arctan2(height, radius)
    np.testing.assert_allclose(line.d_ds(radius), -np.sin(angle), rtol=0.0, atol=1e-3)
    # The helper's own default sampling is coarser, so the length statement is
    # made against the same analytic circumference with its own bound.
    helper_length = line.get_length()
    assert abs(helper_length - 2 * np.pi) / (2 * np.pi) < 1e-3

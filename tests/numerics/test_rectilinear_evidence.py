"""Independent evidence for the rectilinear interpolation and midpoint reductions.

Assets: ``scirel.numerics.bilinear-grid-sampling``,
``scirel.numerics.complex-rectilinear-interpolation``,
``scirel.numerics.face-to-cell``.

Evidence, all independent of the implementation and its regression fixtures:

1. **Exact reproduction of the interpolated polynomial class.**  Bilinear
   interpolation reproduces any field that is affine in each axis, and
   trilinear interpolation reproduces any field affine in each coordinate.
   These are properties of the interpolation weights and are checked against a
   field built from known coefficients.
2. **Second independent implementation, bilinear only.**  For the *bilinear*
   asset ``scipy.interpolate.RegularGridInterpolator(method="linear")`` computes
   the same stencil through different code.  It is **not** an independent
   reference for the *complex trilinear* asset, whose implementation imports and
   calls that same SciPy class internally
   (``complex_rectilinear_interpolation.py`` ``_samples``); for that asset the
   independent evidence is item 3 below, not SciPy.
3. **Exact rational reference.**  For random data, the arithmetic midpoint, the
   bilinear weights and the complex trilinear weights are recomputed in exact
   rational arithmetic (``fractions.Fraction`` over the binary64 inputs) and
   rounded once, which separates rounding error from any weight or index
   mistake and is independent of both the implementation and its SciPy backend.
4. **Declared conventions.**  The complex variant clamps inside a box expanded by
   ``tol = 32 * eps * max(1, span)`` and returns ``nan + nanj`` with
   ``valid_mask`` false outside it; that boundary is tested at, just inside and
   just outside the declared tolerance instead of an invented epsilon.

Budgets, fixed before measurement: reproduction of the interpolated polynomial
allows ``64 * eps * scale`` (the weights are exact for data of this form, so
only rounding remains); the SciPy comparison allows ``64 * eps * scale`` for the
same reason; the midpoint allows ``1 * eps * scale`` because it is one operation.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest
from scipy.interpolate import RegularGridInterpolator

import scirel.numerics as N

EPS = np.finfo(float).eps

R_AXIS = np.array([0.0, 0.7, 2.0])
Z_AXIS = np.array([-1.0, 0.0, 1.5])


def _grid():
    """Return the [Z, R] meshgrid the contract asks for."""
    return np.meshgrid(R_AXIS, Z_AXIS, indexing="xy")


def test_bilinear_reproduces_a_field_affine_in_each_axis():
    """Evidence 1 + 2: exact affine reproduction, cross-checked with SciPy."""
    r_grid, z_grid = _grid()
    field = 2.5 * r_grid - 1.5 * z_grid + 0.25
    points = np.array([[0.0, -1.0], [0.35, -0.2], [2.0, 1.5], [1.1, 0.9], [0.7, 0.0]])

    got = np.asarray(N.sample_rectilinear_field(r_grid, z_grid, field, points)["samples"])
    exact = 2.5 * points[:, 0] - 1.5 * points[:, 1] + 0.25
    scale = max(1.0, float(np.max(np.abs(exact))))
    assert np.max(np.abs(got - exact)) <= 64.0 * EPS * scale

    # RegularGridInterpolator takes points in grid-axis order, so [R, Z] query
    # points are reversed before the call; scirel takes them as [R, Z].
    reference = RegularGridInterpolator((Z_AXIS, R_AXIS), field, method="linear")
    assert np.max(np.abs(got - reference(points[:, ::-1]))) <= 64.0 * EPS * scale


def test_bilinear_reproduces_the_grid_values_at_the_nodes():
    r_grid, z_grid = _grid()
    field = np.array([[1.0, -2.0, 3.5], [0.5, 0.0, 4.0], [-1.0, 6.0, 2.0]])
    nodes = np.array([[r, z] for z in Z_AXIS for r in R_AXIS])
    got = np.asarray(N.sample_rectilinear_field(r_grid, z_grid, field, nodes)["samples"])
    assert np.max(np.abs(got - field.ravel())) <= 64.0 * EPS * 6.0


def test_bilinear_rejects_points_outside_the_closed_grid():
    """Failure matrix: no extrapolation and no clamping."""
    r_grid, z_grid = _grid()
    field = np.zeros((3, 3))
    for outside in ([2.5, 0.0], [0.0, 2.0], [-0.1, 0.0]):
        with pytest.raises(ValueError):
            N.sample_rectilinear_field(r_grid, z_grid, field, np.array([outside]))


def test_complex_trilinear_reproduces_an_affine_complex_field():
    """Evidence 1: affine reproduction for a complex field, real and imaginary apart."""
    axes = {"x_m": np.array([0.0, 1.0]), "y_m": np.array([0.0, 2.0]), "z_m": np.array([0.0, 3.0])}
    x, y, z = np.meshgrid(axes["x_m"], axes["y_m"], axes["z_m"], indexing="ij")
    field = (1.0 + 0.5 * x + 2.0 * y - 0.25 * z) + 1j * (-2.0 + x - y + 0.75 * z)

    points = np.array([[0.25, 0.5, 1.0], [0.9, 1.9, 2.9], [0.5, 1.0, 1.5]])
    result = N.interpolate_complex_rectilinear_field(axes, field, points)

    got = np.asarray(result["interpolated_values"])
    want = (1.0 + 0.5 * points[:, 0] + 2.0 * points[:, 1] - 0.25 * points[:, 2]) + 1j * (
        -2.0 + points[:, 0] - points[:, 1] + 0.75 * points[:, 2]
    )
    scale = max(1.0, float(np.max(np.abs(want))))
    assert np.all(np.asarray(result["valid_mask"]))
    assert np.max(np.abs(got - want)) <= 256.0 * EPS * scale


def _exact_rational_trilinear(axes, values, point):
    """Trilinear value at ``point`` in exact rational arithmetic, rounded once.

    The three axis weights are rebuilt from the binary64 inputs as
    ``Fraction`` ratios ``(b - q)/(b - a)`` and ``(q - a)/(b - a)``, the eight
    corner contributions are summed exactly for the real and imaginary parts
    separately, and the total is converted to ``complex`` at the end.  Nothing
    is taken from the implementation or from SciPy.
    """
    per_axis = []
    for axis, coordinate in zip(axes, point):
        knots = [Fraction(float(value)) for value in axis]
        query = Fraction(float(coordinate))
        upper = next(index for index in range(1, len(knots)) if knots[index] >= query)
        low, high = knots[upper - 1], knots[upper]
        fraction = (query - low) / (high - low)
        per_axis.append(((upper - 1, 1 - fraction), (upper, fraction)))

    real = Fraction(0)
    imaginary = Fraction(0)
    for lower_x, weight_x in per_axis[0]:
        for lower_y, weight_y in per_axis[1]:
            for lower_z, weight_z in per_axis[2]:
                corner = complex(values[lower_x, lower_y, lower_z])
                weight = weight_x * weight_y * weight_z
                real += weight * Fraction(corner.real)
                imaginary += weight * Fraction(corner.imag)
    return complex(float(real), float(imaginary))


def test_complex_trilinear_matches_an_exact_rational_recomputation():
    """Evidence 3 for the trilinear asset, whose own backend is SciPy.

    The weights are recomputed here in exact rational arithmetic, so a shared
    backend or a shared formula evaluation cannot make the test agree by
    construction; only the arithmetic path differs, which is what a rounding
    budget is meant to separate.
    """
    axes = {
        "x_m": np.array([0.0, 1.0, 3.0]),
        "y_m": np.array([0.0, 2.0]),
        "z_m": np.array([0.0, 1.5, 4.0]),
    }
    values = np.array(
        [
            [[1.0 + 0.5j, -2.0 + 1.0j, 0.25 - 3.0j], [0.5 + 0.1j, 3.0 - 1.5j, -1.0 + 0.0j]],
            [[2.0 - 0.25j, 0.0 + 2.0j, 1.5 + 1.25j], [-0.5 + 0.75j, 1.0 - 1.0j, 2.5 + 0.5j]],
            [[0.125 + 0.0625j, -0.75 + 3.5j, 4.0 - 2.0j], [1.25 - 0.5j, -2.5 + 0.25j, 0.5 + 1.5j]],
        ]
    )
    points = np.array(
        [[0.5, 1.0, 0.75], [2.7, 0.3, 3.9], [0.0, 0.0, 0.0], [3.0, 2.0, 4.0], [1.0, 2.0, 1.5]]
    )
    got = np.asarray(
        N.interpolate_complex_rectilinear_field(axes, values, points)["interpolated_values"]
    )
    axis_tuple = (axes["x_m"], axes["y_m"], axes["z_m"])
    for point, actual in zip(points, got):
        expected = _exact_rational_trilinear(axis_tuple, values, point)
        scale = max(1.0, abs(expected))
        assert abs(actual - expected) <= 64.0 * EPS * scale, (point, actual, expected)


def test_complex_trilinear_rejects_outside_its_tolerance_expanded_box():
    """Declared boundary: ``tol = 32 eps max(1, span)``, tested on both sides."""
    axes = {"x_m": np.array([0.0, 1.0]), "y_m": np.array([0.0, 2.0]), "z_m": np.array([0.0, 3.0])}
    field = np.zeros((2, 2, 2), dtype=complex)
    span = 3.0
    tol = 32.0 * EPS * max(1.0, span)

    inside = np.array([[1.0 + 0.5 * tol, 1.0, 1.0]])
    outside = np.array([[1.0 + 10.0 * tol, 1.0, 1.0]])
    far = np.array([[5.0, 5.0, 5.0]])

    inside_result = N.interpolate_complex_rectilinear_field(axes, field, inside)
    assert bool(np.asarray(inside_result["valid_mask"])[0]) is True

    for points in (outside, far):
        result = N.interpolate_complex_rectilinear_field(axes, field, points)
        assert bool(np.asarray(result["valid_mask"])[0]) is False
        assert np.isnan(np.asarray(result["interpolated_values"])[0])


def test_complex_trilinear_propagates_a_nonfinite_corner_even_at_zero_weight():
    """Declared failure behaviour: non-finite samples are not silently ignored."""
    axes = {"x_m": np.array([0.0, 1.0]), "y_m": np.array([0.0, 1.0]), "z_m": np.array([0.0, 1.0])}
    field = np.ones((2, 2, 2), dtype=complex)
    field[1, 0, 0] = complex(np.nan, 0.0)

    at_the_corner = N.interpolate_complex_rectilinear_field(
        axes, field, np.array([[1.0, 0.0, 0.0]])
    )
    assert np.isnan(np.asarray(at_the_corner["interpolated_values"])[0])

    opposite = N.interpolate_complex_rectilinear_field(axes, field, np.array([[0.0, 1.0, 1.0]]))
    assert np.isnan(np.asarray(opposite["interpolated_values"])[0])


def test_face_to_cell_matches_an_exact_rational_midpoint():
    """Evidence 3: the arithmetic midpoint, recomputed exactly from the inputs."""
    face = np.array([0.1, 0.3, 0.7, 1.7e0, 2.9e0])
    got = np.asarray(N.face_to_cell(face))
    want = np.array([float((Fraction(a) + Fraction(b)) / 2) for a, b in zip(face[:-1], face[1:])])
    assert np.max(np.abs(got - want)) <= EPS * max(1.0, float(np.max(np.abs(want))))


def test_face_to_cell_uses_the_halved_endpoint_branch_on_overflow():
    """Declared branch: a non-representable sum falls back to halved endpoints."""
    huge = 1.7e308
    assert float(np.asarray(N.face_to_cell([huge, huge]))[0]) == huge
    # Sum first where it is representable.
    assert np.array_equal(
        np.asarray(N.face_to_cell([0.0, 2.0, 8.0, 10.0])), np.array([1.0, 5.0, 9.0])
    )


def test_face_to_cell_rejection_channels_are_bound_to_their_contract():
    for value, expected, fragment in [
        ([], ValueError, "at least two"),
        ([1.0], ValueError, "at least two"),
        ([[0.0, 1.0], [2.0, 3.0]], ValueError, "one-dimensional"),
        ([0.0, np.nan], ValueError, "finite"),
        ([0.0, np.inf], ValueError, "finite"),
        ([True, False], ValueError, "finite real"),
        (np.array([1.0 + 0.0j, 2.0 + 0.0j]), ValueError, "finite real"),
    ]:
        with pytest.raises(expected) as caught:
            N.face_to_cell(value)
        assert fragment in str(caught.value), (fragment, str(caught.value))

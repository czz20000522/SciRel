"""Independent evidence for the basis factory and the design-matrix builder.

Assets: ``scirel.numerics.build-basis``, ``scirel.numerics.basis-matrix``.

Evidence sources, independent of the implementations and their fixtures:

1. **Closed-form design matrix.**  For the polynomial selection the contract
   states ascending-power columns, so the design matrix has the analytic Vandermonde
   form ``A[i, j] = x_i ** j``.  That is written out directly here rather than
   reproduced from the implementation.
2. **Partition of unity from the boundary data.**  Cardinal splines sum to the
   constant one exactly when the constant satisfies the family's boundary
   conditions: it does for the natural family (zero second derivative), for the
   clamped family at zero end slopes, and for the left-clamped family at ``m = 0``
   (``f'' + f'/x = 0`` for a constant).  The sum is therefore an analytic
   identity for those three families and is tested as one.
3. **Declared structural consequence of the origin row.**  The second-clamped
   default basis fixes ``y_data[0] = 0``, so it carries ``n_knots - 1`` columns and
   is an affine rather than a linear family; its columns must not sum to one.  Both
   facts are consequences of the contract, not of the code.
4. **Declared zero-fill convention** for spline selections outside the knot
   interval, tested at the boundary and one representable step outside it.

Budgets: the Vandermonde identity is exact up to rounding, so ``64 * eps * scale``;
the partition of unity allows ``1024 * eps`` because it is a sum of five splines
each of which is itself computed through a solve; the affine-family statement is a
structural inequality with no tolerance.
"""

from __future__ import annotations

import numpy as np
import pytest

import scirel.numerics as N
from scirel.numerics import ClampedCubicSpline

EPS = np.finfo(float).eps

QUERY = np.linspace(0.05, 0.95, 7)


@pytest.mark.parametrize("degree", [1, 2, 3, 4])
def test_polynomial_design_matrix_is_the_analytic_vandermonde_matrix(degree):
    """Evidence 1: columns are exactly ``x**0 .. x**(degree-1)``."""
    matrix = np.asarray(N.BasisMatrix("poly", poly_deg=degree)(QUERY))
    assert matrix.shape == (QUERY.size, degree)
    vandermonde = np.vstack([QUERY**power for power in range(degree)]).T
    assert np.max(np.abs(matrix - vandermonde)) <= 64.0 * EPS * max(
        1.0, float(np.max(np.abs(vandermonde)))
    )


@pytest.mark.parametrize("degree", [1, 2, 3, 4])
def test_build_basis_polynomial_members_are_the_ascending_powers(degree):
    """Evidence 1 for the factory: member ``j`` evaluates to ``x**j``."""
    members = N.build_basis("poly", poly_deg=degree)
    assert len(members) == degree
    for power, member in enumerate(members):
        values = np.asarray(member(QUERY))
        assert np.max(np.abs(values - QUERY**power)) <= 64.0 * EPS * max(
            1.0, float(np.max(np.abs(QUERY**power)))
        )


@pytest.mark.parametrize(
    "selection",
    ["natural_cubic_spline", "clamped_cubic_spline", "clamped_cubic_spline1"],
)
def test_cardinal_spline_bases_partition_unity(selection):
    """Evidence 2: the sum of the cardinal splines is the constant one."""
    members = N.build_basis(selection, n_knots=5)
    total = sum(np.asarray(member(QUERY), dtype=float) for member in members)
    assert np.max(np.abs(total - 1.0)) <= 1024.0 * EPS * len(members)


def test_second_clamped_default_basis_is_a_linear_subspace():
    """Evidence 3: linearity is homogeneity plus superposition, not partition of unity.

    An earlier version of this file argued "the constant function is absent, so the
    family is affine".  That inference is wrong: a subspace that omits the constant
    function is still a subspace.  The criterion is checked directly on the spline
    class, and the missing constant is reported only as the reason the columns do
    not sum to one.
    """
    x = np.array([0.0, 0.3, 1.0])
    first = np.array([0.0, 0.2, 0.5])
    second = np.array([0.0, 0.3, 0.2])
    query = np.linspace(0.0, 1.0, 7)

    scaled = np.asarray(N.SecondClampedCubicSpline(x, 2.0 * first, m=1.0)(query), dtype=float)
    plain = np.asarray(N.SecondClampedCubicSpline(x, first, m=1.0)(query), dtype=float)
    assert np.max(np.abs(scaled - 2.0 * plain)) <= 64.0 * EPS

    summed = np.asarray(N.SecondClampedCubicSpline(x, first + second, m=1.0)(query), dtype=float)
    left = np.asarray(N.SecondClampedCubicSpline(x, first, m=1.0)(query), dtype=float)
    right = np.asarray(N.SecondClampedCubicSpline(x, second, m=1.0)(query), dtype=float)
    assert np.max(np.abs(summed - (left + right))) <= 64.0 * EPS

    # The structural consequence of the fixed origin ordinate: one fewer column and
    # no partition of unity, because the constant function is not in the span.
    members = N.build_basis("clamped_cubic_spline2", n_knots=5)
    assert len(members) == 4  # n_knots - 1
    total = sum(np.asarray(member(QUERY), dtype=float) for member in members)
    assert np.max(np.abs(total - 1.0)) > 1e-2


def test_clamped_family_is_linear_at_zero_slopes_and_affine_at_a_fixed_nonzero_slope():
    """The plain clamped family's linearity depends on the endpoint slope being zero.

    With ``yp = (0, 0)`` the map from ordinates to spline is linear, which is why the
    basis builder accepts only that value.  With a fixed nonzero ``yp`` the fixed
    slope contributes a constant term, so the map is affine and doubling the
    ordinates does not double the spline; the builder rejects that value.
    """
    x = np.array([0.0, 0.3, 1.0])
    y = np.array([0.0, 0.2, 0.5])
    query = np.linspace(0.0, 1.0, 7)

    zero_slope_scaled = np.asarray(ClampedCubicSpline(x, 2.0 * y, yp=(0.0, 0.0))(query), dtype=float)
    zero_slope_plain = np.asarray(ClampedCubicSpline(x, y, yp=(0.0, 0.0))(query), dtype=float)
    assert np.max(np.abs(zero_slope_scaled - 2.0 * zero_slope_plain)) <= 64.0 * EPS

    fixed_slope_scaled = np.asarray(ClampedCubicSpline(x, 2.0 * y, yp=(1.0, 0.5))(query), dtype=float)
    fixed_slope_plain = np.asarray(ClampedCubicSpline(x, y, yp=(1.0, 0.5))(query), dtype=float)
    assert np.max(np.abs(fixed_slope_scaled - 2.0 * fixed_slope_plain)) > 1e-3

    with pytest.raises(ValueError):
        N.build_basis("clamped_cubic_spline", yp=(1.0, 1.0))


def test_spline_design_matrix_columns_follow_the_member_order():
    """The matrix and the factory agree column by column."""
    members = N.build_basis("natural_cubic_spline", n_knots=5)
    matrix = np.asarray(N.BasisMatrix("natural_cubic_spline", n_knots=5)(QUERY))
    assert matrix.shape == (QUERY.size, len(members))
    for index, member in enumerate(members):
        assert (
            np.max(np.abs(matrix[:, index] - np.asarray(member(QUERY), dtype=float)))
            <= 64.0 * EPS * 16.0
        )


def test_spline_selections_zero_fill_outside_the_knot_interval():
    """Declared convention, tested on both boundary sides."""
    members = N.build_basis("natural_cubic_spline", n_knots=5)
    below = np.nextafter(0.0, -1.0)
    above = np.nextafter(1.0, 2.0)
    outside = np.array([-1.0, below, above, 2.0])
    for member in members:
        assert np.array_equal(np.asarray(member(outside), dtype=float), np.zeros(outside.size))
    assert float(np.asarray(members[0](np.array([np.nan])))[0]) == 0.0


def test_basis_matrix_rejects_an_unknown_selection():
    """Failure matrix: the unregistered-selector channel, pinned as observed.

    The contract already declares ``KeyError`` for an unregistered selector, so
    the type matches the contract; what does not match
    ``skills/development/scirel-code-style/references/api-spec.md`` (invalid
    input -> ``ValueError``) is the contract itself.  The correction is tracked in
    ``tickets/convention/T-2026-0002.md``; this test pins the observed type so a
    silent change in either direction is visible, and must be updated together
    with that ticket's resolution.
    """
    with pytest.raises(KeyError):
        N.build_basis("quartic")


def test_basis_matrix_rejects_nonzero_clamped_slopes_and_short_knots():
    """Declared rejections that do match the contract."""
    with pytest.raises(ValueError) as caught:
        N.build_basis("clamped_cubic_spline", yp=(1.0, 1.0))
    assert "yp=0" in str(caught.value)

    with pytest.raises(ValueError) as caught:
        N.build_basis("natural_cubic_spline", n_knots=2)
    assert "at least 3" in str(caught.value)


def test_poly_coeff_control_shape_deviations_are_recorded():
    """A mis-shaped ``coeffs`` control fails outside the declared channel.

    ``AttributeError`` (plain list) and ``IndexError`` (1-D array) are neither
    ``ValueError`` nor ``TypeError``, so they are undocumented leaks rather than
    promises; ``coeffs`` is array_like in the api-spec and a list should be
    accepted or rejected with ``ValueError``.  The correction is tracked in
    ``tickets/convention/T-2026-0002.md``; the accepted form today is a 2-D
    ``(poly_deg, k)`` array.  This test pins the observed behaviour and must be
    updated together with that ticket's resolution.
    """
    with pytest.raises(AttributeError):
        N.build_basis("poly", poly_deg=2, coeffs=[1.0, 0.0])
    with pytest.raises(IndexError):
        N.build_basis("poly", poly_deg=2, coeffs=np.array([2.0, 3.0]))

    members = N.build_basis("poly", poly_deg=2, coeffs=np.array([[2.0], [3.0]]))
    assert len(members) == 1
    points = np.array([0.0, 0.5, 1.0])
    values = np.asarray(members[0](points))
    assert np.max(np.abs(values - (2.0 + 3.0 * points))) <= 64.0 * EPS * 6.0

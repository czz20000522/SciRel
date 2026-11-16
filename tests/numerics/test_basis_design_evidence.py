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

EPS = np.finfo(float).eps

QUERY = np.linspace(0.05, 0.95, 7)


@pytest.mark.parametrize("degree", [1, 2, 3, 4])
def test_polynomial_design_matrix_is_the_analytic_vandermonde_matrix(degree):
    """Evidence 1: columns are exactly ``x**0 .. x**(degree-1)``."""
    matrix = np.asarray(N.BasisMatrix("poly", poly_deg=degree)(QUERY))
    assert matrix.shape == (QUERY.size, degree)
    vandermonde = np.vstack([QUERY**power for power in range(degree)]).T
    assert np.max(np.abs(matrix - vandermonde)) <= 64.0 * EPS * max(1.0, float(np.max(np.abs(vandermonde))))


@pytest.mark.parametrize("degree", [1, 2, 3, 4])
def test_build_basis_polynomial_members_are_the_ascending_powers(degree):
    """Evidence 1 for the factory: member ``j`` evaluates to ``x**j``."""
    members = N.build_basis("poly", poly_deg=degree)
    assert len(members) == degree
    for power, member in enumerate(members):
        values = np.asarray(member(QUERY))
        assert np.max(np.abs(values - QUERY**power)) <= 64.0 * EPS * max(1.0, float(np.max(np.abs(QUERY**power))))


@pytest.mark.parametrize(
    "selection",
    ["natural_cubic_spline", "clamped_cubic_spline", "clamped_cubic_spline1"],
)
def test_cardinal_spline_bases_partition_unity(selection):
    """Evidence 2: the sum of the cardinal splines is the constant one."""
    members = N.build_basis(selection, n_knots=5)
    total = sum(np.asarray(member(QUERY), dtype=float) for member in members)
    assert np.max(np.abs(total - 1.0)) <= 1024.0 * EPS * len(members)


def test_second_clamped_default_basis_is_affine_not_linear():
    """Evidence 3: the fixed origin ordinate removes one column and breaks unity."""
    members = N.build_basis("clamped_cubic_spline2", n_knots=5)
    assert len(members) == 4  # n_knots - 1

    total = sum(np.asarray(member(QUERY), dtype=float) for member in members)
    assert np.max(np.abs(total - 1.0)) > 1e-2, "the affine family must not sum to the constant"


def test_spline_design_matrix_columns_follow_the_member_order():
    """The matrix and the factory agree column by column."""
    members = N.build_basis("natural_cubic_spline", n_knots=5)
    matrix = np.asarray(N.BasisMatrix("natural_cubic_spline", n_knots=5)(QUERY))
    assert matrix.shape == (QUERY.size, len(members))
    for index, member in enumerate(members):
        assert np.max(np.abs(matrix[:, index] - np.asarray(member(QUERY), dtype=float))) <= 64.0 * EPS * 16.0


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
    """Failure matrix: the undeclared selector channel.

    The contract's ``failure_semantics`` names ``ValueError`` for unsupported
    basis selectors, but the factory surfaces the mapping miss as a ``KeyError``,
    which is not a ``ValueError``.  This test pins the observed type so the gap
    cannot go unnoticed; it is reported for a maintainer decision (widen the
    contract or raise ``ValueError``) and is not treated as the declared channel.
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

    Recorded deviations, both reported rather than blessed: a plain list reaches
    an attribute access and raises ``AttributeError``, and a 1-D array raises
    ``IndexError``, while the contract's ``failure_semantics`` names
    ``ValueError``.  The accepted form is a 2-D ``(poly_deg, k)`` array.
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

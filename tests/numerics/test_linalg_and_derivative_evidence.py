"""Independent evidence for the truncated pseudo-inverse and the nonuniform derivative.

Assets: ``scirel.numerics.truncated-svd-inverse``,
``scirel.numerics.nonuniform-derivatives``.

Evidence sources, independent of the implementations and their fixtures:

1. **Moore-Penrose axioms.**  The four defining identities
   ``A A+ A = A``, ``A+ A A+ = A+``, ``(A A+)^T = A A+``, ``(A+ A)^T = A+ A``
   characterise the pseudo-inverse uniquely, so satisfying them on a matrix whose
   singular values are all retained proves the value without comparing to any
   implementation.  Rank-deficient cases are checked separately against the
   analytic rank-one result.
2. **Second implementation with a declared semantic difference.**  SciPy/NumPy
   ``pinv`` discards singular values *equal to* its cutoff as well as below it,
   while this asset keeps ``s >= rcond * max(s)``.  The two are therefore only
   comparable where no singular value sits on the cutoff, and that condition is
   constructed explicitly instead of assumed.
3. **Exact rational differentiation.**  ``diff_12_central`` is declared to
   differentiate the local quadratic through three abscissae.  That quadratic is
   rebuilt here with ``fractions.Fraction`` from the original binary64 inputs and
   differentiated exactly, which is independent of how the finite differences are
   formed.
4. **Declared quadratic exactness and its order.**  Both returned derivatives are
   exact for quadratic data on any strictly increasing grid; for smooth data the
   three-point central difference on nonuniform grids is O(h^2), so halving the
   spacing must cut the error by about 4.

Budgets, fixed before measurement: axiom residuals ``256 * eps * ||A||``; the exact
rational comparison ``64 * eps * scale``; the refinement ratio is required to be
in 3.0..5.5 for a 2x refinement (theory 4).
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import scirel.numerics as N
from scirel.geometry import diff_12_central

EPS = np.finfo(float).eps


def _mp_axiom_defects(matrix, inverse):
    return {
        "A A+ A - A": float(np.max(np.abs(matrix @ inverse @ matrix - matrix))),
        "A+ A A+ - A+": float(np.max(np.abs(inverse @ matrix @ inverse - inverse))),
        "AA+ symmetric": float(np.max(np.abs(matrix @ inverse - (matrix @ inverse).T))),
        "A+A symmetric": float(np.max(np.abs(inverse @ matrix - (inverse @ matrix).T))),
    }


@pytest.mark.parametrize(
    "matrix",
    [
        np.array([[1.0, 2.0], [2.0, 4.0]]),
        np.array([[3.0, 0.0], [0.0, 1.0 / 3.0]]),
        np.array([[1.0, 0.0, 2.0], [0.0, 1.0, -1.0], [2.0, 1.0, 1.0]]),
        np.array([[0.5]]),
    ],
)
def test_retained_spectrum_satisfies_the_moore_penrose_axioms(matrix):
    """Evidence 1: the four defining identities, scaled by the matrix norm."""
    inverse = np.asarray(N.compute_truncated_pseudoinverse(matrix))
    assert inverse.shape == (matrix.shape[1], matrix.shape[0])
    scale = max(1.0, float(np.linalg.norm(matrix, 2)))
    budget = 256.0 * EPS * scale * scale
    for name, defect in _mp_axiom_defects(matrix, inverse).items():
        assert defect <= budget, (name, defect, budget)


def test_rank_deficient_case_matches_the_analytic_rank_one_inverse():
    """Evidence 1 on a known deficiency: ``A = u v^T`` has ``A+ = v u^T / (|u|^2 |v|^2)``."""
    u = np.array([[1.0], [2.0], [3.0]])
    v = np.array([[2.0], [-1.0]])
    matrix = u @ v.T
    want = (v @ u.T) / ((u.T @ u).item() * (v.T @ v).item())
    got = np.asarray(N.compute_truncated_pseudoinverse(matrix))
    assert np.max(np.abs(got - want)) <= 256.0 * EPS * float(np.max(np.abs(want)))


def test_agrees_with_numpy_pinv_away_from_the_cutoff():
    """Evidence 2, where the two documented semantics coincide."""
    rng = np.random.default_rng(20261116)
    matrix = rng.normal(size=(5, 3))
    singular = np.linalg.svd(matrix, compute_uv=False)
    # Keep every singular value well above the cutoff so both rules retain it.
    assert singular.min() > 1e6 * 1e-10 * singular.max()
    got = np.asarray(N.compute_truncated_pseudoinverse(matrix))
    assert np.max(np.abs(got - np.linalg.pinv(matrix))) <= 256.0 * EPS * float(np.max(np.abs(got)))


def test_cutoff_rule_keeps_a_singular_value_exactly_on_the_threshold():
    """The declared ``>=`` rule, which NumPy's ``pinv`` does not share."""
    matrix = np.diag([1.0, 1e-3])
    # rcond chosen so that 1e-3 sits exactly on rcond * max(s).
    inverse = np.asarray(N.compute_truncated_pseudoinverse(matrix, rcond=1e-3))
    assert inverse[1, 1] == pytest.approx(1e3, rel=1e-12)

    dropped = np.asarray(N.compute_truncated_pseudoinverse(matrix, rcond=2e-3))
    assert dropped[1, 1] == 0.0


def test_zero_matrix_returns_the_declared_zero_inverse():
    inverse = np.asarray(N.compute_truncated_pseudoinverse(np.zeros((2, 3))))
    assert inverse.shape == (3, 2)
    assert np.array_equal(inverse, np.zeros((3, 2)))


def test_rejection_channels_are_bound_to_their_contract():
    for call, expected, fragment in [
        (lambda: N.compute_truncated_pseudoinverse(np.zeros(3)), ValueError, "2-D"),
        (lambda: N.compute_truncated_pseudoinverse(np.array([[np.nan]])), ValueError, "finite"),
        (lambda: N.compute_truncated_pseudoinverse(np.eye(2), rcond=0.0), ValueError, "positive"),
        (lambda: N.compute_truncated_pseudoinverse(np.eye(2), rcond=-1.0), ValueError, "positive"),
        (
            lambda: N.compute_truncated_pseudoinverse(np.eye(2), rcond=float("inf")),
            ValueError,
            "positive",
        ),
        (lambda: N.compute_truncated_pseudoinverse(np.eye(2), rcond=True), ValueError, "positive"),
    ]:
        with pytest.raises(expected) as caught:
            call()
        assert fragment in str(caught.value), (fragment, str(caught.value))

    with pytest.raises(FloatingPointError):
        N.compute_truncated_pseudoinverse(np.array([[1e-310]]))


def test_multiple_pseudo_inverse_is_the_complement_on_the_retained_spectrum():
    """A structural identity: ``A A+`` projects onto the retained right/left space."""
    rng = np.random.default_rng(7)
    matrix = rng.normal(size=(4, 4))
    inverse = np.asarray(N.compute_truncated_pseudoinverse(matrix))
    projector = matrix @ inverse
    assert np.max(np.abs(projector @ projector - projector)) <= 1024.0 * EPS


def _exact_quadratic_derivatives(x, y):
    """Differentiate the exact interpolating quadratic through each interior triple."""
    one = np.empty(x.size - 2)
    two = np.empty(x.size - 2)
    for index in range(x.size - 2):
        x0, x1, x2 = (Fraction(float(value)) for value in x[index : index + 3])
        y0, y1, y2 = (Fraction(float(value)) for value in y[index : index + 3])
        # Divided-difference form of the quadratic through the three nodes.
        d1 = (y1 - y0) / (x1 - x0)
        d2 = (y2 - y1) / (x2 - x1)
        curvature = (d2 - d1) / (x2 - x0)
        centre = x1
        # p(t) = y0 + d_l (t - x0) + curvature (t - x0)(t - x1), so
        # p'(x1) = d_l + curvature (x1 - x0) and p'' = 2 curvature.
        one[index] = float(d1 + curvature * (centre - x0))
        two[index] = float(2 * curvature)
    return one, two


def test_nonuniform_derivative_matches_exact_rational_differentiation():
    """Evidence 3: exact rational reference on arbitrary data."""
    x = np.array([0.0, 0.3, 1.0, 1.1, 2.0, 2.5])
    y = np.array([0.0, 1.7, -0.4, 2.2, 0.9, 3.1])
    d_one, d_two = diff_12_central(x, y)
    want_one, want_two = _exact_quadratic_derivatives(x, y)
    scale_one = max(1.0, float(np.max(np.abs(want_one))))
    scale_two = max(1.0, float(np.max(np.abs(want_two))))
    assert np.max(np.abs(np.asarray(d_one) - want_one)) <= 64.0 * EPS * scale_one
    assert np.max(np.abs(np.asarray(d_two) - want_two)) <= 64.0 * EPS * scale_two


@pytest.mark.parametrize("coefficients", [(3.0, -2.0, 0.5), (0.0, 1.0, 0.0), (-1.5, 0.0, 2.5)])
def test_derivatives_are_exact_for_quadratic_data(coefficients):
    """Evidence 4: declared quadratic exactness on a deliberately nonuniform grid."""
    a, b, c = coefficients
    x = np.array([0.0, 0.11, 0.5, 1.4, 2.0, 3.3])
    y = a * x**2 + b * x + c
    d_one, d_two = diff_12_central(x, y)
    assert np.max(np.abs(np.asarray(d_one) - (2.0 * a * x[1:-1] + b))) <= 64.0 * EPS * max(
        1.0, abs(b), abs(2 * a * x[-2])
    )
    assert np.max(np.abs(np.asarray(d_two) - 2.0 * a)) <= 64.0 * EPS * max(1.0, abs(2 * a))


def test_first_derivative_error_refines_at_second_order_on_a_uniform_grid():
    """Evidence 4 for ``d_one``: the three-point central difference is O(h^2)."""

    def error(count):
        x = np.linspace(0.0, 2.0, count)
        d_one, _ = diff_12_central(x, np.sin(x))
        return float(np.max(np.abs(np.asarray(d_one) - np.cos(x[1:-1]))))

    coarse, fine = error(21), error(41)
    ratio = coarse / fine
    assert 3.0 <= ratio <= 5.5, f"observed refinement ratio {ratio:.2f} is not O(h^2)"


def test_first_derivative_error_refines_at_second_order_on_a_nonuniform_grid():
    """Evidence 4 for ``d_one`` away from uniform spacing."""

    def error(scale):
        x = np.array([0.0, 0.7 * scale, 1.9 * scale, 3.3 * scale, 5.0 * scale])
        d_one, _ = diff_12_central(x, np.sin(x))
        return float(np.max(np.abs(np.asarray(d_one) - np.cos(x[1:-1]))))

    coarse, fine = error(0.2), error(0.1)
    ratio = coarse / fine
    assert 3.0 <= ratio <= 5.5, f"observed non-uniform refinement ratio {ratio:.2f} is not O(h^2)"


def test_second_derivative_is_only_first_order_on_a_nonuniform_grid():
    """Measured order for ``d_two``, which is NOT second order off a uniform grid.

    On ``x = [0, h, 3h]`` with ``y = x^3`` the three-point second difference returns
    ``8h`` against the exact ``6h``, so the error is ``2h`` and halves when ``h``
    halves: first order.  This is intrinsic to the three-point formula (its leading
    error term is proportional to the local spacing ratio), not an implementation
    defect, so the contract restricts the O(h^2) claim to uniform grids.  Reverting
    that restriction -- asserting an O(h^2) ratio here -- makes this test fail with
    the observed ratio of about 2.
    """
    errors = []
    for h in (0.1, 0.05, 0.025):
        x = np.array([0.0, h, 3.0 * h])
        _, d_two = diff_12_central(x, x**3)
        exact = 6.0 * h
        observed = float(np.asarray(d_two)[0])
        assert abs(observed - 8.0 * h) <= 64.0 * EPS * 8.0 * h
        errors.append(abs(observed - exact))

    ratio = errors[0] / errors[1]
    assert 1.8 <= ratio <= 2.2, f"observed ratio {ratio:.2f} is not the first order of the witness"
    assert errors[1] / errors[2] == pytest.approx(2.0, rel=0.05)


def test_second_derivative_is_exact_for_cubics_on_a_uniform_grid():
    """Why the two previous tests disagree: the error term vanishes at equal spacing."""
    x = np.linspace(0.3, 1.3, 21)
    _, d_two = diff_12_central(x, x**3)
    assert np.max(np.abs(np.asarray(d_two) - 6.0 * x[1:-1])) <= 1e-10


def test_second_derivative_refines_at_second_order_on_a_uniform_grid():
    """The uniform grid keeps O(h^2) for d_two, which the contract states as "about 4".

    Guarding the ratio, not only the cubic-exact case, is what stops the contract
    from drifting back to a fourth-order claim that the implementation cannot meet.
    """
    ratios = []
    previous = None
    for count in (17, 33, 65):
        x = np.linspace(0.0, np.pi, count)
        _, d_two = diff_12_central(x, np.sin(x))
        error = np.max(np.abs(np.asarray(d_two) - (-np.sin(x))[1:-1]))
        if previous is not None:
            ratios.append(previous / error)
        previous = error
    assert all(3.5 <= ratio <= 4.5 for ratio in ratios), ratios


def test_derivative_rejection_channels_are_bound_to_their_contract():
    for call, expected in [
        (lambda: diff_12_central([0.0, 1.0], [0.0, 1.0]), ValueError),
        (lambda: diff_12_central([0.0, 1.0, 2.0], [0.0, 1.0]), ValueError),
        (lambda: diff_12_central([0.0, 1.0, 2.0], [0.0, np.nan, 1.0]), ValueError),
        (lambda: diff_12_central([0.0, 2.0, 1.0], [0.0, 1.0, 2.0]), ValueError),
        (lambda: diff_12_central([0.0, 1.0, 1.0], [0.0, 1.0, 2.0]), ValueError),
    ]:
        with pytest.raises(expected):
            call()

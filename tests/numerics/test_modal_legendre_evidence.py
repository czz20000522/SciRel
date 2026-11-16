"""Independent evidence for the orthonormal modal basis and its projection.

Assets: ``scirel.numerics.orthonormal-modal-basis``,
``scirel.numerics.modal-projection``.

Evidence sources, independent of the implementation and of its regression
fixtures:

1. **Closed-form Legendre reference.**  The contract states members are products
   of one-dimensional orthonormal Legendre polynomials on the reference cell.
   The orthonormal family has the closed form ``phi_n(x) = sqrt((2n+1)/2) * P_n(x)``
   on ``[-1, 1]``, because ``int_{-1}^{1} P_n^2 = 2/(2n+1)``.  That expression is
   evaluated here with ``mpmath.legendre`` at 40 decimal digits, a mature
   arbitrary-precision implementation that shares no code with this module.
2. **Gauss-Legendre exactness.**  An ``order+1`` point Gauss-Legendre rule per
   axis integrates polynomials up to degree ``2*order+1`` exactly.  Products of
   two members have degree at most ``2*order``, so the discrete Gram matrix on
   the basis's own rule must equal the identity in exact arithmetic.  This is
   what makes the discrete projection an L2 projection for polynomial data, and
   it is checked directly rather than assumed.
3. **Interpolation and projection identities.**  ``project(expand(c)) == c`` is
   the declared recovery property; it is checked as a round trip against
   coefficients chosen before the call.

Budgets, fixed before measurement: the mpmath comparison allows
``512 * eps`` because the only error is binary64 rounding of an exactly known
polynomial; the Gram defect allows ``1024 * eps`` scaled by ``num_basis``; round
trips allow the same scale.  No tolerance here is a fitting parameter.
"""

from __future__ import annotations

import mpmath
import numpy as np
import pytest

import scirel.numerics as N

EPS = np.finfo(float).eps
MP_DPS = 40


def _mp_orthonormal_legendre(order, x):
    """``sqrt((2n+1)/2) P_n(x)`` for n = 0..order, at high precision."""
    mpmath.mp.dps = MP_DPS
    point = mpmath.mpf(float(x))
    return np.array(
        [float(mpmath.sqrt(mpmath.mpf(2 * n + 1) / 2) * mpmath.legendre(n, point)) for n in range(order + 1)]
    )


@pytest.mark.parametrize("order", [0, 1, 2, 3])
def test_members_match_the_closed_form_orthonormal_legendre_polynomials(order):
    """Evidence 1: values agree with ``mpmath`` at 40 decimal digits."""
    basis = N.modal_basis("tensor", 1, order)
    nodes, _ = basis.quadrature()
    points = np.array([-0.93, -0.5, 0.0, 0.21, 0.66, 0.99])
    for point in points:
        got = np.asarray(basis.evaluate(np.array([[point]])))[0]
        want = _mp_orthonormal_legendre(order, point)
        assert np.max(np.abs(got - want)) <= 512.0 * EPS


@pytest.mark.parametrize("order", [0, 1, 2, 3])
def test_the_basis_rule_makes_the_gram_matrix_the_identity(order):
    """Evidence 2: the declared rule integrates member products exactly."""
    basis = N.modal_basis("tensor", 1, order)
    nodes, weights = basis.quadrature()
    values = np.asarray(basis.evaluate(nodes))
    gram = values.T @ (np.asarray(weights)[:, None] * values)
    identity = np.eye(gram.shape[0])
    assert np.max(np.abs(gram - identity)) <= 1024.0 * EPS * gram.shape[0]


def test_two_dimensional_tensor_family_is_orthonormal():
    """Evidence 2 in ``ndim = 2``: the rule is the tensor product of one-dimensional rules."""
    basis = N.modal_basis("tensor", 2, 2)
    nodes, weights = basis.quadrature()
    values = np.asarray(basis.evaluate(nodes))
    gram = values.T @ (np.asarray(weights)[:, None] * values)
    assert np.max(np.abs(gram - np.eye(gram.shape[0]))) <= 4096.0 * EPS * gram.shape[0]


def test_serendipity_family_keeps_an_orthonormal_subset():
    """Evidence 2 for the reduced family: dropping whole members preserves orthonormality."""
    tensor = np.asarray(N.modal_basis("tensor", 2, 2).exponents())
    serendipity = np.asarray(N.modal_basis("serendipity", 2, 2).exponents())

    kept = {tuple(row) for row in serendipity}
    assert kept <= {tuple(row) for row in tensor}
    # The declared rule: at most one axis may carry exponent >= 2.
    for row in serendipity:
        assert int(np.sum(np.asarray(row) >= 2)) <= 1

    basis = N.modal_basis("serendipity", 2, 2)
    nodes, weights = basis.quadrature()
    values = np.asarray(basis.evaluate(nodes))
    gram = values.T @ (np.asarray(weights)[:, None] * values)
    assert np.max(np.abs(gram - np.eye(gram.shape[0]))) <= 4096.0 * EPS * gram.shape[0]


def test_exponents_follow_the_declared_ordering():
    """The ordering rule is total degree, then descending exponent on earlier axes."""
    exponents = np.asarray(N.modal_basis("tensor", 2, 2).exponents())
    keys = [(int(np.sum(row)),) + tuple(-int(value) for value in row) for row in exponents]
    assert keys == sorted(keys)
    # And the concrete declared order for order=2, ndim=2.
    assert [list(row) for row in exponents] == [
        [0, 0], [1, 0], [0, 1], [2, 0], [1, 1], [0, 2], [2, 1], [1, 2], [2, 2]
    ]


@pytest.mark.parametrize("order,coefficients", [
    (1, np.array([0.4, -0.7])),
    (2, np.array([0.3, -0.2, 0.5])),
    (3, np.array([1.1, 0.0, -2.0, 0.25])),
])
def test_projection_recovers_member_coefficients_on_the_basis_rule(order, coefficients):
    """Evidence 3: ``project(expand(c)) == c`` round trip."""
    basis = N.modal_basis("tensor", 1, order)
    nodes, _ = basis.quadrature()
    values = np.asarray(basis.expand(nodes, coefficients))
    recovered = np.asarray(basis.project(values))
    assert np.max(np.abs(recovered - coefficients)) <= 1024.0 * EPS * max(1.0, float(np.max(np.abs(coefficients))))


def test_discrete_projection_equals_the_continuous_l2_projection_for_polynomials():
    """Evidence 2 used as a bridge: for ``f(x) = x^k`` the discrete projection is exact.

    Gauss-Legendre with ``order+1`` points integrates ``x^k * phi_m`` exactly for
    ``k + m <= 2*order + 1``, so the discrete weighted projection of a low-degree
    monomial equals the continuous L2 coefficient.  The continuous coefficient is
    computed here from ``mpmath`` quadrature of the closed-form reference, not
    from the basis object.
    """
    mpmath.mp.dps = MP_DPS
    order = 2
    basis = N.modal_basis("tensor", 1, order)
    nodes, _ = basis.quadrature()
    for degree in (0, 1, 2):
        values = np.asarray(nodes).ravel() ** degree
        got = np.asarray(basis.project(values))
        want = np.array(
            [
                float(mpmath.quad(lambda t, m=m: t**degree * mpmath.sqrt(mpmath.mpf(2 * m + 1) / 2) * mpmath.legendre(m, t), [-1, 1]))
                for m in range(order + 1)
            ]
        )
        assert np.max(np.abs(got - want)) <= 4096.0 * EPS * max(1.0, float(np.max(np.abs(want))))


def test_modal_projection_agrees_with_the_basis_object_project():
    """The free function and the handle are one relation, checked on the same data."""
    values = np.array([0.1, 0.2, 0.3])
    via_function = np.asarray(N.modal_projection("tensor", 1, 2, values))
    via_handle = np.asarray(N.modal_basis("tensor", 1, 2).project(values))
    assert np.max(np.abs(via_function - via_handle)) <= 64.0 * EPS


def test_rejection_channels_are_bound_to_their_contract():
    """Failure matrix for the handle construction."""
    for factory, expected, fragment in [
        (lambda: N.modal_basis("unknown", 1, 1), ValueError, "kind"),
        (lambda: N.modal_basis("tensor", 0, 1), ValueError, "ndim"),
        (lambda: N.modal_basis("tensor", 7, 1), ValueError, "ndim"),
        (lambda: N.modal_basis("tensor", 1, -1), ValueError, "order"),
        (lambda: N.modal_basis("tensor", True, 1), (TypeError, ValueError), "ndim"),
        (lambda: N.modal_basis("tensor", 1, True), (TypeError, ValueError), "order"),
    ]:
        with pytest.raises(expected) as caught:
            factory()
        assert fragment in str(caught.value).lower(), (fragment, str(caught.value))

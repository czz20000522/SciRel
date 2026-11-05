"""Direct numerical tests for the orthonormal modal basis pilot asset.

Every expected number is either an independent oracle (NumPy's Gauss-Legendre
and Legendre evaluators), an analytic polynomial identity, or a literal
coefficient transcribed from the reference kernel that motivated the pilot.
The tests never call the implementation to produce their own expected value.
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path
import sys

import numpy as np
import pytest

IMPLEMENTATION = Path(__file__).resolve().parents[2] / "src"
if str(IMPLEMENTATION) not in sys.path:
    sys.path.insert(0, str(IMPLEMENTATION))

from scirel.numerics.modal_basis import (  # noqa: E402
    ModalBasis,
    gauss_legendre,
    modal_basis,
    modal_projection,
    project_on_modal_basis,
)

# Reference kernel literals for the one-dimensional orthonormal Legendre member
# of each degree, transcribed from the generated kernel body. Each entry is the
# list of (power, coefficient) monomials of one member.
REFERENCE_1D = {
    0: [(0, 7.0710678118654757e-01)],
    1: [(1, 1.2247448713915889e00)],
    2: [(2, 2.3717082451262845e00), (0, -7.9056941504209488e-01)],
    3: [(3, 4.6770717334674270e00), (1, -2.8062430400804561e00)],
}

# Member counts the reference implementation asserts for its serendipity basis.
REFERENCE_SERENDIPITY_COUNTS = {
    (1, 0): 1,
    (1, 1): 2,
    (1, 2): 3,
    (1, 3): 4,
    (2, 1): 4,
    (2, 2): 8,
    (2, 3): 12,
    (3, 1): 8,
    (3, 2): 20,
    (3, 3): 32,
}


def _reference_1d_value(order, z):
    return sum(coefficient * z**power for power, coefficient in REFERENCE_1D[order])


@pytest.mark.parametrize("order", sorted(REFERENCE_1D))
def test_one_dimensional_matches_reference_coefficients(order):
    basis = modal_basis("tensor", 1, order)
    assert basis.num_basis == order + 1
    points = np.array([[-0.83], [-0.5], [0.0], [0.31], [1.0]])
    values = basis.evaluate(points)
    for member, order_member in enumerate(range(order + 1)):
        expected = [_reference_1d_value(order_member, point[0]) for point in points]
        assert values[:, member] == pytest.approx(expected, rel=1e-14, abs=1e-15)


@pytest.mark.parametrize("ndim,order", sorted(REFERENCE_SERENDIPITY_COUNTS))
def test_serendipity_member_count_matches_reference(ndim, order):
    assert (
        modal_basis("serendipity", ndim, order).num_basis
        == (REFERENCE_SERENDIPITY_COUNTS[(ndim, order)])
    )


@pytest.mark.parametrize("ndim", [1, 2, 3, 4, 5, 6])
@pytest.mark.parametrize("order", [0, 1, 2, 3])
def test_tensor_member_count_is_full_product(ndim, order):
    assert modal_basis("tensor", ndim, order).num_basis == (order + 1) ** ndim


@pytest.mark.parametrize("ndim", [1, 2, 3])
@pytest.mark.parametrize("order", [0, 1, 2, 3])
def test_serendipity_keeps_at_most_one_high_axis(ndim, order):
    basis = modal_basis("serendipity", ndim, order)
    exponents = basis.exponents()
    assert len(exponents) == basis.num_basis
    assert len(set(exponents)) == basis.num_basis
    for item in exponents:
        assert len(item) == ndim
        assert all(0 <= exponent <= order for exponent in item)
        assert sum(1 for exponent in item if exponent >= 2) <= 1


@pytest.mark.parametrize("kind", ["tensor", "serendipity"])
@pytest.mark.parametrize("ndim", [1, 2, 3])
@pytest.mark.parametrize("order", [0, 1, 2, 3])
def test_members_are_orthonormal_under_independent_rule(kind, ndim, order):
    basis = modal_basis(kind, ndim, order)
    points, weights = np.polynomial.legendre.leggauss(order + 4)
    nodes = np.array(list(itertools.product(points, repeat=ndim)))
    node_weights = np.array(list(itertools.product(weights, repeat=ndim))).prod(axis=1)
    members = basis.evaluate(nodes)
    gram = np.einsum("q,qi,qj->ij", node_weights, members, members)
    assert np.abs(gram - np.eye(basis.num_basis)).max() < 1e-12


@pytest.mark.parametrize("order", [0, 1, 2, 3, 4])
def test_gauss_legendre_matches_numpy(order):
    nodes, weights = gauss_legendre(order + 1)
    expected_nodes, expected_weights = np.polynomial.legendre.leggauss(order + 1)
    assert nodes == pytest.approx(expected_nodes, rel=0.0, abs=1e-14)
    assert weights == pytest.approx(expected_weights, rel=1e-14)
    assert nodes.sum() == pytest.approx(0.0, abs=1e-14)
    assert weights.sum() == pytest.approx(2.0, rel=1e-14)


@pytest.mark.parametrize("ndim", [1, 2, 3])
def test_quadrature_integrates_polynomials_exactly(ndim):
    order = 2
    nodes, weights = modal_basis("tensor", ndim, order).quadrature()
    # The (order+1)-point rule is exact through degree 2*order+1, so the
    # single-axis monomial z^(2*order) integrated over the remaining axes gives
    # (2/(2*order+1)) * 2^(ndim-1).
    for axis in range(ndim):
        integrand = nodes[..., axis] ** (2 * order)
        assert (weights * integrand).sum() == pytest.approx(
            2.0 / (2 * order + 1) * 2.0 ** (ndim - 1), rel=1e-13
        )
    total = weights * (nodes**2).prod(axis=1)
    assert total.sum() == pytest.approx((2.0 / 3.0) ** ndim, rel=1e-13)


def test_expand_reproduces_an_affine_function_exactly():
    basis = modal_basis("tensor", 2, 1)
    coefficients = np.array([0.5, -1.25, 2.0, 0.75])
    points = np.array([[0.2, -0.4], [-1.0, 1.0], [0.0, 0.0]])
    values = basis.expand(points, coefficients)
    # A two-dimensional member carries one factor per axis: the constant is
    # 1/2, an axis-linear member is sqrt(3/4) * z_axis, and the cross member is
    # 3/2 * z_0 * z_1.
    reference = (
        0.5 * 0.5
        + (-1.25) * math.sqrt(0.75) * points[:, 0]
        + 2.0 * math.sqrt(0.75) * points[:, 1]
        + 0.75 * 1.5 * points[:, 0] * points[:, 1]
    )
    assert values == pytest.approx(reference, rel=1e-14)


@pytest.mark.parametrize("direction", [0, 1])
def test_gradient_matches_central_difference(direction):
    basis = modal_basis("serendipity", 2, 3)
    coefficients = np.arange(1.0, basis.num_basis + 1.0) / basis.num_basis
    point = np.array([0.23, -0.37])
    step = 1e-6
    upper = point.copy()
    lower = point.copy()
    upper[direction] += step
    lower[direction] -= step
    finite_difference = (basis.expand(upper, coefficients) - basis.expand(lower, coefficients)) / (
        2 * step
    )
    assert basis.gradient(point, coefficients, direction) == pytest.approx(
        finite_difference, rel=1e-8, abs=1e-9
    )


def test_gradient_of_a_known_monomial_is_exact():
    basis = modal_basis("tensor", 2, 2)
    # Coefficient vector selecting only the constant member gives zero gradient.
    constant_only = np.zeros(basis.num_basis)
    constant_only[basis.exponents().index((0, 0))] = 1.0
    points = np.array([[0.4, -0.2]])
    for direction in (0, 1):
        assert basis.gradient(points, constant_only, direction) == pytest.approx([0.0], abs=1e-15)
    # Selecting the (1, 0) member gives its constant reference derivative
    # sqrt(3/4); the perpendicular direction is identically zero.
    linear = np.zeros(basis.num_basis)
    linear[basis.exponents().index((1, 0))] = 1.0
    assert basis.gradient(points, linear, 0) == pytest.approx([math.sqrt(0.75)], rel=1e-14)
    assert basis.gradient(points, linear, 1) == pytest.approx([0.0], abs=1e-15)


@pytest.mark.parametrize("kind", ["tensor", "serendipity"])
@pytest.mark.parametrize("ndim", [1, 2, 3])
@pytest.mark.parametrize("order", [1, 2, 3])
def test_projection_recovers_its_own_coefficients(kind, ndim, order):
    basis = modal_basis(kind, ndim, order)
    nodes, _ = basis.quadrature()
    expected = np.linspace(-1.5, 2.0, basis.num_basis)
    values = basis.expand(nodes, expected)
    recovered = basis.project(values)
    assert recovered == pytest.approx(expected, rel=1e-12, abs=1e-12)


def test_projection_of_a_product_is_its_gauss_integral():
    basis = modal_basis("tensor", 1, 2)
    # b_1 = sqrt(3/2) z, so b_1^2 = (3/2) z^2. Its modal coefficients are the
    # analytic integrals (3/2) * integral of b_i z^2 over [-1, 1].
    nodes, weights = basis.quadrature()
    members = basis.evaluate(nodes)
    product = members[:, 1] * members[:, 1]
    coefficients = np.einsum("q,qi,q->i", weights, members, product)
    second_moment = 2.0 / 3.0
    fourth_moment = 2.0 / 5.0
    expected = np.array(
        [
            1.5 * (1.0 / math.sqrt(2.0)) * second_moment,
            0.0,
            1.5 * (2.3717082451262845 * fourth_moment - 0.79056941504209488 * second_moment),
        ]
    )
    assert coefficients == pytest.approx(expected, rel=1e-13, abs=1e-14)


@pytest.mark.parametrize("direction", [0, 1])
def test_flip_sign_reflects_the_expansion(direction):
    basis = modal_basis("serendipity", 2, 2)
    coefficients = np.linspace(-0.5, 0.9, basis.num_basis)
    point = np.array([0.37, 0.61])
    reflected = point.copy()
    reflected[direction] *= -1.0
    flipped = basis.flip_sign(coefficients, direction)
    assert basis.expand(reflected, coefficients) == pytest.approx(
        basis.expand(point, flipped), rel=1e-13
    )


@pytest.mark.parametrize("kind", ["tensor", "serendipity"])
def test_project_on_modal_basis_is_the_end_to_end_path(kind):
    order = 2
    basis = modal_basis(kind, 2, order)
    nodes, _ = basis.quadrature()
    expected = np.arange(basis.num_basis, dtype=float) - 2.5
    values = basis.expand(nodes, expected)
    assert project_on_modal_basis(kind, 2, order, values) == pytest.approx(
        expected, rel=1e-12, abs=1e-12
    )


def test_modal_projection_forwards_its_input_mapping():
    order = 1
    basis = modal_basis("tensor", 2, order)
    nodes, _ = basis.quadrature()
    expected = np.array([1.0, -2.0, 0.5, 3.0])
    values = basis.expand(nodes, expected)
    assert modal_projection(
        {"kind": "tensor", "ndim": 2, "order": order, "values": values}
    ) == pytest.approx(expected, rel=1e-13)


@pytest.mark.parametrize(
    "argument,message",
    [
        ({"kind": "spectral", "ndim": 1, "order": 1}, "kind must be"),
        ({"kind": "tensor", "ndim": 0, "order": 1}, "ndim must be an integer"),
        ({"kind": "tensor", "ndim": 7, "order": 1}, "ndim must be an integer"),
        ({"kind": "tensor", "ndim": 1, "order": -1}, "order must be a non-negative"),
        ({"kind": "tensor", "ndim": 1, "order": 1.5}, "order must be a non-negative"),
        ({"kind": "tensor", "ndim": True, "order": 1}, "ndim must be an integer"),
    ],
)
def test_invalid_construction_is_rejected(argument, message):
    with pytest.raises(ValueError, match=message):
        modal_basis(**argument)


def test_coordinates_outside_the_reference_cell_are_rejected():
    basis = modal_basis("tensor", 1, 1)
    with pytest.raises(ValueError, match="reference cell"):
        basis.evaluate(np.array([[1.2]]))
    with pytest.raises(ValueError, match="reference cell"):
        basis.evaluate(np.array([[-1.0000001]]))
    with pytest.raises(ValueError, match="trailing axis"):
        basis.evaluate(np.array([[0.0, 0.0]]))
    with pytest.raises(ValueError, match="finite"):
        basis.evaluate(np.array([[np.nan]]))


def test_invalid_coefficients_and_directions_are_rejected():
    basis = modal_basis("tensor", 2, 1)
    with pytest.raises(ValueError, match="coefficients must have shape"):
        basis.expand(np.array([[0.0, 0.0]]), np.ones(2))
    with pytest.raises(ValueError, match="finite"):
        basis.expand(np.array([[0.0, 0.0]]), np.array([np.inf, 0.0, 0.0, 0.0]))
    for direction in (-1, 2, True, 0.0):
        with pytest.raises(ValueError, match="direction must be an axis index"):
            basis.gradient(np.array([[0.0, 0.0]]), np.ones(4), direction)


def test_projection_rejects_mismatched_samples():
    basis = modal_basis("tensor", 1, 1)
    with pytest.raises(ValueError, match="values must have shape"):
        basis.project(np.ones(3))


def test_gauss_legendre_rejects_a_non_positive_order():
    for order in (0, -1, 1.5, True):
        with pytest.raises(ValueError, match="order must be a positive integer"):
            gauss_legendre(order)


def test_basis_properties_are_exposed():
    basis = ModalBasis("serendipity", 3, 2)
    assert (basis.kind, basis.ndim, basis.order, basis.num_basis) == (
        "serendipity",
        3,
        2,
        20,
    )


def test_gauss_legendre_reports_nonconvergence(monkeypatch):
    import importlib

    module = importlib.import_module("scirel.numerics.modal_basis")
    monkeypatch.setattr(module, "_MAX_NEWTON_SWEEPS", 0)
    with pytest.raises(ValueError, match="did not converge"):
        module.gauss_legendre(3)

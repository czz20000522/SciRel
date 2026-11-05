"""Orthonormal modal polynomial bases and Gauss-Legendre quadrature.

The reference cell is the hypercube ``[-1, 1] ** ndim``.  A modal basis is a
family of polynomials orthonormal under the unweighted inner product on that
cell,

    integral over [-1,1]^ndim of b_i(z) b_j(z) dz = delta_ij

so a modal coefficient is a projection rather than an interpolation weight.
Two families share one construction:

``tensor``
    The full tensor product of the one-dimensional orthonormal Legendre
    polynomials, with ``(order + 1) ** ndim`` members.  Every monomial whose
    per-axis degree does not exceed ``order`` appears exactly once.

``serendipity``
    The same tensor product with the monomials that reach the maximum total
    degree on two or more axes removed, leaving
    ``(order + 1) ** ndim - order ** ndim`` members.  The removed members are
    the ones whose cross terms cost a full tensor slot without adding resolved
    per-axis structure, so a serendipity basis keeps the per-axis resolution at
    a lower member count.

Members are ordered by total degree, then by descending exponent on the first
axis, then the second, and so on.  The member order is part of the contract
because a coefficient vector is only meaningful next to the order that produced
it.
"""

from __future__ import annotations

import itertools
import math

import numpy as np

__all__ = [
    "ModalBasis",
    "gauss_legendre",
    "modal_basis",
    "modal_projection",
    "project_on_modal_basis",
]

_KINDS = ("tensor", "serendipity")
_MAX_NEWTON_SWEEPS = 200
_MAX_DIM = 6


def _check_order(order):
    if isinstance(order, bool) or not isinstance(order, int) or order < 0:
        raise ValueError("order must be a non-negative integer")
    return order


def _check_ndim(ndim):
    if isinstance(ndim, bool) or not isinstance(ndim, int) or not 1 <= ndim <= _MAX_DIM:
        raise ValueError(f"ndim must be an integer between 1 and {_MAX_DIM}")
    return ndim


def gauss_legendre(order):
    """Nodes and weights of the ``order``-point Gauss-Legendre rule on ``[-1, 1]``.

    The rule integrates every polynomial of degree up to ``2 * order - 1``
    exactly.  Roots are refined from a Chebyshev initial guess by Newton
    iteration on the three-term Legendre recurrence, so no ordinate table is
    stored.

    Args:
        order: Number of points, at least 1.

    Returns:
        ``(nodes, weights)`` as float64 arrays of length ``order``; nodes ascend
        and the weights sum to 2 within round-off.

    Raises:
        ValueError: If ``order`` is not a positive integer.
    """
    if isinstance(order, bool) or not isinstance(order, int) or order < 1:
        raise ValueError("order must be a positive integer")
    nodes = np.zeros(order, dtype=float)
    weights = np.zeros(order, dtype=float)
    tolerance = 4.0 * np.finfo(float).eps
    for index in range((order + 1) // 2):
        z = math.cos(math.pi * (index + 0.75) / (order + 0.5))
        derivative = 0.0
        for _ in range(_MAX_NEWTON_SWEEPS):
            # Recurrence for P_0(z), ..., P_order(z): after the sweep
            # ``legendre`` holds P_order and ``legendre_lower`` P_(order-1).
            legendre_lower, legendre = 1.0, z
            for degree in range(2, order + 1):
                legendre_before = legendre_lower
                legendre_lower = legendre
                legendre = (
                    (2.0 * degree - 1.0) * z * legendre_lower - (degree - 1.0) * legendre_before
                ) / degree
            if order == 1:
                legendre, legendre_lower = z, 1.0
            derivative = order * (z * legendre - legendre_lower) / (z * z - 1.0)
            step = legendre / derivative
            z -= step
            if abs(step) <= tolerance * max(1.0, abs(z)):
                break
        else:
            raise ValueError("Gauss-Legendre root iteration did not converge")
        weight = 2.0 / ((1.0 - z * z) * derivative * derivative)
        nodes[index] = -z
        nodes[order - 1 - index] = z
        weights[index] = weight
        weights[order - 1 - index] = weight
    return nodes, weights


def _legendre_value(degree, z):
    """Orthonormal Legendre polynomial of ``degree`` at coordinate ``z``."""
    z = np.asarray(z, dtype=float)
    if degree == 0:
        return np.full(z.shape, 1.0 / math.sqrt(2.0))
    p_older = np.ones(z.shape)
    p_previous = z.copy()
    if degree == 1:
        return math.sqrt(1.5) * p_previous
    for step in range(2, degree + 1):
        p_current = ((2.0 * step - 1.0) * z * p_previous - (step - 1.0) * p_older) / step
        p_older, p_previous = p_previous, p_current
    return math.sqrt((2.0 * degree + 1.0) / 2.0) * p_previous


def _legendre_derivative(degree, z):
    """Reference-coordinate derivative of the orthonormal Legendre polynomial."""
    z = np.asarray(z, dtype=float)
    if degree == 0:
        return np.zeros(z.shape)
    if degree == 1:
        return np.full(z.shape, math.sqrt(1.5))
    plain_older = np.ones(z.shape)
    plain_previous = z.copy()
    derivative_older = np.zeros(z.shape)
    derivative_current = np.ones(z.shape)
    for step in range(2, degree + 1):
        plain_current = (
            (2.0 * step - 1.0) * z * plain_previous - (step - 1.0) * plain_older
        ) / step
        derivative_current, derivative_older = (
            (2.0 * step - 1.0) * plain_previous + derivative_older,
            derivative_current,
        )
        plain_older, plain_previous = plain_previous, plain_current
    return math.sqrt((2.0 * degree + 1.0) / 2.0) * derivative_current


def _exponents(kind, ndim, order):
    """Exponent tuples of the members, in the declared member order."""
    corner = list(itertools.product(range(order + 1), repeat=ndim))
    if kind == "tensor":
        candidates = corner
        expected = (order + 1) ** ndim
    else:
        candidates = [item for item in corner if sum(1 for exponent in item if exponent >= 2) <= 1]
        expected = 1 if order == 0 else 2**ndim + ndim * (order - 1) * 2 ** (ndim - 1)
    candidates.sort(key=lambda item: (sum(item), tuple(-exponent for exponent in item)))
    if len(candidates) != expected:
        raise RuntimeError(
            f"{kind} basis in {ndim}D at order {order} produced {len(candidates)} "
            f"members, expected {expected}"
        )
    return tuple(candidates)


class ModalBasis:
    """An orthonormal modal polynomial basis on ``[-1, 1] ** ndim``."""

    __slots__ = ("_exponents", "_kind", "_ndim", "_order")

    def __init__(self, kind, ndim, order):
        if kind not in _KINDS:
            raise ValueError("kind must be 'tensor' or 'serendipity'")
        self._kind = kind
        self._ndim = _check_ndim(ndim)
        self._order = _check_order(order)
        self._exponents = _exponents(kind, self._ndim, self._order)

    @property
    def kind(self):
        """Basis family, ``tensor`` or ``serendipity``."""
        return self._kind

    @property
    def ndim(self):
        """Reference-cell dimension."""
        return self._ndim

    @property
    def order(self):
        """Polynomial order."""
        return self._order

    @property
    def num_basis(self):
        """Number of basis members."""
        return len(self._exponents)

    def exponents(self):
        """Per-member exponent tuples, in the declared member order."""
        return list(self._exponents)

    def _coordinates(self, z):
        coordinates = np.asarray(z, dtype=float)
        if coordinates.shape[-1:] != (self._ndim,):
            raise ValueError(f"z must have a trailing axis of length {self._ndim}")
        if not np.all(np.isfinite(coordinates)):
            raise ValueError("z must be finite")
        if np.any(np.abs(coordinates) > 1.0):
            raise ValueError("z must lie in the reference cell [-1, 1] ** ndim")
        return coordinates

    def _axis_values(self, coordinates, derivative_of=None):
        per_axis = []
        for axis in range(self._ndim):
            column = coordinates[..., axis]
            evaluator = _legendre_derivative if derivative_of == axis else _legendre_value
            per_axis.append([evaluator(degree, column) for degree in range(self._order + 1)])
        return per_axis

    @staticmethod
    def _product(per_axis, item):
        factors = [per_axis[axis][exponent] for axis, exponent in enumerate(item)]
        if len(factors) == 1:
            return factors[0]
        return np.multiply.reduce(factors)

    def evaluate(self, z):
        """Evaluate every member at the logical coordinates ``z``.

        Args:
            z: Array with trailing axis of length ``ndim`` inside ``[-1, 1]``.

        Returns:
            Array of shape ``z.shape[:-1] + (num_basis,)``.

        Raises:
            ValueError: If the trailing shape is wrong, a value is not finite,
                or a coordinate leaves the reference cell.
        """
        coordinates = self._coordinates(z)
        per_axis = self._axis_values(coordinates)
        columns = [self._product(per_axis, item) for item in self._exponents]
        return np.stack([np.asarray(column, dtype=float) for column in columns], axis=-1)

    def _checked_coefficients(self, coefficients):
        weights = np.asarray(coefficients, dtype=float)
        if weights.shape != (self.num_basis,):
            raise ValueError(f"coefficients must have shape ({self.num_basis},)")
        if not np.all(np.isfinite(weights)):
            raise ValueError("coefficients must be finite")
        return weights

    def expand(self, z, coefficients):
        """Evaluate the expansion ``sum_i c_i b_i(z)`` at ``z``.

        Args:
            z: Array with trailing axis of length ``ndim``.
            coefficients: Array of shape ``(num_basis,)``.

        Returns:
            Array of shape ``z.shape[:-1]``.

        Raises:
            ValueError: If the coefficient shape is wrong or not finite.
        """
        weights = self._checked_coefficients(coefficients)
        return np.einsum("...i,i->...", self.evaluate(z), weights)

    def gradient(self, z, coefficients, direction):
        """Evaluate the ``direction`` derivative of the expansion at ``z``.

        Args:
            z: Array with trailing axis of length ``ndim``.
            coefficients: Array of shape ``(num_basis,)``.
            direction: Reference-coordinate axis in ``range(ndim)``.

        Returns:
            Array of shape ``z.shape[:-1]``.

        Raises:
            ValueError: If the axis is out of range or coefficients are invalid.
        """
        if isinstance(direction, bool) or not isinstance(direction, int):
            raise ValueError("direction must be an axis index of the reference cell")
        if not 0 <= direction < self._ndim:
            raise ValueError("direction must be an axis index of the reference cell")
        weights = self._checked_coefficients(coefficients)
        coordinates = self._coordinates(z)
        per_axis = self._axis_values(coordinates, derivative_of=direction)
        columns = np.stack(
            [np.asarray(self._product(per_axis, item), dtype=float) for item in self._exponents],
            axis=-1,
        )
        return np.einsum("...i,i->...", columns, weights)

    def flip_sign(self, coefficients, direction):
        """Sign-flip odd powers in ``direction``, as a cell-reflection update.

        Args:
            coefficients: Array of shape ``(num_basis,)``.
            direction: Reference-coordinate axis whose odd powers change sign.

        Returns:
            Array of shape ``(num_basis,)``.

        Raises:
            ValueError: If the axis or coefficient shape is invalid.
        """
        weights = self._checked_coefficients(coefficients)
        if isinstance(direction, bool) or not isinstance(direction, int):
            raise ValueError("direction must be an axis index of the reference cell")
        if not 0 <= direction < self._ndim:
            raise ValueError("direction must be an axis index of the reference cell")
        signs = np.array(
            [-1.0 if item[direction] % 2 else 1.0 for item in self._exponents],
            dtype=float,
        )
        return weights * signs

    def quadrature(self):
        """Tensor Gauss-Legendre rule that integrates member products exactly.

        Returns:
            ``(nodes, weights)`` of shapes ``((order + 1) ** ndim, ndim)`` and
            ``((order + 1) ** ndim,)``.
        """
        points, one_dimensional = gauss_legendre(self._order + 1)
        nodes = np.array(list(itertools.product(points, repeat=self._ndim)), dtype=float)
        weights = np.array(
            list(itertools.product(one_dimensional, repeat=self._ndim)), dtype=float
        ).prod(axis=1)
        return nodes, weights

    def project(self, values):
        """Modal coefficients of the ``L2`` projection of values on the Gauss rule.

        Args:
            values: Sampled values with shape ``(num_quad,)`` matching this
                basis's own tensor Gauss rule.

        Returns:
            Coefficient array of shape ``(num_basis,)``.

        Raises:
            ValueError: If the shape disagrees or a sample is not finite.
        """
        nodes, weights = self.quadrature()
        samples = np.asarray(values, dtype=float)
        if samples.shape != weights.shape:
            raise ValueError(f"values must have shape {weights.shape}")
        if not np.all(np.isfinite(samples)):
            raise ValueError("values must be finite")
        members = self.evaluate(nodes)
        return np.einsum("q,qi,q->i", weights, members, samples)


def modal_basis(kind="tensor", ndim=1, order=1):
    """Construct an orthonormal modal basis on ``[-1, 1] ** ndim``.

    Args:
        kind: ``tensor`` for the full tensor product, ``serendipity`` for the
            tensor product without the monomials that reach the maximum order
            on two or more axes.
        ndim: Reference-cell dimension, 1 through 6.
        order: Polynomial order, at least 0.

    Returns:
        A :class:`ModalBasis` whose members are orthonormal with unit norm under
        the unweighted inner product on the reference cell.

    Raises:
        ValueError: If ``kind``, ``ndim`` or ``order`` is outside its domain.
    """
    return ModalBasis(kind, ndim, order)


def project_on_modal_basis(kind, ndim, order, values):
    """Project values sampled on the basis's own Gauss rule onto the basis.

    This is the end-to-end projection step: build the orthonormal basis, form
    its tensor Gauss-Legendre rule, and apply the weighted inner product that
    the orthonormality of the members makes a projection.

    Args:
        kind: ``tensor`` or ``serendipity``.
        ndim: Reference-cell dimension, 1 through 6.
        order: Polynomial order, at least 0.
        values: Samples at the nodes of ``ModalBasis.quadrature()``, with shape
            ``((order + 1) ** ndim,)``.

    Returns:
        Modal coefficient array of shape ``(num_basis,)``.

    Raises:
        ValueError: If the basis is undefined or the sample shape disagrees.
    """
    basis = modal_basis(kind=kind, ndim=ndim, order=order)
    return basis.project(values)


def modal_projection(inputs):
    """Port-mapped entry point for the modal projection composition.

    Args:
        inputs: Mapping with exactly ``kind``, ``ndim``, ``order`` and
            ``values``; forwarded unchanged to :func:`project_on_modal_basis`.

    Returns:
        The coefficient array produced by :func:`project_on_modal_basis`.
    """
    return project_on_modal_basis(**inputs)

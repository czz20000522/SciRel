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
    The same tensor product restricted to exponent tuples where at most one
    axis has exponent two or greater. At order zero there is one constant
    member; for positive order the count is
    ``2 ** ndim + ndim * (order - 1) * 2 ** (ndim - 1)``. The removed members
    are the ones whose cross terms cost a full tensor slot without adding
    resolved per-axis structure, so a serendipity basis keeps the per-axis
    resolution at a lower member count.

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
    """Return the Gauss-Legendre rule on ``[-1, 1]``.

    Parameters
    ----------
    order : int
        Number of quadrature points [1]. The value must be a positive integer;
        booleans and non-integral values are rejected.

    Returns
    -------
    nodes : ndarray of float64, shape (order,)
        Ascending nodes on ``[-1, 1]`` [1].
    weights : ndarray of float64, shape (order,)
        Quadrature weights [1]. Their sum is two within floating-point
        round-off.

    Raises
    ------
    ValueError
        If ``order`` is not a positive integer, or if the bounded Newton
        iteration does not converge.

    See Also
    --------
    ModalBasis.quadrature : Form the tensor-product rule used by a basis.
    ModalBasis.project : Use the rule to project samples onto a basis.

    Notes
    -----
    The rule integrates every polynomial of degree at most
    ``2 * order - 1`` exactly. Roots are refined from a Chebyshev initial
    guess with Newton iteration on the three-term Legendre recurrence; no
    ordinate table is stored. The iteration is bounded at 200 sweeps per root
    and reports non-convergence rather than returning an approximate node.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.numerics.modal_basis import gauss_legendre
    >>> nodes, weights = gauss_legendre(2)
    >>> np.allclose(nodes, [-1.0 / np.sqrt(3.0), 1.0 / np.sqrt(3.0)])
    True
    >>> np.allclose(weights, [1.0, 1.0])
    True
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
    """An orthonormal modal polynomial basis on the reference hypercube.

    Parameters
    ----------
    kind : {"tensor", "serendipity"}
        Basis family selector [1]. ``tensor`` keeps the full tensor product;
        ``serendipity`` keeps members that do not have degree at least two on
        two or more axes.
    ndim : int
        Dimension of the logical reference cell [1]. It must be an integer
        from 1 through 6; booleans are rejected.
    order : int
        Polynomial order per axis [1]. It must be a non-negative integer;
        booleans are rejected. Orders zero through three have regression
        evidence; higher orders are accepted but unqualified.

    Returns
    -------
    basis : ModalBasis
        A constructed basis handle [1] exposing the member order, evaluation,
        differentiation, reflection, quadrature, and projection operations.

    Attributes
    ----------
    kind : {"tensor", "serendipity"}
        The selected basis family [1].
    ndim : int
        Dimension of the logical reference cell [1].
    order : int
        Polynomial order per axis [1].
    num_basis : int
        Number of members in the selected basis [1].

    Raises
    ------
    ValueError
        If ``kind`` is not ``tensor`` or ``serendipity``, if ``ndim`` is not an
        integer from 1 through 6, or if ``order`` is not a non-negative
        integer.

    See Also
    --------
    modal_basis : Construct a basis with optional defaults.
    modal_projection : Project samples on a basis's own Gauss rule.

    Notes
    -----
    The reference cell is ``[-1, 1] ** ndim``. The members are products of
    one-dimensional orthonormal Legendre polynomials and satisfy the
    unweighted inner-product identity

    .. math:: \\int_{[-1,1]^{n}} b_i(z)b_j(z)\\,dz = \\delta_{ij}.

    The cell is logical and dimensionless: no physical mesh, Jacobian, metric,
    boundary condition, limiting, or positivity treatment is applied. A
    coefficient vector is meaningful only with the same family, dimension,
    order, and member order that produced it. The regression evidence covers
    dimensions one through three and orders zero through three; construction
    accepts dimensions one through six but does not qualify the untested
    combinations.

    Examples
    --------
    >>> basis = ModalBasis("serendipity", 2, 2)
    >>> basis.num_basis
    8
    >>> basis.exponents()[:4]
    [(0, 0), (1, 0), (0, 1), (2, 0)]
    """

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
        """Return per-member exponent tuples in the declared member order.

        Returns
        -------
        exponents : list of tuple of int, length num_basis
            Exponent tuple for each member [1]. Each tuple has ``ndim`` entries
            and records the polynomial degree on each reference axis.

        See Also
        --------
        evaluate : Evaluate the members at logical coordinates.
        quadrature : Return the tensor Gauss-Legendre rule for the basis.

        Notes
        -----
        The order is part of the basis definition. Sorting is by total degree,
        then by descending exponent on the first axis, then the second, and so
        on; do not reorder a coefficient vector independently of this list.

        Examples
        --------
        >>> basis = ModalBasis("tensor", 1, 1)
        >>> basis.exponents()
        [(0,), (1,)]
        """
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
        """Evaluate every basis member at logical coordinates.

        Parameters
        ----------
        z : array_like, shape (..., ndim)
            Logical coordinates [1]. The trailing axis must have length
            ``ndim``; values are converted to float64 and must be finite and
            lie inside ``[-1, 1]`` on every axis.

        Returns
        -------
        members : ndarray, shape (..., num_basis)
            Member values [1]. The leading shape is the leading shape of
            ``z`` and the final axis follows :meth:`exponents`.

        Raises
        ------
        ValueError
            If the trailing shape is wrong, a coordinate is not finite, or a
            coordinate lies outside the reference cell.

        See Also
        --------
        expand : Evaluate a coefficient-weighted expansion.
        gradient : Evaluate one reference-coordinate derivative.

        Notes
        -----
        ``z`` is a logical coordinate, not a physical coordinate. No mesh,
        Jacobian, cell measure, or boundary condition is applied.

        Examples
        --------
        >>> import numpy as np
        >>> basis = ModalBasis("tensor", 1, 1)
        >>> np.allclose(basis.evaluate([[0.0]]), [[1.0 / np.sqrt(2.0), 0.0]])
        True
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
        """Evaluate a modal expansion at logical coordinates.

        The expansion is :math:`\\sum_i c_i b_i(z)`, where ``b_i`` are the
        members returned by :meth:`evaluate`.

        Parameters
        ----------
        z : array_like, shape (..., ndim)
            Logical coordinates [1]. The trailing axis must have length
            ``ndim``; values are converted to float64 and must be finite and
            lie inside ``[-1, 1]`` on every axis.
        coefficients : array_like, shape (num_basis,)
            Modal coefficients [field]. The array must have exactly one entry
            per basis member and must contain only finite values.

        Returns
        -------
        values : ndarray, shape (...,)
            Expansion values [field]. The leading shape is the leading shape
            of ``z``.

        Raises
        ------
        ValueError
            If ``coefficients`` has the wrong shape or contains a non-finite
            value, or if ``z`` fails the coordinate checks described in
            :meth:`evaluate`.

        See Also
        --------
        evaluate : Evaluate all basis members.
        gradient : Evaluate one reference-coordinate derivative.

        Notes
        -----
        The coefficients are not normalized by the method; they are multiplied
        by the already orthonormal members. No physical cell measure or
        boundary condition is applied.

        Examples
        --------
        >>> import numpy as np
        >>> basis = ModalBasis("tensor", 1, 1)
        >>> coefficients = np.array([1.0, 0.0])
        >>> np.allclose(basis.expand([[0.0]], coefficients), [1.0 / np.sqrt(2.0)])
        True
        """
        weights = self._checked_coefficients(coefficients)
        return np.einsum("...i,i->...", self.evaluate(z), weights)

    def gradient(self, z, coefficients, direction):
        """Evaluate one reference-coordinate derivative of a modal expansion.

        Parameters
        ----------
        z : array_like, shape (..., ndim)
            Logical coordinates [1]. The trailing axis must have length
            ``ndim``; values are converted to float64 and must be finite and
            lie inside ``[-1, 1]`` on every axis.
        coefficients : array_like, shape (num_basis,)
            Modal coefficients [field]. The array must have exactly one entry
            per basis member and must contain only finite values.
        direction : int
            Reference-coordinate axis in ``range(ndim)`` [1]. The derivative
            is with respect to the logical coordinate on this axis, not a
            physical-coordinate derivative.

        Returns
        -------
        values : ndarray, shape (...,)
            Derivative values [field]. The leading shape is the leading shape
            of ``z``.

        Raises
        ------
        ValueError
            If ``direction`` is not an axis index, ``coefficients`` has the
            wrong shape or a non-finite value, or ``z`` fails the coordinate
            checks described in :meth:`evaluate`.

        See Also
        --------
        evaluate : Evaluate all basis members.
        expand : Evaluate a coefficient-weighted expansion.

        Notes
        -----
        The result is a derivative in the dimensionless logical coordinate. To
        obtain a physical derivative, the caller must apply the physical mesh
        Jacobian or metric; this class does not do so.

        Examples
        --------
        >>> import numpy as np
        >>> basis = ModalBasis("tensor", 1, 1)
        >>> coefficients = np.array([0.0, 1.0])
        >>> np.allclose(basis.gradient([[0.0]], coefficients, 0), [np.sqrt(1.5)])
        True
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
        """Reflect an expansion across one reference axis.

        Parameters
        ----------
        coefficients : array_like, shape (num_basis,)
            Modal coefficients [field]. The array must have exactly one entry
            per basis member and must contain only finite values.
        direction : int
            Reference-coordinate axis across which the expansion is reflected
            [1]. It must be in ``range(ndim)``.

        Returns
        -------
        reflected_coefficients : ndarray, shape (num_basis,)
            Coefficients after sign-flipping every member with odd exponent on
            ``direction`` [field].

        Raises
        ------
        ValueError
            If ``direction`` is not an axis index, or if ``coefficients`` has
            the wrong shape or contains a non-finite value.

        See Also
        --------
        evaluate : Evaluate the reflected expansion on the reference cell.
        gradient : Evaluate a reference-coordinate derivative.

        Notes
        -----
        Reflection maps a logical coordinate ``z_direction`` to
        ``-z_direction``. Only odd powers change sign, so this operation does
        not evaluate the expansion or alter the basis member order.

        Examples
        --------
        >>> basis = ModalBasis("tensor", 1, 1)
        >>> basis.flip_sign([1.0, 2.0], 0)
        array([ 1., -2.])
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
        """Return a tensor Gauss-Legendre rule for the basis.

        Returns
        -------
        nodes : ndarray, shape ((order + 1) ** ndim, ndim)
            Quadrature nodes on ``[-1, 1] ** ndim`` [1]. The node order follows
            the tensor product of the one-dimensional rules.
        weights : ndarray, shape ((order + 1) ** ndim,)
            Tensor-product quadrature weights [1]. They are the product of the
            one-dimensional Gauss-Legendre weights.

        Raises
        ------
        ValueError
            If the internal Gauss-Legendre root iteration does not converge.

        See Also
        --------
        project : Project samples on this rule back onto the basis.
        gauss_legendre : Return the one-dimensional rule used by this method.

        Notes
        -----
        The rule uses ``order + 1`` points per axis. Because each member has
        degree at most ``order`` on every axis, the tensor rule integrates all
        member products exactly. The rule is still logical and dimensionless;
        no physical-cell Jacobian is included.

        Examples
        --------
        >>> basis = ModalBasis("tensor", 1, 1)
        >>> nodes, weights = basis.quadrature()
        >>> print(nodes.shape, weights.shape)
        (2, 1) (2,)
        >>> print(round(float(weights.sum()), 12))
        2.0
        """
        points, one_dimensional = gauss_legendre(self._order + 1)
        nodes = np.array(list(itertools.product(points, repeat=self._ndim)), dtype=float)
        weights = np.array(
            list(itertools.product(one_dimensional, repeat=self._ndim)), dtype=float
        ).prod(axis=1)
        return nodes, weights

    def project(self, values):
        """Project samples on this basis's own Gauss rule onto the basis.

        Parameters
        ----------
        values : array_like, shape (num_quad,)
            Values sampled at the nodes returned by :meth:`quadrature` [field].
            The sample order must match that rule; the array must contain only
            finite values.

        Returns
        -------
        coefficients : ndarray, shape (num_basis,)
            Modal coefficients of the unweighted L2 projection [field], in the
            basis member order.

        Raises
        ------
        ValueError
            If ``values`` has the wrong shape or contains a non-finite value.

        See Also
        --------
        quadrature : Return the required sample nodes and weights.
        modal_projection : Build a basis and perform this operation directly.

        Notes
        -----
        The projection uses the quadrature weights and orthonormality of the
        members. It is exact for values generated by the same basis on its own
        quadrature nodes, but it does not provide an arbitrary scattered-node
        projection. No physical mesh, Jacobian, cell measure, filtering,
        limiting, or positivity correction is applied.

        Examples
        --------
        >>> import numpy as np
        >>> basis = ModalBasis("tensor", 1, 1)
        >>> expected = np.array([1.0, -2.0])
        >>> nodes, _ = basis.quadrature()
        >>> samples = basis.expand(nodes, expected)
        >>> print(bool(np.allclose(basis.project(samples), expected)))
        True
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
    """Construct an orthonormal modal basis on the reference hypercube.

    Parameters
    ----------
    kind : {"tensor", "serendipity"}, default "tensor"
        Basis family selector [1]. ``tensor`` keeps the full tensor product;
        ``serendipity`` keeps members that do not have degree at least two on
        two or more axes.
    ndim : int, default 1
        Dimension of the logical reference cell [1]. It must be an integer
        from 1 through 6; booleans are rejected.
    order : int, default 1
        Polynomial order per axis [1]. It must be a non-negative integer;
        booleans are rejected. Orders zero through three have regression
        evidence; higher orders are accepted but unqualified.

    Returns
    -------
    basis : ModalBasis
        A basis whose members are orthonormal with unit norm under the
        unweighted inner product on ``[-1, 1] ** ndim`` [1]. The returned
        handle exposes the member order, evaluation, differentiation,
        reflection, quadrature, and projection operations.

    Raises
    ------
    ValueError
        If ``kind`` is not ``tensor`` or ``serendipity``, if ``ndim`` is not an
        integer from 1 through 6, or if ``order`` is not a non-negative
        integer.

    See Also
    --------
    ModalBasis : The basis handle with evaluation and projection methods.
    modal_projection : Build a basis and project samples in one call.
    project_on_modal_basis : Explicit-argument projection convenience function.

    Notes
    -----
    The reference cell is logical and dimensionless: no physical mesh,
    Jacobian, metric, boundary condition, limiting, or positivity handling is
    applied. Members are ordered by total degree, then by descending exponent
    on the first axis, then the second, and so on. A coefficient vector is
    meaningful only with the same family, dimension, order, and member order
    that produced it. Regression evidence covers dimensions one through three
    and orders zero through three; higher accepted values are unqualified.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.numerics.modal_basis import modal_basis

    >>> basis = modal_basis("serendipity", 2, 2)
    >>> assert basis.num_basis == 8

    >>> nodes, weights = basis.quadrature()
    >>> members = basis.evaluate(nodes)
    >>> gram = np.einsum("q,qi,qj->ij", weights, members, members)
    >>> coefficients = np.arange(8, dtype=float) - 3.5
    >>> recovered = basis.project(basis.expand(nodes, coefficients))
    >>> print("orthonormal within 1e-12:", bool(np.abs(gram - np.eye(8)).max() < 1e-12))
    orthonormal within 1e-12: True
    >>> print("coefficients recovered within 1e-12:", bool(np.abs(recovered - coefficients).max() < 1e-12))
    coefficients recovered within 1e-12: True
    """
    return ModalBasis(kind, ndim, order)


def project_on_modal_basis(kind, ndim, order, values):
    """Project values sampled on the basis's own Gauss rule onto the basis.

    Parameters
    ----------
    kind : {"tensor", "serendipity"}
        Basis family selector [1].
    ndim : int
        Reference-cell dimension [1], from 1 through 6.
    order : int
        Polynomial order per axis [1], at least 0.
    values : array_like, shape ((order + 1) ** ndim,)
        Samples at the nodes of the constructed basis's own tensor
        Gauss-Legendre rule, ordered as returned by ``ModalBasis.quadrature``.
        Values are interpreted in the field unit [field] and converted to
        float64.

    Returns
    -------
    coefficients : ndarray of float64, shape (num_basis,)
        Modal coefficients of the L2 projection [field], in the basis member
        order.

    Raises
    ------
    TypeError
        If a required parameter is missing.
    ValueError
        If ``kind``, ``ndim`` or ``order`` is outside its domain, if
        ``values`` has the wrong shape or contains a non-finite value, or if
        the underlying Gauss-Legendre root iteration does not converge.

    See Also
    --------
    modal_basis : Construct the basis and its tensor Gauss-Legendre rule.
    ModalBasis.project : Apply the projection to a basis already in hand.

    Notes
    -----
    The function constructs the basis, obtains its tensor rule, and evaluates
    the weighted inner product of the samples with every orthonormal member.
    It applies no physical mesh, Jacobian, filtering, limiting, or positivity
    correction.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.numerics.modal_basis import modal_basis, project_on_modal_basis
    >>> basis = modal_basis("tensor", 2, 2)
    >>> nodes, _ = basis.quadrature()
    >>> expected = np.linspace(-1.0, 1.0, basis.num_basis)
    >>> values = basis.expand(nodes, expected)
    >>> coefficients = project_on_modal_basis("tensor", 2, 2, values)
    >>> print("coefficients recovered within 1e-12:", bool(np.abs(coefficients - expected).max() < 1e-12))
    coefficients recovered within 1e-12: True
    """
    basis = modal_basis(kind=kind, ndim=ndim, order=order)
    return basis.project(values)


def modal_projection(kind, ndim, order, values):
    """Project values sampled on the basis's own Gauss rule onto the basis.

    Parameters
    ----------
    kind : {"tensor", "serendipity"}
        Basis family selector [1].
    ndim : int
        Reference-cell dimension [1], from 1 through 6.
    order : int
        Polynomial order per axis [1], at least 0.
    values : array_like, shape ((order + 1) ** ndim,)
        Samples at the nodes of the constructed basis's own tensor
        Gauss-Legendre rule, ordered as returned by ``ModalBasis.quadrature``.
        Values are interpreted in the field unit [field] and converted to
        float64.

    Returns
    -------
    coefficients : numpy.ndarray, shape (num_basis,)
        Modal coefficients of the L2 projection [field], in the basis member
        order.

    Raises
    ------
    TypeError
        If a required parameter is missing, including when the former single
        mapping argument is supplied instead of the four explicit parameters.
    ValueError
        If ``kind``, ``ndim`` or ``order`` is outside its domain, or if
        ``values`` has the wrong shape or contains a non-finite value.

    See Also
    --------
    project_on_modal_basis
        Apply the same end-to-end projection with explicit scientific inputs.
    modal_basis
        Construct the basis and its own tensor Gauss-Legendre rule.

    Notes
    -----
    The projection uses the weighted inner product of the samples with each
    orthonormal member. It applies no physical mesh, Jacobian, filtering,
    limiting or positivity correction.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.numerics.modal_basis import modal_basis, modal_projection
    >>> basis = modal_basis("tensor", 2, 2)
    >>> nodes, _ = basis.quadrature()
    >>> expected = np.linspace(-1.0, 1.0, basis.num_basis)
    >>> values = basis.expand(nodes, expected)
    >>> coefficients = modal_projection("tensor", 2, 2, values)
    >>> print(
    ...     "coefficients recovered within 1e-12:",
    ...     bool(np.abs(coefficients - expected).max() < 1e-12),
    ... )
    coefficients recovered within 1e-12: True
    """
    return project_on_modal_basis(kind, ndim, order, values)

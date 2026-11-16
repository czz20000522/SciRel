"""Finite-volume cell values and boundary constraints for one coordinate."""

from dataclasses import dataclass
from math import frexp, ldexp

import numpy as np


__all__ = ["CellVariable"]


def finite_array(value, name, shape=None):
    """Return a writable float64 copy after strict real-array validation."""

    if np.ma.isMaskedArray(value) and np.any(np.ma.getmaskarray(value)):
        raise ValueError(f"{name} must not be masked")
    object_values = np.asarray(value, dtype=object)
    if any(isinstance(item, (bool, np.bool_)) for item in object_values.flat):
        raise TypeError(f"{name} must be real numeric, not boolean")
    raw = np.asarray(value)
    if raw.dtype.kind not in "iuf":
        raise TypeError(f"{name} must be real numeric")
    result = np.array(raw, dtype=np.float64, copy=True)
    if shape is not None and result.shape != shape:
        raise ValueError(f"{name} must have shape {shape}")
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must be finite")
    return result


def finite_scalar(value, name):
    """Validate a scalar through the common finite-array path."""

    return float(finite_array(value, name, ()).item())


def checked(value):
    """Raise when a finite-volume operation leaves the finite range."""

    if not np.isfinite(value).all():
        raise FloatingPointError("nonfinite finite-volume result")
    return value


def _scaled_sum(first, second):
    """Add two (mantissa, exponent) pairs without restoring physical scales."""
    a, ea = first
    b, eb = second
    if a == 0.0:
        return second
    if b == 0.0:
        return first
    exponent = max(ea, eb)
    # Only align toward smaller magnitudes; no intermediate can overflow.
    # Underflow here drops a term far below one ulp of the larger operand.
    mantissa, adjustment = frexp(ldexp(a, ea - exponent) + ldexp(b, eb - exponent))
    return mantissa, exponent + adjustment


def _scaled_difference(left, right):
    """Retain the scale even when a difference exceeds the float64 range."""
    return _scaled_sum(frexp(left), frexp(-right))


def _quadratic_face_derivative(points, samples, face):
    """Combine both weighted secants before restoring the derivative scale."""
    # For coordinates a,b,c relative to the face, the derivative is
    # ((b+c)*du01/dx01 - (a+b)*du12/dx12)/(c-a).
    # Neither the complete secants nor the dimensionless weights are stored.
    left, middle, right = [_scaled_difference(point, face) for point in points]
    first_weight = _scaled_sum(middle, right)
    last_weight = _scaled_sum(left, middle)
    last_weight = (-last_weight[0], last_weight[1])
    span, span_exp = _scaled_difference(points[2], points[0])
    terms = []
    for j, (weight, weight_exp) in enumerate((first_weight, last_weight)):
        change, change_exp = _scaled_difference(samples[j + 1], samples[j])
        spacing, spacing_exp = _scaled_difference(points[j + 1], points[j])
        # weight/span times change/spacing: all four nonzero mantissas
        # have magnitude in [0.5, 1), so their products/quotient are bounded.
        # In particular a zero weight never multiplies an infinite secant.
        mantissa = np.divide(weight * change, span * spacing)
        terms.append((mantissa, weight_exp + change_exp - span_exp - spacing_exp))
    mantissa, exponent = _scaled_sum(*terms)
    # Only the completed derivative is restored; genuinely nonfinite output
    # still follows the caller's NumPy policy and the final checked() call.
    return np.ldexp(mantissa, exponent)


@dataclass(frozen=True)
class CellVariable:
    """Store one-dimensional point samples with explicit face and boundary data.

    Parameters
    ----------
    value : array-like, shape (N,)
        Point samples at arithmetic cell centers, not cell-volume averages.
        Values are copied to read-only float64 data and use
        [caller quantity Q].  The input must be a finite real one-dimensional
        array with at least two cells.
    face_centers : array-like, shape (N+1,)
        Explicit cell-boundary coordinates [coordinate X].  The coordinates
        must be finite and strictly increasing; adjacent cell widths and the
        midpoint spacings derived from them must be finite and positive.
    left_face_constraint : float or None, default None
        Dirichlet value at the left boundary [Q].  Exactly one of this value
        and ``left_face_grad_constraint`` must be set.  The input is converted
        to a finite float64 scalar when present.
    right_face_constraint : float or None, default None
        Dirichlet value at the right boundary [Q].  Exactly one of this value
        and ``right_face_grad_constraint`` must be set.  The input is converted
        to a finite float64 scalar when present.
    left_face_grad_constraint : float or None, default 0.0
        Neumann derivative at the left boundary in the positive coordinate
        direction [Q/X].  Exactly one of this value and
        ``left_face_constraint`` must be set.  ``None`` selects a Dirichlet
        boundary instead.
    right_face_grad_constraint : float or None, default 0.0
        Neumann derivative at the right boundary in the positive coordinate
        direction [Q/X].  Exactly one of this value and
        ``right_face_constraint`` must be set.  ``None`` selects a Dirichlet
        boundary instead.

    Returns
    -------
    variable : CellVariable
        Immutable copied float64 cell samples with explicit face coordinates
        and boundary data [Q; derivatives Q/X].  It provides ``face_value()``,
        ``face_grad()`` and ``grad()`` for reconstruction.

    Raises
    ------
    TypeError
        If ``value``, ``face_centers`` or a supplied boundary scalar is not a
        real numeric value, or if a boolean value is supplied.
    ValueError
        If an array is masked, non-finite, not one-dimensional, has the wrong
        shape, has a non-positive width or midpoint spacing, or if either end
        does not have exactly one of a Dirichlet value and a Neumann gradient.
    FloatingPointError
        If a face-value or face-gradient reconstruction produces a non-finite
        result.

    See Also
    --------
    make_convection_terms : Assemble conservative convection terms on the
        face grid.
    make_diffusion_terms : Assemble two-point diffusion terms on the face
        grid.
    theta_step : Advance one cell variable with the assembled operators.

    Notes
    -----
    Cell centers are the arithmetic midpoints of adjacent face coordinates.
    ``face_value`` linearly interpolates interior faces and uses the declared
    boundary values or a half-cell gradient extrapolation at the endpoints.
    ``face_grad`` uses local quadratic stencils on interior faces; the final
    interior face uses the right boundary value or gradient when present.
    Three-point derivatives combine weighted adjacent secants without squared
    coordinate lengths. Weights, value differences and spacings retain binary
    mantissas and exponents until both contributions have been added; an
    unweighted secant need not fit in float64.
    ``grad`` is the difference of reconstructed face values divided by each
    cell width.  The returned arrays are read-only and are not volume
    averages.

    The precision budget for a stencil derivative is one float64 rounding after
    both weighted contributions have been added: each contribution is carried as
    a mantissa and an exponent, so the budget does not depend on the coordinate
    scale, and only the completed derivative is restored with ``ldexp``.
    ``face_value`` costs one linear combination per interior face and is not
    scale-reduced. The evidence tests compare against exact rational Lagrange
    derivatives on the two- and four-cell nonuniform grids at coordinate scales
    ``2**-540``, ``1`` and ``2**512``; a genuinely nonrepresentable derivative is
    reported through the declared runtime channel instead of being rounded.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.fvm import CellVariable
    >>> v=CellVariable([.5,1.5],[0.,1.,2.],left_face_grad_constraint=1.,right_face_grad_constraint=1.)
    >>> np.testing.assert_allclose(v.face_value(),[0.,1.,2.])
    >>> np.testing.assert_allclose(v.face_grad(),1.)
    """

    value: object
    face_centers: object
    left_face_constraint: object = None
    right_face_constraint: object = None
    left_face_grad_constraint: object = 0.0
    right_face_grad_constraint: object = 0.0

    def __post_init__(self):
        values = finite_array(self.value, "value")
        if values.ndim != 1 or values.size < 2:
            raise ValueError("value must be one-dimensional with at least two cells")
        faces = finite_array(self.face_centers, "face_centers", (values.size + 1,))
        with np.errstate(over="ignore", invalid="ignore"):
            widths = np.diff(faces)
            centers = faces[:-1] + widths / 2.0
        if (
            not np.isfinite(widths).all()
            or np.any(widths <= 0.0)
            or not np.isfinite(centers).all()
            or np.any(np.diff(centers) <= 0.0)
        ):
            raise ValueError("face and midpoint spacings must be finite and positive")

        values.setflags(write=False)
        faces.setflags(write=False)
        object.__setattr__(self, "value", values)
        object.__setattr__(self, "face_centers", faces)

        for side in ("left", "right"):
            value_name = f"{side}_face_constraint"
            gradient_name = f"{side}_face_grad_constraint"
            boundary_value = getattr(self, value_name)
            boundary_gradient = getattr(self, gradient_name)
            if (boundary_value is None) == (boundary_gradient is None):
                raise ValueError("exactly one boundary value or gradient is required at each end")
            if boundary_value is not None:
                object.__setattr__(self, value_name, finite_scalar(boundary_value, value_name))
            if boundary_gradient is not None:
                object.__setattr__(
                    self, gradient_name, finite_scalar(boundary_gradient, gradient_name)
                )

    @property
    def cell_widths(self):
        return np.diff(self.face_centers)

    @property
    def cell_centers(self):
        return self.face_centers[:-1] + self.cell_widths / 2.0

    @property
    def cell_spacings(self):
        return np.diff(self.cell_centers)

    @property
    def left_face_value(self):
        if self.left_face_constraint is not None:
            return self.left_face_constraint
        return self.value[0] - self.left_face_grad_constraint * self.cell_widths[0] / 2.0

    @property
    def right_face_value(self):
        if self.right_face_constraint is not None:
            return self.right_face_constraint
        return self.value[-1] + self.right_face_grad_constraint * self.cell_widths[-1] / 2.0

    def face_value(self):
        """Interpolate values to faces, using the declared endpoint data."""

        centers = self.cell_centers
        weights = (self.face_centers[1:-1] - centers[:-1]) / self.cell_spacings
        with np.errstate(all="ignore"):
            internal = (1.0 - weights) * self.value[:-1] + weights * self.value[1:]
            return checked(
                np.concatenate(([self.left_face_value], internal, [self.right_face_value]))
            )

    def face_grad(self, *, two_point_mask=None):
        """Return ``du/dx`` at every face using local quadratic stencils."""

        n = self.value.size
        faces = self.face_centers
        centers = self.cell_centers
        gradients = np.empty(n + 1, dtype=float)

        for index in range(1, n):
            if index < n - 1:
                points = centers[index - 1 : index + 2]
                samples = self.value[index - 1 : index + 2]
            elif self.right_face_constraint is None:
                widths = self.cell_widths[-2:]
                scaled_left, scaled_right = widths / np.max(widths)
                weight = (scaled_left - scaled_right) / (scaled_left + 3.0 * scaled_right)
                secant = (self.value[-1] - self.value[-2]) / self.cell_spacings[-1]
                gradients[index] = (
                    1.0 - weight
                ) * secant + weight * self.right_face_grad_constraint
                continue
            else:
                points = np.concatenate((centers[-2:], [faces[-1]]))
                samples = np.concatenate((self.value[-2:], [self.right_face_constraint]))

            gradients[index] = _quadratic_face_derivative(points, samples, faces[index])

        if two_point_mask is not None:
            mask = np.asarray(two_point_mask)
            if mask.dtype.kind != "b" or mask.shape != (n + 1,):
                raise ValueError("two_point_mask must be boolean N+1")
            gradients[1:-1] = np.where(
                mask[1:-1], np.diff(self.value) / self.cell_spacings, gradients[1:-1]
            )

        if self.left_face_constraint is not None:
            gradients[0] = (self.value[0] - self.left_face_constraint) / (self.cell_widths[0] / 2.0)
        else:
            gradients[0] = self.left_face_grad_constraint
        if self.right_face_constraint is not None:
            gradients[-1] = (self.right_face_constraint - self.value[-1]) / (
                self.cell_widths[-1] / 2.0
            )
        else:
            gradients[-1] = self.right_face_grad_constraint
        return checked(gradients)

    def grad(self):
        """Return the finite-volume gradient from interpolated face values."""

        return checked(np.diff(self.face_value()) / self.cell_widths)

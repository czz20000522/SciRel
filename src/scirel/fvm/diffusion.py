"""Two-point diffusion and a compact tridiagonal matrix container."""

import numpy as np

from .cell_variable import CellVariable, checked, finite_array

__all__ = ["TriDiagonal", "make_diffusion_terms"]


class TriDiagonal:
    """Store a square nearest-neighbour operator as three diagonals.

    Parameters
    ----------
    diagonal : array-like, shape (N,)
        Main diagonal coefficients [coefficient unit].  The input is copied to
        a finite float64 array.
    above : array-like, shape (N-1,)
        Superdiagonal coefficients coupling each row to the next column
        [coefficient unit].  The input is copied to a finite float64 array.
    below : array-like, shape (N-1,)
        Subdiagonal coefficients coupling each row to the previous column
        [coefficient unit].  The input is copied to a finite float64 array.

    Returns
    -------
    operator : TriDiagonal
        Tridiagonal operator container [coefficient unit].

    Raises
    ------
    TypeError
        If a coefficient array cannot be converted to real numeric data.
    ValueError
        If the diagonal is empty, is not one-dimensional, the off-diagonal
        lengths do not match, or any coefficient is non-finite.

    See Also
    --------
    make_diffusion_terms : Build a diffusion operator represented by this
        container.
    make_convection_terms : Build a convection operator represented by this
        container.

    Notes
    -----
    The matrix has ``above`` on the first superdiagonal and ``below`` on the
    first subdiagonal.  ``to_dense`` is intended for diagnostics and small
    systems; ``to_banded`` returns the layout accepted by
    ``scipy.linalg.solve_banded``.  ``matvec`` preserves trailing dimensions
    when the first axis of the input has one entry per row.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.fvm import TriDiagonal
    >>> matrix=TriDiagonal([2.,2.],[-1.],[-1.])
    >>> np.testing.assert_allclose(matrix.matvec([1.,1.]),[1.,1.])
    """

    def __init__(self, diagonal, above, below):
        diagonal = np.asarray(diagonal, dtype=float)
        above = np.asarray(above, dtype=float)
        below = np.asarray(below, dtype=float)
        if diagonal.ndim != 1 or diagonal.size < 1:
            raise ValueError("diagonal must be a nonempty one-dimensional array")
        if above.shape != (diagonal.size - 1,) or below.shape != (diagonal.size - 1,):
            raise ValueError("tridiagonal lengths mismatch")
        if not all(np.all(np.isfinite(values)) for values in (diagonal, above, below)):
            raise ValueError("tridiagonal coefficients must be finite")
        self.diagonal = np.array(diagonal, copy=True)
        self.above = np.array(above, copy=True)
        self.below = np.array(below, copy=True)

    def to_dense(self):
        """Materialize the matrix for diagnostics and small systems."""
        matrix = np.diag(self.diagonal.copy())
        matrix += np.diag(self.above, 1) + np.diag(self.below, -1)
        return matrix

    def to_banded(self):
        """Return the layout accepted by ``scipy.linalg.solve_banded``."""
        return np.vstack((np.r_[0.0, self.above], self.diagonal, np.r_[self.below, 0.0]))

    def matvec(self, x):
        """Multiply by a vector or by a stack whose first axis is rows."""
        values = np.asarray(x, dtype=float)
        if values.ndim == 0 or values.shape[0] != self.diagonal.size:
            raise ValueError("x must have one value per tridiagonal row")
        shape = (self.diagonal.size,) + (1,) * (values.ndim - 1)
        result = np.array(self.diagonal.reshape(shape) * values, copy=True)
        if self.diagonal.size > 1:
            result[:-1] += (
                self.above.reshape((self.above.size,) + (1,) * (values.ndim - 1)) * values[1:]
            )
            result[1:] += (
                self.below.reshape((self.below.size,) + (1,) * (values.ndim - 1)) * values[:-1]
            )
        return result


def _dirichlet_coefficient(diffusivity, width):
    """Evaluate the same ``2*D/h**2`` without an overflowing/vanishing square."""
    d_mantissa, d_exponent = np.frexp(diffusivity)
    h_mantissa, h_exponent = np.frexp(width)
    # Positive h has .5 <= m_h < 1; abs(m_D) < 1. The intermediate
    # mantissa stays below 8. Only the final coefficient is rescaled.
    mantissa = (2.0 * d_mantissa / h_mantissa) / h_mantissa
    return np.ldexp(mantissa, d_exponent - 2 * h_exponent)


def _boundary_forcing(diffusivity, width, boundary, *, dirichlet):
    """Restore the scale only after the complete boundary product is formed."""
    d_mantissa, d_exponent = np.frexp(diffusivity)
    h_mantissa, h_exponent = np.frexp(width)
    b_mantissa, b_exponent = np.frexp(boundary)
    if dirichlet:
        mantissa = (2.0 * d_mantissa / h_mantissa) / h_mantissa
        exponent = d_exponent - 2 * h_exponent
    else:
        mantissa = d_mantissa / h_mantissa
        exponent = d_exponent - h_exponent
    # Multiply bounded mantissas before restoring either product's range.
    # The separate matrix coefficient may round to zero while this is finite.
    return np.ldexp(mantissa * b_mantissa, exponent + b_exponent)


def make_diffusion_terms(d_face, var):
    """Assemble two-point diffusion terms as a tridiagonal operator and forcing.

    Parameters
    ----------
    d_face : array-like, shape (N+1,)
        Face-centred diffusivity [X^2/time].  The input is converted to finite
        float64 data and must have one value per cell face.
    var : CellVariable
        Cell values and boundary data for the same explicit one-dimensional
        face grid [Q].

    Returns
    -------
    matrix : TriDiagonal
        Cell operator for ``d/dx(D*du/dx)`` [1/time].
    forcing : ndarray of float64, shape (N,)
        Explicit boundary contribution to add to ``matrix @ var.value``
        [Q/time].

    Raises
    ------
    TypeError
        If ``var`` is not a ``CellVariable`` or an input cannot be converted
        to real numeric data.
    ValueError
        If an input is masked, non-finite, or has the wrong shape.
    FloatingPointError
        If the assembled coefficients contain a non-finite result.

    See Also
    --------
    CellVariable : Cell and face data used by this operator.
    make_convection_terms : Assemble the conservative convection operator.
    theta_step : Combine old and new operators in a theta step.

    Notes
    -----
    Interior fluxes use the diffusivity at each face and the distance between
    adjacent cell centres.  Dirichlet faces use a half-cell secant, whereas
    Neumann data are positive-coordinate gradients.  Dividing each flux
    difference by the cell width makes the shared internal flux cancel in the
    cell-weighted sum.  The returned matrix and forcing are an ordinary pair;
    no fallback or clipping of a non-finite result is applied.

    At each Dirichlet end, ``2*D/h**2`` is evaluated with binary mantissas
    and exponents, avoiding an unrepresentable intermediate ``h**2`` or
    ``2*D`` when the coefficient is finite. Signed and zero diffusivities
    retain their original algebra; no diffusivity floor is introduced.
    Boundary forcing is rescaled after multiplying the boundary data:
    ``2*D*g/h**2`` for a Dirichlet value and signed ``D*g/h`` for a
    Neumann gradient. Thus a finite forcing is retained when the separate
    Dirichlet coefficient rounds to zero or an intermediate product would
    underflow or overflow. Non-finite matrix or forcing outputs still fail.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.fvm import CellVariable,make_diffusion_terms
    >>> v=CellVariable([.5,1.5],[0.,1.,2.],left_face_grad_constraint=1.,right_face_grad_constraint=1.)
    >>> m,b=make_diffusion_terms([1.,1.,1.],v)
    >>> np.testing.assert_allclose(m.matvec(v.value)+b,0.)
    """
    if not isinstance(var, CellVariable):
        raise TypeError("var must be CellVariable")
    n_cells = var.value.size
    diffusivity = finite_array(d_face, "d_face", (n_cells + 1,))
    widths = var.cell_widths
    diagonal = np.zeros(n_cells, dtype=float)
    upper = np.zeros(n_cells - 1, dtype=float)
    lower = np.zeros(n_cells - 1, dtype=float)
    offset = np.zeros(n_cells, dtype=float)

    with np.errstate(all="ignore"):
        conductance = diffusivity[1:-1] / var.cell_spacings
        diagonal[:-1] -= conductance / widths[:-1]
        diagonal[1:] -= conductance / widths[1:]
        upper += conductance / widths[:-1]
        lower += conductance / widths[1:]

        if var.left_face_constraint is not None:
            coefficient = _dirichlet_coefficient(diffusivity[0], widths[0])
            diagonal[0] -= coefficient
            offset[0] += _boundary_forcing(
                diffusivity[0], widths[0], var.left_face_constraint, dirichlet=True
            )
        else:
            offset[0] -= _boundary_forcing(
                diffusivity[0], widths[0], var.left_face_grad_constraint, dirichlet=False
            )

        if var.right_face_constraint is not None:
            coefficient = _dirichlet_coefficient(diffusivity[-1], widths[-1])
            diagonal[-1] -= coefficient
            offset[-1] += _boundary_forcing(
                diffusivity[-1], widths[-1], var.right_face_constraint, dirichlet=True
            )
        else:
            offset[-1] += _boundary_forcing(
                diffusivity[-1], widths[-1], var.right_face_grad_constraint, dirichlet=False
            )

    return TriDiagonal(checked(diagonal), checked(upper), checked(lower)), checked(offset)

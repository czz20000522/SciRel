"""Two-point diffusion and a compact tridiagonal matrix container."""

import numpy as np

from .cell_variable import CellVariable, checked, finite_array

__all__ = ["TriDiagonal", "make_diffusion_terms"]


class TriDiagonal:
    """Store the three diagonals of a square nearest-neighbour operator."""

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
            result[:-1] += self.above.reshape((self.above.size,) + (1,) * (values.ndim - 1)) * values[1:]
            result[1:] += self.below.reshape((self.below.size,) + (1,) * (values.ndim - 1)) * values[:-1]
        return result


def make_diffusion_terms(d_face, var):
    """Return ``(M, b)`` for ``d/dx(D*du/dx)`` on cell point values.

    Interior gradients use the distance between adjacent cell centres.
    Dirichlet faces use a half-cell secant; Neumann data are positive-axis
    gradients.  Flux differences are divided by each cell width, which makes
    the shared internal flux cancel in a weighted sum.
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
            coefficient = 2.0 * diffusivity[0] / widths[0] ** 2
            diagonal[0] -= coefficient
            offset[0] += coefficient * var.left_face_constraint
        else:
            offset[0] -= diffusivity[0] * var.left_face_grad_constraint / widths[0]

        if var.right_face_constraint is not None:
            coefficient = 2.0 * diffusivity[-1] / widths[-1] ** 2
            diagonal[-1] -= coefficient
            offset[-1] += coefficient * var.right_face_constraint
        else:
            offset[-1] += diffusivity[-1] * var.right_face_grad_constraint / widths[-1]

    return TriDiagonal(checked(diagonal), checked(upper), checked(lower)), checked(offset)

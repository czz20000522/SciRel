"""Single-channel theta integration for the local finite-volume operators."""

from dataclasses import replace

import numpy as np

from .cell_variable import CellVariable, checked, finite_array, finite_scalar
from .convection import make_convection_terms
from .diffusion import TriDiagonal, make_diffusion_terms

__all__ = ["theta_step"]


def _assemble_operator(var, diffusion, convection, source, dirichlet_mode, neumann_mode):
    """Assemble ``F(u) = C u + c`` for one time level."""
    n_cells = var.value.size
    diagonal = np.zeros(n_cells, dtype=float)
    upper = np.zeros(n_cells - 1, dtype=float)
    lower = np.zeros(n_cells - 1, dtype=float)
    offset = np.zeros(n_cells, dtype=float)

    if diffusion is not None:
        matrix, constant = make_diffusion_terms(diffusion, var)
        diagonal += matrix.diagonal
        upper += matrix.above
        lower += matrix.below
        offset += constant
    if convection is not None:
        face_diffusion = np.zeros(n_cells + 1) if diffusion is None else diffusion
        matrix, constant = make_convection_terms(
            convection, face_diffusion, var, dirichlet_mode, neumann_mode
        )
        diagonal += matrix.diagonal
        upper += matrix.above
        lower += matrix.below
        offset += constant
    if source is not None:
        offset += finite_array(source, "source", (n_cells,))

    return TriDiagonal(checked(diagonal), checked(upper), checked(lower)), checked(offset)


def theta_step(
    var_old,
    var_new,
    dt,
    *,
    d_old=None,
    d_new=None,
    v_old=None,
    v_new=None,
    source_old=None,
    source_new=None,
    theta=1.0,
    dirichlet_mode="ghost",
    neumann_mode="ghost",
):
    """Advance ``u_t = F(u)`` with explicit old and new boundary data.

    ``theta=0`` is forward Euler, ``theta=1/2`` is Crank--Nicolson and
    ``theta=1`` is backward Euler.  The spatial operator combines conservative
    diffusion, power-law convection and a cell source.  A singular implicit
    system is reported by NumPy/SciPy; no clipping or iterative fallback is
    applied.
    """
    if not isinstance(var_old, CellVariable) or not isinstance(var_new, CellVariable):
        raise TypeError("var_old/var_new must be CellVariable")
    step = finite_scalar(dt, "dt")
    weight = finite_scalar(theta, "theta")
    if not np.isfinite(step) or step <= 0.0 or not np.isfinite(weight) or not 0.0 <= weight <= 1.0:
        raise ValueError("dt must be finite positive and theta in [0,1]")
    if var_old.value.shape != var_new.value.shape or not np.array_equal(var_old.face_centers, var_new.face_centers):
        raise ValueError("old/new grids must match")

    old_matrix, old_offset = _assemble_operator(
        var_old, d_old, v_old, source_old, dirichlet_mode, neumann_mode
    )
    new_matrix, new_offset = _assemble_operator(
        var_new, d_new, v_new, source_new, dirichlet_mode, neumann_mode
    )
    rhs = var_old.value + step * (
        (1.0 - weight) * old_matrix.matvec(var_old.value)
        + (1.0 - weight) * old_offset
        + weight * new_offset
    )
    if weight == 0.0:
        return replace(var_new, value=checked(rhs))

    lhs = TriDiagonal(
        1.0 - step * weight * new_matrix.diagonal,
        -step * weight * new_matrix.above,
        -step * weight * new_matrix.below,
    )
    from scipy.linalg import solve_banded

    updated = solve_banded((1, 1), lhs.to_banded(), rhs)
    return replace(var_new, value=checked(updated))

"""Conservative one-dimensional convection assembled on cell faces."""

import numpy as np

from .cell_variable import CellVariable, checked, finite_array
from .diffusion import TriDiagonal

__all__ = ["make_convection_terms"]


def _power_weight(peclet):
    """Evaluate the bounded power-law interpolation weight elementwise."""

    result = np.full_like(peclet, 0.5, dtype=float)
    high = peclet > 10.0
    low = peclet < -10.0
    result[high] = 1.0 - 1.0 / peclet[high]
    result[low] = -1.0 / peclet[low]
    middle_positive = (peclet > 1.0e-3) & (peclet <= 10.0)
    middle_negative = (peclet < -1.0e-3) & (peclet >= -10.0)
    result[middle_positive] = (
        (peclet[middle_positive] - 1.0) + (1.0 - peclet[middle_positive] / 10.0) ** 5
    ) / peclet[middle_positive]
    result[middle_negative] = ((1.0 + peclet[middle_negative] / 10.0) ** 5 - 1.0) / peclet[
        middle_negative
    ]
    return result


def make_convection_terms(v_face, d_face, var, dirichlet_mode="ghost", neumann_mode="ghost"):
    """Return ``(M, b)`` for the conservative flux ``-d(v*u)/dx``.

    Face values are assembled locally and differenced by cell width.  The
    coefficient arrays contain one finite value per face.  Dirichlet modes
    are ``ghost``, ``direct`` and ``semi-implicit``; Neumann modes are
    ``ghost`` and ``semi-implicit``.  Boundary gradients use the positive
    coordinate direction at both ends.
    """
    if not isinstance(var, CellVariable):
        raise TypeError("var must be CellVariable")
    if dirichlet_mode not in ("ghost", "direct", "semi-implicit"):
        raise ValueError("invalid convection boundary mode")
    if neumann_mode not in ("ghost", "semi-implicit"):
        raise ValueError("invalid convection boundary mode")

    n_cells = var.value.size
    velocity = finite_array(v_face, "v_face", (n_cells + 1,))
    diffusivity = finite_array(d_face, "d_face", (n_cells + 1,))
    widths = var.cell_widths
    face_spacing = np.concatenate(([widths[0]], var.cell_spacings, [widths[-1]]))
    scale = np.where(diffusivity < 0.0, -1.0, 1.0) * np.maximum(1.0e-20, np.abs(diffusivity))

    with np.errstate(all="ignore"):
        peclet = face_spacing * velocity / scale
        peclet[[0, -1]] /= 2.0
        left_weight = _power_weight(-peclet[:-1])
        right_weight = _power_weight(peclet[1:])
        diagonal = (left_weight * velocity[:-1] - right_weight * velocity[1:]) / widths
        upper = -(1.0 - right_weight[:-1]) * velocity[1:-1] / widths[:-1]
        lower = (1.0 - left_weight[1:]) * velocity[1:-1] / widths[1:]
        offset = np.zeros(n_cells, dtype=float)

        if var.left_face_constraint is not None:
            boundary = var.left_face_constraint
            if dirichlet_mode == "ghost":
                diagonal[0] = (
                    velocity[0] * (2.0 * left_weight[0] - 1.0) - velocity[1] * right_weight[0]
                ) / widths[0]
                offset[0] = 2.0 * velocity[0] * (1.0 - left_weight[0]) * boundary / widths[0]
            elif dirichlet_mode == "direct":
                diagonal[0] = -velocity[1] * right_weight[0] / widths[0]
                offset[0] = velocity[0] * boundary / widths[0]
            else:
                offset[0] = velocity[0] * (1.0 - left_weight[0]) * boundary / widths[0]
        else:
            diagonal[0] = (velocity[0] - right_weight[0] * velocity[1]) / widths[0]
            offset[0] = -velocity[0] * (1.0 - left_weight[0]) * var.left_face_grad_constraint
            if neumann_mode == "semi-implicit":
                offset[0] /= 2.0

        if var.right_face_constraint is not None:
            boundary = var.right_face_constraint
            if dirichlet_mode == "ghost":
                diagonal[-1] = (
                    velocity[-2] * left_weight[-1] + velocity[-1] * (1.0 - 2.0 * right_weight[-1])
                ) / widths[-1]
                offset[-1] = -2.0 * velocity[-1] * (1.0 - right_weight[-1]) * boundary / widths[-1]
            elif dirichlet_mode == "direct":
                diagonal[-1] = velocity[-2] * left_weight[-1] / widths[-1]
                offset[-1] = -velocity[-1] * boundary / widths[-1]
            else:
                offset[-1] = -velocity[-1] * (1.0 - right_weight[-1]) * boundary / widths[-1]
        else:
            diagonal[-1] = -(velocity[-1] - velocity[-2] * left_weight[-1]) / widths[-1]
            offset[-1] = -velocity[-1] * (1.0 - right_weight[-1]) * var.right_face_grad_constraint
            if neumann_mode == "semi-implicit":
                offset[-1] /= 2.0

    return TriDiagonal(checked(diagonal), checked(upper), checked(lower)), checked(offset)

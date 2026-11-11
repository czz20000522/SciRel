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
    """Assemble conservative power-law convection terms.

    Parameters
    ----------
    v_face : array-like, shape (N+1,)
        Face-centred convective coefficient [X/time].  The input is converted
        to finite float64 data and must have one value per cell face.
    d_face : array-like, shape (N+1,)
        Face-centred diffusivity used to form the local Peclet number
        [X^2/time].  The input is converted to finite float64 data and must
        have one value per cell face.
    var : CellVariable
        Cell values and boundary data for the same explicit one-dimensional
        face grid [Q].
    dirichlet_mode : {'ghost', 'direct', 'semi-implicit'}, default 'ghost'
        Reconstruction of a Dirichlet boundary face [1].  ``'ghost'`` adds a
        ghost-cell contribution, ``'direct'`` places the boundary value
        directly in the cell equation, and ``'semi-implicit'`` uses the
        corresponding half-cell contribution.
    neumann_mode : {'ghost', 'semi-implicit'}, default 'ghost'
        Reconstruction of a prescribed Neumann boundary flux [1].  Boundary
        gradients use the positive coordinate direction at both ends.

    Returns
    -------
    matrix : TriDiagonal
        Cell operator representing the convection contribution [1/time].
    forcing : ndarray of float64, shape (N,)
        Explicit boundary contribution to add to ``matrix @ var.value``
        [Q/time].

    Raises
    ------
    TypeError
        If ``var`` is not a ``CellVariable`` or an input cannot be converted
        to real numeric data.
    ValueError
        If an input is masked, non-finite, has the wrong shape, or if a
        boundary mode is not one of the documented choices.
    FloatingPointError
        If the assembled coefficients contain a non-finite result.

    See Also
    --------
    CellVariable : Cell and face data used by this operator.
    make_diffusion_terms : Assemble the two-point diffusion operator.
    theta_step : Combine old and new operators in a theta step.

    Notes
    -----
    The assembled expression is the conservative flux difference for
    ``-d(v*u)/dx``.  The local interpolation uses a bounded power-law weight
    based on the face Peclet number.  The Peclet scale floors ``abs(d_face)`` at
    ``1e-20`` and keeps the sign of ``d_face``.  The floor prevents division by zero
    for an exactly zero face diffusivity, and any nonzero magnitude below ``1e-20``
    is approximated by that floor, so such a face carries the floored Peclet number
    rather than its own.  The resulting matrix and forcing are
    returned as one ordinary ``(matrix, forcing)`` pair; no fallback or
    clipping of a non-finite result is applied.  The returned operator is
    valid for the supplied cell grid and must be rebuilt if that grid changes.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.fvm import CellVariable,make_convection_terms
    >>> v=CellVariable([1.,1.],[0.,1.,2.])
    >>> m,b=make_convection_terms([2.,2.,2.],[0.,0.,0.],v)
    >>> np.testing.assert_allclose(m.matvec(v.value)+b,0.)
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

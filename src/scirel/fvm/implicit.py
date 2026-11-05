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
    """Advance one finite-volume channel with a theta time step.

    Parameters
    ----------
    var_old : CellVariable
        Old cell values and old boundary data [Q].
    var_new : CellVariable
        Output grid and new boundary data [Q].  Its cell values are not used
        as a nonlinear iteration guess; they are replaced by the computed
        state.
    dt : float
        Positive time increment [time].  The value is converted to a finite
        float64 scalar.
    d_old : array-like or None, shape (N+1,), default None
        Old face diffusivity [X^2/time].  ``None`` omits the diffusion term;
        when supplied, the array must be finite and explicit.
    d_new : array-like or None, shape (N+1,), default None
        New face diffusivity [X^2/time].  ``None`` omits the diffusion term;
        when supplied, the array must be finite and explicit.
    v_old : array-like or None, shape (N+1,), default None
        Old face convective coefficient [X/time].  ``None`` omits convection;
        when supplied, the array must be finite and explicit.
    v_new : array-like or None, shape (N+1,), default None
        New face convective coefficient [X/time].  ``None`` omits convection;
        when supplied, the array must be finite and explicit.
    source_old : array-like or None, shape (N,), default None
        Old explicit cell source [Q/time].  ``None`` omits the source.
    source_new : array-like or None, shape (N,), default None
        New explicit cell source [Q/time].  ``None`` omits the source.
    theta : float, default 1.0
        Weight of the new-time operator [1].  ``0`` is forward Euler, ``0.5``
        is Crank--Nicolson, and ``1`` is backward Euler; the value must lie in
        ``[0, 1]``.
    dirichlet_mode : {'ghost', 'direct', 'semi-implicit'}, default 'ghost'
        Dirichlet boundary reconstruction strategy [1].
    neumann_mode : {'ghost', 'semi-implicit'}, default 'ghost'
        Neumann boundary reconstruction strategy [1].

    Returns
    -------
    variable : CellVariable
        New float64 cell values with the boundary data from ``var_new`` [Q].

    Raises
    ------
    TypeError
        If ``var_old`` or ``var_new`` is not a ``CellVariable``, or if a
        supplied source or coefficient cannot be converted to real numeric
        data.
    ValueError
        If ``dt`` or ``theta`` is outside its allowed range, the old and new
        grids differ, an array has the wrong shape, or a boundary mode is not
        one of the documented choices.
    FloatingPointError
        If an assembled or updated value is non-finite.
    numpy.linalg.LinAlgError
        If the implicit banded system is singular.

    See Also
    --------
    CellVariable : Cell and face data used by this time step.
    make_diffusion_terms : Assemble the diffusion contribution.
    make_convection_terms : Assemble the convection contribution.

    Notes
    -----
    The spatial operator is
    ``F(u) = diffusion_operator(u) + convection_operator(u) + source``.
    The update solves the theta-weighted equation
    ``u_new = u_old + dt * ((1-theta) * F(u_old) + theta * F(u_new))``
    with separately supplied old and new boundary data.  The explicit branch
    is evaluated directly; the implicit branch uses one banded linear solve.
    There is no clipping, positivity guarantee, adaptive time step, or
    iterative fallback.  A singular or non-finite system is reported as an
    error.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.fvm import CellVariable,theta_step
    >>> v=CellVariable([0.,0.],[0.,1.,2.])
    >>> x=theta_step(v,v,.2,source_old=[1.,1.],source_new=[1.,1.],theta=.5)
    >>> np.testing.assert_allclose(x.value,.2)
    """
    if not isinstance(var_old, CellVariable) or not isinstance(var_new, CellVariable):
        raise TypeError("var_old/var_new must be CellVariable")
    step = finite_scalar(dt, "dt")
    weight = finite_scalar(theta, "theta")
    if not np.isfinite(step) or step <= 0.0 or not np.isfinite(weight) or not 0.0 <= weight <= 1.0:
        raise ValueError("dt must be finite positive and theta in [0,1]")
    if var_old.value.shape != var_new.value.shape or not np.array_equal(
        var_old.face_centers, var_new.face_centers
    ):
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

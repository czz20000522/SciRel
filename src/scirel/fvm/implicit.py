# Derived from TORAX: Copyright 2024 DeepMind Technologies Limited.
# Apache-2.0; retained license: licenses/torax/LICENSE.
"""One-channel NumPy theta method bound to TORAX FVM operators."""
from dataclasses import replace
import numpy as np
from .cell_variable import CellVariable, checked, finite_array, finite_scalar
from .diffusion import TriDiagonal, make_diffusion_terms
from .convection import make_convection_terms


def _operator(var,d,v,source,dm,nm):
    n=len(var.value); diagonal=np.zeros(n); above=np.zeros(n-1); below=np.zeros(n-1); b=np.zeros(n)
    if d is not None:
        md,bd=make_diffusion_terms(d,var); diagonal+=md.diagonal; above+=md.above; below+=md.below; b+=bd
    if v is not None:
        if d is None: d=np.zeros(n+1)
        mc,bc=make_convection_terms(v,d,var,dm,nm); diagonal+=mc.diagonal; above+=mc.above; below+=mc.below; b+=bc
    if source is not None:
        s=finite_array(source,'source',(n,))
        if s.shape!=(n,): raise ValueError('source must have one value per cell')
        if not np.isfinite(s).all(): raise ValueError('source must be finite')
        b+=s
    return TriDiagonal(checked(diagonal),checked(above),checked(below)),checked(b)


def theta_step(var_old, var_new, dt, *, d_old=None, d_new=None, v_old=None, v_new=None, source_old=None, source_new=None, theta=1.0, dirichlet_mode='ghost', neumann_mode='ghost'):
    """Advance ``u_t = F(u)`` with TORAX's theta convention.

    ``var_old`` supplies old boundary data and ``var_new`` new boundary data;
    geometry must match. ``F=C u+c`` combines conservative diffusion,
    power-law convection and explicit source. ``theta=1`` is backward Euler,
    1/2 Crank--Nicolson and 0 forward Euler. ``dt`` must be finite and >0;
    theta must lie in [0,1]. Returns a replacement ``CellVariable`` carrying
    the new values and new boundary data. Singular linear systems raise
    ``numpy.linalg.LinAlgError``; no clipping or iterative fallback is used.
    """
    if not isinstance(var_old,CellVariable) or not isinstance(var_new,CellVariable): raise TypeError('var_old/var_new must be CellVariable')
    dt=finite_scalar(dt,'dt'); theta=finite_scalar(theta,'theta')
    if not np.isfinite(dt) or dt<=0 or not np.isfinite(theta) or not 0<=theta<=1: raise ValueError('dt must be finite positive and theta in [0,1]')
    if var_old.value.shape!=var_new.value.shape or not np.array_equal(var_old.face_centers,var_new.face_centers): raise ValueError('old/new grids must match')
    co,bo=_operator(var_old,d_old,v_old,source_old,dirichlet_mode,neumann_mode)
    cn,bn=_operator(var_new,d_new,v_new,source_new,dirichlet_mode,neumann_mode)
    rhs=var_old.value + dt*((1-theta)*co.matvec(var_old.value) + (1-theta)*bo + theta*bn)
    if theta == 0.0:
        return replace(var_new,value=checked(rhs))
    lhs=TriDiagonal(
        1.0-dt*theta*cn.diagonal,
        -dt*theta*cn.above,
        -dt*theta*cn.below,
    )
    from scipy.linalg import solve_banded
    return replace(var_new,value=checked(solve_banded((1,1),lhs.to_banded(),rhs)))



# Derived from TORAX: Copyright 2024 DeepMind Technologies Limited.
# Apache-2.0; retained license: licenses/torax/LICENSE.
"""TORAX power-law conservative convection; stable Péclet asymptotes."""
import numpy as np
from .cell_variable import CellVariable, finite_array, checked
from .diffusion import TriDiagonal


def _alpha(p):
    # Algebraic source branches, using 1-1/p avoids inf/inf for p=+inf.
    a=np.full(p.shape,.5)
    hi=p>10; lo=p<-10
    a[hi]=1-1/p[hi]; a[lo]=-1/p[lo]
    midp=(p>1e-3)&(p<=10); midn=(p<-1e-3)&(p>=-10)
    a[midp]=((p[midp]-1)+(1-p[midp]/10)**5)/p[midp]
    a[midn]=((1+p[midn]/10)**5-1)/p[midn]
    return a


def make_convection_terms(v_face,d_face,var,dirichlet_mode='ghost',neumann_mode='ghost'):
    """Return a ``(TriDiagonal, b)`` pair for -d/dx(v u)=M u+b, with TORAX power-law weights.

    v has coordinate/time units, D coordinate^2/time; both are finite N+1
    arrays. Relative v/D chooses the upstream face weighting. D is floored in
    magnitude at 1e-20 (zero takes positive sign), as in TORAX. Boundary Péclet
    distances are half cell widths. Modes: Dirichlet 'ghost' (default), 'direct',
    'semi-implicit'; Neumann 'ghost' (default) or 'semi-implicit'. Gradient means
    du/dx, not outward normal derivative. All modes conserve shared internal
    face fluxes on nonuniform meshes; no arbitrary-grid accuracy claim. The
    integrated conservation boundary flux uses the selected numerical face
    value, which can differ from the prescribed Dirichlet value in ghost mode.
    Pure convection reaches its finite upwind limit when the ratio overflows;
    unrepresentable final coefficients raise FloatingPointError.
    """
    if not isinstance(var,CellVariable): raise TypeError('var must be CellVariable')
    if dirichlet_mode not in ('ghost','direct','semi-implicit') or neumann_mode not in ('ghost','semi-implicit'): raise ValueError('invalid convection boundary mode')
    n=len(var.value); v=finite_array(v_face,'v_face',(n+1,)); d=finite_array(d_face,'d_face',(n+1,)); w=var.cell_widths
    spacing=np.r_[w[0],var.cell_spacings,w[-1]]
    dd=np.where(d<0,-1.,1.)*np.maximum(1e-20,np.abs(d))
    with np.errstate(all='ignore'):
        ratio=spacing*v/dd; ratio[[0,-1]]/=2
        la=_alpha(-ratio[:-1]); ra=_alpha(ratio[1:])
        diag=(la*v[:-1]-ra*v[1:])/w
        mat=np.diag(diag)+np.diag(-(1-ra[:-1])*v[1:-1]/w[:-1],1)+np.diag((1-la[1:])*v[1:-1]/w[1:],-1)
        b=np.zeros(n)
        if var.left_face_constraint is not None:
            z=var.left_face_constraint
            if dirichlet_mode=='ghost': mat[0,0]=(v[0]*(2*la[0]-1)-v[1]*ra[0])/w[0]; b[0]=2*v[0]*(1-la[0])*z/w[0]
            elif dirichlet_mode=='direct': mat[0,0]=-v[1]*ra[0]/w[0]; b[0]=v[0]*z/w[0]
            else: b[0]=v[0]*(1-la[0])*z/w[0]
        else:
            mat[0,0]=(v[0]-ra[0]*v[1])/w[0]; b[0]=-v[0]*(1-la[0])*var.left_face_grad_constraint
            if neumann_mode=='semi-implicit': b[0]/=2
        if var.right_face_constraint is not None:
            z=var.right_face_constraint
            if dirichlet_mode=='ghost': mat[-1,-1]=(v[-2]*la[-1]+v[-1]*(1-2*ra[-1]))/w[-1]; b[-1]=-2*v[-1]*(1-ra[-1])*z/w[-1]
            elif dirichlet_mode=='direct': mat[-1,-1]=v[-2]*la[-1]/w[-1]; b[-1]=-v[-1]*z/w[-1]
            else: b[-1]=-v[-1]*(1-ra[-1])*z/w[-1]
        else:
            mat[-1,-1]=-(v[-1]-v[-2]*la[-1])/w[-1]; b[-1]=-v[-1]*(1-ra[-1])*var.right_face_grad_constraint
            if neumann_mode=='semi-implicit': b[-1]/=2
    return TriDiagonal(checked(np.diag(mat)),checked(np.diag(mat,1)),checked(np.diag(mat,-1))),checked(b)

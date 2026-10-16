# Derived from TORAX: Copyright 2024 DeepMind Technologies Limited.
# Apache-2.0; retained license: licenses/torax/LICENSE.
"""Conservative TORAX two-point diffusion on explicit one-dimensional cells."""
import numpy as np
from .cell_variable import CellVariable, finite_array, checked

__all__ = ["TriDiagonal", "make_diffusion_terms"]


class TriDiagonal:
    def __init__(self, diagonal, above, below):
        self.diagonal=np.asarray(diagonal,dtype=float); self.above=np.asarray(above,dtype=float); self.below=np.asarray(below,dtype=float)
        n=self.diagonal.size
        if self.above.shape!=(n-1,) or self.below.shape!=(n-1,): raise ValueError('tridiagonal lengths mismatch')
    def to_dense(self):
        m=np.diag(self.diagonal.copy()); m+=np.diag(self.above,1)+np.diag(self.below,-1); return m
    def to_banded(self):
        """Return SciPy's ``solve_banded((1, 1), ...)`` representation."""
        return np.vstack((np.r_[0.0, self.above], self.diagonal, np.r_[self.below, 0.0]))
    def matvec(self,x):
        x=np.asarray(x,dtype=float)
        if x.ndim == 0 or x.shape[0] != self.diagonal.size:
            raise ValueError('x must have one value per tridiagonal row')
        out=self.diagonal.reshape((self.diagonal.size,)+(1,)*(x.ndim-1))*x
        out=np.array(out,copy=True)
        if self.diagonal.size > 1:
            out[:-1] += self.above.reshape((self.above.size,)+(1,)*(x.ndim-1))*x[1:]
            out[1:] += self.below.reshape((self.below.size,)+(1,)*(x.ndim-1))*x[:-1]
        return out


def make_diffusion_terms(d_face, var):
    """Return a ``(TriDiagonal, b)`` pair for +d/dx(D du/dx)=M u+b.

    D is N+1 finite face values, in coordinate^2/time for a diffusion equation.
    Signed coefficients retain the algebra; physical diffusion requires D>=0.
    Interior gradients use adjacent center spacing; boundary Dirichlet gradients
    use half-cell distances, Neumann data is positive-coordinate du/dx. Dividing
    flux differences by each cell width guarantees weighted conservation. No
    area/volume metric is inferred. Nonfinite arithmetic raises FloatingPointError.
    """
    if not isinstance(var,CellVariable): raise TypeError('var must be CellVariable')
    n=len(var.value); d=finite_array(d_face,'d_face',(n+1,)); w=var.cell_widths
    diagonal=np.zeros(n); above=np.zeros(n-1); below=np.zeros(n-1); b=np.zeros(n)
    with np.errstate(all='ignore'):
        conductance=d[1:-1]/var.cell_spacings
        for j,k in enumerate(conductance):
            diagonal[j]-=k/w[j]; above[j]+=k/w[j]
            below[j]+=k/w[j+1]; diagonal[j+1]-=k/w[j+1]
        if var.left_face_constraint is not None:
            k=2*d[0]/w[0]**2; diagonal[0]-=k; b[0]+=k*var.left_face_constraint
        else: b[0]-=d[0]*var.left_face_grad_constraint/w[0]
        if var.right_face_constraint is not None:
            k=2*d[-1]/w[-1]**2; diagonal[-1]-=k; b[-1]+=k*var.right_face_constraint
        else: b[-1]+=d[-1]*var.right_face_grad_constraint/w[-1]
    return TriDiagonal(checked(diagonal),checked(above),checked(below)),checked(b)

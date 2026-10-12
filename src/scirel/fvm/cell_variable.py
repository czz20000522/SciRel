# Derived from TORAX: Copyright 2024 DeepMind Technologies Limited.
# Apache-2.0; retained license: licenses/torax/LICENSE.
"""Explicit cell/face conventions derived from TORAX CellVariable.

The final internal Neumann derivative uses a derivative-constrained quadratic
reconstruction; the inherited linear boundary extrapolation is not used there.

Cell values live at arithmetic midpoints of strictly increasing faces. Values
are point samples, not cell averages; gradients use coordinate units of faces.
Boundary gradient means du/dx in the positive coordinate direction at BOTH ends,
not the outward normal derivative. This NumPy public variant is unbatched.
"""
from dataclasses import dataclass
import numpy as np


def finite_array(value, name, shape=None):
    if np.ma.isMaskedArray(value) and np.any(np.ma.getmaskarray(value)):
        raise ValueError(f'{name} must not be masked')
    if any(isinstance(x,(bool,np.bool_)) for x in np.asarray(value,dtype=object).flat):
        raise TypeError(f'{name} must be real numeric, not boolean')
    raw = np.asarray(value)
    if raw.dtype.kind not in 'iuf':
        raise TypeError(f'{name} must be real numeric')
    arr = np.array(raw, dtype=np.float64, copy=True)
    if shape is not None and arr.shape != shape:
        raise ValueError(f'{name} must have shape {shape}')
    if not np.isfinite(arr).all():
        raise ValueError(f'{name} must be finite')
    return arr


def finite_scalar(value, name):
    return float(finite_array(value, name, ()).item())


def checked(value):
    if not np.isfinite(value).all():
        raise FloatingPointError('nonfinite finite-volume result')
    return value


@dataclass(frozen=True)
class CellVariable:
    """One-dimensional point values with one value or gradient at each boundary.

    ``left_face_constraint/right_face_constraint=None`` select Neumann data;
    gradients then default to zero. Set the corresponding gradient to ``None``
    when supplying a Dirichlet value. N>=2; no inferred mesh or broadcasting.
    Invalid shapes, nonfinite data, nonincreasing faces and ambiguous boundaries
    raise ValueError; nonnumeric/complex inputs raise TypeError. Float64 output.
    """
    value: object
    face_centers: object
    left_face_constraint: object = None
    right_face_constraint: object = None
    left_face_grad_constraint: object = 0.0
    right_face_grad_constraint: object = 0.0

    def __post_init__(self):
        value = finite_array(self.value, 'value')
        if value.ndim != 1 or value.size < 2:
            raise ValueError('value must be one-dimensional with at least two cells')
        faces = finite_array(self.face_centers, 'face_centers', (value.size+1,))
        with np.errstate(over='ignore', invalid='ignore'):
            widths = np.diff(faces)
            centers = faces[:-1] + widths/2
        if not np.isfinite(widths).all() or np.any(widths <= 0) or not np.isfinite(centers).all() or np.any(np.diff(centers) <= 0):
            raise ValueError('face and midpoint spacings must be finite and positive')
        for name, arr in [('value',value),('face_centers',faces)]:
            arr.setflags(write=False)
            object.__setattr__(self,name,arr)
        for side in ('left','right'):
            vn, gn = f'{side}_face_constraint',f'{side}_face_grad_constraint'
            v,g = getattr(self,vn),getattr(self,gn)
            if (v is None)==(g is None):
                raise ValueError('exactly one boundary value or gradient is required at each end')
            for n,z in ((vn,v),(gn,g)):
                if z is not None: object.__setattr__(self,n,finite_scalar(z,n))

    @property
    def cell_widths(self): return np.diff(self.face_centers)
    @property
    def cell_centers(self): return self.face_centers[:-1] + self.cell_widths/2
    @property
    def cell_spacings(self): return np.diff(self.cell_centers)
    @property
    def left_face_value(self):
        return self.left_face_constraint if self.left_face_constraint is not None else self.value[0]-self.left_face_grad_constraint*self.cell_widths[0]/2
    @property
    def right_face_value(self):
        return self.right_face_constraint if self.right_face_constraint is not None else self.value[-1]+self.right_face_grad_constraint*self.cell_widths[-1]/2

    def face_value(self):
        """Linear interpolation internally; constrained or linearly extrapolated endpoints."""
        f,c=self.face_centers,self.cell_centers
        w=(f[1:-1]-c[:-1])/self.cell_spacings
        with np.errstate(all='ignore'):
            return checked(np.r_[self.left_face_value,(1-w)*self.value[:-1]+w*self.value[1:],self.right_face_value])

    def face_grad(self, *, two_point_mask=None):
        """TORAX three-point nonuniform derivative internally; endpoints follow BCs.

        On a uniform grid this reduces to adjacent-cell differences. On a
        nonuniform grid internal quadratic point samples are differentiated
        exactly when the boundary data match that polynomial. The last internal
        Neumann stencil fits the two final cell values and the actual boundary
        derivative; it does not use a linearly extrapolated boundary value.
        Dirichlet endpoints use a half-cell secant (first order for a
        quadratic). A boolean N+1 mask selects two-point internal gradients.
        """
        n=len(self.value); f,c=self.face_centers,self.cell_centers
        out=np.empty(n+1)
        for j in range(1,n):
            if j<n-1:
                xx=c[j-1:j+2]-f[j]; yy=self.value[j-1:j+2]
            elif self.right_face_constraint is None:
                # For q(x)=A*x**2+B*x+C, secant s=q[x0,x1] is
                # A*(x0+x1)+B. Hence q'(f)=s+(g-s)*(2*f-x0-x1)/
                # (2*b-x0-x1), where g=q'(b). Midpoint coordinates give
                # weight (w0-w1)/(w0+3*w1). Scale widths before summing.
                widths=self.cell_widths[-2:]
                w0,w1=widths/np.max(widths)
                weight=(w0-w1)/(w0+3*w1)
                secant=(self.value[-1]-self.value[-2])/self.cell_spacings[-1]
                out[j]=(1-weight)*secant+weight*self.right_face_grad_constraint
                continue
            else:
                xx=np.r_[c[-2:]-f[j],f[-1]-f[j]]; yy=np.r_[self.value[-2:],self.right_face_constraint]
            a,b,d=xx
            k1=(b+d)/(-a*a+a*b+a*d-b*d)
            k3=(-a-b)/(a*b-a*d-b*d+d*d)
            out[j]=k1*(yy[0]-yy[1])+k3*(yy[2]-yy[1])
        if two_point_mask is not None:
            mask=np.asarray(two_point_mask)
            if mask.dtype.kind!='b' or mask.shape!=(n+1,): raise ValueError('two_point_mask must be boolean N+1')
            out[1:-1]=np.where(mask[1:-1],np.diff(self.value)/self.cell_spacings,out[1:-1])
        out[0]=(self.value[0]-self.left_face_constraint)/(self.cell_widths[0]/2) if self.left_face_constraint is not None else self.left_face_grad_constraint
        out[-1]=(self.right_face_constraint-self.value[-1])/(self.cell_widths[-1]/2) if self.right_face_constraint is not None else self.right_face_grad_constraint
        return checked(out)

    def grad(self):
        """Cell finite-volume gradient: difference of interpolated face values / width."""
        return checked(np.diff(self.face_value())/self.cell_widths)

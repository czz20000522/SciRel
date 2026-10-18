"""Equilibrium-specific numerical helpers kept behind the legacy module path."""

import numpy as np

from scirel._anisotropic_numerics import (
    gradient_roundoff,
    pressure_divergence,
    residual_metrics,
    rms,
)
from scirel._numerics import stable_gradient


def cell_areas(R, Z, cell_edges=None):
    """Cross-section quadrature areas on the declared node domain by default.

    Without cell_edges, composite-trapezoid weights integrate over
    [min(R),max(R)] x [min(Z),max(Z)]; endpoints own half-neighbor intervals.
    For actual cell-center data, pass (radial_edges, axial_edges), each with
    one more value than centers, in the same orientation, enclosing its
    associated center. This explicitly binds the physical integration domain.
    The toroidal filament current has no 2*pi*R volume factor.
    """
    def widths(x, edges, radial=False):
        x = np.asarray(x,dtype=float)
        if x.size<2 or not np.all(np.isfinite(x)):
            raise ValueError('cell axes require at least two finite locations')
        d = np.diff(x)
        if not (np.all(d>0.) or np.all(d<0.)):
            raise ValueError('cell axes must be strictly monotone')
        if radial and np.min(x)<0.:
            raise ValueError('radial locations must be nonnegative')
        if edges is None:
            h=np.abs(d)
            return np.r_[h[0]/2,(h[:-1]+h[1:])/2,h[-1]/2]
        e=np.asarray(edges,dtype=float)
        if e.shape!=(x.size+1,) or not np.all(np.isfinite(e)):
            raise ValueError('cell edges must be finite and have center_count+1 entries')
        de=np.diff(e)
        if not np.all(de*np.sign(d[0])>0.):
            raise ValueError('cell edges must be strictly monotone in center orientation')
        if np.any(x<np.minimum(e[:-1],e[1:])) or np.any(x>np.maximum(e[:-1],e[1:])):
            raise ValueError('each center must lie within its declared cell edges')
        if radial and np.min(e)<0.:
            raise ValueError('radial cell edges must be nonnegative')
        return np.abs(de)
    if cell_edges is not None and (not isinstance(cell_edges,(tuple,list)) or len(cell_edges)!=2):
        raise ValueError('cell_edges must be (radial_edges, axial_edges)')
    re,ze=(None,None) if cell_edges is None else cell_edges
    return widths(Z[:,0],ze)[:,None]*widths(R[0],re,True)[None,:]


def flux_field_increment(R,Z,psi):
    """Differentiate an added psi on increasing axes (linear for two nodes).

    This preserves the feedback leaf's two-node contract; with three or more
    nodes each axis uses the quadratic stencil. A regular axis has BR=0 and
    BZ=2*(psi(R1)-psi(0))/R1**2, consistent to second order for even psi.
    """
    r,z=R[0],Z[:,0]
    def derivative(f,x,axis):
        if x.size>=3:
            return stable_gradient(f,x,axis)
        slope=np.diff(f,axis=axis)/(x[1]-x[0])
        return np.repeat(slope,2,axis=axis)
    dr,dz=derivative(psi,r,1),derivative(psi,z,0)
    br=np.divide(-dz,R,out=np.zeros_like(psi),where=R>0.)
    bz=np.divide(dr,R,out=np.zeros_like(psi),where=R>0.)
    if r[0]==0.:
        bz[:,0]=2*(psi[:,1]-psi[:,0])/r[1]**2
    return {'B_R':br,'B_Z':bz}

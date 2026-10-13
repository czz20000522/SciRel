"""Parametric Pleiades field lines with corrected curvature and bounded crossings.

Selective recovery from accepted D2 FieldLine/HelperFieldLine after maintained
exclusion. The Mac D2 successor resolves cubic physical-component interpolation
on complete rectilinear grids with tensor splines and on scattered support with
a tightly converged Clough-Tocher gradient estimate. Curvature differentiates
geometry and normalized B in one common local curve parameter, then applies
sign(p_prime dot bhat) b_prime / abs(p_prime). This avoids the polygonal chord
metric bias while retaining public d_ds_arclength's three-point contract.
Curvature requires actual smooth magnetic field lines; a nonzero tangent
projection alone cannot certify tangency. Reversing B preserves kappa.
Open vertices keep supplied order, preventing cyclic rolls from creating an
artificial internal jump. Closed periodic FITPACK interpolation is retained.
Intersections use bounded distance solves and reject numerical noncrossings or
multiple found crossings; this is not a complete topology/tangency certificate.
Field nulls, out-of-support queries and nonfinite field interpolation reject.
get_kappa_n_2 remains a uniform-grid, nonzero-flux-gradient method, not an axis
limit. No physical stability claim is supplied.
"""


import numpy as np


def d_ds_arclength(vertices, values):
    """Differentiate values along vertices using their actual cumulative arc length.

    Supports finite 1-D values sampled at finite 2-D vertices with strictly
    positive adjacent segment lengths.  Endpoint formulas are second-order
    one-sided finite differences on the nonuniform coordinate; interior values
    use the three-point quadratic derivative.
    """
    p = np.asarray(vertices, dtype=float)
    q = np.asarray(values, dtype=float)
    if p.ndim != 2 or p.shape[1] != 2 or q.ndim != 1 or q.size != p.shape[0] or q.size < 3:
        raise ValueError("vertices must be (N,2), values must be (N,), N >= 3")
    if not (np.all(np.isfinite(p)) and np.all(np.isfinite(q))):
        raise ValueError("vertices and values must be finite")
    ds = np.linalg.norm(np.diff(p, axis=0), axis=1)
    if np.any(ds <= 0.0):
        raise ValueError("adjacent vertices must be distinct")
    s = np.r_[0.0, np.cumsum(ds)]
    out = np.empty_like(q, dtype=float)
    # Interior: derivative of the quadratic through each local triplet.
    h0, h1 = s[1:-1] - s[:-2], s[2:] - s[1:-1]
    out[1:-1] = (h0 * (q[2:] - q[1:-1]) / h1 + h1 * (q[1:-1] - q[:-2]) / h0) / (h0 + h1)
    # One-sided quadratic derivatives at the endpoints.
    h0, h1 = s[1] - s[0], s[2] - s[1]
    out[0] = -(2.0 * h0 + h1) / (h0 * (h0 + h1)) * q[0] + (h0 + h1) / (h0 * h1) * q[1] - h0 / (h1 * (h0 + h1)) * q[2]
    h0, h1 = s[-1] - s[-2], s[-2] - s[-3]
    out[-1] = (2.0 * h0 + h1) / (h0 * (h0 + h1)) * q[-1] - (h0 + h1) / (h0 * h1) * q[-2] + h0 / (h1 * (h0 + h1)) * q[-3]
    return out


from scipy.interpolate import griddata, CloughTocher2DInterpolator, RectBivariateSpline
from scipy.interpolate import splprep,splev
from scipy.optimize import least_squares

def _sample_fieldline(vertices, R, Z, Q, method, filter_nonfinite):
    """Interpolate physical samples without degrading a complete tensor grid.

    Cubic rectangular data use an interpolating tensor-product spline, with
    explicit support masking (FITPACK itself would extrapolate). Scattered or
    incomplete data retain Clough-Tocher, with gradient estimation resolved to
    1e-12 rather than griddata's default 1e-6. Linear/nearest remain griddata.
    The two public classes retain their distinct finite-Q filtering behavior.
    """
    R, Z, Q = (np.asarray(v) for v in (R, Z, Q))
    if (method == "cubic" and not np.iscomplexobj(Q) and R.ndim == 2 and
            min(R.shape) >= 4 and Z.shape == R.shape == Q.shape and
            all(np.all(np.isfinite(v)) for v in (R, Z, Q)) and
            np.array_equal(R, np.broadcast_to(R[0], R.shape)) and
            np.array_equal(Z, np.broadcast_to(Z[:, 0, None], Z.shape))):
        x, y, q = R[0].copy(), Z[:, 0].copy(), Q.copy()
        if np.all(np.diff(x) < 0):
            x, q = x[::-1], q[:, ::-1]
        if np.all(np.diff(y) < 0):
            y, q = y[::-1], q[::-1, :]
        if np.all(np.diff(x) > 0) and np.all(np.diff(y) > 0):
            vr, vz = vertices[:, 0], vertices[:, 1]
            inside = (np.isfinite(vr) & np.isfinite(vz) &
                      (vr >= x[0]) & (vr <= x[-1]) &
                      (vz >= y[0]) & (vz <= y[-1]))
            result = np.full(len(vertices), np.nan)
            spline = RectBivariateSpline(y, x, q, kx=3, ky=3, s=0)
            result[inside] = spline.ev(vz[inside], vr[inside])
            # Enforce the exact interpolation constraint at supplied nodes,
            # including field nulls; no absolute magnetic-field cutoff.
            ix = np.clip(np.searchsorted(x, vr), 0, len(x)-1)
            iy = np.clip(np.searchsorted(y, vz), 0, len(y)-1)
            nodes = inside & (vr == x[ix]) & (vz == y[iy])
            result[nodes] = q[iy[nodes], ix[nodes]]
            return result
    idx = np.isfinite(Q.ravel()) if filter_nonfinite else np.ones(Q.size, dtype=bool)
    points = np.column_stack((R.ravel()[idx], Z.ravel()[idx]))
    values = Q.ravel()[idx]
    query = (vertices[:, 0], vertices[:, 1])
    if method == "cubic":
        return CloughTocher2DInterpolator(points, values, tol=1e-12)(*query)
    return griddata(points, values, xi=query, method=method)


def _curve_curvature(vertices, br, bz):
    """Differentiate direction and geometry in the same local curve parameter.

    For a genuine smooth field line p(t), kappa=sign(p' dot b)*b'/|p'|.
    Common polynomial derivative weights cancel the leading chord-coordinate
    scale error. Five local points give quartic derivatives; N=3/4 uses the
    available quadratic/cubic stencil. Public polygonal d_ds stays unchanged.
    """
    p = np.asarray(vertices, dtype=float)
    field = np.column_stack((br, bz))
    if (p.ndim != 2 or p.shape[1] != 2 or len(p) < 3 or
            field.shape != p.shape or not np.all(np.isfinite(p))):
        raise ValueError("curvature requires finite vertices (N,2), N >= 3")
    magnitude = np.hypot(field[:, 0], field[:, 1])
    if not (np.all(np.isfinite(magnitude)) and np.all(magnitude > 0)):
        raise ValueError("curvature requires finite nonzero field inside interpolation support")
    ds = np.linalg.norm(np.diff(p, axis=0), axis=1)
    if np.any(ds <= 0):
        raise ValueError("adjacent vertices must be distinct")
    t = np.r_[0., np.cumsum(ds)]
    b = field / magnitude[:, None]
    values = np.column_stack((p, b))
    derivative = np.empty_like(values)
    width = min(5, len(p))
    for i in range(len(p)):
        start = min(max(i-width//2, 0), len(p)-width)
        local = t[start:start+width]-t[i]
        scale = np.max(np.abs(local))
        x = local/scale
        moments = np.zeros(width)
        moments[1] = 1.
        weights = np.linalg.solve(np.vander(x, N=width, increasing=True).T, moments)/scale
        # Subtract the central value to avoid cancellation under translation.
        derivative[i] = weights @ (values[start:start+width]-values[i])
    tangent, db = derivative[:, :2], derivative[:, 2:]
    speed = np.linalg.norm(tangent, axis=1)
    direction = np.sign(np.sum(tangent*b, axis=1))
    if not (np.all(np.isfinite(speed)) and np.all(speed > 0) and
            np.all(np.isfinite(direction)) and np.all(direction != 0)):
        raise ValueError("curvature requires finite nonzero tangent-aligned field")
    return direction[:, None]*db/speed[:, None]


def _bounded_intersection(line,boundary):
    lower = np.array([float(line.u.min()),float(boundary.u.min())])
    upper = np.array([float(line.u.max()),float(boundary.u.max())])
    geometry = np.vstack((line.verts,boundary.verts))
    tolerance = 1e-9*max(1.,float(np.max(np.ptp(geometry,axis=0))))
    def separation(uv):
        return np.asarray(line.interpolate(uv[0]))-np.asarray(boundary.interpolate(uv[1]))
    roots=[]
    for u in np.linspace(lower[0],upper[0],7):
        for v in np.linspace(lower[1],upper[1],7):
            result=least_squares(separation,[u,v],bounds=(lower,upper),
                                 xtol=1e-13,ftol=1e-13,gtol=1e-13)
            if result.success and np.linalg.norm(separation(result.x)) <= tolerance:
                if not any(np.linalg.norm(result.x-root) < 1e-6 for root in roots):
                    roots.append(result.x)
    if not roots:
        raise ValueError("no intersection found within fitted parameter intervals")
    if len(roots)>1:
        raise ValueError("multiple intersections found; crossing selection is undefined")
    return float(roots[0][0])


class FieldLineSet(object):
    def __init__(self,contourset,**kwargs):
        self.flset = {}
        for ilev,lev in enumerate(contourset.levels):
            fllist = [FieldLine(lev,seg,**kwargs) for seg in contourset.allsegs[ilev]]
            self.flset[lev] = fllist 

class FieldLine(object):
    def __init__(self,psi,verts,**kwargs):
        self.psi = psi
        self._verts = verts
        self._interpolate_verts(**kwargs)
        self.reorder_verts()

    def is_closed(self):
        return np.all(self._verts[0,:] == self._verts[-1,:])

    def _interpolate_verts(self,u=None,s=0.0,k=2,npts=1000):
        if self.is_closed():
            per = 1
        else:
            per = 0
        tck,u = splprep(self._verts.T,u=u,k=k,s=s,per=per)
        u_new = np.linspace(u.min(),u.max(),npts)
        self.tck = tck
        self.u = u_new
        r_new,z_new = splev(u_new,tck,der=0)
        self.verts = np.vstack((r_new,z_new)).T

    def interpolate(self,u):
        return splev(u,self.tck,der=0)

    def reorder_verts(self,steptol=0.1):
        """Retain ordered spline samples; open paths cannot be cyclically rolled."""
        return None

    def get_svec(self):
        s = np.zeros(self.verts.shape[0])
        r,z = self.verts[:,0], self.verts[:,1]
        s[1:] = np.cumsum(np.sqrt((r[1:]-r[0:-1])**2+(z[1:]-z[0:-1])**2))
        return s

    def get_length(self):
        return self.get_svec()[-1]

    def get_ds(self):
        r,z = self.verts[:,0], self.verts[:,1]
        return np.sqrt((r[1]-r[0])**2+(z[1]-z[0])**2)

    def interpolate_onto(self,R,Z,Q,method="cubic"):
        return _sample_fieldline(self.verts, R, Z, Q, method, filter_nonfinite=True)

    def get_kappa_n(self,R,Z,BR,BZ,method="cubic"):
        # Normalize the interpolated physical vector, not its grid-node direction.
        br = self.interpolate_onto(R,Z,BR,method=method)
        bz = self.interpolate_onto(R,Z,BZ,method=method)
        return _curve_curvature(self.verts, br, bz)

    def get_kappa_n_2(self,R,Z,psi,method="cubic"):
        # The inherited stencil is defined only on a finite uniform xy grid.
        if any(np.iscomplexobj(v) for v in (R,Z,psi)):
            raise ValueError("flux curvature requires real grid and flux")
        R,Z,psi=(np.asarray(v,dtype=float) for v in (R,Z,psi))
        if (R.ndim!=2 or min(R.shape)<3 or Z.shape!=R.shape or psi.shape!=R.shape or
                not all(np.all(np.isfinite(v)) for v in (R,Z,psi))):
            raise ValueError("finite matching 2-D grid and flux, at least three nodes per axis required")
        if not (np.array_equal(R,np.broadcast_to(R[0,:],R.shape)) and
                np.array_equal(Z,np.broadcast_to(Z[:,0,None],Z.shape))):
            raise ValueError("flux curvature requires separable uniform xy grid")
        dx,dz=R[0,1]-R[0,0],Z[1,0]-Z[0,0]
        eps=np.finfo(float).eps
        rtol=16*eps*max(np.max(np.abs(R)),np.ptp(R))
        ztol=16*eps*max(np.max(np.abs(Z)),np.ptp(Z))
        if (dx==0 or dz==0 or not np.allclose(np.diff(R[0]),dx,rtol=0,atol=rtol) or
                not np.allclose(np.diff(Z[:,0]),dz,rtol=0,atol=ztol)):
            raise ValueError("flux curvature requires nondegenerate uniform xy grid")
        dpsidz, dpsidr = np.gradient(psi,dz,dx)
        modgpsi = np.hypot(dpsidr,dpsidz)
        if not (np.all(np.isfinite(modgpsi)) and np.all(modgpsi>0)):
            raise ValueError("flux curvature is undefined on zero or nonfinite gradient support")
        gz1, gr1 = np.gradient(-1.0/modgpsi*dpsidz,dz,dx)
        gz2, gr2 = np.gradient(1.0/modgpsi*dpsidr,dz,dx)
        kap_r = 1.0/modgpsi*(dpsidr*gz1 - dpsidz*gr1)
        kap_z = 1.0/modgpsi*(dpsidr*gz2 - dpsidz*gr2)
        kapr_terp = self.interpolate_onto(R,Z,kap_r,method=method)
        kapz_terp = self.interpolate_onto(R,Z,kap_z,method=method)
        if not (np.all(np.isfinite(kapr_terp)) and np.all(np.isfinite(kapz_terp))):
            raise ValueError("flux curvature queries must be inside finite interpolation support")
        return np.vstack((kapr_terp,kapz_terp)).T

    def d_ds(self,Q):
        return d_ds_arclength(self.verts, Q)

    def get_gradpsi(self,R,Z,BR,BZ,method="cubic"):
        gradpsi_r = self.interpolate_onto(R,Z,R*BZ,method=method)
        gradpsi_z = -self.interpolate_onto(R,Z,R*BR,method=method)
        return gradpsi_r,gradpsi_z

    def intersection(self,boundary):
        """Locate one numerical crossing in the finite fitted parameter intervals.

        Raises ValueError for no accepted crossing or multiple located crossings.
        A finite multistart search cannot certify all tangencies or spline roots.
        """
        return _bounded_intersection(self,boundary)

    def apply_boundary(self,b1,b2):
        # Commit terminal bounds only after both crossing solves succeed.
        u0, u1 = self.intersection(b1), self.intersection(b2)
        self.ubound0, self.ubound1 = u0, u1

    def get_bounded_fl(self,npts=1000):
        return self.interpolate(np.linspace(self.ubound0,self.ubound1,npts))
    
def contour_points(contourset):
    condict = {}
    for ilev, lev in enumerate(contourset.levels):
        condict[lev] = [FieldLine(lev,seg) for seg in contourset.allsegs[ilev]]
    return condict


class Boundary(object):
    def __init__(self,vertices):
        self._interpolate_verts(vertices)

    def _interpolate_verts(self,vertices,u=None,s=0.0,npts=200):
        tck,u = splprep(vertices.T,u=u,s=s)
        u_new = np.linspace(u.min(),u.max(),npts)
        self.tck = tck
        self.u = u_new
        r_new,z_new = splev(u_new,tck,der=0)
        self.verts = np.vstack((r_new,z_new)).T

    def interpolate(self,u):
        return splev(u,self.tck,der=0)


class HelperFieldLine(object):
    def __init__(self,psi,verts):
        self.psi = psi
        self._verts = verts
        self._interpolate_verts()
        self.reorder_verts()

    def is_closed(self):
        return np.all(self._verts[0,:] == self._verts[-1,:])

    def _interpolate_verts(self,u=None,s=0.0,k=2,npts=1000):
        if self.is_closed():
            per = 1
        else:
            per = 0
        tck,u = splprep(self._verts.T,u=u,k=k,s=s,per=per)
        u_new = np.linspace(u.min(),u.max(),npts)
        self.tck = tck
        self.u = u_new
        r_new,z_new = splev(u_new,tck,der=0)
        self.verts = np.vstack((r_new,z_new)).T

    def interpolate(self,u):
        return splev(u,self.tck,der=0)

    def reorder_verts(self,steptol=0.1):
        """Retain ordered spline samples; open paths cannot be cyclically rolled."""
        return None

    def get_svec(self):
        s = np.zeros(self.verts.shape[0])
        r,z = self.verts[:,0], self.verts[:,1]
        s[1:] = np.cumsum(np.sqrt((r[1:]-r[0:-1])**2+(z[1:]-z[0:-1])**2))
        return s

    def get_length(self):
        return self.get_svec()[-1]

    def get_ds(self):
        r,z = self.verts[:,0], self.verts[:,1]
        return np.sqrt((r[1]-r[0])**2+(z[1]-z[0])**2)

    def interpolate_onto(self,R,Z,Q,method="cubic"):
        return _sample_fieldline(self.verts, R, Z, Q, method, filter_nonfinite=False)

    def get_kappa_n(self,R,Z,BR,BZ,method="cubic"):
        # Normalize the interpolated physical vector, not its grid-node direction.
        br = self.interpolate_onto(R,Z,BR,method=method)
        bz = self.interpolate_onto(R,Z,BZ,method=method)
        value = _curve_curvature(self.verts, br, bz)
        return value[:, 0], value[:, 1]

    def d_ds(self,Q):
        return d_ds_arclength(self.verts, Q)

    def get_gradpsi(self,R,Z,BR,BZ,method="cubic"):
        gradpsi_r = self.interpolate_onto(R,Z,R*BZ,method=method)
        gradpsi_z = -self.interpolate_onto(R,Z,R*BR,method=method)
        return gradpsi_r,gradpsi_z

    def intersection(self,boundary):
        """Locate one numerical crossing in the finite fitted parameter intervals.

        Raises ValueError for no accepted crossing or multiple located crossings.
        A finite multistart search cannot certify all tangencies or spline roots.
        """
        return _bounded_intersection(self,boundary)

    def apply_boundary(self,b1,b2):
        # Commit terminal bounds only after both crossing solves succeed.
        u0, u1 = self.intersection(b1), self.intersection(b2)
        self.ubound0, self.ubound1 = u0, u1

    def get_bounded_fl(self,npts=1000):
        return self.interpolate(np.linspace(self.ubound0,self.ubound1,npts))

def helper_contour_points(contourset):
    condict = {}
    for ilev, lev in enumerate(contourset.levels):
        condict[lev] = [HelperFieldLine(lev,seg) for seg in contourset.allsegs[ilev]]
    return condict


__all__ = ['d_ds_arclength', 'FieldLineSet', 'FieldLine', 'HelperFieldLine', 'Boundary', 'contour_points', 'helper_contour_points']

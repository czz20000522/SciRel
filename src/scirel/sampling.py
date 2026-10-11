"""Pleiades grid sampling, finite differences and line-integral utilities.

Derived from helpers.py:160-182,212-253,275-415 (frozen D0 be412aa14b77).
Scientific conventions are explicit: regular_grid defaults to ij indexing;
locs_to_vals/interp require xy-style separable grids; poly_fit retains the
absolute SVD cutoff 1e-10; reflect_and_hstack assumes a radius-zero first
column and reflects scalar/even quantities. It is not a vector parity rule.
flux_surface_avg computes integral(Q/B ds)/integral(1/B ds), or the latter
integral alone. It does not supply toroidal 2pi factors or close open lines.
Support requires finite B>0 along supplied finite path and queries within
rectangular interpolation support. Units follow the supplied data: length
coordinate, B field and Q; integral(1/B ds) has length/field units.

D2 corrects parse_segment's unconditional omission of the terminal vertex.
The nearest requested endpoint is included. diff_central absorbs the shared
quadratic nonuniform operator; its qualified domain is finite monotone x.
"""
import numpy as np
import scipy.integrate
from scipy.interpolate import griddata, RectBivariateSpline
from .numerics import diff_12_central

def regular_grid(xx,yy,*args,**kwargs):
    # Named scientific port for exact documents; preserve positional source calls.
    values = kwargs.pop("values", None)
    if values is not None:
        if args:
            raise ValueError("supply fields either positionally or through values")
        args = tuple(values)
    nx = kwargs.pop("nx",200)
    ny = kwargs.pop("ny",200)
    xi = kwargs.pop("xi",None)
    yi = kwargs.pop("yi",None)
    method = kwargs.pop("method","linear")
    """ interpolate irregularly gridded data onto regular grid."""
    if xi is not None and yi is not None:
        pass
    else:
        x = np.linspace(xx.min(), xx.max(), nx)
        y = np.linspace(yy.min(), yy.max(), ny)
        xi, yi = np.meshgrid(x,y,indexing="ij")

    #then, interpolate your data onto this grid:
    points = np.vstack((xx.flatten(),yy.flatten())).T
    zs = []
    for z in args:
        zi = griddata(points,z.flatten(),(xi,yi),method=method)
        zs.append(zi)
    
    return (xi,yi) + tuple(zs)

def poly_fit(x,y,order=3):
    n = order+1
    m = len(y)
    basis_fns = [(lambda z,i=i: z**i) for i in range(n)]
    A = np.zeros((m,n))
    for i in range(m):
        for j in range(n):
            A[i,j] = basis_fns[j](x[i])
    (u,s,vt) = np.linalg.svd(A)
    Sinv = np.zeros((n,m))
    s[ s<1.0e-10 ] = 0.0
    s[ s>=1.0e-10 ] = 1.0/s[ s>=1.0e-10]
    Sinv[:len(s),:len(s)] = np.diag(s)
    c = np.dot(Sinv,u.T)
    c = np.dot(vt.T,c)
    c = np.dot(c,y)
    return basis_fns,c

def reflect_and_hstack(Rho, Z, *args, quantities=None):
    """Reflect and concatenate grid and quantities in args to plot both half
    planes (rho>=0 and rho<=0). Currently this function only reflects across
    the z axis since that is the symmetry convention we've taken for the
    machine.

    Parameters
    ----------
    Rho : np.array
        2D array for the R coordinates of the grid
    Z : np.array
        2D array for the Z coordinates of the grid
    args : tuple
        2D arrays of any quantity on this grid you wish to plot in both half
        planes
    """
    # Named scalar-field port preserves the original variadic positional API.
    if quantities is not None:
        if args:
            raise ValueError("supply fields either positionally or through quantities")
        args = tuple(quantities)
    Rho_total = np.hstack((-Rho[:,-1:0:-1],Rho))
    Z_total = np.hstack((Z[:,-1:0:-1],Z))
    arglist = []
    for arg in args:
        assert arg.shape == Rho.shape
        arglist.append(np.hstack((arg[:,-1:0:-1],arg)))
    return (Rho_total,Z_total)+tuple(arglist)

def transform_to_rtheta(Rho,Z,rho_component,z_component):
    """Meridional spherical position/vector mapping; theta from +Z toward +R.

    Coordinates have caller length units, theta is radians, vector units are
    unchanged. The origin has no polar basis. D2 corrects the source plus sign
    in pi/2+atan2(Z,Rho), which reflected Z under the stated inverse convention.
    """
    rho,z,urho,uz=np.broadcast_arrays(*[np.asarray(v,dtype=float) for v in
                                      (Rho,Z,rho_component,z_component)])
    if not all(np.all(np.isfinite(v)) for v in (rho,z,urho,uz)):
        raise ValueError("polar mapping inputs must be finite")
    radius=np.hypot(rho,z)
    if np.any(radius==0):raise ValueError("polar basis is undefined at the origin")
    theta=np.arctan2(rho,z)
    sin_t,cos_t=rho/radius,z/radius
    return radius,theta,urho*sin_t+uz*cos_t,urho*cos_t-uz*sin_t


def transform_to_rhoz(R,Theta,r_component,theta_component):
    """Inverse meridional polar position and orthonormal vector projection."""
    r,t,ur,ut=np.broadcast_arrays(*[np.asarray(v,dtype=float) for v in
                                  (R,Theta,r_component,theta_component)])
    if not all(np.all(np.isfinite(v)) for v in (r,t,ur,ut)) or np.any(r<=0):
        raise ValueError("finite polar inputs and positive radius required; origin basis undefined")
    sin_t,cos_t=np.sin(t),np.cos(t)
    return r*sin_t,r*cos_t,ur*sin_t+ut*cos_t,ur*cos_t-ut*sin_t


def locs_to_vals(X,Y,Q,coord_list):
    """Picks values of field Q at desired coordinates.

    Args:
        X (2D array): grid representing column coordinates of Q
        Y (2D array): grid representing row coordinates of Q
        Q (2D array): value of Q on grid
        coord_list (list):list of tuples (x,y) for desired coordinates
    """
    q_vals = []
    for x,y in coord_list:
        x0_idx,y0_idx = np.argmin(np.abs(X[0,:]-x)),np.argmin(np.abs(Y[:,0]-y))
        q_vals.append(Q[y0_idx,x0_idx])
    return q_vals

def locs_to_vals_griddata(X,Y,Q,coord_list):
    """Picks values of field Q at desired coordinates.

    Args:
        X (2D array): grid representing column coordinates of Q
        Y (2D array): grid representing row coordinates of Q
        Q (2D array): value of Q on grid
        coord_list (list):list of tuples (x,y) for desired coordinates
    """
    xi,yi = zip(*coord_list)
    return griddata((X.flatten(),Y.flatten()),Q.flatten(),(xi,yi))

def locs_to_vals1D(X,Y,Q,coord_list):
    """Picks values of field Q at desired coordinates.

    Args:
        X (2D array): grid representing column coordinates of Q
        Y (2D array): grid representing row coordinates of Q
        Q (2D array): value of Q on grid
        coord_list (list):list of tuples (x,y) for desired coordinates
    """
    q_vals = []
    for x,y in coord_list:
        idx = ((X-x)**2 + (Y-y)**2).argmin()
        q_vals.append(np.asarray(Q).ravel()[idx])
    return q_vals

def get_fieldlines(contourset,level,start_coord=None,end_coord=None,clockwise=True,idx_check=[]):
    """Return coordinates for segments comprising a flux surface (Nx2 array).

    Args:
        contourset (matplotlib.contour.QuadContourSet instance): i.e.
        ax.contour call
        level (float): desired contour level
        start_coord (tuple): coordinate (x,y) at which to start the field line
        end_coord (tuple): coordinate (x,y) at which to end the field line
        clockwise (bool): whether to order the field line coordinates clockwise or
        counterclockwise
    """
    ## Find desired flux surface and get its vertices
    assert level in list(contourset.levels), "level: {0} not found in contourset".format(level)
    idx = list(contourset.levels).index(level)
    segs = contourset.allsegs[idx]
    len_list = [s.shape[0] for s in segs]
    max_idx = len_list.index(max(len_list))
    flpoints = parse_segment(segs[max_idx],start_coord=start_coord,end_coord=end_coord,clockwise=clockwise)
#    if idx in idx_check:
#        fig_pts,ax_pts = plt.subplots()
#        fig_B,ax_B = plt.subplots()
#        for i,pts in enumerate(segs):
#            tmp_pts = parse_segment(pts,start_coord=start_coord,end_coord=end_coord,clockwise=clockwise)
#            ax_pts.plot(tmp_pts[:,0],tmp_pts[:,1],"o")
#            ax_pts.plot(tmp_pts[0,0],tmp_pts[0,1],"go")
#            ax_pts.plot(tmp_pts[-1,0],tmp_pts[-1,1],"ro")
#            ax_pts.set_xlim(0,2.50)
#            ax_pts.set_ylim(-1.25,1.25)
#            ax_pts.set_aspect(1)
#            B_interp = interp(Rho,Z,B,tmp_pts)
#            s = get_fieldline_distance(tmp_pts)
#            ax_B.plot(s,B_interp,"o")
#        plt.show()
    return flpoints

def parse_segment(flpoints,start_coord=None,end_coord=None,clockwise=True):
    if start_coord is not None:
        i_start = np.argmin(np.array([x0**2+y0**2 for x0,y0 in zip(flpoints[:,0]-start_coord[0],flpoints[:,1]-start_coord[1])]))
        flpoints = np.roll(flpoints,-i_start,axis=0)
    ## Find out if curve is cw or ccw
    x = flpoints[:,0]
    y = flpoints[:,1]
    iscw = np.sum((x[1:]-x[0:-1])*(y[1:]+y[0:-1]))+(x[0]-x[-1])*(y[0]+y[-1]) > 0
    if clockwise != iscw:
        flpoints = np.roll(flpoints[::-1,:],1,axis=0)
    i_end = len(x)
    if end_coord is not None:
        i_end = np.argmin(np.array([x0**2+y0**2 for x0,y0 in zip(flpoints[:,0]-end_coord[0],flpoints[:,1]-end_coord[1])]))
        i_end += 1
    flpoints = flpoints[0:i_end,:]
    return flpoints

def get_fieldline_distance(flpoints):
    """Return cumulative field line distance vector
    """
    s = np.zeros(flpoints.shape[0])
    x = flpoints[:,0]
    y = flpoints[:,1]
    s[1:] = np.cumsum(np.sqrt((x[1:]-x[0:-1])**2+(y[1:]-y[0:-1])**2))
    return s

def interp(Rho,Z,Q,flpoints):
    """interpolate quantity Q on Rho, Z grid onto flpoints (Nx2 array of x,y pairs).
    """
    x0 = Rho[0,:].squeeze()
    y0 = Z[:,0].squeeze()
    f = RectBivariateSpline(y0,x0,Q)
    return np.array([float(f(yi,xi)[0,0]) for xi,yi in zip(flpoints[:,0],flpoints[:,1])])

def flux_surface_avg(Rho,Z,B,flpoints,Q=None):
    """Compute flux surface average of quantity Q or return dVdpsi (dl_B)
    """
    ## Interpolate B and quantity Q onto flux line
    B_interp = interp(Rho,Z,B,flpoints)
    s = get_fieldline_distance(flpoints)
    dl_B = scipy.integrate.trapezoid(y=1.0/B_interp,x=s)
    if Q is not None:
        Q_interp = interp(Rho,Z,Q,flpoints)
        fsa = 1/dl_B*scipy.integrate.trapezoid(y=Q_interp/B_interp,x=s)
        return fsa
    else:
        return dl_B

def diff_central(x, y):
    """First derivative at interior x, quadratic on each nonuniform triplet."""
    return diff_12_central(x, y)[0]

__all__ = ['transform_to_rtheta', 'transform_to_rhoz', 'regular_grid', 'poly_fit', 'reflect_and_hstack', 'locs_to_vals', 'locs_to_vals_griddata', 'locs_to_vals1D', 'get_fieldlines', 'parse_segment', 'get_fieldline_distance', 'interp', 'flux_surface_avg', 'diff_central']

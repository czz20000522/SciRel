"""Frozen D2 gates: primary equations, independent quadrature, lifecycle."""
import numpy as np
import pytest
from scipy.integrate import quad
from scirel.geometry import (PointsMesh, RectMesh, Mesh, ThetaChord, SphericalRChord, rotate)
from scirel.electromagnetism import (compute_greens, ArbitraryPoints, RectangularCoil, MagnetRing, Device)

MU0 = 4e-7*np.pi


def loop_integrals(a, z0, r, z):
    # Direct Biot-Savart and vector potential, not elliptic production formulas.
    h = z-z0
    distance = lambda t: np.sqrt(a*a+r*r-2*a*r*np.cos(t)+h*h)
    psi = 1e-7*a*r*quad(lambda t: np.cos(t)/distance(t), 0, 2*np.pi, epsabs=1e-12, epsrel=1e-12)[0]
    br = 1e-7*quad(lambda t: a*h*np.cos(t)/distance(t)**3, 0, 2*np.pi, epsabs=1e-12, epsrel=1e-12)[0]
    bz = 1e-7*quad(lambda t: (a*a-a*r*np.cos(t))/distance(t)**3, 0, 2*np.pi, epsabs=1e-12, epsrel=1e-12)[0]
    return np.array([psi, br, bz])


@pytest.mark.parametrize('point', [(0.,0.), (0.,1.3), (.2,.3), (2.,-.7), (1.01,.03), (.000001,.7)])
def test_loop_independent_integrals(point):
    got = np.array(compute_greens(np.array([[1.,0.,1.]]), np.array([point])))[:,0]
    np.testing.assert_allclose(got, loop_integrals(1., 0., *point), rtol=2e-9, atol=2e-18)


def test_axis_analytic_limit():
    z = np.array([-2., 0., .4, 3.])
    psi, br, bz = compute_greens(np.array([[.7,.1,2.]]), np.column_stack((0*z,z)))
    np.testing.assert_array_equal(psi, 0*z)
    np.testing.assert_array_equal(br, 0*z)
    np.testing.assert_allclose(bz, MU0*2*.7**2/(2*(.7**2+(z-.1)**2)**1.5), rtol=5e-15)


def test_flux_derivative_sign_and_normalization():
    r,z,h = .6,.4,1e-5
    coil = np.array([[1.,0.,1.]])
    psi = lambda r,z: compute_greens(coil, np.array([[r,z]]))[0][0]
    br,bz = compute_greens(coil, np.array([[r,z]]))[1:]
    np.testing.assert_allclose(br[0], -(psi(r,z+h)-psi(r,z-h))/(2*h*r), rtol=2e-8, atol=1e-16)
    np.testing.assert_allclose(bz[0], (psi(r+h,z)-psi(r-h,z))/(2*h*r), rtol=2e-8, atol=1e-16)


def test_near_axis_nonzero_radial_field():
    for r in [1e-4,1e-6,1e-9]:
        psi, br, bz = compute_greens(np.array([[1.,0.,1.]]),np.array([[r,.7]]))
        b0 = MU0/(2*(1+.7**2)**1.5)
        np.testing.assert_allclose(br[0]/r, 3*MU0*.7/(4*(1+.7**2)**2.5), rtol=2e-8)
        np.testing.assert_allclose(psi[0]/r**2, b0/2, rtol=2e-8)
        np.testing.assert_allclose(bz[0], b0, rtol=2e-8)


def test_zero_weights_skip_singular_and_zero_radius_loop():
    got = compute_greens(np.array([[1.,0.,0.],[0.,0.,3.]]),np.array([[1.,0.],[0.,0.]]))
    for val in got: np.testing.assert_array_equal(val, [0.,0.])


def test_small_nonzero_loop_not_dropped():
    a=1e-13
    _,_,bz=compute_greens(np.array([[a,0.,1.]]),np.array([[0.,a]]))
    np.testing.assert_allclose(bz[0], MU0/(2*a*2**1.5),rtol=5e-15)


def test_theta_polar_angle_and_rotate():
    m=PointsMesh([0.,1.,1.],[1.,0.,-1.])
    np.testing.assert_allclose(m.theta,[0.,np.pi/2,3*np.pi/4],atol=1e-15)
    np.testing.assert_allclose(rotate([[1.,0.]],90),[[0.,-1.]],atol=1e-15)
    np.testing.assert_allclose(ThetaChord([0.,90.]).R,[0.,1.],atol=1e-15)
    np.testing.assert_allclose(SphericalRChord([1.,2.],90).Z,0.,atol=1e-15)


def test_mesh_mutation_invalidates_cache():
    m=RectMesh(rmin=.2,rmax=.4,nr=3,zmin=.2,zmax=.3,nz=2)
    c=ArbitraryPoints([[1.,0.]],mesh=m)
    old=c.psi().copy()
    m.rmax=.7
    assert not np.allclose(old,c.psi())
    np.testing.assert_allclose(c.psi(),c.psi(mesh=m),rtol=1e-15)
    m.R[0,0]=.25
    np.testing.assert_allclose(c.psi(),c.psi(mesh=m),rtol=1e-15)


def test_registration_replacement_delete_and_mesh():
    m=PointsMesh([.2],[.3])
    d=Device(mesh=m)
    d.c=ArbitraryPoints([[1.,0.]])
    np.testing.assert_allclose(d.psi(),d.c.psi())
    d.c=ArbitraryPoints([[1.2,.1]])
    assert len(d.current_sets)==1
    np.testing.assert_allclose(d.psi(),d.c.psi())
    del d.c
    assert len(d.current_sets)==0
    np.testing.assert_array_equal(d.psi(),[0.])
    d.c=ArbitraryPoints([[1.,0.]])
    d.c=None
    assert len(d.current_sets)==0


def test_child_and_weights_direct_mutation_cache():
    m=PointsMesh([.2],[.3])
    c=ArbitraryPoints([[1.,0.]],mesh=m)
    d=Device(mesh=m); d.c=c
    old=d.psi().copy()
    c.rz_pts[0,0]=1.3
    c.weights[0]=2
    np.testing.assert_allclose(d.psi(),c.psi(mesh=m),rtol=1e-15)
    assert not np.allclose(old,d.psi(),rtol=1e-7,atol=0.)
    c.current=7
    np.testing.assert_allclose(d.psi(),c.psi(),rtol=1e-15)


def test_grouped_kernels_and_empty_inputs():
    a=np.array([[1.,0.,1.]])
    b=np.array([[.8,.2,-2.]])
    points=np.array([[.2,.3],[.4,-.2]])
    grouped=compute_greens([a,b],points)
    for j in range(3):
        np.testing.assert_allclose(grouped[j][0],compute_greens(a,points)[j],rtol=1e-15)
        np.testing.assert_allclose(grouped[j][1],compute_greens(b,points)[j],rtol=1e-15)
        np.testing.assert_allclose(grouped[j].sum(axis=0),compute_greens(np.concatenate((a,b)),points)[j],rtol=1e-15)
    assert compute_greens([],points)[0].shape==(0,2)
    assert compute_greens(np.empty((0,3)),points)[0].shape==(2,)
    assert compute_greens(a,np.empty((0,2)))[0].shape==(0,)


def test_source_geometry_order_weights_and_transform():
    c=RectangularCoil(1.,.2,nr=2,nz=3,dr=.1,dz=.2)
    expected=np.array([[.95,0.],[.95,.2],[.95,.4],[1.05,0.],[1.05,.2],[1.05,.4]])
    np.testing.assert_allclose(c.rz_pts,expected,atol=1e-15)
    assert c.area==pytest.approx(.12)
    np.testing.assert_array_equal(c.weights,np.ones(6))
    c.rotate(90,pivot=(1.,.2))
    np.testing.assert_allclose(c.rz_pts,rotate(expected,90,(1.,.2)),atol=1e-15)
    c.translate([.2,.1]); np.testing.assert_allclose(c.centroid,[1.2,.3])
    mr=MagnetRing(1.,.2)
    np.testing.assert_array_equal(mr.weights,np.r_[-np.ones(8),np.ones(8)])
    assert mr.total_current==0
    np.testing.assert_allclose(mr.rz_pts[:8,0],.995)
    np.testing.assert_allclose(mr.rz_pts[8:,0],1.005)


@pytest.mark.parametrize('src,pts',[(np.array([[-1.,0.,1.]]),np.array([[1.,0.]])),(np.array([[1.,0.,np.nan]]),np.array([[.3,0.]])),(np.array([[1.,0.,1.]]),np.array([[-1.,0.]]))])
def test_kernel_invalid_domain(src,pts):
    with pytest.raises(ValueError): compute_greens(src,pts)


def test_mesh_array_conversion_no_geometry_invention():
    r,z=np.meshgrid([.2,.5,.8],[-.4,0.,.4])
    m=Mesh.from_array(np.array([r,z]))
    np.testing.assert_array_equal(m.R,r)
    np.testing.assert_array_equal(m.Z,z)
    distorted=r.copy(); distorted[1,1]+=.1
    with pytest.raises(ValueError): Mesh.from_array(np.array([distorted,z]))


def test_invalid_geometry_and_zero_weight_current():
    c=ArbitraryPoints([[1.,0.]],weights=[0.])
    with pytest.raises(ValueError): c.total_current=1.
    with pytest.raises(ValueError): RectangularCoil(nr=0)
    with pytest.raises(ValueError): MagnetRing(weights=[-1.,1.,1.])

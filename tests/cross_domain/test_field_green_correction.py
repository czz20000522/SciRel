"""Predeclared ideal-loop counterexamples for the selected field interfaces."""
import numpy as np
import pytest
import mpmath as mp
from scirel.field import (dense_axisymmetric_green_response as dense,
    circular_filament_green_response as aggregate,
    build_mirror_plasma_flux_green as mirror,
    integrate_filament_vacuum_field as integrate)


def high_precision_loop(a, h, r, weight=1.):
    # Independent 70-digit closed-form evaluation, not production special
    # functions, derivative or small-m expansion. Raw decimal coordinates bind
    # the physical fixture; no candidate results set expected values.
    with mp.workdps(70):
        a,h,r,w = [mp.mpf(str(v)) for v in (a,h,r,weight)]
        if r == 0:
            return 0.,0.,float(2*mp.pi*mp.mpf('1e-7')*w*a*a/(a*a+h*h)**mp.mpf('1.5'))
        d=mp.sqrt((a+r)**2+h*h);rho2=(a-r)**2+h*h
        m=4*a*r/(d*d);K,E=mp.ellipk(m),mp.ellipe(m)
        psi=mp.mpf('1e-7')*w*d*((2-m)*K-2*E)
        br=mp.mpf('2e-7')*w*h/(r*d)*(-K+(a*a+r*r+h*h)/rho2*E)
        bz=mp.mpf('2e-7')*w/d*(K+(a*a-r*r-h*h)/rho2*E)
        return tuple(float(v) for v in (psi,br,bz))


@pytest.mark.parametrize('api',[dense,aggregate])
def test_every_positive_loop_radius_retains_analytic_axis_field(api):
    points=np.array([[0.,0.],[0.,1e-13]])
    sources=np.array([[1e-13,0.,1.]])
    out=api(points,sources) if api is dense else api(sources,points)
    expected=np.array([high_precision_loop(1e-13,h,0.)[2] for h in points[:,1]])
    observed=out['gBZ'][:,0] if api is dense else out['gBZ']
    np.testing.assert_allclose(observed,expected,rtol=1e-13,atol=1e-300)
    np.testing.assert_array_equal(out['gBR'],np.zeros_like(out['gBR']))


@pytest.mark.parametrize('r,h',[(1e-10,.2),(.4,1e-8)])
def test_radial_quadrature_uses_correct_unclipped_filament_field(r,h):
    R,Z=np.meshgrid([r,r+.01],[h,h+.1])
    out=integrate(R,Z,[[.4,0.,1.]])
    expected=high_precision_loop(.4,h,r)
    np.testing.assert_allclose(out['b_r'][0,0],expected[1],rtol=2e-13,atol=1e-300)
    np.testing.assert_allclose(out['b_z'][0,0],expected[2],rtol=2e-13,atol=1e-300)
    # Preserve discrete trapezoid producer/gauge; do not silently substitute psi.
    np.testing.assert_array_equal(out['psi'][:,0],np.zeros(2))
    np.testing.assert_allclose(out['psi'][:,1],
        .005*(R[:,0]*out['b_z'][:,0]+R[:,1]*out['b_z'][:,1]),rtol=2e-14,atol=1e-300)


def test_mirror_small_positive_loops_are_not_removed_by_axis_tolerance():
    R,Z=np.meshgrid([1e-13,2e-13],[-1e-13,1e-13])
    result=mirror(R,Z)['g_psi']
    points=list(zip(R.ravel(),Z.ravel()))
    expected=np.zeros_like(result)
    for i,(r,z) in enumerate(points):
        for j,(a,z0) in enumerate(points):
            if i!=j:expected[i,j]=high_precision_loop(a,z-z0,r)[0]
    np.testing.assert_allclose(result,expected,rtol=2e-14,atol=1e-300)


@pytest.mark.parametrize('api',[dense,aggregate])
def test_exact_self_rule_is_distinct_from_arithmetic_failure(api):
    points=np.array([[.4,.2],[.1,.2]])
    sources=np.array([[.4,.2,1.]])
    out=api(points,sources) if api is dense else api(sources,points)
    for v in out.values(): np.testing.assert_array_equal(v[0],np.zeros_like(v[0]))
    tiny_source=np.array([[1e-13,0.,1e308]])
    with pytest.raises(FloatingPointError):
        api([[0.,0.]],tiny_source) if api is dense else api(tiny_source,[[0.,0.]])


@pytest.mark.parametrize('m',[.499999,.500001,.99])
def test_equivalent_formula_cutover_retains_psi_and_analytic_derivatives(m):
    h=float(2*np.sqrt(1/m-1))
    out=aggregate([[1.,0.,1.]],[[1.,h]])
    expected=high_precision_loop(1.,h,1.)
    for name,value in zip(('gpsi','gBR','gBZ'),expected):
        np.testing.assert_allclose(out[name][0],value,rtol=2e-14,atol=1e-300)


def test_near_one_elliptic_parameter_has_no_artificial_cap():
    out=aggregate([[1.,0.,1.]],[[1.,1e-6]])
    expected=high_precision_loop(1.,1e-6,1.)
    for name,value in zip(('gpsi','gBR','gBZ'),expected):
        np.testing.assert_allclose(out[name][0],value,rtol=2e-14,atol=1e-300)


def test_near_wire_radial_separation_is_not_lost_by_squared_subtraction():
    a,r,h = 1.0,1.0+2e-8,3e-8
    with mp.workdps(70):
        aa,rr,hh=map(mp.mpf,[a,r,h])  # exact input binary64 values
        d=mp.sqrt((aa+rr)**2+hh**2);rho2=(aa-rr)**2+hh**2
        m=4*aa*rr/d**2;K,E=mp.ellipk(m),mp.ellipe(m)
        expected=float(mp.mpf('2e-7')/d*(K+(aa**2-rr**2-hh**2)/rho2*E))
    out=aggregate([[a,0.,1.]],[[r,h]])
    np.testing.assert_allclose(out['gBZ'][0],expected,rtol=3e-11,atol=1e-300)


def test_radial_quadrature_active_and_inactive_self_are_distinct():
    R,Z=np.meshgrid([.2,.4],[0.,.1])
    with pytest.raises(ValueError,match='singular circular filament'):
        integrate(R,Z,[[.4,0.,1.]])
    out=integrate(R,Z,[[.4,0.,0.]])
    for value in out.values():np.testing.assert_array_equal(value,np.zeros_like(R))


@pytest.mark.parametrize('api',[dense,aggregate,mirror,integrate])
def test_public_field_interfaces_reject_complex_coordinates(api):
    R,Z=np.meshgrid([.2,.4],[-.1,.1])
    with pytest.raises(ValueError,match='real'):
        if api is dense:api([[.2+1j,.1]],[[.4,0.,1.]])
        elif api is aggregate:api([[.4,0.,1.]],[[.2+1j,.1]])
        elif api is mirror:api(R+1j,Z)
        else:api(R+1j,Z,[[.4,0.,1.]])

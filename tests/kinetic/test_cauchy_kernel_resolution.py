"""Independent polynomial antiderivatives expose missed Cauchy kernel peaks.

The oracle uses complex logarithms, not the production quadrature or mapping.
Tolerances fixed before repair: 5e-9 scaled polynomial error; 1e-9 Gaussian.
"""
import numpy as np
import pytest
from scipy.special import wofz
from scirel.kinetic import evaluate_cauchy_transform as cauchy


def exact_polynomial(z, a, b, slope=0., intercept=1.):
    logarithm=np.log(complex(b-z))-np.log(complex(a-z))
    return slope*(b-a)+(intercept+slope*z)*logarithm


@pytest.mark.parametrize('height',[1.,1e-3,1e-6,1e-9,1e-12,1e-16,1e-100,1e-300])
@pytest.mark.parametrize('sign',[-1.,1.])
@pytest.mark.parametrize('slope,intercept',[(0.,1.),(.7,1.2)])
def test_known_kernel_peak_across_scales(height,sign,slope,intercept):
    points=np.array([-.75+sign*height*1j,sign*height*1j,.8+sign*height*1j])
    expected=np.array([exact_polynomial(z,-1.,1.,slope,intercept) for z in points])
    result=cauchy(points,lambda v:intercept+slope*v,bounds=(-1.,1.))
    assert result['G'].shape==points.shape
    assert result['quadrature_error'].shape==points.shape+(2,)
    np.testing.assert_allclose(result['G'],expected,rtol=5e-9,atol=5e-9)
    # Conditional numerical errors cannot be negative or silently all zero.
    assert np.all(result['quadrature_error']>=0)
    assert np.all(result['quadrature_error'].sum(axis=-1)>0)


@pytest.mark.parametrize('x',[-1.-1e-12,-1.,-1.+1e-12,1.-1e-12,1.,1.+1e-12])
@pytest.mark.parametrize('sign',[-1.,1.])
def test_endpoint_and_exterior_near_kernel(x,sign):
    z=x+sign*1e-12j
    expected=exact_polynomial(z,-1.,1.,.25,1.)
    actual=cauchy(z,lambda v:1.+.25*v,bounds=(-1.,1.))['G']
    assert abs(actual-expected)<=5e-9*(1+abs(expected))


@pytest.mark.parametrize('x',[-1.-1e-12,-1.,-.6,0.,.7,1.,1.+1e-12])
def test_near_real_landau_branch_and_endpoint_policy(x):
    z=x-1e-12j
    expected=exact_polynomial(z,-1.,1.,.25,1.)
    if -1.<x<1.: expected+=2j*np.pi*(1.+.25*z)
    actual=cauchy(z,lambda v:1.+.25*v,bounds=(-1.,1.),analytic_density=lambda z:1.+.25*z)['G']
    assert abs(actual-expected)<=5e-9*(1+abs(expected))


@pytest.mark.parametrize('height',[1e-3,1e-9,1e-12])
@pytest.mark.parametrize('sign',[-1.,1.])
def test_whole_line_gaussian_kernel_and_infinite_tails(height,sign):
    z=.3+sign*height*1j
    # Upper contour identity and conjugation for the real lower contour.
    upper=.3+height*1j
    expected=1j*np.sqrt(np.pi)*wofz(upper)
    if sign<0: expected=np.conj(expected)
    actual=cauchy(z,lambda v:np.exp(-v*v)/np.sqrt(np.pi),integration_mesh=np.linspace(-8,8,33))['G']
    assert abs(actual-expected)<1e-9


def test_linear_additivity_and_panel_refinement():
    z=.63+1e-12j
    density=lambda v:1.+.3*v
    expected=exact_polynomial(z,-2.,3.,.3,1.)
    coarse=cauchy(z,density,bounds=(-2.,3.))
    fine=cauchy(z,density,bounds=(-2.,3.),integration_mesh=np.linspace(-2,3,21),epsabs=1e-12,epsrel=1e-12)
    for result in [coarse,fine]: assert abs(result['G']-expected)<5e-9
    assert abs(fine['G']-coarse['G'])<5e-9


def test_kernel_outside_mesh_in_tail_is_resolved():
    # All density features resolved by mesh; evaluation point outside mesh.
    z=10.+1e-12j
    density=lambda v:1./(np.pi*(1.+v*v))
    # Residue theorem on upper half-plane: G=-1/(z+i).
    actual=cauchy(z,density,integration_mesh=np.linspace(-4,4,33))['G']
    assert abs(actual+1/(z+1j))<1e-9

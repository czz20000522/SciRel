"""Scientific red regressions for the six legacy absorption decisions."""
import math
import numpy as np
import pytest
from scipy.interpolate import InterpolatedUnivariateSpline
from scirel.closures.tabulated_pressure_closure import evaluate_tabulated_pressure
from scirel.equilibrium.isotropic_picard_step import pressure_flux_picard_step
from scirel.equilibrium.isotropic_pressure_flux import solve_isotropic_pressure_flux
from scirel.equilibrium.pressure_flux_state import build_pressure_flux_state
from scirel.field.permanent_ring_filaments import discretize_permanent_ring


def grid():
    R,Z=np.meshgrid(np.linspace(.2,.8,4),[-.1,0.,.1]);return R,Z

def test_nearly_equal_1d_tables_must_not_silently_discard_anisotropy():
    with pytest.raises(ValueError,match='equal'):
        evaluate_tabulated_pressure(1.,.5,[0,1],[1,2],[1+1e-8,2])

def test_equal_2d_tables_report_component_equality_not_grid_branch():
    p=np.array([[1.,2.],[2.,3.]])
    got=evaluate_tabulated_pressure(1.5,.5,[0,1],p,p.copy(),[1,2])
    assert got['is_isotropic'] is True
    assert got['table_dimension']==2

@pytest.mark.parametrize('kind',['green','current','total'])
def test_picard_nonfinite_state_fails_instead_of_vacuum_mask(kind):
    R,Z=grid(); n=R.size;G=np.eye(n);p=np.ones(n);old=np.zeros(n);vac=np.zeros_like(R)
    if kind=='green':G*=1e308;p*=1e3
    if kind=='current':p[:]=1e308;R=R*1e3
    if kind=='total':G*=1e308;p[:]=30;vac[:]=1.7e308
    with pytest.raises(FloatingPointError):
        pressure_flux_picard_step(R,Z,vac,vac,G,p,1.,old,0.)

@pytest.mark.parametrize('relax',[.5,.9])
def test_zero_green_flux_stationary_is_not_current_closure(relax):
    R,Z=grid();got=solve_isotropic_pressure_flux(r_grid=R,z_grid=Z,psi_vac=R,g_psi=np.zeros((R.size,R.size)),pressure_of_radius=lambda r:max(.8-r,0.),tol=1e-12,maxiter=1,relax=relax)
    assert not got['converged']
    assert got['closure_residual']==pytest.approx(relax)

@pytest.mark.parametrize('tol',[1.,2.])
def test_zero_updates_never_claim_convergence(tol):
    R,Z=grid();got=solve_isotropic_pressure_flux(r_grid=R,z_grid=Z,psi_vac=R,g_psi=np.zeros((R.size,R.size)),pressure_of_radius=lambda r:max(.8-r,0.),tol=tol,maxiter=0,relax=0.)
    assert not got['converged']
    assert np.isinf(got['residual']) and np.isinf(got['closure_residual'])

def test_full_solver_rejects_relax_one():
    R,Z=grid()
    with pytest.raises(ValueError,match='relax'):
        solve_isotropic_pressure_flux(r_grid=R,z_grid=Z,psi_vac=R,g_psi=np.zeros((R.size,R.size)),pressure_of_radius=lambda r:max(.8-r,0.),tol=1e-12,maxiter=2,relax=1.)

def test_interior_edge_representation_exactly_reconstructs_fitted_prefix():
    R,Z=np.meshgrid(np.arange(1.,7.),[-1.,0.,1.])
    got=build_pressure_flux_state(R,Z,R,lambda r:max(4-r,0.)**2)
    rep=got['pressure_of_psi'];assert len(rep['psi_samples'])==4
    spline=InterpolatedUnivariateSpline(rep['psi_samples'],rep['pressure_samples'],ext='zeros')
    np.testing.assert_allclose(spline([1.5,2.5,3.5,4.5]),[6.25,2.25,.25,0],rtol=2e-14,atol=1e-14)
    expected=spline.derivative()(R.ravel());expected[R.ravel()>4]=0
    np.testing.assert_allclose(got['pressure_derivative'],expected,rtol=2e-14,atol=1e-14)

def test_pressure_state_rejects_numeric_mask():
    R,Z=grid()
    with pytest.raises(ValueError,match='boolean'):
        build_pressure_flux_state(R,Z,R,lambda r:max(.8-r,0.),np.zeros(R.shape))

def test_pressure_state_rejects_nonfinite_spline_derivative():
    R,Z=grid();psi=R*1e-308
    with pytest.raises((ValueError,FloatingPointError)):
        build_pressure_flux_state(R,Z,psi,lambda r:1e308 if r<.8 else 0.)

def test_pressure_state_descending_radial_storage_keeps_physical_edge():
    R,Z=np.meshgrid(np.arange(6.,0.,-1),[-1.,0.,1.])
    got=build_pressure_flux_state(R,Z,R,lambda r:max(4-r,0.)**2)
    assert got['limiter_index']==3
    np.testing.assert_array_equal(got['pressure_of_psi']['psi_samples'],[1.,2.,3.,4.])
    np.testing.assert_allclose(got['pressure_derivative'],np.where(R.ravel()>4,0,2*(R.ravel()-4)),atol=2e-14)

def test_ring_tiny_angle_is_rotated_without_legacy_snap():
    got=discretize_permanent_ring(3.,0.,2.,1.,mu_hat_deg=5e-13)['rz_pts']
    zero=discretize_permanent_ring(3.,0.,2.,1.)['rz_pts']
    assert not np.array_equal(got,zero)
    angle=math.radians(5e-13);delta=zero-np.array([3.,0.]);expected=np.column_stack((delta[:,0]*math.cos(angle)+delta[:,1]*math.sin(angle),-delta[:,0]*math.sin(angle)+delta[:,1]*math.cos(angle)))+[3.,0.]
    np.testing.assert_array_equal(got,expected)

def test_ring_finite_angle_avoids_unnecessary_pi_times_angle_overflow():
    got=discretize_permanent_ring(3.,0.,2.,1.,mu_hat_deg=1e308)['rz_pts']
    assert np.all(np.isfinite(got))

def test_ring_nonfinite_generated_coordinates_rejected():
    with pytest.raises(ValueError,match='finite'):
        discretize_permanent_ring(3.,1.7e308,2.,1.7e308)


def test_nonzero_green_manufactured_solution_and_both_histories():
    # P(R)=4-R, G=c*identity and unit cell area imply psi=a*R,
    # I=-R/a and a^2-a+c=0, choosing the vacuum-connected branch.
    R,Z=np.meshgrid(np.arange(1.,5.),[-1.,0.,1.]); c=.05
    got=solve_isotropic_pressure_flux(r_grid=R,z_grid=Z,psi_vac=R,g_psi=c*np.eye(R.size),pressure_of_radius=lambda r:4-r,tol=1e-11,maxiter=100,relax=.3)
    a=(1+np.sqrt(1-4*c))/2
    assert got['converged'] and got['status']=='converged'
    np.testing.assert_allclose(got['psi'],a*R,rtol=2e-11,atol=0)
    np.testing.assert_allclose(got['plasma_currents'],-R/a,rtol=2e-11,atol=0)
    assert len(got['residual_history'])==len(got['closure_residual_history'])==got['iterations']
    assert got['residual_history'][-1]<=1e-11 and got['closure_residual_history'][-1]<=1e-11


def test_pointwise_kernel_retains_singleton_repeated_and_unsorted_samples():
    from scirel.diagnostics.pointwise_firehose_margin import compute_pointwise_firehose_margin
    B=np.array([2.,1.,2.]);pp=np.array([4.,7.,6.]);pt=np.array([3.,1.,9.]);mu=2.
    np.testing.assert_array_equal(compute_pointwise_firehose_margin(pp,pt,B,mu0=mu)['firehose_margin'],B**2/mu+pt-pp)
    np.testing.assert_array_equal(compute_pointwise_firehose_margin(4.,3.,2.,mu0=mu)['firehose_margin'],1.)


@pytest.mark.parametrize('B,mu,expected',[(1e200,1e200,1e200),(1e-200,1e-300,1e-100)])
def test_representable_firehose_avoids_intermediate_square_range_loss(B,mu,expected):
    from scirel.diagnostics.pointwise_firehose_margin import compute_pointwise_firehose_margin
    from scirel.diagnostics.firehose_mirror_margins import compute_firehose_mirror_margins
    point=compute_pointwise_firehose_margin(0.,0.,B,mu0=mu)
    combined=compute_firehose_mirror_margins(0.,0.,B,mu0=mu,dp_perp_dB=0.)
    np.testing.assert_allclose(point['firehose_margin'],expected,rtol=2e-15,atol=0.)
    np.testing.assert_allclose(combined['firehose_margin'],expected,rtol=2e-15,atol=0.)
    np.testing.assert_allclose(combined['mirror_margin'],expected,rtol=2e-15,atol=0.)

@pytest.mark.parametrize('B,mu,pt,pp',[(1e200,1e200,0.,0.),(1e-160,1e-100,0.,0.),(1e154,.5,0.,1e308),(0.,1.,1e308,-1e308)])
def test_range_fallback_agrees_with_independent_decimal(B,mu,pt,pp):
    from decimal import Decimal,localcontext
    from scirel.diagnostics.pointwise_firehose_margin import compute_pointwise_firehose_margin
    with localcontext() as context:
        context.prec=2000
        b,m,t,p=map(Decimal.from_float,(B,mu,pt,pp));expected=float(b*b/m+t-p)
    if not np.isfinite(expected):
        with pytest.raises(ValueError,match='must be finite'):
            compute_pointwise_firehose_margin(pp,pt,B,mu0=mu)
    else:
        got=compute_pointwise_firehose_margin(pp,pt,B,mu0=mu)['firehose_margin']
        np.testing.assert_allclose(got,expected,rtol=2e-15,atol=0.)


def test_combined_margin_recovers_representable_cancellation():
    from decimal import Decimal,localcontext
    from scirel.diagnostics.firehose_mirror_margins import compute_firehose_mirror_margins
    B=1e154;mu=.5;pp=1e308;derivative=-1e154
    with localcontext() as context:
        context.prec=2000
        b,m,p,d=map(Decimal.from_float,(B,mu,pp,derivative));fire=float(b*b/m-p);mirror=float(b*b/m+b*d)
    got=compute_firehose_mirror_margins(pp,0.,B,mu0=mu,dp_perp_dB=derivative)
    np.testing.assert_allclose(got['firehose_margin'],fire,rtol=2e-15,atol=0.)
    np.testing.assert_allclose(got['mirror_margin'],mirror,rtol=2e-15,atol=0.)

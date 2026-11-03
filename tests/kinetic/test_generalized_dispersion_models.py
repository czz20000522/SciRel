"""Independent integral, analytic, boundary and source-defect regressions."""
import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import wofz
from scirel.kinetic.generalized_dispersion import (
    DensityExpression,evaluate_generalized_hilbert,evaluate_generalized_dispersion,
    evaluate_gpdf_residual,evaluate_gpdf_small_k,scan_gpdf_roots)


def integral(f,z,edges):
    values=[]
    for a,b in zip(edges[:-1],edges[1:]):
        values.append(quad(lambda v:(f(v)/(v-z)).real,a,b,epsabs=1e-11)[0]
                      +1j*quad(lambda v:(f(v)/(v-z)).imag,a,b,epsabs=1e-11)[0])
    return sum(values)


def test_expression_derivative_and_security():
    f=DensityExpression('1./(1+v.^2)/pi')
    for v in (0.,.7,1.2+.4j):
        assert f(v)==pytest.approx(1/(1+v*v)/np.pi)
        assert f.derivative(v)==pytest.approx(-2*v/(1+v*v)**2/np.pi)
    for expression in ("__import__('os').system('true')",'v.real','v[0]','unknown(v)','exp(v, v)','True','[v]'):
        with pytest.raises(ValueError): DensityExpression(expression)


def test_expression_lorentzian_all_planes_and_removable_upper_pole():
    z=np.array([.4+.7j,.4-.7j,.4+0j,1j])
    result=evaluate_generalized_hilbert(z,'1/(1+v**2)/pi',integration_mesh=[-20,-2,-1,0,1,2,20])
    np.testing.assert_allclose(result['Z'],-1/(z+1j),atol=2e-9,rtol=2e-9)
    np.testing.assert_allclose(result['Zp'],1/(z+1j)**2,atol=2e-9,rtol=2e-9)


@pytest.mark.parametrize('selector',[0,1,2,3,4,5,6])
def test_selectors_against_independent_defining_integral(selector):
    z=.37+.61j
    c=3*np.sqrt(3)/(4*np.pi)
    cases={0:(lambda v:np.exp(-v*v)/np.sqrt(np.pi),[-np.inf,0,np.inf]),
           2:(lambda v:1.,[-.5,.5]),
           3:(lambda v:1-abs(v),[-1,0,1]),
           4:(lambda v:np.sqrt(2)/np.pi/(1+v*v/2)**2,[-np.inf,0,np.inf]),
           5:(lambda v:np.exp(-v*v)/np.sqrt(np.pi),[.1,1,np.inf]),
           6:(lambda v:c/(abs(v)**3+1),[-4,0,4])}
    result=evaluate_generalized_dispersion(z,selector)
    if selector==1:
        expected=-1/z; derivative=1/z**2
    else:
        f,edges=cases[selector]
        expected=integral(f,z,edges)
        derivative=integral(lambda v:f(v)/(v-z),z,edges)
    np.testing.assert_allclose(result['Z'],expected,atol=2e-9,rtol=2e-9)
    np.testing.assert_allclose(result['Zp'],derivative,atol=2e-9,rtol=2e-9)


@pytest.mark.parametrize('selector',[2,3,5,6])
def test_piecewise_lower_plane_is_explicit_real_contour(selector):
    upper=evaluate_generalized_dispersion(.23+.4j,selector)
    lower=evaluate_generalized_dispersion(.23-.4j,selector)
    for key in ('Z','Zp'): assert lower[key]==pytest.approx(np.conj(upper[key]),abs=2e-10)


def test_top_hat_sign_and_incomplete_cutoff_jump_regressions():
    # Old H(v-.5)-H(v+.5) had negative mass, inconsistent with old Zp.
    assert evaluate_generalized_dispersion(100j,2)['Z'].imag>0
    z=.3+.2j
    f=lambda v:np.exp(-v*v)/np.sqrt(np.pi)
    smooth=integral(lambda v:-2*v*f(v),z,[.1,1,np.inf])
    corrected=smooth+f(.1)/(.1-z)
    wrong=smooth-f(-.1)/(z+.1)
    actual=evaluate_generalized_dispersion(z,5)['Zp']
    assert actual==pytest.approx(corrected,abs=1e-9)
    assert abs(actual-wrong)>.1


def test_maxwellian_residual_small_k_and_mixture_normalization():
    for kind in ('langmuir','generalized'):
        assert evaluate_gpdf_residual(kind,1/(np.sqrt(2)*1e-7),1e-7)==pytest.approx(-3e-28,abs=1e-29)
    x=.5+.2j; k=.3
    response=lambda q:1+q*1j*np.sqrt(np.pi)*wofz(q)
    assert evaluate_gpdf_residual('iaw',x,k)==pytest.approx(k*k+response(x)+response(x*np.sqrt(1836)),abs=1e-11)
    assert evaluate_gpdf_residual('beam',x,k)==pytest.approx(k*k+.9*response(x)+.1*response(x-5),abs=1e-11)
    result=evaluate_gpdf_small_k(np.array([1e-200,.1,.3]))
    assert result['omega_imag'][0]==0
    assert result['omega_real'][1]==pytest.approx(1.015)
    assert result['omega_imag'][1]==pytest.approx(-np.sqrt(np.pi/8)*np.exp(-50-1.5)/.1**3)


@pytest.mark.parametrize('kind,ks,seed',[('langmuir',[.3,.4],None),('generalized',[.3,.4],None),('iaw',[.3,.25],None),('beam',[.3,.295],(1-.01j)/(np.sqrt(2)*.4))])
def test_real_vector_solver_and_fixed_parameter_closure(kind,ks,seed):
    result=scan_gpdf_roots(kind,k_values=ks,initial_guess=seed)
    assert result['omega'].shape==(2,)
    assert np.max(result['dielectric_residual'])<1e-9
    for k,omega in zip(result['k'],result['omega']):
        x=omega/(np.sqrt(2)*k)
        assert abs(evaluate_gpdf_residual(kind,x,k)/(k*k))<1e-9


def test_failures_are_explicit():
    with pytest.raises(ValueError): evaluate_generalized_dispersion(0,1)
    with pytest.raises(ValueError): evaluate_generalized_dispersion(.5,2)
    with pytest.raises(ValueError): evaluate_generalized_dispersion(.1,5)
    with pytest.raises(ValueError): evaluate_generalized_dispersion(1j,0,expression='exp(-v*v)')
    with pytest.raises(RuntimeError): scan_gpdf_roots('langmuir',k_values=[.3],max_evaluations=1)
    with pytest.raises(ValueError): scan_gpdf_roots('beam',k_values=[0])


@pytest.mark.parametrize('kind,count',[('langmuir',19),('generalized',18),('iaw',22),('beam',71)])
def test_complete_original_scans(kind,count):
    result=scan_gpdf_roots(kind)
    assert len(result['k'])==count
    assert np.max(result['dielectric_residual'])<1e-9


def test_original_beam_seed_custom_grid_failure_preserved():
    with pytest.raises(RuntimeError,match='beam scan failed'):
        scan_gpdf_roots('beam',k_values=[.3,.295])


@pytest.mark.parametrize('kind,k,seed',[
    ('langmuir',.3,None),('iaw',.3,None),
    ('beam',.4,None),('beam',.3,(1-.01j)/(np.sqrt(2)*.4))])
def test_roots_against_independent_high_precision_equations(kind,k,seed):
    import mpmath as mp
    result=scan_gpdf_roots(kind,k_values=[k],initial_guess=seed)
    phase=result['omega'][0]/(np.sqrt(2)*k)
    with mp.workdps(50):
        kk=mp.mpf(str(k))
        def response(z):
            Z=mp.j*mp.sqrt(mp.pi)*mp.exp(-z*z)*mp.erfc(-mp.j*z)
            return 1+z*Z
        def equation(z):
            if kind=='langmuir': return kk*kk+response(z)
            if kind=='iaw': return kk*kk+response(z)+response(z*mp.sqrt(1836))
            return kk*kk+mp.mpf('.9')*response(z)+mp.mpf('.1')*response(z-5)
        oracle=mp.findroot(equation,(mp.mpc(phase)*(1+mp.mpf('1e-4')),mp.mpc(phase)*(1-mp.mpf('1e-4'))),tol=mp.mpf('1e-40'),maxsteps=100)
        assert abs(equation(oracle))<mp.mpf('1e-35')
        assert abs(complex(oracle)-phase)<2e-9


def test_integer_small_k_input_no_machine_integer_wrap():
    k=np.array([2**32],dtype=np.int64)
    result=evaluate_gpdf_small_k(k)
    assert result['omega_real'][0]==pytest.approx(1+1.5*float(2**32)**2)
    assert result['omega_imag'][0]<0
    assert result['omega_imag'][0]==pytest.approx(-np.sqrt(np.pi/8)*np.exp(-1.5-.5/float(2**32)**2)/float(2**32)**3,abs=0,rel=1e-12)


def test_expression_integer_velocity_promotes_before_powers():
    v=np.array([2**32],dtype=np.int64)
    f=DensityExpression('1/(1+v**2)/pi')
    np.testing.assert_allclose(f(v),1/(1+float(2**32)**2)/np.pi,rtol=1e-15)
    np.testing.assert_allclose(f.derivative(v),-2*float(2**32)/(1+float(2**32)**2)**2/np.pi,rtol=1e-15)


def test_real_exterior_quadrature_warning_fails_closed(monkeypatch):
    import warnings
    import scirel.kinetic.generalized_dispersion as module
    from scipy.integrate import IntegrationWarning
    def warned(*args,**kwargs):
        warnings.warn('controlled quadrature failure',IntegrationWarning)
        return 0.,1.
    monkeypatch.setattr(module,'quad',warned)
    with pytest.raises(RuntimeError,match='quadrature did not converge'):
        evaluate_generalized_dispersion(4.01,6)
    with pytest.raises(RuntimeError,match='quadrature did not converge'):
        evaluate_generalized_dispersion(.3,3)

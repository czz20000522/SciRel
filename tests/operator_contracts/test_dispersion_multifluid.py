"""UNRUN proposed gates. Owner/independent validator must bind exact candidates first.

Analytic, high-precision and tensor-perturbation oracles, never candidate-generated
expected results. This file is a plan implementation, not validation evidence.
"""
import numpy as np
import pytest
import mpmath as mp
from scipy.optimize import linear_sum_assignment
from scirel.kinetic.dispersion import _fluid_parallel as c


def test_faddeeva_independent_80_digit_definition():
    z=np.array([[0,30j],[-2j,.31+.73j],[-2.2-.4j,7+.01j]],complex)
    with mp.workdps(80):
        expected=np.array([complex(mp.exp(-mp.mpc(complex(t))**2)*mp.erfc(-1j*mp.mpc(complex(t))))for t in z.flat]).reshape(z.shape)
    got=c.canonical_faddeeva(z)
    np.testing.assert_allclose(got['w'],expected,rtol=2e-13,atol=2e-14)
    assert got['w'].shape==z.shape and np.isfinite(got['w']).all()
    with pytest.raises(ValueError):c.canonical_faddeeva(-30j)


def test_collision_momentum_energy_and_two_species_closed_form():
    rho=np.array([2.,5.]);K=np.array([[0.,3.],[3.,0.]])
    L=c.collision_velocity_generator(rho,K)
    np.testing.assert_allclose(rho@L,0,atol=1e-14)
    np.testing.assert_allclose(L@np.ones(2),0,atol=1e-14)
    expected=np.array([0.,-3.*(1/2+1/5)])
    np.testing.assert_allclose(np.sort(np.linalg.eigvals(L)),np.sort(expected),rtol=1e-13,atol=1e-14)
    for v in [np.array([1.,-2.]),np.array([4.,4.]),np.array([-3.,.2])]:
        energy_rate=v@(rho*(L@v));pair_loss=-3.*(v[0]-v[1])**2
        np.testing.assert_allclose(energy_rate,pair_loss,rtol=1e-13,atol=1e-13)


def _deck():
    # Neutral two-species manufactured SI plasma, q=+/-1C,m=1kg,n=1m^-3.
    return np.array([[-1,1,1,0,0,0,0,0,0,0],[1,1,1,0,0,0,0,0,0,0]],float)


def test_zero_field_cold_frequency_analytic_modes_and_state():
    state=c.fluid_equilibrium_si(_deck(),B0=0)
    assert state['beta_z']is None and state['beta_p']is None
    np.testing.assert_array_equal(state['vA_species'],0)
    wp=np.sqrt(2/state['epsilon0']);scale=np.ones(14);scale[8:11]=wp;scale[11:]=wp/np.sqrt(state['c2'])
    pencil=c.fluid_frequency_pencil(state,0,0);got=c.solve_frequency_pencil(**{n:pencil[n]for n in ['M','A']},state_scales=scale)
    expected=np.array([-wp]*3+[0.]*8+[wp]*3,dtype=complex)
    cost=np.abs(got['w1'][:,None]-expected[None,:]);i,j=linear_sum_assignment(cost)
    assert np.max(cost[i,j])<=1e-9*wp


def test_gyrotropic_pressure_tensor_rotation_coefficient():
    deck=_deck();deck[:,6]=2.;deck[:,7]=3.;state=c.fluid_equilibrium_si(deck,B0=1.)
    kx=.3;kz=.7;h=2**-20;pencil=c.fluid_frequency_pencil(state,kx,kz)
    def pressure(B):
        b=B/np.linalg.norm(B);return state['Pp'][0]*np.eye(3)+(state['Pz'][0]-state['Pp'][0])*np.outer(b,b)
    derivative=(pressure(np.array([h,0,1.]))-pressure(np.array([-h,0,1.])))/(2*h)
    expected=-1j*np.array([kx,0,kz])@derivative/state['rho'][0]
    actual=pencil['M'][1:4,8+3]
    np.testing.assert_allclose(actual,expected,rtol=1e-9,atol=1e-12)


def test_zero_field_anisotropy_is_not_silently_invented():
    deck=_deck();deck[:,6]=2.;deck[:,7]=3.
    with pytest.raises(ValueError,match='zero-B'):c.fluid_equilibrium_si(deck,B0=0)


def test_generalized_pencil_known_nonidentity_inertia():
    # Independent manufactured exact eigenvalues, not a source/candidate replay.
    A=np.diag([2.,3.,7.]);T=np.array([[1.,.2,.1],[.1,1.,-.2],[.2,.1,1.]])
    lambdas=np.array([-2.,3j,.5+.2j]);M=A@T@np.diag(lambdas)@np.linalg.inv(T)
    got=c.solve_frequency_pencil(M,A);target=1j*lambdas
    cost=abs(got['w1'][:,None]-target[None,:]);ii,jj=linear_sum_assignment(cost)
    assert cost[ii,jj].max()<1e-11
    assert got['X1'].shape==got['X2'].shape==(3,3)


def test_all_original_grid_mappings_without_eigensolves():
    a=c.fluid_scan_plan(1);b=c.fluid_scan_plan(2);d=c.fluid_scan_plan(3);e=c.fluid_scan_plan(4)
    assert a['kx'].shape==(1,1)and b['kx'].shape==(101,1)and d['kx'].shape==(1,51)and e['kx'].shape==(75,50)
    np.testing.assert_allclose(b['axis_values'][0][[0,-1]],[0,.001],rtol=0,atol=1e-15)
    np.testing.assert_allclose(d['axis_values'][1][[0,-1]],[0,np.pi/2],rtol=0,atol=1e-15)
    np.testing.assert_allclose(e['kx'][[0,-1],0],[.01,2.97],rtol=0,atol=1e-14)
    np.testing.assert_allclose(e['kz'][0,[0,-1]],[.01,1.97],rtol=0,atol=1e-14)


def test_plot_units_require_explicit_scales_and_round_trip():
    k=np.array([.1,.2]);w=np.array([2+3j,4+1j]);plain=c.normalize_plot_coordinates(k,w)
    assert plain['k_units']=='m^-1'and plain['omega_units']=='rad/s'
    normalized=c.normalize_plot_coordinates(k,w,length_scale_m=4,frequency_scale_rad_s=2)
    np.testing.assert_array_equal(normalized['k']/4,k);np.testing.assert_array_equal(normalized['omega']*2,w)
    with pytest.raises(ValueError):c.normalize_plot_coordinates(k,w,length_scale_m=4)


def test_false_convergence_is_rejected_before_seed_update(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(c,'root',lambda *a,**kw:SimpleNamespace(success=True,status=1,x=np.array([9.,0.])))
    state=dict(wps2=np.zeros(4),vds=np.zeros(4),vtzs=np.ones(4),wcs=np.ones(4),c2=4.,cwp=1.,wcs1=1.)
    with pytest.raises(c.ContinuationFailure)as caught:c.continue_em1d(state,k_grid=[1.,2.],initial_guess=2.)
    assert caught.value.record['accepted_prefix']==()and caught.value.record['guess']==2
    assert caught.value.record['scaled_residual']>1e-10


def test_explicit_fixed_axis_zero_field_preserves_anisotropic_capability():
    deck=_deck();deck[:,6]=2.;deck[:,7]=3.
    state=c.fluid_equilibrium_si(deck,B0=0,pressure_frame='fixed_z')
    assert state['pressure_frame']=='fixed_z'
    pencil=c.fluid_frequency_pencil(state,.3,.7)
    # Fixed tensor axes mean no deltaP from rotating a magnetic perturbation.
    np.testing.assert_array_equal(pencil['M'][1:4,11],0)


def test_declared_relative_rate_variant_all_roles_and_permutation():
    rho=np.array([2.,5.,7.,11.]);roles=['electron','ion','electron','ion']
    params=dict(electron_bath_rate=.1,ion_bath_rate=.2,electron_pair_relative_rate=.3,ion_pair_relative_rate=.4,electron_ion_relative_rate=.5)
    got=c.pair_exchange_from_relative_rates(rho,roles,**params)
    permutation=np.array([3,0,2,1]);again=c.pair_exchange_from_relative_rates(rho[permutation],[roles[i]for i in permutation],**params)
    np.testing.assert_allclose(again['velocity_generator'],got['velocity_generator'][np.ix_(permutation,permutation)],rtol=1e-14,atol=1e-14)
    two=c.pair_exchange_from_relative_rates([2.,5.],['electron','ion'],electron_ion_relative_rate=.7)
    np.testing.assert_allclose(np.sort(np.linalg.eigvals(two['velocity_generator'])),[-.7,0],rtol=1e-13,atol=1e-14)


def test_defective_zero_sector_reports_incomplete_basis_without_false_small_roots():
    M=np.array([[0.,1.,0.],[0.,0.,0.],[0.,0.,-2.]])
    got=c.solve_frequency_pencil(M,np.eye(3))
    np.testing.assert_allclose(np.sort(abs(got['w1'])),[0.,0.,2.],rtol=0,atol=0)
    assert got['zero_structure']['geometric_multiplicity']==1
    assert got['zero_structure']['algebraic_multiplicity']==2
    assert got['zero_structure']['complete_eigenbasis_not_claimed']
    assert np.max(got['componentwise_backward_errors'])<=1e-10


def test_complex_wavevector_point_contract_cold_analytic_holdout():
    state=c.fluid_equilibrium_si(_deck(),B0=0.);kx=1e-4+2e-5j;kz=2e-4-1e-5j
    wp2=2/state['epsilon0'];wp=np.sqrt(wp2);wt=np.sqrt(wp2+state['c2']*(kx*kx+kz*kz))
    scale=np.ones(14);scale[8:11]=wp;scale[11:]=wp/np.sqrt(state['c2'])
    pencil=c.fluid_frequency_pencil(state,kx,kz);got=c.solve_frequency_pencil(pencil['M'],pencil['A'],state_scales=scale)
    expected=np.array([-wt,-wt,-wp]+[0.]*8+[wp,wt,wt]);cost=abs(got['w1'][:,None]-expected[None,:]);i,j=linear_sum_assignment(cost)
    assert cost[i,j].max()<=1e-9*wp
    assert got['componentwise_backward_errors'].max()<=1e-10


def test_relativistic_inertia_is_derivative_of_physical_momentum():
    state=c.fluid_equilibrium_si(_deck(),B0=.3);speed=np.sqrt(state['c2']);v=np.array([.11,-.07,.23])*speed;state['v'][0]=v
    pencil=c.fluid_frequency_pencil(state,.1,.2,relativistic=True);h=2**-20*speed
    def momentum(u):return u/np.sqrt(1-u@u/state['c2'])
    derivative=np.column_stack([(momentum(v+h*np.eye(3)[i])-momentum(v-h*np.eye(3)[i]))/(2*h)for i in range(3)])
    np.testing.assert_allclose(pencil['A'][1:4,1:4],derivative,rtol=1e-9,atol=1e-12)

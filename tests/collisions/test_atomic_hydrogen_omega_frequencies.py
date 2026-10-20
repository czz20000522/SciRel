"""Physical local moment contracts; original source-replay tests are frozen in
collision-core-continuation/before. Invalid global-sentinel/floor/clamp behavior
is intentionally not a compatibility requirement. Numerical tolerances unchanged
for retained finite formula comparisons (rtol 1e-14, atol 1e-14).
"""
import numpy as np
import pytest
from scirel.collisions import assemble_atomic_hydrogen_omega_frequencies as atomic
from scirel.collisions import assemble_molecular_hydrogen_omega_frequencies as molecular

OPS = [(atomic, ('H_P','H_H2','H_H'), 'VxH','Wperp_paraH'),
       (molecular, ('H2_P','H2_H','H2_H2'),'VxH2','Wperp_paraH2')]


def arguments():
    vr=np.array([.5,1.5]);vx=np.array([-2.,0.,1.]);wr=np.array([1.,2.]);dx=np.array([.5,1.,.75])
    f=np.array([[[1.,2.],[2.,3.],[4.,2.]],[[3.,1.],[1.,2.],[2.,5.]]])
    n=np.einsum('i,j,ijk->k',wr,dx,f)
    alpha1=np.arange(12).reshape(f.shape)*.02-.04
    alpha2=np.flip(alpha1,axis=1)*.3
    sig=np.arange(36).reshape(6,6)*.01-.12
    return [f,n,alpha1,alpha2,sig,wr,dx,vr,vx,2.,np.array([-.4,.3]),np.array([.7,-.1])]


@pytest.mark.parametrize('op,names,flow,stress',OPS)
def test_independent_scalar_reductions_and_units(op,names,flow,stress):
    a=arguments();r=op(*a);f,n,a1,a2,sig,wr,dx,vr,vx,vth,p1,p2=a
    for k in range(2):
        U=sum(wr[i]*dx[j]*f[i,j,k]*vx[j] for i in range(2) for j in range(3))/n[k]
        W=sum(wr[i]*dx[j]*f[i,j,k]*(vr[i]**2-2*(vx[j]-U)**2) for i in range(2) for j in range(3))/n[k]
        np.testing.assert_allclose(r[flow][k],vth*U,rtol=1e-14,atol=1e-14)
        np.testing.assert_allclose(r[stress][k],W,rtol=1e-14,atol=1e-14)
        alphas=[a1[:,:,k],a2[:,:,k],np.array([[sum(sig[i+2*j,l+2*m]*f[l,m,k] for l in range(2) for m in range(3)) for j in range(3)] for i in range(2)])]
        for c,alpha,denom in zip(names,alphas,[U-p1[k]/vth,U-p2[k]/vth,W]):
            N=sum(wr[i]*dx[j]*f[i,j,k]*alpha[i,j] for i in range(2) for j in range(3))/n[k]
            np.testing.assert_allclose(r['moment_'+c][k],N,rtol=1e-14,atol=1e-14)
            np.testing.assert_allclose(r['Omega_'+c][k],N/denom,rtol=1e-14,atol=1e-14)
            np.testing.assert_allclose(r['nu_'+c][k],vth*N/denom,rtol=1e-14,atol=1e-14)
    np.testing.assert_array_equal(r['Omega_EL'],sum(r['Omega_'+c] for c in names))


@pytest.mark.parametrize('op,names,flow,stress',OPS)
def test_self_matrix_keeps_fortran_flatten_and_exact_cell_results(
    op, names, flow, stress
):
    rng = np.random.default_rng(20261019)
    nr, nv, nx = 3, 4, 5
    f_base = rng.lognormal(mean=-230.0, sigma=0.5, size=(nr, nv, nx * 2))
    f = f_base[:, :, ::2]
    wr = rng.lognormal(mean=0.0, sigma=1.0, size=nr)
    dx = rng.lognormal(mean=-1.0, sigma=1.0, size=nv)
    vr = np.arange(nr, dtype=float) + 0.5
    vx = np.linspace(-2.0, 2.0, nv)
    weights = wr[:, None] * dx[None, :]
    density = np.sum(weights[:, :, None] * f, axis=(0, 1))
    alpha1 = np.zeros_like(f)
    alpha2 = np.zeros_like(f)
    m = nr * nv
    sig_base = rng.normal(size=(2 * m, 2 * m)) * 1.0e100
    sig_self = sig_base[::2, ::2]
    expected_self = np.stack([
        (sig_self @ f[:, :, k].reshape(-1, order='F')).reshape(
            (nr, nv), order='F'
        )
        for k in range(nx)
    ], axis=2)
    expected_moment = (
        np.sum(weights[:, :, None] * (f * expected_self), axis=(0, 1))
        / density
    )

    result = op(
        f, density, alpha1, alpha2, sig_self, wr, dx, vr, vx, 2.0,
        np.zeros(nx), np.zeros(nx),
        **{
            names[0] + '_EL': False,
            names[1] + '_EL': False,
        },
    )
    np.testing.assert_array_equal(result['moment_' + names[2]], expected_moment)


@pytest.mark.parametrize('op,names,flow,stress',OPS)
@pytest.mark.parametrize('boost',[.25,4.,-7.])
def test_common_boost_and_spatial_partition(op,names,flow,stress,boost):
    a=arguments();target=a[0].copy();target[0,:,1] *= .75
    # Target f itself preserves density/flow exactly and gives an explicit zero
    # stress gap in only the second cell. It cannot alter the first cell.
    target=a[0].copy();r=op(*a,moment_state=['central','target'],target_distribution=target)
    b=[x.copy() if isinstance(x,np.ndarray) else x for x in a]
    b[8]+=boost;b[10]+=boost*b[9];b[11]+=boost*b[9]
    q=op(*b,moment_state=['central','target'],target_distribution=target)
    for key in r:
        if key.startswith('status') or key.startswith('defined'):np.testing.assert_array_equal(r[key],q[key])
        elif key==flow:np.testing.assert_allclose(q[key],r[key]+boost*a[9],rtol=1e-14,atol=1e-14)
        else:np.testing.assert_allclose(q[key],r[key],rtol=1e-14,atol=1e-14,equal_nan=True)
    c=[x.copy() if isinstance(x,np.ndarray) else x for x in a]
    for idx in [0,2,3]:c[idx]=c[idx][:,:,:1]
    for idx in [1,10,11]:c[idx]=c[idx][:1]
    one=op(*c)
    for key in one:
        if key.startswith('status') or key.startswith('defined'):np.testing.assert_array_equal(one[key],r[key][:1])
        else:np.testing.assert_allclose(one[key],r[key][:1],rtol=1e-14,atol=1e-14,equal_nan=True)


@pytest.mark.parametrize('op,names,flow,stress',OPS)
def test_zero_denominator_returns_moment_and_propagates_unknown(op,names,flow,stress):
    a=arguments();r=op(*a);a[10]=r[flow].copy();a[11]=r[flow].copy()
    q=op(*a,moment_state='target',target_distribution=a[0])
    for name in names:
        assert np.isfinite(q['moment_'+name]).all()
        assert np.isnan(q['Omega_'+name]).all()
        assert np.isnan(q['nu_'+name]).all()
        assert not q['defined_'+name].any()
        assert (q['status_'+name]=='undefined_zero_denominator').all()
    assert np.isnan(q['Omega_EL']).all() and not q['defined_EL'].any()
    flags={name+'_EL':False for name in names}
    off=op(*a,moment_state='target',target_distribution=a[0],**flags)
    for name in names:
        np.testing.assert_array_equal(off['Omega_'+name],0)
        assert (off['status_'+name]=='disabled').all()
    assert off['defined_EL'].all()


@pytest.mark.parametrize('op,names,flow,stress',OPS)
def test_negative_ratio_is_not_a_relaxation_frequency(op,names,flow,stress):
    a=arguments();a[2]=np.full_like(a[0],-1.);a[10]=np.full(2,-100.)
    r=op(*a)
    assert (r['Omega_'+names[0]]<0).all()
    assert (r['status_'+names[0]]=='negative_no_bgk_closure').all()


@pytest.mark.parametrize('op,names,flow,stress',OPS)
@pytest.mark.parametrize('bad',['density','flow','negative'])
def test_target_requires_physical_number_and_flow_conservation(op,names,flow,stress,bad):
    a=arguments();target=a[0].copy()
    if bad=='density':target*=2
    elif bad=='negative':target[0,0,0]=-1
    else:
        target[0,0,0]-=.25
        target[0,1,0]+=.125  # same density, different flow
    with pytest.raises(ValueError):op(*a,moment_state='target',target_distribution=target)


@pytest.mark.parametrize('op,names,flow,stress',OPS)
@pytest.mark.parametrize('idx,value',[(0,-1),(1,0),(5,-1),(6,0),(9,0),(9,np.inf)])
def test_invalid_physical_inputs(op,names,flow,stress,idx,value):
    a=arguments();a[idx]=np.full_like(a[idx],value) if isinstance(a[idx],np.ndarray) else value
    with pytest.raises(ValueError):op(*a)


@pytest.mark.parametrize('op,names,flow,stress',OPS)
def test_density_must_be_actual_integral_and_flags_boolean(op,names,flow,stress):
    a=arguments();a[1]*=1.1
    with pytest.raises(ValueError,match='density'):op(*a)
    with pytest.raises(ValueError,match='boolean'):op(*arguments(),**{names[0]+'_EL':1})


@pytest.mark.parametrize('op,names,flow,stress',OPS)
def test_nontrivial_target_conserves_energy_and_changes_only_stress_gap(op,names,flow,stress):
    a=arguments();f=a[0];w=(a[5][:,None]*a[6]).ravel();r=np.broadcast_to(a[7][:,None],(2,3)).ravel();x=np.broadcast_to(a[8],(2,3)).ravel()
    constraints=np.array([w,w*x,w*(r*r+x*x)])
    projector=r*r-2*x*x
    _,_,vh=np.linalg.svd(constraints,full_matrices=True)
    perturb=vh[3:].T@(vh[3:]@projector)
    perturb*=.1/np.max(np.abs(perturb))
    target=f+perturb.reshape(2,3,1)
    y=op(*a,moment_state='target',target_distribution=target)
    expect=np.sum(w[:,None]*(f-target).reshape(6,2)*projector[:,None],axis=0)/a[1]
    np.testing.assert_allclose(y[stress],expect,rtol=1e-14,atol=1e-14)
    assert np.all(np.abs(y[stress])>0)
    invalid=target.copy();invalid[0,1,:]-=.1;invalid[1,1,:]+=.05
    with pytest.raises(ValueError,match='energy'):
        op(*a,moment_state='target',target_distribution=invalid)


@pytest.mark.parametrize('op,names,flow,stress',OPS)
@pytest.mark.parametrize('index',range(12))
def test_shapes_and_finiteness_remain_fail_closed(op,names,flow,stress,index):
    a=arguments()
    if index==9:a[index]=[2.]
    else:a[index]=np.asarray(a[index]).reshape(-1)[:1]
    with pytest.raises(ValueError):op(*a)


@pytest.mark.parametrize('op,names,flow,stress',OPS)
def test_inputs_unchanged_and_channels_distinct(op,names,flow,stress):
    a=arguments();snapshot=[x.copy() if isinstance(x,np.ndarray) else x for x in a]
    r=op(*a)
    for x,y in zip(a,snapshot):np.testing.assert_array_equal(x,y)
    assert not np.allclose(r['Omega_'+names[0]],r['Omega_'+names[1]],rtol=1e-9,atol=1e-12)

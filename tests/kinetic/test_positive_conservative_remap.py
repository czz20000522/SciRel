"""Independent finite-volume moment tests for positive distribution remapping.

Quadrature below reconstructs faces directly, without calling SciRel helpers.
The moments are density, sqrt(Tnorm)-scaled axial-velocity density, and
Tnorm-scaled squared-speed density; common species constants cancel between
the two normalization temperatures.
"""
import numpy as np
import pytest
from scirel.kinetic import interp_distribution_across_mesh as remap
from scirel.kinetic.cross_mesh_distribution_interpolation import (
    InfeasibleMomentsError, MomentCorrectionConvergenceError,
)


def volume(r, v):
    radial_faces = np.r_[0., (r[:-1]+r[1:])/2, r[-1]+(r[-1]-r[-2])/2]
    axial_faces = np.r_[v[0]-(v[1]-v[0])/2, (v[:-1]+v[1:])/2,
                        v[-1]+(v[-1]-v[-2])/2]
    return np.pi*np.diff(radial_faces**2)[:, None]*np.diff(axial_faces)[None, :]


def moments(f, r, v, temperature):
    result = np.empty((3, f.shape[2]))
    weights = volume(r, v)
    # Deliberately scalar summation independent of production's matmul and
    # vector reductions; includes unequal cells and nonzero signed momentum.
    for k in range(f.shape[2]):
        result[:, k] = [sum(float(f[i,j,k]*weights[i,j]*term(i,j))
                           for i in range(r.size) for j in range(v.size))
                        for term in (lambda i,j:1.,
                                     lambda i,j:np.sqrt(temperature)*v[j],
                                     lambda i,j:temperature*(r[i]**2+v[j]**2))]
    return result


def check(f, a, b, **kwargs):
    r,v,x,T=a;rb,vb,xb,Tb=b
    original=f.copy();out=remap(f,r,v,x,T,rb,vb,xb,Tb,**kwargs)
    assert np.all(out>=0) and np.all(np.isfinite(out))
    np.testing.assert_array_equal(f,original)
    ma=moments(f,r,v,T); actual=moments(out,rb,vb,Tb)
    target=np.array([np.interp(xb,x,row,left=0.,right=0.) for row in ma])
    np.testing.assert_allclose(actual,target,rtol=1e-11,atol=1e-12)
    return out,target


def original_case():
    a=(np.linspace(.5,2,4),np.linspace(-1.5,1.5,6),np.linspace(0,1,5),2.)
    b=(np.linspace(.4,1.8,5),np.linspace(-1.2,1.2,7),np.linspace(.1,.9,4),1.5)
    f=np.exp(np.random.default_rng(0).normal(size=(4,6,5)))
    return f,a,b


def test_original_negative_witness_is_infeasible_and_rejected():
    f,a,b=original_case();m=moments(f,a[0],a[1],a[3]);tar=np.array([np.interp(b[2],a[2],row) for row in m])
    max_energy=b[3]*(b[0][-1]**2+max(b[1]**2))
    assert tar[2,0]/tar[0,0]>max_energy
    assert tar[2,1]/tar[0,1]>max_energy
    with pytest.raises(InfeasibleMomentsError,match='convex hull') as error:
        remap(f,*a[:3],a[3],*b[:3],b[3])
    assert error.value.diagnostics['x_b_index']==0
    assert error.value.diagnostics['scaled_margin']<0


def test_same_positive_witness_on_sufficient_support_conserves_all_moments():
    f,a,b=original_case();b=(np.linspace(.1,2.8,8),np.linspace(-2.7,2.7,11),b[2],b[3]);check(f,a,b)


def test_original_witness_feasible_spatial_tail_conserves_all_moments():
    f,a,b=original_case();b=(b[0],b[1],b[2][2:],b[3]);check(f,a,b)


@pytest.mark.parametrize('Tb',[.4,1.,2.3])
def test_nonuniform_unequal_meshes_drift_density_temperature_and_space(Tb):
    r=np.array([.05,.2,.7,1.4]);v=np.array([-1.7,-.6,-.1,.4,1.3]);x=np.array([0.,.1,.55,1.6]);T=1.7
    f=np.stack([n*np.exp(-(r[:,None]/.6)**2-((v[None,:]-drift)/.7)**2)
                for n,drift in zip([0.,1.,7.,2.],[-.2,.1,.5,-.3])],axis=2)
    scale=np.sqrt(T/Tb)
    b=(np.array([0.,.12,.5,1.,1.8])*scale,np.array([-2.,-1.3,-.35,.05,.7,1.9])*scale,
       np.array([-.1,.05,.3,.8,1.4,1.8]),Tb)
    out,target=check(f,(r,v,x,T),b)
    np.testing.assert_array_equal(out[:,:,[0,-1]],0.)
    # Density-weighted target is materially different from interpolating
    # intensive mean velocity and multiplying by interpolated density.
    m=moments(f,r,v,T);mean=np.divide(m[1],m[0],out=np.zeros_like(m[0]),where=m[0]>0)
    wrong=np.interp(b[2],x,mean,left=0,right=0)*target[0]
    assert np.max(np.abs(wrong-target[1]))>0.01


@pytest.mark.parametrize('same',[False,True])
def test_zero_density_is_exact_zero(same):
    f,a,b=original_case();f[:]=0.;b=a if same else b
    out,_=check(f,a,b);np.testing.assert_array_equal(out,0.)


def test_identical_mesh_is_exact_identity_including_zero_cells():
    f,a,_=original_case();f[::2,::2,:]=0.;out,_=check(f,a,a)
    np.testing.assert_array_equal(out,f)


def test_same_velocity_mesh_spatial_interpolation_is_exact_convex_mixture():
    f,a,_=original_case();b=(*a[:2],np.array([.125,.375,.625,.875]),a[3]);out,_=check(f,a,b)
    np.testing.assert_array_equal(out,.5*f[:,:,:-1]+.5*f[:,:,1:])


@pytest.mark.parametrize('face',['lower','upper','vertex','near_lower'])
def test_hull_boundary_and_near_boundary_targets(face):
    rb=np.array([.2,1.2]);vb=np.array([-1.,0.,1.]);x=np.array([0.,1.])
    if face in ('lower','near_lower'):
        u=.6;energy=.04+.6+(1e-8 if face=='near_lower' else 0.);r0=np.sqrt(energy-u*u)
        r=np.array([r0,1.7]);v=np.array([-1.3,u,1.5]);i=0;j=1
    elif face=='upper':
        u=.2;r0=np.sqrt(1.2**2+1-u*u);r=np.array([.1,r0]);v=np.array([-1.3,u,1.5]);i=1;j=1
    else:
        r=np.array([.2,1.7]);v=np.array([-1.3,1.,1.5]);i=0;j=1
    f=np.zeros((len(r),len(v),2));f[i,j,:]=1/volume(r,v)[i,j]
    out,_=check(f,(r,v,x,1.),(rb,vb,x,1.))
    if face=='lower':np.testing.assert_array_equal(out[1,:,:],0.)
    if face=='upper':np.testing.assert_array_equal(out[0,:,:],0.)
    if face=='vertex':assert np.count_nonzero(out)==2


@pytest.mark.parametrize('kind',['below_energy','outside_velocity'])
def test_infeasible_discrete_moments_fail_without_partial_result(kind):
    r=np.array([.01,.6]);v=np.array([-2.,.1,2.]);x=np.array([0.,1.]);f=np.zeros((2,3,2))
    f[0,1 if kind=='below_energy' else 2,:]=1.
    rb=np.array([.2,1.2]);vb=np.array([-1.,0.,1.])
    with pytest.raises(InfeasibleMomentsError):remap(f,r,v,x,1.,rb,vb,x,1.)


def test_iteration_exhaustion_is_distinct_from_infeasible_support():
    f,a,b=original_case();b=(np.linspace(.1,2.8,8),np.linspace(-2.7,2.7,11),b[2],b[3])
    with pytest.raises(MomentCorrectionConvergenceError,match='within 1 iterations at x_b index 0'):
        remap(f,*a[:3],a[3],*b[:3],b[3],max_correction_iterations=1)


def test_negative_particle_distribution_is_rejected_only_for_physical_branch():
    f,a,b=original_case();f[0,0,0]=-1.
    with pytest.raises(ValueError,match='fa must be nonnegative'):remap(f,*a[:3],a[3],*b[:3],b[3])
    raw=remap(f,*a[:3],a[3],*b[:3],b[3],correct=0)
    assert np.all(np.isfinite(raw))

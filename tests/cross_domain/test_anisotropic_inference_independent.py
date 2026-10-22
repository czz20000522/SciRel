"""Held-out curved-field inverse task; independent Biot-Savart and tensor oracle.

No SciRel field/force/forward function is used to generate these observations.
The reference independently solves the discrete equations; it is not a continuum
convergence certificate. Coincident filaments use the declared zero-self convention.
"""
import numpy as np
from scipy.integrate import quad
from scipy.optimize import root
from scirel.field import dense_axisymmetric_green_response
from scirel.equilibrium import solve_axisymmetric_anisotropic_picard
from scirel.diagnostics import synthesize_equilibrium_diagnostics
from scirel.inference.direct_anisotropic_inversion import solve_direct_anisotropic_inversion


def independent_case(n=5):
    r,z=np.linspace(.4,1.2,n),np.linspace(-.3,.3,n)
    R,Z=np.meshgrid(r,z);points=np.c_[R.ravel(),Z.ravel()]
    # Aphi = mu0/(4pi) integral Rsource*cos(phi)/distance dphi; psi=R*Aphi.
    G=np.zeros((R.size,R.size))
    for i,(rt,zt) in enumerate(points):
        for j,(rs,zs) in enumerate(points):
            if i==j:continue
            v,error=quad(lambda a: np.cos(a)/np.sqrt(rt*rt+rs*rs-2*rt*rs*np.cos(a)+(zt-zs)**2),0.,2*np.pi,epsabs=1e-12,epsrel=1e-12)
            G[i,j]=1e-7*rt*rs*v
    runtimeG=dense_axisymmetric_green_response(points,np.c_[points,np.ones(R.size)])['gpsi']
    np.testing.assert_allclose(runtimeG,G,rtol=1e-11,atol=1e-19)
    wr=np.full(n,(r[-1]-r[0])/(n-1));wr[[0,-1]]*=.5
    wz=np.full(n,(z[-1]-z[0])/(n-1));wz[[0,-1]]*=.5
    area=wz[:,None]*wr[None,:]
    vacuum=.5*R**2*(1-.08*Z)
    def reference_state(x,a,c):
        psi=np.reshape(x,R.shape)
        br=-np.gradient(psi,z,axis=0,edge_order=2)/R
        bz=np.gradient(psi,r,axis=1,edge_order=2)/R
        b=np.sqrt(br*br+bz*bz);ur,uz=br/b,bz/b
        pp=10000+a*psi+c*b;pt=10000+a*psi
        rr=pt+(pp-pt)*ur*ur;zz=pt+(pp-pt)*uz*uz;rz=(pp-pt)*ur*uz
        fr=np.gradient(rr,r,axis=1,edge_order=2)+np.gradient(rz,z,axis=0,edge_order=2)+(rr-pt)/R
        fz=np.gradient(rz,r,axis=1,edge_order=2)+np.gradient(zz,z,axis=0,edge_order=2)+rz/R
        j=(bz*fr-br*fz)/(b*b)
        return psi,pp,pt,j
    a,c=4800.,1100.
    solution=root(lambda x:(x-vacuum.ravel()-G@(reference_state(x,a,c)[3]*area).ravel()),vacuum.ravel(),tol=1.e-11)
    assert solution.success and np.max(abs(solution.fun))<1e-12
    psi,pp,pt,j=reference_state(solution.x,a,c)
    indexes=[(1,1),(2,3),(3,2)]
    signal_points=np.array([[R[k],Z[k]] for k in indexes])
    pick=lambda values:np.array([values[k] for k in indexes])
    obs={'flux_loops':{'points':signal_points,'quantity':'magnetic_flux','unit':'Wb','values':2*np.pi*pick(psi),'sigma':1e-5},
         'thomson':{'points':signal_points,'p_parallel':{'unit':'Pa','values':pick(pp),'sigma':1.},'p_perp':{'unit':'Pa','values':pick(pt),'sigma':1.}}}
    config={'r_grid':R,'z_grid':Z,'psi_vac':vacuum,'g_psi':runtimeG,'tol':1e-12,'maxiter':200,'relax':.3}
    def forward(payload):
        values=payload['params'];a,c=values['gradient'],values['anisotropy']
        state=solve_axisymmetric_anisotropic_picard(**{k:v for k,v in payload.items() if k!='params'},
            pressure_closure=lambda b,p:{'p_parallel':10000+a*p+c*b,'p_perpendicular':10000+a*p})
        return {**state,'psi_unit':'Wb/rad','profiles':{'p_parallel':state['p_parallel'],'p_perp':state['p_perpendicular']},'profile_units':{'p_parallel':'Pa','p_perp':'Pa'}}
    fit=solve_direct_anisotropic_inversion(initial_params={'gradient':3500.,'anisotropy':700.},bounds={'gradient':(1000.,7000.),'anisotropy':(100.,2000.)},method='least_squares',max_evaluations=140,solver_config=config,observations=obs,equilibrium_solver=forward,diagnostic_evaluator=synthesize_equilibrium_diagnostics)
    assert fit['converged']
    np.testing.assert_allclose([fit['best_parameters']['gradient'],fit['best_parameters']['anisotropy']],[a,c],rtol=1e-6,atol=0.)
    np.testing.assert_allclose(fit['equilibrium']['psi'],psi,rtol=1e-10,atol=1e-12)
    np.testing.assert_allclose(fit['equilibrium']['J_phi'],j,rtol=1e-8,atol=1e-7)
    assert np.max(abs(fit['equilibrium']['psi']-vacuum))>1e-5
    # Show that anisotropy is dynamically active, not merely an extra reported pressure.
    isotropic=forward({**config,'params':{'gradient':a,'anisotropy':0.}})
    assert np.max(abs(fit['equilibrium']['J_phi']-isotropic['J_phi']))>1.
    return fit


def test_independent_curved_field_biot_savart_tensor_observations():
    fit=independent_case()
    assert fit['residual_size']==9
    assert fit['chi2']<1e-10

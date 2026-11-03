"""中文物理示范：独立解析观测驱动的两参数各向异性平衡恢复。

测试模型采用显式制造的非零 rank-one Green 响应，产生均匀轴向磁场。
它验证力平衡、Green 反馈、磁通单位和推断的连接，不冒充具体线圈装置。
无需原来源源码、网络或捕获答案；观测由独立解析方程生成。
"""
import json
import numpy as np
from scirel.equilibrium import solve_axisymmetric_anisotropic_picard
from scirel.diagnostics import synthesize_equilibrium_diagnostics
from scirel.inference.direct_anisotropic_inversion import solve_direct_anisotropic_inversion


def case(n=7, true_gradient=1.7, true_ratio=1.6, with_failed_trials=True):
    R,Z=np.meshgrid(np.linspace(.2,.6,n),np.linspace(-.2,.2,n))
    B0,gain=1.,.6
    # Trapezoidal integration is exact for Jphi=a*R/B: C=integral R dR dZ.
    C=(.6**2-.2**2)/2*.4
    B=(B0+np.sqrt(B0**2+4*gain*true_gradient*C))/2
    points=np.array([[R[2,2],Z[2,2]],[R[-2,-2],Z[-2,-2]]])
    psi=B*points[:,0]**2/2
    pperp=5+true_gradient*points[:,0]**2/2
    observations={'flux_loops':{'points':points,'quantity':'magnetic_flux','unit':'Wb',
        'values':2*np.pi*psi,'sigma':1.e-3},
        'thomson':{'points':points,'p_parallel':{'values':true_ratio*pperp,'sigma':.02,'unit':'Pa'},
                   'p_perp':{'values':pperp,'sigma':.02,'unit':'Pa'}}}
    config={'r_grid':R,'z_grid':Z,'psi_vac':B0*R**2/2,
        'g_psi':gain*(R**2/2).ravel()[:,None]*np.ones((1,R.size)),
        'tol':1.e-12,'maxiter':150,'relax':.2}
    calls=[]
    def forward(payload):
        params=payload['params'];a,ratio=params['gradient'],params['ratio']
        p=5+a*R**2/2
        kwargs={k:v for k,v in payload.items() if k!='params'}
        if with_failed_trials and a>2.5:
            kwargs['maxiter']=1  # Deliberately insufficient iteration budget, not a physical bound.
        state=solve_axisymmetric_anisotropic_picard(**kwargs,
            pressure_closure=lambda _b,_psi:{'p_parallel':ratio*p,'p_perpendicular':p})
        calls.append({'gradient':a,'ratio':ratio,'converged':state['converged'],
                      'fixed_point_residual':state['fixed_point_residual'],'iterations':state['iterations']})
        return {**state,'psi_unit':'Wb/rad',
            'profiles':{'p_parallel':state['p_parallel'],'p_perp':state['p_perpendicular']},
            'profile_units':{'p_parallel':'Pa','p_perp':'Pa'}}
    result=solve_direct_anisotropic_inversion(initial_params={'gradient':1.,'ratio':1.2},
        bounds={'gradient':(.2,3.),'ratio':(1.1,2.5)},method='least_squares',
        n_initial_samples=8,seed=3,max_evaluations=140,
        observations=observations,solver_config=config,
        equilibrium_solver=forward,diagnostic_evaluator=synthesize_equilibrium_diagnostics)
    expected={'gradient':true_gradient,'ratio':true_ratio,'B':B,'psi':B*R**2/2,
              'J_phi':true_gradient*R/B,'C':C}
    return result,expected,config,calls


def run():
    result,expected,config,calls=case()
    assert result['converged'] and result['forward_converged']
    for key in ('gradient','ratio'):
        np.testing.assert_allclose(result['best_parameters'][key],expected[key],rtol=1.e-6,atol=0.)
    np.testing.assert_allclose(result['equilibrium']['psi'],expected['psi'],rtol=1.e-10,atol=1.e-12)
    np.testing.assert_allclose(result['equilibrium']['J_phi'],expected['J_phi'],rtol=1.e-10,atol=1.e-12)
    assert result['residual_vector'].shape==(6,)
    assert result['chi2']<1.e-12
    assert any(not x['converged'] for x in calls)
    assert result['best_valid_trial']['valid']
    assert np.max(np.abs(result['equilibrium']['psi']-config['psi_vac']))>1.e-3
    return {'recovered':result['best_parameters'],'truth':{k:expected[k] for k in ('gradient','ratio','B')},
            'chi2':result['chi2'],'residual_count':result['residual_size'],
            'forward_fixed_point_residual':result['equilibrium']['fixed_point_residual'],
            'scientific_evaluations':result['scientific_evaluations'],
            'failed_trials':sum(not x['converged'] for x in calls),
            'maximum_plasma_flux_increment':float(np.max(abs(result['equilibrium']['psi']-config['psi_vac']))),
            'identifiability':'two-parameter manufactured case only; no general inference guarantee',
            'green_model':'declared rank-one uniform-field response; not a calibrated device'}

if __name__=='__main__':
    print(json.dumps(run(),indent=2,ensure_ascii=False))

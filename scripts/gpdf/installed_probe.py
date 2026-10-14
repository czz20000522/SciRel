"""Source/answer/network-free scientific acceptance driver; NumPy/SciPy only.

Mounted separately read-only. References are recalculated from equations,
never read from captured arrays. JSON result is written to the output directory.
"""
import json,sys,os,hashlib,importlib.metadata as metadata
from pathlib import Path
import numpy as np
from scipy.integrate import quad
from scipy.linalg import expm
from scipy.special import wofz
import scirel
from scirel import kinetic as K

checks=[]
def check(name,fn):
    fn();checks.append(name)
def close(a,b,**kwargs):np.testing.assert_allclose(a,b,**kwargs)
def faddeeva():
    z=np.array([[0,40j,.3+.1j],[1-.2j,2+1j,-3-1j]])
    close(K.evaluate_faddeeva_gpdf(z)['w'],wofz(z),rtol=5e-13,atol=5e-13)
    close(K.evaluate_faddeeva_dr(z)['w'],wofz(z),rtol=3e-6,atol=4e-7)
    assert K.evaluate_faddeeva_gpdf(1j)['order']==32 and K.evaluate_faddeeva_dr(1j)['order']==16
    for order in (16,32):
        close(K.evaluate_maxwellian_fft(z,order=order)['Z'],1j*np.sqrt(np.pi)*K.evaluate_faddeeva_gpdf(z,order=order)['w'])
    for order in (8,12,16,24):
        close(K.evaluate_maxwellian_jpole(z,order=order)['Z'],1j*np.sqrt(np.pi)*wofz(z),rtol=5e-5,atol=5e-6)
    for phase in (1e200-.1j,1.79e308+1j,1.79e308-1j):
        close(K.evaluate_faddeeva_gpdf(phase)['w'],(1j/np.sqrt(np.pi))/phase,rtol=5e-15,atol=0)
check('faddeeva16_32_fft16_32_jpole8_12_16_24_matrix_overflow',faddeeva)

def cauchy():
    z=.3+.7j;mesh=np.linspace(-12,12,49)
    r=K.evaluate_cauchy_transform(z,lambda v:np.exp(-v*v)/np.sqrt(np.pi),integration_mesh=mesh)
    close(r['G'],1j*np.sqrt(np.pi)*wofz(z),atol=1e-10)
    close(K.evaluate_maxwellian_electrostatic(2,1e-8)['epsilon'],.75,atol=1e-12)
    r=K.solve_maxwellian_electrostatic_mode(.3,1.16-.013j)
    assert abs(r['residual'])<1e-9
check('preserved_selected4_cauchy_cold_response_seeded_mode',cauchy)

def generalized():
    z=.31+.7j
    densities={2:(lambda v:1.,(-.5,.5),[]),3:(lambda v:1-abs(v),(-1,1),[0]),
       4:(lambda v:np.sqrt(2)/np.pi/(1+v*v/2)**2,(-np.inf,np.inf),[0]),
       5:(lambda v:np.exp(-v*v)/np.sqrt(np.pi),(.1,np.inf),[]),
       6:(lambda v:3*np.sqrt(3)/(4*np.pi)/(1+abs(v)**3),(-4,4),[0])}
    for selector,(f,(a,b),splits) in densities.items():
        edges=[a,*splits,b]
        def integrate(power):
            value=0j
            for lo,hi in zip(edges[:-1],edges[1:]):
                for part,factor in ((np.real,1),(np.imag,1j)):
                    value+=factor*quad(lambda v:part(f(v)/(v-z)**power),lo,hi,epsabs=1e-11,epsrel=1e-11)[0]
            return value
        r=K.evaluate_generalized_dispersion(z,selector)
        close(r['Z'],integrate(1),atol=2e-9,rtol=2e-9)
        close(r['Zp'],integrate(2),atol=2e-8,rtol=2e-8)
    close(K.evaluate_generalized_dispersion(z,0)['Z'],1j*np.sqrt(np.pi)*wofz(z))
    close(K.evaluate_generalized_dispersion(z,1)['Zp'],1/z**2)
    r=K.evaluate_generalized_hilbert(np.array([.2+.7j,.2-.7j,.2]),'1/pi/(1+v.^2)',integration_mesh=[-8,-2,0,2,8])
    close(r['Z'],-1/(np.array([.2+.7j,.2-.7j,.2])+1j),atol=1e-9)
    expr=K.DensityExpression('exp(-v.^2)/sqrt(pi)')
    close(expr.derivative(.3),-2*.3*expr(.3),atol=1e-15)
check('all7_selectors_definition_integrals_Z_Zp_expression_Hilbert',generalized)
def source_grids():
    line=np.linspace(-10,10,201)
    close(K.evaluate_generalized_dispersion(line)['Z'],1j*np.sqrt(np.pi)*wofz(line),atol=1e-13)
    for axis in (np.linspace(-2,2,41),np.linspace(-6,6,201)):
        x,y=np.meshgrid(axis,axis);z=x+1j*y
        r=K.evaluate_generalized_dispersion(z)
        close(r['Z'],1j*np.sqrt(np.pi)*wofz(z),rtol=1e-13,atol=1e-13)
        assert r['Zp'].shape==z.shape
    for order in (8,12,16,24):
        close(K.evaluate_maxwellian_jpole(.1-1j,order=order)['Z'],1j*np.sqrt(np.pi)*wofz(.1-1j),rtol=5e-5,atol=5e-6)
check('source_1d201_and_2d41x41_201x201_science_grids_no_graphics',source_grids)
scans={}
def scan_all():
    for kind,count in [('langmuir',19),('generalized',18),('iaw',22),('beam',71)]:
        result=K.scan_gpdf_roots(kind)
        assert len(result['k'])==count and np.max(result['dielectric_residual'])<1e-9
        scans[kind]={'roots':count,'max_residual':float(np.max(result['dielectric_residual']))}
    unstable=K.scan_gpdf_roots('beam',k_values=[.3,.295],initial_guess=(1-.01j)/(np.sqrt(2)*.4))
    assert np.all(unstable['omega'].imag>0)
    r=K.evaluate_gpdf_small_k(np.array([.01,.1]))
    close(r['omega_real'],1+1.5*np.array([.01,.1])**2,atol=0)
check('four_complete_legacy_scans_130_roots_two_beam_branches_small_k',scan_all)
vp={}
def vp_all():
    for Fn in (1,2,3,4):
        r=K.solve_vlasov_poisson(Fn=Fn);s=r['state']
        assert s['df'].shape==(2049,) and s['dEt'].shape==(2001,)
        assert np.isfinite(s['df']).all() and np.isfinite(s['dEt']).all()
        close(s['dE'],1j*s['dv']*np.sum(s['df'])/s['k'],rtol=1e-13)
        vp[str(Fn)]={'last_field_real':float(s['dE'].real),'last_field_imag':float(s['dE'].imag),'recurrence_time':float(s['TR']),'diagnostic':r['diagnostic_status']}
    s=K.vp_init(nv=32,nt=100,dt=.001,vmax=5)
    A=-1j*s['k']*np.diag(s['vv'])+1j*s['dv']/s['k']*np.outer(s['df0dv'],np.ones(s['nv']+1))
    expected=expm(A*.1)@s['df'];actual=K.vp_evolve(s)['df']
    close(actual,expected,rtol=1e-10,atol=1e-12)
check('VP_all4_full_default_2049x2000_poisson_dense_expm_oracle',vp_all)

origin=Path(scirel.__file__).resolve()
assert '/site-packages/' in str(origin) and not any('/work' in p for p in sys.path)
assert not Path('/work').exists()
for forbidden in ('pytest','mpmath','sympy','matplotlib','scirel_workflow','scirel_plugin'):
    import importlib.util
    assert importlib.util.find_spec(forbidden) is None,forbidden
result={'schema':'scirel.gpdf-installed-independent.v1','checks':checks,'all_passed':True,
        'scirel_origin':str(origin),'python':sys.version,'platform':sys.platform,
        'distributions':{x:metadata.version(x) for x in ('scirel','numpy','scipy')},
        'sys_path':sys.path,'scans':scans,'vp':vp,
        'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'forbidden_development_imports':'ABSENT','source_mount':'ABSENT','answers':'NOT_USED'}
Path('/results/SCIENCE.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))

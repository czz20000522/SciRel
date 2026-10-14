"""Independent finite-harmonic velocity-integral and analytic-axis regressions."""
import json
from pathlib import Path
import numpy as np
import pytest
from scirel.kinetic.pdrk import magnetized as m
import _pdrk_oracle as oracle
import _pdrk_axis_oracle as axes

T=Path(__file__).resolve().parents[1]
CASES=json.loads((T/'pdrk-canonical-fixtures.json').read_text())['cases']+json.loads((T/'pdrk-holdout-fixtures.json').read_text())['cases']

def _case(f,iem=1):
    p=oracle.physical(f['deck'],f['B0']);scale=abs(p['gyro'][0])/p['vtz'][0]
    eq=m.initialize_equilibrium(np.asarray(f['deck']),controls=dict(B0=f['B0'],iem=iem,N=12,J=12,iout=1,sp=0))
    return eq,p,f['kx_over_Omega1_vt1']*scale,f['kz_over_Omega1_vt1']*scale,complex(*f['omega_over_absOmega1'])*abs(p['gyro'][0])

def _close(a,b,bound):
    metric=oracle.error(np.asarray(a),np.asarray(b));assert max(metric['component'],metric['relative'])<=bound

@pytest.mark.parametrize('J',[4,8,12])
def test_poles_asymptotic_moments(J):
    s=m.pole_coefficients(J).state;b=np.asarray(s['bzj']).ravel();c=np.asarray(s['czj']).ravel()
    assert b.size==c.size==J
    for n,value in [(0,-1),(1,0),(2,-.5)]:_close(np.sum(b*c**n),value,1e-10)
    if J==12:
        z=np.array([.2+.7j,2+.3j,4+.6j,-1.5+.8j]);_close(np.sum(b/(z[:,None]-c),axis=1),oracle.plasma_z(z),5e-5)

@pytest.mark.parametrize('f',CASES,ids=lambda f:f['id'])
def test_signed_oblique_response_independent_velocity_integral(f):
    eq,p,kx,kz,w=_case(f)
    for sign in [1,-1]:
        K64,es64=oracle.response(f['deck'],f['B0'],kx,sign*kz,w,12,64)
        K,es=oracle.response(f['deck'],f['B0'],kx,sign*kz,w,12,96)
        K8,es8=oracle.response(f['deck'],f['B0'],kx,sign*kz,w,8,96)
        for a,b in[(K64,K),(es64,es),(K8,K),(es8,es)]:_close(a,b,1e-8)
        actual=oracle.em_schur(m.electromagnetic_matrix(eq,kx=kx,kz=sign*kz).state['M'],w)[0];_close(actual,K,5e-5);_close(actual-np.eye(3),K-np.eye(3),5e-5)
        eseq,*_=_case(f,0);_close(oracle.es_schur(m.electrostatic_matrix(eseq,kx=kx,kz=sign*kz).state['M'],w),es,5e-5)

@pytest.mark.parametrize('f',CASES,ids=lambda f:f['id'])
def test_exact_perpendicular_and_zero_wavevector_analytic_tensor(f):
    eq,p,kx,kz,w=_case(f)
    ref=axes.perpendicular(f['deck'],f['B0'],kx,w,12,96)
    _close(axes.perpendicular(f['deck'],f['B0'],kx,w,12,64),ref,1e-8)
    _close(axes.perpendicular(f['deck'],f['B0'],kx,w,8,96),ref,1e-8)
    _close(oracle.em_schur(m.electromagnetic_matrix(eq,kx=kx,kz=0).state['M'],w)[0],ref,5e-5)
    ref=np.eye(3,dtype=complex)
    for wp,g in zip(p['wp2'],p['gyro']):
        ref[0,0]-=wp/(w*w-g*g);ref[1,1]-=wp/(w*w-g*g);ref[0,1]-=1j*wp*g/(w*(w*w-g*g));ref[1,0]+=1j*wp*g/(w*(w*w-g*g));ref[2,2]-=wp/(w*w)
    for N in [0,1,12]:
        zero_eq=m.initialize_equilibrium(np.asarray(f['deck']),controls=dict(B0=f['B0'],iem=1,N=N,J=12,iout=1,sp=0))
        _close(oracle.em_schur(m.electromagnetic_matrix(zero_eq,kx=0,kz=0).state['M'],w)[0],ref,1e-12)

def test_invalid_domains_rejected_before_native_process():
    with pytest.raises(ValueError):m.pole_coefficients(5)
    with pytest.raises(ValueError):m.initialize_equilibrium(controls={'B0':0})
    deck=np.asarray(CASES[0]['deck']);deck[0,1]=0
    with pytest.raises(ValueError):m.initialize_equilibrium(deck)

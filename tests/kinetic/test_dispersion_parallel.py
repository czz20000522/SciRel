"""Signed-wavevector causal response from direct Gaussian velocity integrals."""
import numpy as np
import pytest
from scipy.special import roots_hermite
from scirel.kinetic.dispersion.parallel import em1d_parallel_residual,continue_em1d

STATE=dict(wps2=np.array([1.,2.,.4]),vds=np.array([.2,-.1,.3]),vtzs=np.array([.7,1.1,.5]),wcs=np.array([.4,-.7,.2]),c2=9.,cwp=1.,wcs1=1.)

def _integral(state,w,k,pm,Q):
    x,h=roots_hermite(Q);out=w*w-k*k*state['c2']
    for wp,vd,vt,wc in zip(state['wps2'],state['vds'],state['vtzs'],state['wcs']):
        out-=wp*(w-k*vd)*np.sum(h/np.sqrt(np.pi)/(w-k*(vd+vt*x)+pm*wc))
    return out

@pytest.mark.parametrize('k',[-.3,.3])
@pytest.mark.parametrize('pm',[-1,1])
def test_causal_signed_k_direct_velocity_integral(k,pm):
    w=2.1+.8j;a=_integral(STATE,w,k,pm,96);b=_integral(STATE,w,k,pm,160)
    f,scale=em1d_parallel_residual(STATE,w,k,pm=pm)
    assert abs(a-b)/max(1,abs(b))<=1e-12
    assert abs(f-b)/scale<=1e-12
    reflected=dict(STATE,vds=-STATE['vds']);mirror,_=em1d_parallel_residual(reflected,w,-k,pm=pm)
    assert abs(f-mirror)/scale<=1e-12

def test_parallel_rejects_complex_and_unrepresentable_wavevectors():
    for k in [0,1+1j,True,np.longdouble('1e400')]:
        with pytest.raises(ValueError):em1d_parallel_residual(STATE,2+.7j,k)
    with pytest.raises(ValueError):em1d_parallel_residual(STATE,np.clongdouble('1e400'),.3)
    for k in [[],[0],[.1+1j]]:
        with pytest.raises(ValueError):continue_em1d(dict(state=STATE,k_grid=k))

"""Private D2 scientific support adapters to unchanged D1 packaged renderers.

This is an integration candidate, not a new distribution. The minimal native resource closure and generic transport are bundled locally.
No pdrk_l1 package is imported. No original checkout/network/globalkinetic state is read.
Scientific coordinate/normalization mapping is explicit below; no new source
plotting math is inferred. WHAMP table is attributed stored data, never an oracle
for a different physical setup. Rights status remains unresolved for redistribution.
"""
import numpy as np
from . import _example_native as _d1

def fluid_deck():
    """Source ten-column SI default deck as packaged data, returned independently."""
    return np.array(_d1.fluid_deck(),dtype=np.float64,copy=True)

def fluid_plot_scan(graph,state,*,method=2,length_scale_m=None,frequency_scale_rad_s=None,capture_png=True,transport=None):
    """Unchanged native renderer with explicit SI/default or normalized coordinates.

    Method2 consumes k in m^-1 and omega in rad/s unless both normalization
    scales are explicitly given. No tmpglobals are inferred from kinetic state.
    Methods3/4 retain source theta/rad and kx/kz SI renderer conventions; requesting
    other normalization there is rejected instead of silently ignored.
    Undefined zero-B beta remains None scientifically; empty MATports in renderer
    mean no defined beta annotation, never an invented zero beta.
    """
    from ._fluid_parallel import normalize_plot_coordinates

    normalize_plot_coordinates([0.],[0.],length_scale_m=length_scale_m,frequency_scale_rad_s=frequency_scale_rad_s)
    if method!=2 and length_scale_m is not None:raise ValueError('source methods3/4 plot SI/radian axes; normalization here is method2-only')
    w1=np.asarray(graph['w1']);w2=np.asarray(graph['w2']);axes=graph['axis_values']
    values=dict(kk=np.array([]),tt=np.array([]),kkx=np.array([]),kkz=np.array([]),ww1=w1,ww2=w2,k=0.)
    if method in (1,2):values.update(kk=np.asarray(axes[0]),ww1=w1[:,0,:],ww2=w2[:,0,:])
    elif method==3:values.update(tt=np.asarray(axes[1]),k=float(np.hypot(graph['kx'][0,0],graph['kz'][0,0])),ww1=w1[0,:,:],ww2=w2[0,:,:])
    elif method==4:values.update(kkx=np.asarray(graph['kx']).T,kkz=np.asarray(graph['kz']).T,ww1=w1.transpose(1,0,2),ww2=w2.transpose(1,0,2))
    else:raise ValueError('method1..4 required')
    eq=dict(s=len(state['q']),c2=state['c2'],ms=state['m'],betasz=np.array([])if state['beta_z']is None else state['beta_z'],betasp=np.array([])if state['beta_p']is None else state['beta_p'])
    return _d1.fluid_plot_scan(values,eq,method=method,tmpcwp=1. if length_scale_m is None else length_scale_m,tmpwcs1=1. if frequency_scale_rad_s is None else frequency_scale_rad_s,capture_png=capture_png,transport=transport)

def em1d_plot(graph,state,predecessor_plot=None,*,pm=1,transport=None):
    """Compose accepted continuation on explicit prior FIG, retaining native styles.

    Exact source suffix/pm=-1 legend remains attributable D1 implementation.
    A mismatched source six-label legend is preserved, not a claim that unrelated
    predecessor curves have those scientific identities. Caller owns predecessor
    lineage and physical normalization cwp[m],wcs1[rad/s]. No solve is repeated.
    """
    continuation=dict(k=graph['k'],wre=np.real(graph['omega']),wie=np.imag(graph['omega']))
    return _d1.em1d_plot(continuation,state,predecessor_plot,pm=pm,transport=transport)

def whamp_reference(*,transport=None):
    """Exact stored40x4 source table; units/run metadata are not inferred."""
    return _d1.whamp_reference(transport=transport)

def whamp_overlay(predecessor_plot=None,*,transport=None):
    """Original every-other-row overlay/legend onto explicit FIG, no solver."""
    return _d1.whamp_overlay(predecessor_plot,transport=transport)

"""Minimal private packaged support closure; no full D1 package dependency."""
from pathlib import Path
from typing import Mapping
import numpy as np
from scipy import sparse
from ._transport import NativeAction,NativeTransport
ROOT=Path(__file__).resolve().parent/'_native'
PLOT=('figure_native','figure_png','line_x','line_y','line_offsets','line_axes','line_width','line_markers','axes_limits','legend_labels')
ACTIONS={
 'fluid_plot':NativeAction('examples/fluid_plot_scan.m',('plot_line_count','plot_surface_count','png_bytes'),('s','method','kk','tt','kkx','kkz','ww1','ww2','c2','ms','betasz','betasp','k','tmpcwp','tmpwcs1','capture_png'),('examples',)),
 'em_plot':NativeAction('examples/em1d_plot.m',PLOT,('predecessor_figure','k','wre','wie','cwp','wcs1','pm'),('examples',)),
 'whamp_data':NativeAction('examples/whamp_data.m',('whpdat','kxwhp','kzwhp','wrwhp','wiwhp'),(),('examples',)),
 'whamp_overlay':NativeAction('examples/whamp_overlay.m',(*PLOT,'whpdat','kxwhp','kzwhp','wrwhp','wiwhp'),('predecessor_figure',),('examples',)),
 'finiteN':NativeAction('finiteN/action.m',('w',),('z','N'),('finiteN',))}
def state(x):return x.state if hasattr(x,'state')else x

def source_numeric(value):
    if sparse.issparse(value):
        target=np.complex128 if value.dtype.kind=='c'else np.float64
        already=(value.dtype.kind=='f'and value.dtype.itemsize==8)or(value.dtype.kind=='c'and value.dtype.itemsize==16)
        return value.astype(target)if value.dtype.kind in 'biufc'and not already else value
    a=np.asarray(value)
    if a.dtype.kind in 'biuf'and not(a.dtype.kind=='f'and a.dtype.itemsize==8):return a.astype(np.float64)
    if a.dtype.kind=='c'and a.dtype.itemsize!=16:return a.astype(np.complex128)
    return value

def invoke(name,ports,transport=None):
    return (transport or NativeTransport(ROOT,ACTIONS)).invoke(name,{k:v if k=='predecessor_figure'else source_numeric(v)for k,v in ports.items()})

def fluid_deck():return np.loadtxt(ROOT/'examples/pdrf_SI.in',skiprows=1,ndmin=2)
def fluid_plot_scan(scan,equilibrium,*,method=2,tmpcwp=None,tmpwcs1=None,capture_png=False,transport=None):
    values=state(scan);eq=state(equilibrium);ports={k:values[k]for k in ('kk','tt','kkx','kkz','ww1','ww2','k')};ports.update({k:eq[k]for k in ('s','c2','ms','betasz','betasp')});ports.update(method=method,tmpcwp=np.array([])if tmpcwp is None else tmpcwp,tmpwcs1=np.array([])if tmpwcs1 is None else tmpwcs1,capture_png=capture_png)
    return invoke('fluid_plot',ports,transport)
def em1d_plot(continuation,initialized_state,predecessor_plot,*,pm=1,transport=None):
    values=state(continuation);eq=state(initialized_state);ports={k:values[k]for k in ('k','wre','wie')};ports.update({k:eq[k]for k in ('cwp','wcs1')});ports.update(pm=pm,predecessor_figure=np.array([],dtype=np.uint8)if predecessor_plot is None else state(predecessor_plot)['figure_native']);return invoke('em_plot',ports,transport)
def whamp_reference(*,transport=None):return invoke('whamp_data',{},transport)
def whamp_overlay(predecessor_plot,*,transport=None):return invoke('whamp_overlay',{'predecessor_figure':np.array([],dtype=np.uint8)if predecessor_plot is None else state(predecessor_plot)['figure_native']},transport)
def faddeeva_finite_N(z,N=16,*,transport=None):
    """Explicit finite-N approximation; N16/64 bounded independently, not canonicalaccuracy."""
    if not isinstance(N,(int,np.integer))or isinstance(N,(bool,np.bool_))or N<=0:raise ValueError('positive integer N required')
    return invoke('finiteN',{'z':z,'N':N},transport)

"""Finite rational kinetic models with explicit approximation and axis limits.

Contracts retain legacy dimensionless ES and SI EM conventions. ES3D uses the
correct finite-Harris descriptor rather than the source's scaled frequencies.
Packaged native resources supply attributable original relations; scientific
corrections/limits remain explicit below. No D1 package, original checkout,
network, symbolic package or GUI is required by these callable numeric APIs.
This development module is not approved for default distribution.
"""
from pathlib import Path
import numpy as np
from ._transport import NativeAction,NativeTransport
from ._rational_frequency import solve_rational_frequency


# Canonical rational operators are catalogued here.  The lower-level
# composition helpers (``ordered_spectrum`` and friends) are routed through
# ``scirel.kinetic.pdrk.workflows`` and are therefore not star-import exports.
__all__ = [
    "default_deck",
    "equilibrium",
    "pole_table",
    "point_matrix",
    "solve_matrix",
    "em_coordinates",
    "jpole_grid_coordinates",
    "jpole_evaluate",
    "jpole_coefficients",
]

_ROOT=Path(__file__).resolve().parent/'_native'
_MODELS=('es1d','es3d','em')
_EQ={
 'es1d':('S','qs','ms','ns0','Ts','vs0','vts','lambdaDs','kDs','wps'),
 'es3d':('S','qs','ms','ns0','Tzs','Tps','vs0','vtzs','lambdaDs','kDs','wps','wcs','rhocs'),
 'em':('S','qs0','ms0','ns0','Tzs0','Tps0','qs','ms','Tzs','Tps','vs0','vtzs','lambdaDs','kDs','wps','wcs','rhocs','wps2','lmdT','betasz','betasp','vA','cS','wci','wpi','cwp','vAwp','c2','epsilon0','mu0','kB')}
_IN={'es1d':('S','J','bzj','czj','vts','vs0','kDs','k'),'es3d':('S','N','J','bzj','czj','kx','kz','rhocs','kDs','wcs','vtzs','vs0','Tzs','Tps'),'em':('S','N','J','bzj','czj','kx','kz','rhocs','wcs','vtzs','vs0','lmdT','wps2','c2')}
_OUT={'es1d':('M','SJ','csj','bsj'),'es3d':('SNJ','k','bs','bs2','aSNJ','csnj','bsnj'),'em':('M','SNJ','SNJ1','SNJ3','NN','k','bs','bs2','csnj','b11','b12','b13','b21','b22','b23','b31','b32','b33')}


def _model(model):
 if model not in _MODELS:raise ValueError('unknown legacy physical model')
 return model


def _scalar(value,name,*,positive=False,nonzero=False):
 v=np.asarray(value)
 if v.shape!=() or v.dtype.kind not in 'iuf' or not np.isfinite(v) or (positive and v<=0) or (nonzero and v==0):raise ValueError(name+' must be finite real scalar in the physical domain')
 try: narrowed=float(v)
 except (OverflowError,ValueError):raise ValueError(name+' not representable in float64') from None
 if not np.isfinite(narrowed) or (positive and narrowed<=0) or (nonzero and narrowed==0):raise ValueError(name+' not representable in declared float64 domain')
 return narrowed


def _complex_scalar(value,name):
 v=np.asarray(value)
 if v.shape!=() or v.dtype.kind not in 'iufc' or not np.isfinite(v):raise ValueError(name+' must be finite numeric scalar')
 try:narrowed=complex(v)
 except (OverflowError,ValueError):raise ValueError(name+' not representable in complex128') from None
 if not np.isfinite(narrowed):raise ValueError(name+' not representable in complex128')
 return narrowed


def _integer(value,name,minimum=0):
 v=_scalar(value,name)
 if v!=int(v) or v<minimum:raise ValueError(name+' must be integer in the declared domain')
 return int(v)


def _native(script,state,outputs):
 from scipy import sparse
 state={k:(v.astype(np.complex128 if v.dtype.kind=='c' else np.float64) if sparse.issparse(v) else np.asarray(v,dtype=np.complex128 if np.asarray(v).dtype.kind=='c' else np.float64)) for k,v in state.items()}
 if not all(np.isfinite(v.data if sparse.issparse(v) else v).all() for v in state.values()):raise ValueError('native numeric port not representable in float64/complex128')
 action=NativeAction('legacy/'+script+'.m',tuple(outputs),tuple(state))
 result=NativeTransport(_ROOT,{'relation':action},timeout_seconds=600).invoke('relation',state)
 return {'state':dict(result.state),'receipt':result.receipt}


def default_deck(model='es1d'):
 """Exact read-only legacy deck; callers explicitly select its unit convention."""
 name={'es1d':'pdrk_es1d.in','es3d':'pdrk_es3d.in','em':'pdrk_em3d.in'}[_model(model)]
 return np.loadtxt(_ROOT/'legacy'/name,skiprows=1,ndmin=2)


def equilibrium(model,deck,*,B0=None):
 """Positive finite Maxwellian species scales; source constants explicit in output.

 ES1D q,m,n,T,v dimensionless; ES3D q,m,n,Tparallel,Tperp,v dimensionless.
 EM q/e,m/me,n[m^-3],Tparallel/perp[eV],v/c; source normalizers require two
 species. ES3D rho is absolute; EM rho signed. Zero B in magnetized models
 requires a different unmagnetized relation and is not replaced by epsilon.
 """
 model=_model(model);d=np.asarray(deck)
 cols=5 if model=='es1d' else 6
 if d.ndim!=2 or d.shape[1]!=cols or len(d)<(2 if model=='em' else 1) or d.dtype.kind not in 'iuf' or not np.isfinite(d).all():raise ValueError('invalid physical species deck')
 if np.any(d[:,0]==0) or np.any(d[:,1:4]<=0) or (cols==6 and np.any(d[:,4]<=0)):raise ValueError('charges must be nonzero, masses/densities/temperatures positive')
 state={'deck':d}
 if model!='es1d':state['B0']=_scalar((1 if model=='es3d' else 100e-9) if B0 is None else B0,'B0',nonzero=True)
 with np.errstate(over='ignore',under='ignore',invalid='ignore'):d=np.asarray(d,dtype=np.float64)
 if not np.isfinite(d).all() or np.any(d[:,0]==0) or np.any(d[:,1:4]<=0) or (cols==6 and np.any(d[:,4]<=0)):raise ValueError('physical deck not representable in float64')
 state['deck']=d
 out=_native(model+'_equilibrium',state,_EQ[model])
 if not all(np.isfinite(v).all() for v in out['state'].values()):raise FloatingPointError('derived equilibrium is not representable')
 return out


def pole_table(model='es1d',J=8,*,opt=None):
 """Explicit source-family pole data; no silent fallback to a different order.

 ES1D J2,3,4,8,12; ES3D/EM J4,8,12. opt=1/2 distinguishes ES1D J4/J8
 source tables. Table choice is approximation metadata, not a global accuracy
 claim. General upper/lower-plane error domains still require qualification.
 """
 model=_model(model);J=_integer(J,'J',1)
 if J not in ((2,3,4,8,12) if model=='es1d' else (4,8,12)):raise ValueError('unsupported pole order for selected family')
 p={'J':J}
 if model=='es1d':
  opt=(2 if J==4 else 1) if opt is None else _integer(opt,'opt',1)
  if opt not in (1,2):raise ValueError('opt must select table1 or2')
  p['opt']=opt
 return _native(model+'_poles',p,('J','bzj','czj'))


def point_matrix(model,state,*,k=None,kx=None,kz=None,N=None):
 """Build model-specific eigenmatrix or corrected Harris descriptor coefficients.

 ES3D deliberately does not expose the source's incorrect ordinary matrix M.
 Exact parallel Bessel limits and a separate exact-perpendicular full-I pole
 pencil retain both axes. Signed wavevectors select the causal pole sheet.
 Signed and exact-axis responses have bounded independent qualification;
 installed public contracts are checked separately.
 """
 model=_model(model);s=dict(state)
 if model=='es1d':s['k']=_scalar(k,'k',nonzero=True)
 else:
  s['kx']=_scalar(kx,'kx');s['kz']=_scalar(kz,'kz');s['N']=_integer((10 if model=='es3d' else 2) if N is None else N,'N')
  if model=='es3d' and s['kx']==0 and s['kz']==0:raise ValueError('zero ES wavevector requires separate longitudinal limit')

 # Select the causal Padé sheet locally: Imomega>0 poles remain damped for either signed wavevector.
 direction=s['k'] if model=='es1d' else s['kz']
 if direction<0:s['czj']=-np.asarray(s['czj'])
 if model=='em' and s['kz']==0:
  from ._perpendicular_em import perpendicular_maxwell_pencil
  gyro=np.asarray(s['wcs']).ravel();vtz=np.asarray(s['vtzs']).ravel();rho=np.asarray(s['rhocs']).ravel();wp2=np.asarray(s['wps2']).ravel();vd=np.asarray(s['vs0']).ravel()
  components=[dict(gyro=g,wp2=p,vtz=z,vtp=np.sqrt(2)*abs(g*r),drift=v,weight=1.) for g,p,z,r,v in zip(gyro,wp2,vtz,rho,vd)]
  p=perpendicular_maxwell_pencil(components=components,kx=s['kx'],N=s['N'],c2=float(np.asarray(s['c2']).item()))
  na=p['M'].shape[0]-6;p.update(NN=p['M'].shape[0],SNJ3=na,SNJ1=na//3,SNJ=na//3-1,k=abs(s['kx']),kz=0.,kx=s['kx'],representation='analytic uniform cold pole pencil' if s['kx']==0 else 'exact perpendicular full-I Gaussian pole pencil',source_auxiliary_capacity=3*(int(np.asarray(s['S']).item())*(2*s['N']+1)*int(np.asarray(s['J']).item())+1),source_auxiliary_aliases='not certified as physical waves; compressed pole representation retains E/B observables')
  return {'state':p,'receipt':{'backend':'Python scaled-Bessel pole pencil','source_axis_repair_sha256':'e5f28e534ff231ceb8a1fa3b234e2c4006cb34a8c5a00b6e50943d1ba329b532','causal_sheet':1}}
 out=_native(model+'_matrix',{k:s[k] for k in _IN[model]},_OUT[model])
 if model=='es3d':
  out['state']['constant']=complex(np.asarray(out['state']['aSNJ']).item())
  out['state']['poles']=np.asarray(out['state']['csnj']).ravel()
  out['state']['residues']=np.asarray(out['state']['bsnj']).ravel()
  if s['kz']==0:out['state']['perpendicular_inputs']={'alpha':(np.asarray(s['kDs']).ravel()/abs(s['kx']))**2,'rho':np.asarray(s['rhocs']).ravel(),'gyro':np.asarray(s['wcs']).ravel(),'temperature_ratio':(np.asarray(s['Tzs'])/np.asarray(s['Tps'])).ravel(),'kx':s['kx'],'N':s['N'],'source_pole_order':int(np.asarray(s['J']).item())}
 out['state']['causal_sheet']=-1 if direction<0 else 1
 return out


def solve_matrix(matrix,*,model='es1d',sp=0,nw=None,wg=0):
 """Frequency solve with full eigenvectors/backward residual and explicit shift.

 EM is binary64 eig/eigs, avoiding the source's post-eig VPA conversion which
 does not improve eigenvalue accuracy. This intentional dependency change is
 not a claim of identical incidental LAPACK root order. Physical roots require
 independent dielectric checks as well as a backward-stable matrix solve.
 """
 model=_model(model)
 if model=='es3d':
  if 'perpendicular_inputs' in matrix:
   from ._harris_perpendicular import solve_perpendicular_harris
   return solve_perpendicular_harris(**matrix['perpendicular_inputs'])
  r=solve_rational_frequency(constant=matrix['constant'],poles=matrix['poles'],residues=matrix['residues'])
  if 'accepted' in r and not np.all(r['accepted']):
   error=ArithmeticError('unqualified finite descriptor modes; inspect attached diagnostics');error.diagnostics=r;raise error
  return r
 # Detect SciPy sparse subclasses without importing SciPy for ordinary dense
 # rejected inputs.  A user-defined subclass has its own ``__module__`` but
 # keeps the concrete SciPy sparse base in its MRO, which the old
 # ``scipy.sparse.issparse`` path accepted.
 is_sparse = any(
  cls.__module__.startswith('scipy.sparse.')
  for cls in type(matrix).__mro__
 )
 M=matrix if is_sparse else np.asarray(matrix,dtype=complex)
 finite_values=M.data if is_sparse else M
 if len(M.shape)!=2 or M.shape[0]!=M.shape[1] or M.shape[0]==0 or not np.isfinite(finite_values).all():raise ValueError('finite square frequency matrix required')
 sp=_integer(sp,'sp')
 if sp not in (0,1):raise ValueError('sp must be dense0 or shifted sparse1')
 if sp:
  count=_integer(1 if nw is None else nw,'nw',1)
  if count>=M.shape[0]-1:raise ValueError('sparse eigs requires nw<dimension-1')
  shift=_complex_scalar(wg,'wg')
  if not np.isfinite(shift):raise ValueError('finite frequency shift required')
 from scipy import sparse
 from scipy.linalg import eig
 from scipy.sparse.linalg import eigs
 if sp:
  d,V=eigs(sparse.csc_matrix(M),k=count,sigma=shift)
 else:d,V=eig(M.toarray() if is_sparse else M)
 norm=sparse.linalg.norm(M) if is_sparse else np.linalg.norm(M)
 residual=np.linalg.norm(M@V-V*d,axis=0)/((norm+abs(d))*np.linalg.norm(V,axis=0))
 if not np.isfinite(d).all() or not np.isfinite(residual).all() or np.any(residual>max(1e-11,128*len(d)*np.finfo(float).eps)):raise ArithmeticError('frequency eigensolver failed backward residual gate')
 order=np.argsort(-d.imag,kind='stable');w=d[order]
 return dict(d=d,omega=d,V=V,w=w,wi=w.imag,ind=order,indices='zero-based',backward_residual=residual,wg=w[0])


def em_coordinates(kj,cwp,*,theta_degrees=71):
 """Explicit legacy kc/omega_pi and degrees to SI wavevector components."""
 k=_scalar(kj,'kj')/_scalar(cwp,'cwp',positive=True);theta=np.deg2rad(_scalar(theta_degrees,'theta_degrees'))
 return dict(kx=k*np.sin(theta),kz=k*np.cos(theta),theta=theta,k=k)


def ordered_spectrum(model='es1d',deck=None,*,J=8,opt=None,N=None,B0=None,points=None,sp=0,wg0=1.5):
 """Corrected numeric graph; explicit point axes and per-point spectra/state.

 Defaults retain source sampling grids: ES1D .4:-.02:.01; ES3D kx .05:.1:5
 with kz=0; EM kc/omega_pi .01:.02:1 at71 degrees. EM shift starts wg0*wci
 and follows input order. Physical descriptor root counts may vary; no padding.
 """
 model=_model(model);eq=equilibrium(model,default_deck(model) if deck is None else deck,B0=B0);tab=pole_table(model,J,opt=opt);s={**eq['state'],**tab['state']}
 if points is None:
  grids=_native('default_coordinates',{},('es1d_grid','es3d_grid','em_grid'))['state']
  if model=='es1d':points=[(k,) for k in np.asarray(grids['es1d_grid']).ravel()]
  elif model=='es3d':points=[(k,0.) for k in np.asarray(grids['es3d_grid']).ravel()]
  else:points=[(em_coordinates(k,float(np.asarray(s['cwp']).item()))['kx'],em_coordinates(k,float(np.asarray(s['cwp']).item()))['kz']) for k in np.asarray(grids['em_grid']).ravel()]
 points=[tuple(p) for p in points];spectra=[];guess=_complex_scalar(wg0,'wg0')*float(np.asarray(s['wci']).item()) if model=='em' else 0
 for p in points:
  r=point_matrix(model,s,**({'k':p[0]} if model=='es1d' else {'kx':p[0],'kz':p[1],'N':N}))
  solved=solve_matrix(r['state'] if model=='es3d' else r['state']['M'],model=model,sp=sp,wg=guess)
  if model=='em':guess=solved['wg']
  spectra.append({'matrix':r,'solution':solved})
 return dict(model=model,points=np.asarray(points),equilibrium=eq,pole_table=tab,spectra=spectra,wg=guess,mode_axis='per-point explicit spectrum')


def jpole_grid_coordinates():
 """Source diagnostic grid; this is not an approximation-validity declaration."""
 return _native('jpole_coordinates',{},('x','y','z'))


def jpole_evaluate(bzj,czj,z):
 """Evaluate a simple-pole rational approximation, preserving the z shape."""
 b=np.asarray(bzj,dtype=complex).ravel();c=np.asarray(czj,dtype=complex).ravel();z=np.asarray(z,dtype=complex)
 if len(b)==0 or b.shape!=c.shape or not all(np.isfinite(v).all() for v in (b,c,z)):raise ValueError('finite aligned pole data and evaluation points required')
 if np.any(z[...,None]==c):raise ZeroDivisionError('evaluation at a rational pole')
 out=(b/(z[...,None]-c)).sum(axis=-1)
 if not np.isfinite(out).all():raise FloatingPointError('rational evaluation not representable')
 return {'ZJ':out}


def jpole_coefficients(J=12,I=16,*,precision=80):
 """High-precision two-sided Maxwellian Padé construction, pending refinement.

 Original J12 system condition~3.52e14 motivates explicit precision. No claim
 of universal Z accuracy or monotonic improvement. Residues assume simple roots;
 a repeated root requires a separate higher-order-pole representation.
 """
 from ._pade import construct_maxwellian_pade
 return construct_maxwellian_pade(J=J,I=I,precision=precision)


def jpole_generator(J=12,I=16,*,precision=80):
 """Composition of coefficient construction and historical diagnostic grid."""
 p=jpole_coefficients(J,I,precision=precision);g=jpole_grid_coordinates()['state'];return {**p,**g,**jpole_evaluate(p['bzj'],p['czj'],g['z'])}


def reassemble_original_program(model,output_dir,*,points=None,**controls):
 """Corrected numeric/presentation composition; original replay stays D1 evidence.

 All four legacy scientific purposes are retained. Terminal scientific arrays
 and unit-labelled plots derive from corrected operators. Historical PNG byte
 identity is intentionally not claimed for scientifically corrected data.
 """
 from ._presentation import save_program
 result=jpole_generator(**controls) if model=='generator' else ordered_spectrum(model,points=points,**controls)
 return save_program(model,result,output_dir)

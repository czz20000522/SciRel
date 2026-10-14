"""Linear, one-spatial-Fourier-mode electron Vlasov–Poisson evolution.

Independently authored from df/dt = -i*k*v*f + E*f0_prime and
ikE = -integral(f dv), in plasma-frequency/Debye units with fixed ions.
The GPDF D1 vp_* operators establish the selected scenarios and controls;
this module does not embed or invoke their MATLAB implementation.

The velocity rule deliberately remains the source endpoint-inclusive rectangle
rule (nv intervals, nv+1 nodes). Its finite-window/quadrature errors are distinct
from RK4 temporal error. Poisson closure holds at initialization and all RK4
stages. Source's inconsistent initial E=.01 is corrected, not silently replayed.
"""
from __future__ import annotations

from math import lgamma, pi, sqrt
import numpy as np

__all__ = ['vp_distribution','vp_init','vp_field','vp_rhs','vp_rk4_step',
           'vp_evolve','vp_envelope','vp_diagnostic','solve_vlasov_poisson']


def _vectors(*values):
    arrays = [np.asarray(x) for x in values]
    if not arrays or arrays[0].ndim != 1 or arrays[0].size < 2:
        raise ValueError('velocity arrays must be one-dimensional with at least two nodes')
    if any(x.shape != arrays[0].shape or not np.isfinite(x).all() for x in arrays):
        raise ValueError('velocity arrays must have the same shape and finite values')
    return arrays


def _positive(value, name):
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be positive and finite')


def vp_distribution(vv, Fn=2, *, k=.15, kappa=1., cutoff_mode="weak"):
    """Return (f0_prime, theoretical_wr, theoretical_wi) for source scenarios.

    Fn=1 is unit-variance Maxwellian; 2 is normalized kappa with vt=sqrt(2),
    kappa>1/2; 3 is the triangular density max(1-|v|,0); 4 is slowing-down density A/(|v|^3+vt^3) truncated at |v|=4,
    including the two derivative jump masses. These are deposited linearly
    onto bracketing nodes with quadrature-consistent integrated weights.
    cutoff_mode="smooth" explicitly replays only the source interior forcing;
    it is not the weak derivative of the truncated density. The source A is
    retained: truncation loses density mass and is not silently renormalized.
    Triangular corner derivatives use zero; the ordinary slowing-down
    derivative at a cutoff uses the two-sided half value.
    Theory is available only for kappa=1, whose exact root is 1-i*k*sqrt(2).
    """
    if cutoff_mode not in ("weak", "smooth"):
        raise ValueError('cutoff_mode must be weak or smooth')
    v = np.asarray(vv, dtype=float)
    if v.ndim != 1 or not np.isfinite(v).all():
        raise ValueError('vv must be a finite real vector')
    _positive(k, 'k')
    wr = wi = None
    if Fn == 1:
        g = -v*np.exp(-v*v/2)/sqrt(2*pi)
    elif Fn == 2:
        if not np.isfinite(kappa) or kappa <= .5:
            raise ValueError('kappa must exceed 1/2 for a normalized distribution')
        A = np.exp(lgamma(kappa)-lgamma(kappa-.5))/sqrt(2*pi*kappa)
        g = -A*v*(1+v*v/(2*kappa))**(-kappa-1)
        if kappa == 1:
            wr,wi = 1.,-k*sqrt(2)
    elif Fn == 3:
        g = np.where((v > -1)&(v < 0),1.,np.where((v > 0)&(v < 1),-1.,0.))
    elif Fn == 4:
        vt=sqrt(2)
        g=np.zeros_like(v)
        inside=np.abs(v)<=4
        u=v[inside]
        g[inside]=-np.sign(u)*3*u*u/(np.abs(u)**3+vt**3)**2*3*sqrt(3)*vt*vt/(4*pi)
        g[np.abs(v)==4] *= .5
        if cutoff_mode == "weak":
            if v.size < 2 or np.any(np.diff(v)<=0):
                raise ValueError('weak cutoff derivative requires an increasing uniform grid')
            dv=float(v[1]-v[0])
            if not np.allclose(np.diff(v),dv,rtol=1e-10,atol=1e-13):
                raise ValueError('weak cutoff derivative requires an increasing uniform grid')
            jump=3*sqrt(3)*vt*vt/(4*pi)/(4**3+vt**3)
            for location,mass in ((-4.,jump),(4.,-jump)):
                if v[0] <= location <= v[-1]:
                    j=int(np.searchsorted(v,location))
                    if j == 0:
                        g[0] += mass/dv
                    elif j == v.size:
                        g[-1] += mass/dv
                    else:
                        fraction=(location-v[j-1])/dv
                        g[j-1] += mass*(1-fraction)/dv
                        g[j] += mass*fraction/dv
    else:
        raise ValueError('Fn must be one of 1, 2, 3, 4')
    if not np.isfinite(g).all():
        raise FloatingPointError('distribution derivative is not representable')
    return g,wr,wi


def vp_field(df, k, dv):
    """Poisson closure E=(i/k) sum(df)*dv; both endpoints retain full weight."""
    _positive(dv,'dv')
    if not np.isfinite(k) or k == 0:
        raise ValueError('k must be finite and nonzero')
    (f,) = _vectors(df)
    field=(1j/k)*dv*np.sum(f)
    if not np.isfinite(field):
        raise FloatingPointError('Poisson field is not representable')
    return field


def vp_rhs(df, dE, vv, df0dv, k):
    """Evaluate the linear RHS on 1D nodes; E is a scalar shared by all nodes."""
    f,v,g=_vectors(df,vv,df0dv)
    if np.ndim(dE) != 0 or not np.isfinite(dE) or not np.isfinite(k) or k == 0:
        raise ValueError('dE must be a finite scalar and k finite and nonzero')
    result=-1j*k*v*f+dE*g
    if not np.isfinite(result).all():
        raise FloatingPointError('Vlasov RHS is not representable')
    return result


def vp_init(Fn=2, kappa=1., nv=2048, dt=.01, nt=2000, *, k=.15, vmax=20.):
    """Construct independent mutable state with closed initial Gaussian perturbation.

    Source controls default to 2048 intervals, dt=.01, 2000 steps, k=.15,
    velocity extent ±20. Unlike source, dEt[0] satisfies Poisson. No Maxwellian
    lookup-table frequency is attached to a different k or a different family.
    """
    if isinstance(nv,bool) or not isinstance(nv,(int,np.integer)) or nv < 2:
        raise ValueError('nv must be an integer >= 2')
    if isinstance(nt,bool) or not isinstance(nt,(int,np.integer)) or nt < 0:
        raise ValueError('nt must be a nonnegative integer')
    _positive(dt,'dt'); _positive(k,'k'); _positive(vmax,'vmax')
    v=np.linspace(-vmax,vmax,nv+1); dv=2*vmax/nv
    g,wr,wi=vp_distribution(v,Fn,k=k,kappa=kappa)
    f=(.1*np.exp(-v*v)).astype(complex); E=vp_field(f,k,dv)
    fields=np.zeros(nt+1,complex); fields[0]=E
    return dict(Fn=Fn,kappa=kappa,nv=nv,dt=dt,nt=nt,k=k,vmax=vmax,vmin=-vmax,
                dv=dv,TR=2*pi/(k*dv),vv=v,df=f,df0dv=g,dE=E,dEt=fields,
                tt=np.arange(nt+1)*dt,wr=wr,wi=wi)


def vp_rk4_step(df,dE,vv,df0dv,k,dv,dt):
    """One classical fourth-order step; every stage uses its own Poisson field.

    Reject an unclosed incoming field instead of a non-RK4 first stage. This
    makes the integrator a polynomial of the single semidiscrete linear matrix.
    Inputs are never mutated; return (new_df,new_dE).
    """
    _positive(dt,'dt')
    f,v,g=_vectors(df,vv,df0dv)
    closed=vp_field(f,k,dv)
    if np.ndim(dE)!=0 or not np.isfinite(dE) or not np.isclose(dE,closed,rtol=1e-12,atol=1e-14):
        raise ValueError('incoming dE violates the discrete Poisson constraint')
    def rhs(x):
        return -1j*k*v*x+vp_field(x,k,dv)*g
    a=rhs(f); b=rhs(f+.5*dt*a); c=rhs(f+.5*dt*b); d=rhs(f+dt*c)
    result=f+(dt/6)*(a+2*b+2*c+d)
    if not np.isfinite(result).all():
        raise FloatingPointError('nonfinite RK4 state; reduce dt or revise velocity grid')
    return result,vp_field(result,k,dv)


def vp_evolve(state):
    """Run exactly nt ordered feedback steps; return a new state and full history.

    No implicit convergence stop. Only the final velocity vector and the nt+1
    scalar field samples are retained, so memory is O(nv+nt). A repeated call
    continues from the supplied final df but begins a new local time history.
    """
    s={key:(value.copy() if isinstance(value,np.ndarray) else value) for key,value in state.items()}
    nt=s['nt']
    if isinstance(nt,bool) or not isinstance(nt,(int,np.integer)) or nt<0:
        raise ValueError('nt must be a nonnegative integer')
    fields=np.empty(nt+1,complex); fields[0]=vp_field(s['df'],s['k'],s['dv'])
    if not np.isclose(fields[0],s['dE'],rtol=1e-12,atol=1e-14):
        raise ValueError('initial state violates the discrete Poisson constraint')
    for j in range(nt):
        s['df'],s['dE']=vp_rk4_step(s['df'],s['dE'],s['vv'],s['df0dv'],s['k'],s['dv'],s['dt'])
        fields[j+1]=s['dE']
    s['dEt']=fields; s['tt']=np.arange(nt+1)*s['dt']
    return s


def vp_envelope(dEt,tt,*,wr=None,wi=None):
    """Return log|E| at every supplied sample; exact zeros give -inf.

    Optional theory uses the initial magnitude exp(wi*t). It is an envelope,
    without the source's arbitrary -15 shift or real-part projection.
    """
    E,t=_vectors(dEt,tt)
    if np.iscomplexobj(t) or np.any(np.diff(t)<=0):
        raise ValueError('tt must be real and strictly increasing')
    with np.errstate(divide='ignore'):
        log=np.log(np.abs(E))
        theory=None if wi is None else np.log(abs(E[0]))+wi*(t-t[0])
    return dict(ttmp=t.copy(),lndE=log,lndEe=theory,wr=wr,wi=wi)


def vp_diagnostic(dEt,tt,*,start=None,end=None):
    """Fit log-magnitude local maxima for a standing oscillatory field.

    omega=pi/mean peak spacing, gamma=least-squares log-peak slope. This is
    appropriate for |cos(omega*t)|, not a pure rotating complex exponential;
    insufficient isolated peaks raise ValueError. Default window is 5–80%
    of the actual time span. Sample indices map directly to tt (no offset).
    """
    E,t=_vectors(dEt,tt)
    if np.iscomplexobj(t) or np.any(np.diff(t)<=0):
        raise ValueError('tt must be real and strictly increasing')
    lo=t[0]+.05*(t[-1]-t[0]) if start is None else start
    hi=t[0]+.8*(t[-1]-t[0]) if end is None else end
    a=np.abs(E)
    indices=np.flatnonzero((a[1:-1]>a[:-2])&(a[1:-1]>a[2:]))+1
    indices=indices[(t[indices]>=lo)&(t[indices]<=hi)&(a[indices]>0)]
    if indices.size<2:
        raise ValueError('at least two isolated nonzero field maxima are required')
    times=t[indices]; logs=np.log(a[indices]); centered=times-times.mean()
    gamma=float(centered@(logs-logs.mean())/(centered@centered))
    return dict(peak_indices=indices,peak_times=times,peak_log_magnitudes=logs,
                omega=float(pi/np.mean(np.diff(times))),gamma=gamma,gammas=gamma)


def solve_vlasov_poisson(Fn=2,kappa=1.,nv=2048,dt=.01,nt=2000,*,k=.15,vmax=20.):
    """Compose initialization, finite RK4 feedback, envelope, and peak diagnostic.

    A diagnostic unavailable for a short/nonoscillatory trace is returned as
    None with its reason; the valid evolution is retained. Numerical failures
    propagate. This simulation does not estimate validity past TR=2pi/(k*dv),
    where finite velocity sampling permits recurrence.
    """
    s=vp_evolve(vp_init(Fn,kappa,nv,dt,nt,k=k,vmax=vmax))
    if nt==0:
        return dict(state=s,envelope=None,diagnostic=None,diagnostic_status='insufficient samples')
    envelope=vp_envelope(s['dEt'],s['tt'],wr=s['wr'],wi=s['wi'])
    try:
        diagnostic=vp_diagnostic(s['dEt'],s['tt'])
        status='available'
    except ValueError as error:
        diagnostic=None; status=str(error)
    return dict(state=s,envelope=envelope,diagnostic=diagnostic,diagnostic_status=status)

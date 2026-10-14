"""Pressure/flux task entry backed by the shared closure-aware equilibrium solve."""
from collections.abc import Mapping
import numpy as np
from scirel._validation import finite_scalar, integer_scalar
from .pleiades_feedback import compute_equilibrium
from .pressure_flux_state import build_pressure_flux_state


def run_graph(inputs):
    """Validate domain ports and package the single shared solver's terminal state."""
    if not isinstance(inputs, Mapping):
        raise ValueError('inputs must be a mapping')
    for name in ('r_grid','z_grid','psi_vac','g_psi','pressure_of_radius','tol','maxiter','relax'):
        if name not in inputs:raise ValueError(f'{name} is required')
    R,Z,psi0,G=(np.asarray(inputs[k],dtype=float) for k in ('r_grid','z_grid','psi_vac','g_psi'))
    if R.ndim!=2 or Z.shape!=R.shape or psi0.shape!=R.shape:
        raise ValueError('r_grid, z_grid and psi_vac must be same-shape [Z,R] grids')
    if G.shape!=(R.size,R.size):raise ValueError(f'g_psi must have shape ({R.size}, {R.size})')
    tol=finite_scalar(inputs['tol'],'tol',None)
    maxiter=integer_scalar(inputs['maxiter'],'maxiter',None,minimum=0)
    relax=finite_scalar(inputs['relax'],'relax',None)
    if not callable(inputs['pressure_of_radius']):
        raise ValueError('pressure_of_radius must be callable')
    def pressure(radius):
        value=np.asarray(inputs['pressure_of_radius'](radius),dtype=float)
        if value.ndim!=0 or not np.isfinite(value) or value<0:
            raise ValueError('pressure_of_radius must return finite nonnegative scalar values')
        return float(value)
    try:
        result=compute_equilibrium(R,Z,pressure,psi0,G,tol=tol,maxiter=maxiter,relax=relax,plas_clip=inputs.get('plasma_mask'))
    except ValueError as exc:
        if 'uniformly spaced' in str(exc):
            raise ValueError('r_grid and z_grid must be uniformly spaced tensor-product grids and resolvable') from exc
        raise
    representation=None
    if result.p_psifit is not None and np.isfinite(result.psi).all():
        try:
            representation=build_pressure_flux_state(R,Z,result.psi,pressure,inputs.get('plasma_mask'))['pressure_of_psi']
        except (ValueError,FloatingPointError):
            if result.status!='nonfinite':raise
    return {'psi':result.psi,'plasma_currents':result.plas_currents,
            'pressure_of_psi':representation,'iterations':result.iterations,
            'residual':result.residual,'closure_residual':result.closure_residual,
            'residual_history':np.asarray(result.residual_history,dtype=float),
            'closure_residual_history':np.asarray(result.closure_residual_history,dtype=float),
            'converged':result.status=='converged','status':result.status,
            'failure_reason':None if result.status=='converged' else 'maxiter_reached' if result.status=='maxiter' else result.reason}


def solve_isotropic_pressure_flux(inputs=None, **kwargs):
    """Solve pressure-only Picard feedback with flux and current-closure gates.

    Ports may be a mapping or keywords. Uniform increasing or decreasing tensor
    axes are supported without reordering Green/current storage. Pressure must
    be nonnegative, with an exact first outward zero edge and four increasing
    fitted flux samples. Both residuals must be <=tol; relax=1 is rejected.
    maxiter=0 returns an unsolved state with infinite residuals. Histories cover
    completed residual evaluations; a nonfinite attempted step may stop before
    adding a history item. This discrete closure is not continuum force balance.
    """
    if inputs is None:inputs={}
    if not isinstance(inputs,Mapping):raise ValueError('inputs must be a mapping')
    values=dict(inputs);values.update(kwargs)
    return run_graph(values)


__all__=['solve_isotropic_pressure_flux']

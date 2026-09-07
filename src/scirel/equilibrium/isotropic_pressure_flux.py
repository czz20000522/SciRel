"""Resolver for the historical isotropic Picard assets."""
from __future__ import annotations
from scirel._validation import finite_scalar as _require_finite_scalar, integer_scalar as _require_integer_scalar, bool_scalar as _require_bool_scalar
from collections.abc import Mapping
import hashlib
import math
from pathlib import Path
import numpy as np

def run_graph(inputs, *, asset_loader):
    """按压力--磁通闭环执行一次各向同性 Picard 平衡任务图。"""
    if not isinstance(inputs, Mapping):
        raise ValueError('inputs must be a mapping')
    for name in ('r_grid', 'z_grid', 'psi_vac', 'g_psi', 'pressure_of_radius'):
        if name not in inputs:
            raise ValueError(f'{name} is required by task_graph.yaml')
    r_grid = np.asarray(inputs['r_grid'], dtype=float)
    z_grid = np.asarray(inputs['z_grid'], dtype=float)
    psi_vac = np.asarray(inputs['psi_vac'], dtype=float)
    if r_grid.ndim != 2 or z_grid.shape != r_grid.shape or psi_vac.shape != r_grid.shape:
        raise ValueError('r_grid, z_grid and psi_vac must be same-shape [Z,R] grids')
    if not all((np.all(np.isfinite(value)) for value in (r_grid, z_grid, psi_vac))):
        raise ValueError('r_grid, z_grid and psi_vac must be finite')
    if r_grid.shape[0] < 2 or r_grid.shape[1] < 2:
        raise ValueError('r_grid and z_grid need at least two points per axis')
    r_axis, z_axis = (r_grid[0, :], z_grid[:, 0])
    if not np.allclose(r_grid, r_axis[np.newaxis, :]) or not np.allclose(z_grid, z_axis[:, np.newaxis]) or np.any(np.diff(r_axis) <= 0.0) or np.any(np.diff(z_axis) <= 0.0) or (not np.allclose(np.diff(r_axis), np.diff(r_axis)[0], rtol=1e-12, atol=1e-14)) or (not np.allclose(np.diff(z_axis), np.diff(z_axis)[0], rtol=1e-12, atol=1e-14)):
        raise ValueError('r_grid and z_grid must be uniformly spaced tensor-product grids')
    g_psi = np.asarray(inputs['g_psi'], dtype=float)
    if g_psi.shape != (r_grid.size, r_grid.size) or not np.all(np.isfinite(g_psi)):
        raise ValueError(f'g_psi must have shape ({r_grid.size}, {r_grid.size}) and finite values')
    if not callable(inputs['pressure_of_radius']):
        raise ValueError('pressure_of_radius must be callable')
    for name in ('tol', 'maxiter', 'relax'):
        if name not in inputs:
            raise ValueError(f'{name} is required by task_graph.yaml')
    tol = _require_finite_scalar(inputs['tol'], 'tol', None)
    maxiter = _require_integer_scalar(inputs['maxiter'], 'maxiter', None, minimum=0)
    relax = _require_finite_scalar(inputs['relax'], 'relax', None)
    if not math.isfinite(tol) or tol <= 0.0:
        raise ValueError('tol must be a positive finite scalar')
    if maxiter < 0:
        raise ValueError('maxiter must be non-negative')
    if not math.isfinite(relax) or not 0.0 <= relax <= 1.0:
        raise ValueError('relax must be between 0 and 1')
    profile = asset_loader('scirel.equilibrium.pressure_flux_state')
    picard_step = asset_loader('scirel.equilibrium.isotropic_picard_step')
    psi = np.array(inputs['psi_vac'], dtype=float, copy=True)
    state = profile(inputs.get('r_grid'), inputs.get('z_grid'), psi, inputs.get('pressure_of_radius'), inputs.get('plasma_mask'))
    currents, residual, history, iterations = (None, 1.0, [], 0)
    while residual > tol and iterations < maxiter:
        step = picard_step(inputs.get('r_grid'), inputs.get('z_grid'), psi, inputs.get('psi_vac'), inputs.get('g_psi'), state['pressure_derivative'], state['psi_edge'], currents, relax)
        psi, currents, residual = (step['psi_next'], step['plasma_currents'], step['residual'])
        state = profile(inputs.get('r_grid'), inputs.get('z_grid'), psi, inputs.get('pressure_of_radius'), inputs.get('plasma_mask'))
        history.append(residual)
        iterations += 1
    finite_residual = math.isfinite(residual)
    converged = bool(finite_residual and residual <= tol)
    return {'psi': psi, 'plasma_currents': state['zero_currents'].reshape(psi.shape) if currents is None else currents.reshape(psi.shape), 'pressure_of_psi': state['pressure_of_psi'], 'iterations': iterations, 'residual': float(residual), 'residual_history': np.asarray(history, dtype=float), 'converged': converged, 'failure_reason': None if converged else 'nonfinite_source_residual' if not finite_residual else 'maxiter_reached'}

def solve_isotropic_pressure_flux(inputs=None, **kwargs):
    from scirel._composition import compose
    from scirel.equilibrium.isotropic_picard_step import pressure_flux_picard_step as _dependency_0
    from scirel.equilibrium.pressure_flux_state import build_pressure_flux_state as _dependency_1
    return compose(run_graph, inputs, kwargs, {'asset_loader': {'scirel.equilibrium.isotropic_picard_step': _dependency_0, 'scirel.equilibrium.pressure_flux_state': _dependency_1}})
__all__ = ['solve_isotropic_pressure_flux']

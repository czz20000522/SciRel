"""Standalone orchestration of the anisotropic free-boundary Picard state loop."""
from __future__ import annotations
from scirel._validation import finite_scalar as _require_finite_scalar, integer_scalar as _require_integer_scalar, bool_scalar as _require_bool_scalar
from collections.abc import Mapping
import hashlib
from pathlib import Path
import numpy as np
from ._anisotropic_numerics import cell_areas, flux_field_increment

def _require_mapping(value, name):
    if not isinstance(value, Mapping):
        raise ValueError(f'{name} must be a mapping')
    return value

def _require_ports(inputs):
    for name in ('r_grid', 'z_grid', 'psi_vac', 'br_vac', 'bz_vac', 'g_psi', 'params', 'tol', 'maxiter', 'relax'):
        if name not in inputs:
            raise ValueError(f'{name} is required by task_graph.yaml')
    closure = inputs.get('pressure_closure')
    if not callable(closure):
        raise ValueError('pressure_closure must be a callable N4 closure port')
    return closure

def _profiles(closure, psi, magnetic_field, params):
    profiles = closure({'psi': psi, 'B': magnetic_field, 'params': params})
    profiles = _require_mapping(profiles, 'pressure_closure output')
    for field in ('p_parallel', 'p_perp', 'density', 'electron_temperature'):
        if field not in profiles:
            raise ValueError(f'pressure_closure output missing {field}')
    shape = np.asarray(psi).shape
    for field in ('p_parallel', 'p_perp'):
        try:
            value = np.asarray(profiles[field], dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'pressure_closure output {field} must be a finite nonnegative array with shape {shape}') from exc
        if value.shape != shape or not np.all(np.isfinite(value)) or np.any(value < 0.0):
            raise ValueError(f'pressure_closure output {field} must be a finite nonnegative array with shape {shape}')
        profiles[field] = value
    for field in ('density', 'electron_temperature'):
        if profiles[field] is None:
            continue
        try:
            value = np.asarray(profiles[field], dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'pressure_closure output {field} must be None or a finite nonnegative array with shape {shape}') from exc
        if value.shape != shape or not np.all(np.isfinite(value)) or np.any(value < 0.0):
            raise ValueError(f'pressure_closure output {field} must be None or a finite nonnegative array with shape {shape}')
        profiles[field] = value
    return profiles

def _boundary_config(value):
    if value is None:
        return None
    value = _require_mapping(value, 'boundary_correction')
    required = ('boundary_sample_matrix', 'green_boundary_to_boundary', 'green_boundary_to_field')
    missing = [key for key in required if key not in value]
    if missing:
        raise ValueError(f'boundary_correction missing keys: {missing}')
    return value

def run_graph(inputs, *, asset_loader):
    """Schedule declared N4 closure and N6 feedback assets without hidden numerical kernels."""
    if not isinstance(inputs, Mapping):
        raise ValueError('inputs must be a mapping')
    r_grid = np.asarray(inputs['r_grid'], dtype=float)
    z_grid = np.asarray(inputs['z_grid'], dtype=float)
    if r_grid.ndim != 2 or z_grid.shape != r_grid.shape or r_grid.shape[0] < 3 or (r_grid.shape[1] < 3):
        raise ValueError('r_grid and z_grid must be equal-shape 2-D grids with at least 3 points per axis')
    if not np.all(np.isfinite(r_grid)) or not np.all(np.isfinite(z_grid)):
        raise ValueError('r_grid and z_grid must be finite')
    r_axis, z_axis = (r_grid[0, :], z_grid[:, 0])
    if not np.allclose(r_grid, r_axis[np.newaxis, :]) or not np.allclose(z_grid, z_axis[:, np.newaxis]) or np.any(np.diff(r_axis) <= 0.0) or np.any(np.diff(z_axis) <= 0.0) or r_axis[0]<0.:
        raise ValueError('r_grid and z_grid must be finite, strictly increasing tensor-product grids with nonnegative R')
    if inputs.get('plasma_mask') is not None:
        plasma_mask = np.asarray(inputs['plasma_mask'])
        if plasma_mask.shape != r_grid.shape or plasma_mask.dtype != np.dtype(bool):
            raise ValueError('plasma_mask must be a boolean array with the same shape as r_grid')
    pressure_closure = _require_ports(inputs)
    params = dict(_require_mapping(inputs['params'], 'params'))
    magnitude = asset_loader('scirel.field.poloidal_field_magnitude')
    current = asset_loader('scirel.equilibrium.anisotropic_toroidal_current')
    feedback = asset_loader('scirel.equilibrium.anisotropic_picard_feedback')
    residual_operator = asset_loader('scirel.diagnostics.picard_flux_residual')
    boundary_operator = asset_loader('scirel.field.ideal_conductor_boundary')
    psi, br, bz = (inputs['psi_vac'], inputs['br_vac'], inputs['bz_vac'])
    initial_field = magnitude(br, bz)
    if 'B0' not in params:
        b0 = _require_finite_scalar(inputs.get('b0'), 'b0', initial_field['B0_default'])
        if b0 <= 0.0:
            raise ValueError('b0 must be a finite positive scalar')
        params['B0'] = b0
    tol = _require_finite_scalar(inputs['tol'], 'tol', None)
    maxiter = _require_integer_scalar(inputs['maxiter'], 'maxiter', None, minimum=0)
    relax = _require_finite_scalar(inputs['relax'], 'relax', None)
    if tol <= 0.0 or not 0.0 <= relax <= 1.0:
        raise ValueError('tol, maxiter, and relax violate the declared Picard bounds')
    boundary = _boundary_config(inputs.get('boundary_correction'))
    compatibility_tol = _require_finite_scalar(inputs.get('compatibility_tol'),'compatibility_tol',.05)
    strict = _require_bool_scalar(inputs.get('strict_compatibility'),'strict_compatibility',True)
    minimum_field = _require_finite_scalar(inputs.get('minimum_field'),'minimum_field',1e-8)
    if compatibility_tol<0. or minimum_field<=0.:
        raise ValueError('compatibility_tol and minimum_field are invalid')
    currents_old = None
    residual = float('inf')
    residual_history = []
    iterations = 0
    profiles = None
    current_parts = None
    boundary_result = None
    boundary_flux_correction = None
    while residual > tol and iterations < maxiter:
        field = magnitude(br, bz)
        profiles = _profiles(pressure_closure, psi, field['B'], params)
        current_parts = current(inputs['r_grid'], inputs['z_grid'], br, bz, profiles['p_parallel'], profiles['p_perp'])
        psi_previous = psi
        step = feedback(current_parts['j_phi'], inputs['r_grid'], inputs['z_grid'], inputs.get('plasma_mask'), currents_old, relax, inputs['g_psi'], inputs.get('g_br'), inputs.get('g_bz'), inputs['psi_vac'], inputs['br_vac'], inputs['bz_vac'], cell_edges=inputs.get('cell_edges'))
        psi, br, bz = (step['psi'], step['BR'], step['BZ'])
        if boundary is not None:
            boundary_result = boundary_operator(step['psi'].ravel(), boundary['boundary_sample_matrix'], boundary['green_boundary_to_boundary'], boundary['green_boundary_to_field'], rcond=boundary.get('rcond', 1e-10))
            psi = boundary_result['corrected_field_flux'].reshape(step['psi'].shape)
            boundary_flux_correction = boundary_result['field_flux_correction'].reshape(step['psi'].shape)
            delta_field = flux_field_increment(r_grid,z_grid,boundary_flux_correction)
            br = br+delta_field['B_R']
            bz = bz+delta_field['B_Z']
        residual = residual_operator(psi_previous, psi)['residual']
        residual_history.append(residual)
        currents_old = step['picard_current_state']
        iterations += 1
    field = magnitude(br, bz)
    profiles = _profiles(pressure_closure, psi, field['B'], params)
    current_parts = current(inputs['r_grid'], inputs['z_grid'], br, bz, profiles['p_parallel'], profiles['p_perp'])
    terminal_j_phi = np.asarray(current_parts['j_phi'], dtype=float)
    if inputs.get('plasma_mask') is not None:
        terminal_j_phi = np.where(np.asarray(inputs['plasma_mask'], dtype=bool), terminal_j_phi, 0.0)
    if currents_old is None:
        step = feedback(current_parts['j_phi'], inputs['r_grid'], inputs['z_grid'], inputs.get('plasma_mask'), None, relax, inputs['g_psi'], inputs.get('g_br'), inputs.get('g_bz'), inputs['psi_vac'], inputs['br_vac'], inputs['bz_vac'], cell_edges=inputs.get('cell_edges'))
        currents_old = step['initial_picard_current_state']
    terminal_cell_currents = terminal_j_phi * cell_areas(r_grid,z_grid,inputs.get('cell_edges'))
    unrelaxed=feedback(current_parts['j_phi'],r_grid,z_grid,inputs.get('plasma_mask'),None,0.,inputs['g_psi'],inputs.get('g_br'),inputs.get('g_bz'),inputs['psi_vac'],inputs['br_vac'],inputs['bz_vac'],cell_edges=inputs.get('cell_edges'))
    target_psi=unrelaxed['psi']
    if boundary is not None:
        target_boundary=boundary_operator(target_psi.ravel(),boundary['boundary_sample_matrix'],boundary['green_boundary_to_boundary'],boundary['green_boundary_to_field'],rcond=boundary.get('rcond',1e-10))
        target_psi=target_boundary['corrected_field_flux'].reshape(psi.shape)
    fixed_point_residual=float(np.linalg.norm(target_psi-psi)/max(float(np.linalg.norm(target_psi)),float(np.linalg.norm(inputs['psi_vac'])),np.finfo(float).tiny))
    if np.any(field['B']<minimum_field):
        raise FloatingPointError('free-boundary terminal magnetic field fell below minimum_field')
    force_diagnostics = current_parts['force_diagnostics']
    active = np.ones_like(r_grid,dtype=bool) if inputs.get('plasma_mask') is None else np.asarray(inputs['plasma_mask'],dtype=bool)
    from ._anisotropic_numerics import residual_metrics
    compatibility = residual_metrics(force_diagnostics['parallel_force'], np.hypot(force_diagnostics['force_R'],force_diagnostics['force_Z']), force_diagnostics['parallel_force_roundoff'],active)
    compatible = compatibility['error']<=compatibility_tol
    if strict and not compatible:
        raise ValueError('free-boundary parallel pressure force exceeds compatibility_tol')
    return {'psi': psi, 'BR': br, 'BZ': bz, 'B': field['B'], 'profiles': {key: profiles[key] for key in ('p_parallel', 'p_perp', 'density', 'electron_temperature')}, 'j_phi': terminal_j_phi, 'plasma_currents': terminal_cell_currents, 'picard_current_state': currents_old, 'gradp_term': current_parts['gradp_term'], 'anisotropy_curvature_term': current_parts['anisotropy_curvature_term'], 'converged': bool(fixed_point_residual<=tol and compatible and iterations>0), 'fixed_point_residual':fixed_point_residual, 'flux_converged':bool(residual<=tol), 'equilibrium_compatible':compatible, 'force_diagnostics':force_diagnostics, 'parallel_force_diagnostics':compatibility, 'iterations': iterations, 'residual': residual, 'residual_history': np.asarray(residual_history, dtype=float), 'parameters': params, 'boundary_currents': None if boundary_result is None else boundary_result['boundary_currents'], 'boundary_flux_correction': boundary_flux_correction, 'boundary_residual_norm': None if boundary_result is None else boundary_result['residual_norm'], 'failure_reason': 'parallel_force_incompatible' if not compatible else None if fixed_point_residual<=tol and iterations>0 else 'maxiter_reached'}

def solve_free_boundary_anisotropic_picard(inputs=None, **kwargs):
    from scirel._composition import compose
    from scirel.diagnostics.picard_flux_residual import compute_picard_flux_residual as _dependency_0
    from scirel.equilibrium.anisotropic_picard_feedback import update_anisotropic_picard_flux as _dependency_1
    from scirel.equilibrium.anisotropic_toroidal_current import compute_anisotropic_toroidal_current as _dependency_2
    from scirel.field.ideal_conductor_boundary import correct_ideal_conductor_boundary_flux as _dependency_3
    from scirel.field.poloidal_field_magnitude import compute_poloidal_field_magnitude as _dependency_4
    return compose(run_graph, inputs, kwargs, {'asset_loader': {'scirel.diagnostics.picard_flux_residual': _dependency_0, 'scirel.equilibrium.anisotropic_picard_feedback': _dependency_1, 'scirel.equilibrium.anisotropic_toroidal_current': _dependency_2, 'scirel.field.ideal_conductor_boundary': _dependency_3, 'scirel.field.poloidal_field_magnitude': _dependency_4}})
__all__ = ['solve_free_boundary_anisotropic_picard']

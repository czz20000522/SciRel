"""N1 vacuum-field composition from explicit rectangular coil records."""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np

def run_graph(inputs, *, asset_loader):
    """Expand caller-declared coils and evaluate the existing circular-filament response."""
    missing = sorted((key for key in ('r_grid', 'z_grid', 'rectangular_coils') if key not in inputs)) if isinstance(inputs, dict) else []
    if not isinstance(inputs, dict) or missing:
        raise ValueError('r_grid, z_grid, and rectangular_coils are required')
    r_grid, z_grid = (np.asarray(inputs['r_grid'], dtype=float), np.asarray(inputs['z_grid'], dtype=float))
    if r_grid.ndim != 2 or z_grid.shape != r_grid.shape or (not np.all(np.isfinite(r_grid))) or (not np.all(np.isfinite(z_grid))):
        raise ValueError('r_grid and z_grid must be equal-shape finite 2-D arrays')
    r_axis, z_axis = (r_grid[0], z_grid[:, 0])
    if np.any(r_axis < 0.0) or np.any(np.diff(r_axis) <= 0.0) or np.any(np.diff(z_axis) <= 0.0) or (not np.allclose(r_grid, r_axis[np.newaxis, :])) or (not np.allclose(z_grid, z_axis[:, np.newaxis])):
        raise ValueError('r_grid and z_grid must define a strictly increasing rectilinear R-Z grid')
    coils = inputs['rectangular_coils']
    if not isinstance(coils, (list, tuple)) or not coils:
        raise ValueError('rectangular_coils must be a nonempty list of configuration mappings')
    geometry = asset_loader('scirel.field.rectangular_coil_filaments')
    weighted_rows, currents = ([], [])
    required = {'r0_m', 'z0_m', 'nr', 'nz', 'dr_m', 'dz_m', 'current_a'}
    for index, coil in enumerate(coils):
        missing = sorted((key for key in required if key not in coil)) if isinstance(coil, dict) else sorted(required)
        if not isinstance(coil, dict) or missing:
            raise ValueError(f"rectangular_coils[{index}] misses {', '.join(sorted(missing))}")
        points = geometry(coil['r0_m'], coil['z0_m'], coil['nr'], coil['nz'], coil['dr_m'], coil['dz_m'], coil.get('angle_deg', 0.0))
        current = float(coil['current_a'])
        if not np.isfinite(current):
            raise ValueError(f'rectangular_coils[{index}].current_a must be finite')
        weights = np.asarray(coil.get('weights', np.ones(points.shape[0])), dtype=float)
        if weights.shape != (points.shape[0],) or not np.all(np.isfinite(weights)):
            raise ValueError(f'rectangular_coils[{index}].weights must be finite with one value per filament')
        rzw, drive_current = _attach_coil_current(points, current, weights)
        weighted_rows.append(rzw)
        currents.append(drive_current)
    filaments = _concatenate_filament_blocks(weighted_rows)
    green = asset_loader('scirel.field.circular_filament_green')
    currents = np.asarray(currents)
    target_points = _target_points(r_grid, z_grid)
    responses = []
    for index in range(len(weighted_rows)):
        partial = green(weighted_rows[index], target_points)
        responses.append(partial)
    superpose = asset_loader('scirel.field.current_green_superposition')
    stacked = _stack_response_rows(responses)
    combined = superpose(currents, stacked['gpsi'], stacked['gBR'], stacked['gBZ'])
    return {'psi_vac': combined['psi'].reshape(r_grid.shape), 'b_r_vac': combined['BR'].reshape(r_grid.shape), 'b_z_vac': combined['BZ'].reshape(r_grid.shape), 'filaments': filaments}

def _attach_coil_current(points, current, weights):
    """Pack caller-owned filament points with dimensionless per-filament weights."""
    return (np.concatenate((points, weights[:, None]), axis=1), current)

def _concatenate_filament_blocks(blocks):
    """Concatenate caller-declared coil filament blocks in source order."""
    return np.concatenate(blocks, axis=0)

def _target_points(r_grid, z_grid):
    """Pack the two caller-owned target axes into the Green target port."""
    return np.concatenate((r_grid.ravel()[:, None], z_grid.ravel()[:, None]), axis=1)

def _stack_response_rows(responses):
    """Stack one Green response mapping per declared source set."""
    return {name: np.asarray([response[name] for response in responses]) for name in ('gpsi', 'gBR', 'gBZ')}

def solve_multi_coil_vacuum_field(inputs=None, **kwargs):
    from scirel._composition import compose
    from scirel.field.circular_filament_green import circular_filament_green_response as _dependency_0
    from scirel.field.current_green_superposition import superpose_current_green_field as _dependency_1
    from scirel.field.rectangular_coil_filaments import discretize_rectangular_coil as _dependency_2
    return compose(run_graph, inputs, kwargs, {'asset_loader': {'scirel.field.circular_filament_green': _dependency_0, 'scirel.field.current_green_superposition': _dependency_1, 'scirel.field.rectangular_coil_filaments': _dependency_2}})
__all__ = ['solve_multi_coil_vacuum_field']

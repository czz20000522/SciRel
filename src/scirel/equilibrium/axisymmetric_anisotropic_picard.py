"""Standalone orchestration of the current SciRel anisotropic Picard solver."""
from __future__ import annotations
from scirel._validation import finite_scalar as _require_finite_scalar, integer_scalar as _require_integer_scalar, bool_scalar as _require_bool_scalar
from collections.abc import Mapping
import numpy as np
from ._anisotropic_numerics import cell_areas

def _coerce_pressure(parallel, perpendicular, psi):
    """Broadcast scalar Pa values or validate the caller-owned grid shape."""
    result = []
    for value in (parallel, perpendicular):
        values = np.asarray(value, dtype=float)
        if values.ndim == 0:
            values = np.broadcast_to(values, psi.shape)
        elif values.shape != psi.shape:
            raise ValueError('pressure fields must be scalar or match psi shape')
        result.append(values)
    return tuple(result)

def _apply_active_mask(values, active):
    """Apply the caller-owned active-cell selector without changing the field formula."""
    result = np.array(values, copy=True)
    result[~active] = 0.0
    return result

def _require_state(closure, magnetic, psi):
    state = closure(magnetic['B'], psi)
    if not isinstance(state, Mapping):
        raise TypeError('pressure_closure must return a mapping')
    try:
        parallel, perpendicular = _coerce_pressure(state['p_parallel'], state['p_perpendicular'], psi)
    except KeyError as exc:
        raise KeyError('pressure_closure must return p_parallel and p_perpendicular') from exc
    if not np.all(np.isfinite(parallel)) or not np.all(np.isfinite(perpendicular)) or np.any(parallel < 0.0) or np.any(perpendicular < 0.0):
        raise ValueError('pressure_closure returned invalid pressure')
    result = dict(state)
    result['p_parallel'], result['p_perpendicular'] = (parallel, perpendicular)
    return result

def run_composition(inputs, *, asset_loader):
    """Run current-declared-order field -> closure -> div(P) -> flux feedback."""
    if not isinstance(inputs, Mapping):
        raise ValueError('inputs must be a mapping')
    required = {'r_grid', 'z_grid', 'psi_vac', 'g_psi', 'pressure_closure'}
    missing = sorted((key for key in required if key not in inputs))
    if missing:
        raise ValueError(f"missing required inputs: {', '.join(missing)}")
    closure = inputs['pressure_closure']
    if not callable(closure):
        raise TypeError('pressure_closure must be callable as pressure_closure(B, psi)')
    r_grid, z_grid, psi_vac = (np.asarray(inputs[key], dtype=float) for key in ('r_grid', 'z_grid', 'psi_vac'))
    if r_grid.shape != z_grid.shape or psi_vac.shape != r_grid.shape or r_grid.ndim != 2:
        raise ValueError('r_grid, z_grid, psi_vac must be equal-shape 2-D arrays')
    r, z = (r_grid[0, :], z_grid[:, 0])
    if r.size < 3 or z.size < 3 or (not np.allclose(r_grid, r[np.newaxis, :])) or (not np.allclose(z_grid, z[:, np.newaxis])) or (r[0] < 0.0) or np.any(np.diff(r) <= 0.0) or np.any(np.diff(z) <= 0.0):
        raise ValueError('a strictly increasing rectilinear R-Z grid with at least 3 points per axis is required')
    g_psi = np.asarray(inputs['g_psi'], dtype=float)
    if g_psi.shape != (r_grid.size, r_grid.size) or not np.all(np.isfinite(g_psi)):
        raise ValueError('g_psi must be finite with shape (grid_size, grid_size)')
    tol = _require_finite_scalar(inputs.get('tol'), 'tol', 1e-08)
    maxiter = _require_integer_scalar(inputs.get('maxiter'), 'maxiter', 200, minimum=1)
    relax = _require_finite_scalar(inputs.get('relax'), 'relax', 0.5)
    minimum_field = _require_finite_scalar(inputs.get('minimum_field'), 'minimum_field', 1e-08)
    minimum_firehose = _require_finite_scalar(inputs.get('minimum_firehose_margin'), 'minimum_firehose_margin', 0.0)
    compatibility_tol = _require_finite_scalar(inputs.get('compatibility_tol'), 'compatibility_tol', 0.05)
    strict = _require_bool_scalar(inputs.get('strict_compatibility'), 'strict_compatibility', True)
    if not np.isfinite(tol) or not np.isfinite(relax) or (not np.isfinite(minimum_field)) or (not np.isfinite(minimum_firehose)) or (not np.isfinite(compatibility_tol)) or (tol <= 0.0) or (maxiter < 1) or (not 0.0 <= relax < 1.0) or (minimum_field <= 0.0) or (compatibility_tol < 0.0):
        raise ValueError('Picard controls are invalid')
    mask_port = inputs.get('plasma_mask')
    fixed_mask = np.ones_like(psi_vac, dtype=bool) if mask_port is None else None if callable(mask_port) else np.asarray(mask_port, dtype=bool)
    if fixed_mask is not None and fixed_mask.shape != psi_vac.shape:
        raise ValueError('plasma_mask must match the R-Z grid')
    field = asset_loader('scirel.field.poloidal_field_from_flux')
    force = asset_loader('scirel.equilibrium.anisotropic_force_balance')
    update = asset_loader('scirel.equilibrium.axisymmetric_picard_update')
    psi, old_currents, relative_change, converged = (np.array(psi_vac, copy=True), np.zeros_like(psi_vac), np.inf, False)
    history = []
    for iteration in range(maxiter):
        iteration += 1
        magnetic = field(r_grid, z_grid, psi)
        if np.any(magnetic['B'] < minimum_field):
            raise FloatingPointError('magnetic field fell below minimum_field; the gyrotropic closure is singular')
        state = _require_state(closure, magnetic, psi)
        active = np.asarray(mask_port(magnetic['B'], psi), dtype=bool) if callable(mask_port) else fixed_mask
        if active.shape != psi.shape:
            raise ValueError('callable plasma_mask returned the wrong shape')
        force_state = force(r_grid, z_grid, magnetic['B_R'], magnetic['B_Z'], state['p_parallel'], state['p_perpendicular'], active)
        j_phi = _apply_active_mask(force_state['J_phi'], active)
        step = update(r_grid, z_grid, j_phi, psi, psi_vac, g_psi, relax, old_currents, cell_edges=inputs.get('cell_edges'))
        relative_change = step['relative_psi_change']
        history.append({'iteration': iteration, 'relative_psi_change': relative_change, 'relative_current_change': step['relative_current_change']})
        psi, old_currents = (step['psi_next'], step['plasma_cell_currents'])
        if step['fixed_point_residual'] <= tol:
            converged = True
            break
    magnetic = field(r_grid, z_grid, psi)
    state = _require_state(closure, magnetic, psi)
    active = np.asarray(mask_port(magnetic['B'], psi), dtype=bool) if callable(mask_port) else fixed_mask
    if active.shape != psi.shape:
        raise ValueError('callable plasma_mask returned the wrong shape')
    force_state = force(r_grid, z_grid, magnetic['B_R'], magnetic['B_Z'], state['p_parallel'], state['p_perpendicular'], active)
    j_phi = _apply_active_mask(force_state['J_phi'], active)
    terminal_cell_currents = j_phi * cell_areas(r_grid, z_grid, inputs.get('cell_edges'))
    terminal_update=update(r_grid,z_grid,j_phi,psi,psi_vac,g_psi,0.,old_currents,cell_edges=inputs.get('cell_edges'))
    fixed_point_residual=terminal_update['fixed_point_residual']
    converged=bool(fixed_point_residual<=tol)
    if np.any(magnetic['B'] < minimum_field):
        raise FloatingPointError('magnetic field fell below minimum_field at the returned terminal state')
    if np.any(active & (force_state['firehose_margin'] <= minimum_firehose)):
        raise FloatingPointError('pressure closure crossed the firehose/tension singularity')
    if force_state['parallel_force_error'] > compatibility_tol and strict:
        raise ValueError(f"p_parallel and p_perpendicular leave an unbalanced parallel div(P) fraction of {force_state['parallel_force_error']:.3e}; required <= {compatibility_tol:.3e}")
    return {'psi': psi, 'plasma_cell_currents': terminal_cell_currents, 'J_phi': j_phi, 'B_R': magnetic['B_R'], 'B_Z': magnetic['B_Z'], 'B': magnetic['B'], 'p_parallel': state['p_parallel'], 'p_perpendicular': state['p_perpendicular'], 'parallel_force': force_state['parallel_force'], 'force_R': force_state['force_R'], 'force_Z': force_state['force_Z'], 'converged': converged, 'fixed_point_residual':fixed_point_residual, 'iterations': iteration, 'relative_psi_change': relative_change, 'parallel_force_error': force_state['parallel_force_error'], 'force_diagnostics': force_state, 'closure_state': state, 'firehose_margin': force_state['firehose_margin'], 'iteration_history': history}

def solve_axisymmetric_anisotropic_picard(inputs=None, **kwargs):
    """Run the axisymmetric anisotropic Picard field/pressure feedback loop.

    Parameters
    ----------
    inputs : mapping, optional
        Mapping containing ``r_grid``, ``z_grid``, ``psi_vac``, ``g_psi`` and
        callable ``pressure_closure(B, psi)``. Optional controls include
        ``tol``, ``maxiter``, ``relax``, ``plasma_mask``, field/firehose gates,
        compatibility checks and explicit ``cell_edges``; keyword arguments
        are merged at the composition boundary.
    **kwargs
        Named inputs merged with ``inputs`` by the composition
        boundary.

    Returns
    -------
    dict
        Terminal ``psi``, magnetic field, pressure, current and force fields,
        convergence diagnostics, closure state and iteration history. Array
        outputs follow the declared rectilinear R-Z grid.

    Raises
    ------
    ValueError
        If the grid, Green matrix, controls, pressure closure, mask or terminal
        compatibility contract is invalid.
    TypeError
        If the pressure closure or its returned state has an invalid type.
    FloatingPointError
        If the field gate, firehose gate or another declared finite-value gate
        fails during iteration or terminal reevaluation.
    """
    from scirel._composition import compose
    from scirel.equilibrium.anisotropic_force_balance import compute_anisotropic_force_balance as _dependency_0
    from scirel.equilibrium.axisymmetric_picard_update import update_axisymmetric_picard_flux as _dependency_1
    from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux as _dependency_2
    return compose(run_composition, inputs, kwargs, {'asset_loader': {'scirel.equilibrium.anisotropic_force_balance': _dependency_0, 'scirel.equilibrium.axisymmetric_picard_update': _dependency_1, 'scirel.field.poloidal_field_from_flux': _dependency_2}})
__all__ = ['solve_axisymmetric_anisotropic_picard']

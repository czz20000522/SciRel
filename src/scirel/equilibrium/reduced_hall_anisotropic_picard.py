"""Source-ordered reduced Hall magnetic feedback over emitted leaf assets."""
from __future__ import annotations
from scirel._validation import finite_scalar as _require_finite_scalar, integer_scalar as _require_integer_scalar, bool_scalar as _require_bool_scalar
import numpy as np

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

def run_graph(inputs, *, asset_loader):
    """Iterate magnetic flux, caller-bound kinetic closure, and Hall current."""
    if not isinstance(inputs, dict):
        raise ValueError('inputs must be a mapping')
    required = {'r_grid', 'z_grid', 'psi_vac', 'g_psi', 'ion_mass_kg', 'ion_charge_c', 'pressure_closure'}
    missing = sorted((key for key in required if key not in inputs))
    if missing:
        raise ValueError(f"missing required inputs: {', '.join(missing)}")
    r_grid, z_grid, psi_vac = (np.asarray(inputs['r_grid'], dtype=float), np.asarray(inputs['z_grid'], dtype=float), np.asarray(inputs['psi_vac'], dtype=float))
    if r_grid.shape != z_grid.shape or psi_vac.shape != r_grid.shape or r_grid.ndim != 2:
        raise ValueError('r_grid, z_grid, psi_vac must be equal-shape 2-D arrays')
    if not all((np.all(np.isfinite(value)) for value in (r_grid, z_grid, psi_vac))):
        raise ValueError('r_grid, z_grid, psi_vac must be finite')
    r, z = (r_grid[0], z_grid[:, 0])
    if r.size < 3 or z.size < 3 or (not np.allclose(r_grid, r[np.newaxis, :])) or (not np.allclose(z_grid, z[:, np.newaxis])) or np.any(np.diff(r) <= 0.0) or np.any(np.diff(z) <= 0.0):
        raise ValueError('Hall Picard requires a strictly increasing rectilinear R-Z grid')
    g_psi = np.asarray(inputs['g_psi'], dtype=float)
    if g_psi.shape != (r_grid.size, r_grid.size) or not np.all(np.isfinite(g_psi)):
        raise ValueError('g_psi must be finite with shape (grid_size, grid_size)')
    closure = inputs['pressure_closure']
    if not callable(closure):
        raise TypeError('pressure_closure must be a callable returning a kinetic state mapping')
    tol = _require_finite_scalar(inputs.get('tol'), 'tol', 1e-08)
    maxiter = _require_integer_scalar(inputs.get('maxiter'), 'maxiter', 200, minimum=1)
    relax = _require_finite_scalar(inputs.get('relax'), 'relax', 0.5)
    minimum_field = _require_finite_scalar(inputs.get('minimum_field'), 'minimum_field', 1e-08)
    minimum_firehose = _require_finite_scalar(inputs.get('minimum_firehose_margin'), 'minimum_firehose_margin', 0.0)
    ion_mass = _require_finite_scalar(inputs['ion_mass_kg'], 'ion_mass_kg', None)
    ion_charge = _require_finite_scalar(inputs['ion_charge_c'], 'ion_charge_c', None)
    hall_multiplier = _require_finite_scalar(inputs.get('hall_multiplier'), 'hall_multiplier', 1.0)
    include_toroidal_inertia = _require_bool_scalar(inputs.get('include_toroidal_inertia'), 'include_toroidal_inertia', True)
    hall_density_floor_fraction = _require_finite_scalar(inputs.get('hall_density_floor_fraction'), 'hall_density_floor_fraction', 0.1)
    maximum_inertial_mach = _require_finite_scalar(inputs.get('maximum_inertial_mach'), 'maximum_inertial_mach', 0.5)
    inertia_relax = _require_finite_scalar(inputs.get('inertia_relax'), 'inertia_relax', 0.5)
    inertia_tolerance = _require_finite_scalar(inputs.get('inertia_tolerance'), 'inertia_tolerance', 1e-10)
    inertia_max_iterations = _require_integer_scalar(inputs.get('inertia_max_iterations'), 'inertia_max_iterations', 80, minimum=1)
    compatibility_tol = _require_finite_scalar(inputs.get('compatibility_tol'), 'compatibility_tol', 0.05)
    ohm_tol = _require_finite_scalar(inputs.get('ohm_tolerance'), 'ohm_tolerance', 0.05)
    strict = _require_bool_scalar(inputs.get('strict_compatibility'), 'strict_compatibility', True)
    if minimum_field <= 0.0 or not 0.0 <= relax < 1.0 or hall_multiplier < 0.0 or (not 0.0 <= hall_density_floor_fraction < 1.0) or (maximum_inertial_mach <= 0.0) or (not 0.0 <= inertia_relax < 1.0) or (inertia_tolerance <= 0.0) or (compatibility_tol < 0.0) or (ohm_tol <= 0.0):
        raise ValueError('Hall Picard controls are invalid')
    mask_port = inputs.get('plasma_mask')
    fixed_mask = np.ones_like(r_grid, dtype=bool) if mask_port is None else None if callable(mask_port) else np.asarray(mask_port, dtype=bool)
    if fixed_mask is not None and fixed_mask.shape != r_grid.shape:
        raise ValueError('plasma_mask must match the R-Z grid')
    field = asset_loader('scirel.field.poloidal_field_from_flux')
    drift = asset_loader('scirel.closures.reduced_hall_drift')
    flux_update = asset_loader('scirel.equilibrium.axisymmetric_picard_update')
    psi, old_currents, relative_change, converged = (np.array(psi_vac, copy=True), np.zeros_like(psi_vac), np.inf, False)
    history = []
    for iteration in range(maxiter):
        iteration += 1
        magnetic = field(r_grid, z_grid, psi)
        if np.any(magnetic['B'] < minimum_field):
            raise FloatingPointError('Hall equilibrium magnetic field vanished')
        state = closure(magnetic['B'], psi)
        if not isinstance(state, dict) or 'p_parallel' not in state or 'p_perpendicular' not in state:
            raise ValueError('pressure_closure must return p_parallel and p_perpendicular')
        p_parallel, p_perpendicular = _coerce_pressure(state['p_parallel'], state['p_perpendicular'], psi)
        if not np.all(np.isfinite(p_parallel)) or not np.all(np.isfinite(p_perpendicular)) or np.any(p_parallel < 0.0) or np.any(p_perpendicular < 0.0):
            raise ValueError('pressure_closure returned invalid pressure')
        active = np.asarray(mask_port(magnetic['B'], psi), dtype=bool) if callable(mask_port) else fixed_mask
        if active.shape != psi.shape:
            raise ValueError('callable plasma_mask returned the wrong shape')
        hall = drift(r_grid, z_grid, magnetic['B_R'], magnetic['B_Z'], p_parallel, p_perpendicular, state, active, ion_mass, ion_charge, hall_multiplier=hall_multiplier, include_toroidal_inertia=include_toroidal_inertia, hall_density_floor_fraction=hall_density_floor_fraction, maximum_inertial_mach=maximum_inertial_mach, inertia_relax=inertia_relax, inertia_tolerance=inertia_tolerance, inertia_max_iterations=inertia_max_iterations)
        update = flux_update(r_grid, z_grid, hall['J_phi'], psi, psi_vac, g_psi, relax, old_currents, cell_edges=inputs.get('cell_edges'))
        next_psi = update['psi_next']
        cell_currents = update['plasma_cell_currents']
        relative_change = update['relative_psi_change']
        current_change = update['relative_current_change']
        history.append({'iteration': iteration, 'relative_psi_change': relative_change, 'relative_current_change': current_change, 'generalized_ohm_error': hall['generalized_ohm_error']})
        psi, old_currents = (next_psi, cell_currents)
        if update['fixed_point_residual'] <= tol:
            converged = True
            break
    magnetic = field(r_grid, z_grid, psi)
    state = closure(magnetic['B'], psi)
    p_parallel, p_perpendicular = _coerce_pressure(state['p_parallel'], state['p_perpendicular'], psi)
    active = np.asarray(mask_port(magnetic['B'], psi), dtype=bool) if callable(mask_port) else fixed_mask
    hall = drift(r_grid, z_grid, magnetic['B_R'], magnetic['B_Z'], p_parallel, p_perpendicular, state, active, ion_mass, ion_charge, hall_multiplier=hall_multiplier, include_toroidal_inertia=include_toroidal_inertia, hall_density_floor_fraction=hall_density_floor_fraction, maximum_inertial_mach=maximum_inertial_mach, inertia_relax=inertia_relax, inertia_tolerance=inertia_tolerance, inertia_max_iterations=inertia_max_iterations)
    final_update = flux_update(r_grid, z_grid, hall['J_phi'], psi, psi_vac, g_psi, relax, old_currents, cell_edges=inputs.get('cell_edges'))
    cell_currents = final_update['plasma_cell_currents']
    fixed_point_residual=final_update['fixed_point_residual']
    converged=bool(fixed_point_residual<=tol)
    if np.any(magnetic['B']<minimum_field):
        raise FloatingPointError('Hall terminal magnetic field vanished')
    if minimum_firehose >= 0.0 and np.any(active & (hall['firehose_margin'] <= minimum_firehose)):
        raise FloatingPointError('Hall pressure closure crossed firehose/tension singularity')
    compatibility_tol = compatibility_tol
    messages = []
    if hall['parallel_force_error'] > compatibility_tol:
        messages.append(f"parallel momentum error {hall['parallel_force_error']:.3e} exceeds {compatibility_tol:.3e}")
    if hall['generalized_ohm_error'] > ohm_tol:
        messages.append(f"generalized Ohm error {hall['generalized_ohm_error']:.3e} exceeds {ohm_tol:.3e}")
    if messages and strict:
        raise ValueError('; '.join(messages))
    return {'psi': psi, 'plasma_cell_currents': cell_currents, 'J_phi': hall['J_phi'], 'B_R': magnetic['B_R'], 'B_Z': magnetic['B_Z'], 'B': magnetic['B'], 'p_parallel': p_parallel, 'p_perpendicular': p_perpendicular, 'parallel_force': hall['parallel_force'], 'force_R': hall['force_R'], 'force_Z': hall['force_Z'], 'ion_toroidal_velocity': hall['ion_toroidal_velocity'], 'electron_toroidal_velocity': hall['electron_toroidal_velocity'], 'electric_field_R': hall['electric_field_R'], 'electric_field_Z': hall['electric_field_Z'], 'hall_state': hall, 'converged': converged, 'fixed_point_residual':fixed_point_residual, 'iterations': iteration, 'relative_psi_change': relative_change, 'parallel_force_error': hall['parallel_force_error'], 'generalized_ohm_error': hall['generalized_ohm_error'], 'closure_state': state, 'firehose_margin': hall['firehose_margin'], 'compatibility_messages': messages, 'iteration_history': history}

def solve_reduced_hall_anisotropic_picard(inputs=None, **kwargs):
    """Run reduced-Hall magnetic feedback with a caller-owned pressure closure.

    Parameters
    ----------
    inputs : mapping, optional
        Mapping containing rectilinear ``r_grid``/``z_grid``, ``psi_vac``,
        dense ``g_psi``, the ``pressure_closure(B, psi)`` port and positive
        ion properties.  Optional controls cover outer Picard stopping,
        reduced-Hall inertia, active masks, firehose and generalized-Ohm gates,
        compatibility thresholds and explicit ``cell_edges``.
    **kwargs
        Composition overrides passed to the public graph boundary.

    Returns
    -------
    dict
        Terminal flux, reduced-Hall current and magnetic fields, pressure and
        force components, drift/electric fields, complete ``hall_state``,
        caller ``closure_state``, iteration history, fixed-point residual and
        compatibility messages.  Bounded outer nonconvergence returns the last
        terminally checked state with ``converged=False``.

    Raises
    ------
    ValueError, TypeError
        If grids, Green response, closure, masks or controls are invalid, or
        strict terminal compatibility thresholds are exceeded.
    FloatingPointError
        If the field floor or active-cell firehose/tension gate fails.
    RuntimeError
        If a reduced-Hall local inertia iteration does not converge.
    Exception
        Caller closure and dependency exceptions propagate unchanged.

    Notes
    -----
    ``psi`` is interpreted by the caller closure in the same ``R A_phi``
    convention as the dense Green response.  The outer graph recomputes and
    gates the terminal closure/current state; convergence is not a global
    equilibrium or identifiability guarantee.
    """

    from scirel._composition import compose
    from scirel.closures.reduced_hall_drift import close_reduced_hall_drift as _dependency_0
    from scirel.equilibrium.axisymmetric_picard_update import update_axisymmetric_picard_flux as _dependency_1
    from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux as _dependency_2
    return compose(run_graph, inputs, kwargs, {'asset_loader': {'scirel.closures.reduced_hall_drift': _dependency_0, 'scirel.equilibrium.axisymmetric_picard_update': _dependency_1, 'scirel.field.poloidal_field_from_flux': _dependency_2}})
__all__ = ['solve_reduced_hall_anisotropic_picard']

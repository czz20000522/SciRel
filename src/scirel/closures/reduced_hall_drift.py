"""Reduced axisymmetric Hall drift and inertia-corrected toroidal current."""
from scirel._validation import required_finite_scalar as _require_finite_scalar, required_integer_scalar as _require_integer_scalar
import math
import struct
import numpy as np
MU_0 = 4e-07 * np.pi
ELECTRON_MASS_KG = 9.1093837139e-31

def _stable_hypot(left, right):
    """Evaluate a Euclidean norm without avoidable range loss."""
    left, right = np.broadcast_arrays(np.asarray(left, dtype=float), np.asarray(right, dtype=float))
    values = []
    for x, y in zip(left.flat, right.flat):
        x, y = (abs(float(x)), abs(float(y)))
        if math.isinf(x) or math.isinf(y):
            values.append(math.inf)
            continue
        if math.isnan(x) or math.isnan(y):
            values.append(math.nan)
            continue
        if x < y:
            x, y = (y, x)
        if x == 0.0:
            values.append(0.0)
            continue
        _, exponent = math.frexp(x)
        x = math.ldexp(x, -exponent)
        y = math.ldexp(y, -exponent)
        bits = struct.unpack('>Q', struct.pack('>d', x))[0] & 18446744073575333888
        high = struct.unpack('>d', struct.pack('>Q', bits))[0]
        low = x - high
        scaled = math.sqrt(high * high - (y * -y - low * (x + high)))
        try:
            values.append(math.ldexp(scaled, exponent))
        except OverflowError:
            values.append(math.inf)
    return np.asarray(values, dtype=float).reshape(left.shape)


# Kept for the operator-contract test's numerical stress helper.  Both names
# resolve to the same local implementation; no second numerical path exists.
_source_hypot = _stable_hypot

def _grid(r_grid, z_grid):
    r_grid, z_grid = (np.asarray(r_grid, dtype=float), np.asarray(z_grid, dtype=float))
    if r_grid.shape != z_grid.shape or r_grid.ndim != 2:
        raise ValueError('R and Z must be equal 2-D arrays')
    r, z = (r_grid[0, :], z_grid[:, 0])
    if r.size < 3 or z.size < 3 or (not np.allclose(r_grid, r[np.newaxis, :])) or (not np.allclose(z_grid, z[:, np.newaxis])):
        raise ValueError('a rectilinear R-Z grid with at least 3 points per axis is required')
    if np.any(np.diff(r) <= 0.0) or np.any(np.diff(z) <= 0.0) or r[0] < 0.0:
        raise ValueError('R-Z axes must be increasing and R nonnegative')
    return (r_grid, z_grid, r, z)

def _state_array(state, name, shape):
    if name not in state:
        raise ValueError(f'closure_state requires {name}')
    try:
        value = np.broadcast_to(np.asarray(state[name], dtype=float), shape)
    except ValueError as exc:
        raise ValueError(f'closure_state.{name} does not match the R-Z grid') from exc
    if not np.all(np.isfinite(value)):
        raise ValueError(f'closure_state.{name} must be finite')
    return value

def _rms(values, mask):
    return 0.0 if not np.any(mask) else float(np.sqrt(np.mean(np.asarray(values)[mask] ** 2)))

from scirel._anisotropic_numerics import gradient_roundoff, pressure_divergence, residual_metrics
from scirel._numerics import stable_gradient as _gradient

def _pressure_force(r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular):
    r_grid, z_grid, _, _ = _grid(r_grid, z_grid)
    b_r, b_z, p_parallel, p_perpendicular = np.broadcast_arrays(np.asarray(b_r, dtype=float), np.asarray(b_z, dtype=float), np.asarray(p_parallel, dtype=float), np.asarray(p_perpendicular, dtype=float))
    if b_r.shape != r_grid.shape:
        raise ValueError('field and pressure arrays must match the R-Z grid')
    state = pressure_divergence(r_grid,z_grid,b_r,b_z,p_parallel,p_perpendicular)
    return tuple(state[k] for k in ('force_R','force_Z','parallel_force','J_phi'))

def _require_bool_scalar(value, name):
    if not isinstance(value, (bool, np.bool_)):
        raise ValueError(f'{name} must be a boolean scalar')
    return bool(value)

def close_reduced_hall_drift(r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular, closure_state, plasma_mask, ion_mass_kg, ion_charge_c, hall_multiplier=1.0, include_toroidal_inertia=True, hall_density_floor_fraction=0.1, maximum_inertial_mach=0.5, inertia_relax=0.5, inertia_tolerance=1e-10, inertia_max_iterations=80):
    """Compute reduced Hall current, toroidal species drifts, and diagnostics."""
    ion_mass_kg = _require_finite_scalar(ion_mass_kg, 'ion_mass_kg', positive=True)
    ion_charge_c = _require_finite_scalar(ion_charge_c, 'ion_charge_c', positive=True)
    hall_multiplier = _require_finite_scalar(hall_multiplier, 'hall_multiplier', nonnegative=True)
    include_toroidal_inertia = _require_bool_scalar(include_toroidal_inertia, 'include_toroidal_inertia')
    hall_density_floor_fraction = _require_finite_scalar(hall_density_floor_fraction, 'hall_density_floor_fraction')
    maximum_inertial_mach = _require_finite_scalar(maximum_inertial_mach, 'maximum_inertial_mach', positive=True)
    inertia_relax = _require_finite_scalar(inertia_relax, 'inertia_relax')
    inertia_tolerance = _require_finite_scalar(inertia_tolerance, 'inertia_tolerance', positive=True)
    inertia_max_iterations = _require_integer_scalar(inertia_max_iterations, 'inertia_max_iterations', minimum=1)
    if not 0.0 <= hall_density_floor_fraction < 1.0 or not 0.0 <= inertia_relax < 1.0:
        raise ValueError('Hall inertia controls are invalid')
    r_grid, z_grid, r, z = _grid(r_grid, z_grid)
    shape = r_grid.shape
    b_r, b_z, p_parallel, p_perpendicular = np.broadcast_arrays(np.asarray(b_r, dtype=float), np.asarray(b_z, dtype=float), np.asarray(p_parallel, dtype=float), np.asarray(p_perpendicular, dtype=float))
    if b_r.shape != shape or not all((np.all(np.isfinite(item)) for item in (b_r, b_z, p_parallel, p_perpendicular))):
        raise ValueError('Hall fields and pressures must be finite and match the R-Z grid')
    if np.any(p_parallel<0.) or np.any(p_perpendicular<0.):
        raise ValueError('Hall primary pressure must be nonnegative')
    plasma_mask = np.asarray(plasma_mask)
    if plasma_mask.shape != shape or plasma_mask.dtype != np.dtype(bool):
        raise ValueError('plasma_mask must be a boolean array with the same shape as the R-Z grid')
    ion_density = _state_array(closure_state, 'ion_density', shape)
    electron_pressure = _state_array(closure_state, 'electron_pressure', shape)
    electron_parallel = np.broadcast_to(np.asarray(closure_state.get('electron_p_parallel', electron_pressure), dtype=float), shape)
    electron_perpendicular = np.broadcast_to(np.asarray(closure_state.get('electron_p_perpendicular', electron_pressure), dtype=float), shape)
    if not np.all(np.isfinite(electron_parallel)) or not np.all(np.isfinite(electron_perpendicular)):
        raise ValueError('optional electron pressure components must be finite')
    potential = _state_array(closure_state, 'electrostatic_potential', shape)
    if np.any(ion_density < 0.0) or np.any(electron_pressure < 0.0) or np.any(electron_parallel < 0.0) or np.any(electron_perpendicular < 0.0):
        raise ValueError('Hall densities and electron pressures must be nonnegative')
    total_force = pressure_divergence(r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular)
    force_r, force_z, j_pressure = (total_force[k] for k in ('force_R','force_Z','J_phi'))
    electron_force = pressure_divergence(r_grid, z_grid, b_r, b_z, electron_parallel, electron_perpendicular)
    electron_force_r, electron_force_z = electron_force['force_R'], electron_force['force_Z']
    dphi_dz, dphi_dr = (_gradient(potential, z, axis=0), _gradient(potential, r, axis=1))
    electric_r, electric_z = (-dphi_dr, -dphi_dz)
    b_squared = b_r ** 2 + b_z ** 2
    b = np.sqrt(b_squared)
    peak_density = float(np.max(ion_density[plasma_mask])) if np.any(plasma_mask) else 0.0
    density_floor = hall_density_floor_fraction * peak_density
    hall_mask = plasma_mask & (r_grid > 0.0) & (ion_density > density_floor) & (b_squared > np.finfo(float).tiny)
    charge_density = ion_charge_c * ion_density
    safe_charge_density = np.maximum(charge_density, ion_charge_c * max(density_floor, np.finfo(float).tiny))
    drift_projection = np.divide(b_z * (electric_r + hall_multiplier * electron_force_r / safe_charge_density) - b_r * (electric_z + hall_multiplier * electron_force_z / safe_charge_density), b_squared, out=np.zeros_like(b), where=hall_mask)
    ion_parallel = np.broadcast_to(np.asarray(closure_state.get('ion_p_parallel', p_parallel-electron_parallel), dtype=float), shape)
    ion_perpendicular = np.broadcast_to(np.asarray(closure_state.get('ion_p_perpendicular', p_perpendicular-electron_perpendicular), dtype=float), shape)
    if not np.all(np.isfinite(ion_parallel)) or not np.all(np.isfinite(ion_perpendicular)) or np.any(ion_parallel < 0.0) or np.any(ion_perpendicular < 0.0):
        raise ValueError('optional ion pressure components must be finite and nonnegative')
    composition_mode=closure_state.get('pressure_composition_mode','independent_fit')
    if composition_mode not in {'independent_fit','species_sum'}:
        raise ValueError('pressure_composition_mode must be independent_fit or species_sum')
    residual_parallel=p_parallel-(ion_parallel+electron_parallel)
    residual_perpendicular=p_perpendicular-(ion_perpendicular+electron_perpendicular)
    consistent=bool(np.all(abs(residual_parallel)<=64*np.finfo(float).eps*np.maximum(np.maximum(abs(p_parallel),abs(ion_parallel+electron_parallel)),np.finfo(float).tiny)) and np.all(abs(residual_perpendicular)<=64*np.finfo(float).eps*np.maximum(np.maximum(abs(p_perpendicular),abs(ion_perpendicular+electron_perpendicular)),np.finfo(float).tiny)))
    if composition_mode=='species_sum' and not consistent:
        raise ValueError('total pressure is inconsistent with the species pressure sum')
    ion_scalar_pressure = (ion_parallel + 2.0 * ion_perpendicular) / 3.0
    mass_density = ion_mass_kg * ion_density
    thermal_speed = np.sqrt(np.divide(ion_scalar_pressure, mass_density, out=np.zeros_like(b), where=mass_density > 0.0))
    velocity_limit = maximum_inertial_mach * thermal_speed
    j_phi, ion_velocity, centrifugal_force = (np.where(plasma_mask, j_pressure, 0.0), np.zeros_like(b), np.zeros_like(b))
    converged, change, iterations = (not include_toroidal_inertia or not np.any(hall_mask), 0.0, 0)
    fixed_point_residual = 0.0
    for iterations in range(1, int(inertia_max_iterations) + 1):
        raw_velocity = hall_multiplier * j_phi / safe_charge_density - drift_projection
        next_velocity = np.where(hall_mask, np.clip(raw_velocity, -velocity_limit, velocity_limit), 0.0)
        next_centrifugal = np.divide(mass_density * next_velocity ** 2, r_grid, out=np.zeros_like(b), where=hall_mask)
        candidate = np.divide(b_z * (force_r - next_centrifugal) - b_r * force_z, b_squared, out=np.zeros_like(b), where=b_squared > np.finfo(float).tiny) if include_toroidal_inertia else j_pressure
        candidate = np.where(plasma_mask, candidate, 0.0)
        next_current = inertia_relax * j_phi + (1.0 - inertia_relax) * candidate
        change = float(np.linalg.norm(next_current - j_phi) / max(float(np.linalg.norm(next_current)), 1.0))
        j_phi, ion_velocity, centrifugal_force = (next_current, next_velocity, next_centrifugal)
        # Evaluate the unrelaxed map at the returned candidate current. A small
        # relaxed update, especially relax near 1, does not imply equilibrium.
        terminal_velocity = np.where(hall_mask, np.clip(hall_multiplier*j_phi/safe_charge_density-drift_projection, -velocity_limit, velocity_limit), 0.0)
        terminal_centrifugal = np.divide(mass_density*terminal_velocity**2, r_grid, out=np.zeros_like(b), where=hall_mask)
        terminal_target = np.divide(b_z*(force_r-terminal_centrifugal)-b_r*force_z, b_squared, out=np.zeros_like(b), where=b_squared>np.finfo(float).tiny) if include_toroidal_inertia else j_pressure
        terminal_target = np.where(plasma_mask, terminal_target, 0.0)
        fixed_point_residual = float(np.linalg.norm(terminal_target-j_phi)/max(float(np.linalg.norm(j_phi)),1.0))
        if not include_toroidal_inertia or fixed_point_residual <= inertia_tolerance:
            converged = True
            break
    if not converged:
        raise RuntimeError('local Hall inertia iteration did not converge')
    raw_velocity = hall_multiplier * j_phi / safe_charge_density - drift_projection
    ion_velocity = np.where(hall_mask, np.clip(raw_velocity, -velocity_limit, velocity_limit), 0.0)
    centrifugal_force = np.divide(mass_density * ion_velocity ** 2, r_grid, out=np.zeros_like(b), where=hall_mask & include_toroidal_inertia)
    electron_velocity = np.where(hall_mask, ion_velocity - j_phi / safe_charge_density, 0.0)
    hall_r = hall_multiplier * (j_phi * b_z / safe_charge_density - electron_force_r / safe_charge_density)
    hall_z = hall_multiplier * (-j_phi * b_r / safe_charge_density - electron_force_z / safe_charge_density)
    ohm_r, ohm_z = (np.where(hall_mask, electric_r + ion_velocity * b_z - hall_r, 0.0), np.where(hall_mask, electric_z - ion_velocity * b_r - hall_z, 0.0))
    ohm_parallel = np.divide(b_r * ohm_r + b_z * ohm_z, b, out=np.zeros_like(b), where=hall_mask)
    ohm_scale = np.sqrt(electric_r ** 2 + electric_z ** 2 + hall_r ** 2 + hall_z ** 2 + (ion_velocity * b) ** 2)
    electric_bound = np.hypot(gradient_roundoff(potential,r,1), gradient_roundoff(potential,z,0))
    ohm_bound = electric_bound + hall_multiplier*np.hypot(electron_force['force_roundoff_R'],electron_force['force_roundoff_Z'])/safe_charge_density + 64*np.finfo(float).eps*ohm_scale
    ohm_metrics = residual_metrics(np.hypot(ohm_r,ohm_z),ohm_scale,ohm_bound,hall_mask)
    generalized_ohm_error = ohm_metrics['error']
    target_force_r, target_force_z = (force_r - centrifugal_force, force_z)
    momentum_r, momentum_z = (j_phi * b_z - target_force_r, -j_phi * b_r - target_force_z)
    parallel_force = np.divide(b_r * target_force_r + b_z * target_force_z, b, out=np.zeros_like(b), where=b > np.finfo(float).tiny)
    force_norm = _stable_hypot(target_force_r, target_force_z)
    force_bound = np.hypot(total_force['force_roundoff_R'],total_force['force_roundoff_Z']) + 64*np.finfo(float).eps*np.abs(centrifugal_force)
    parallel_metrics = residual_metrics(parallel_force,force_norm,force_bound,plasma_mask)
    momentum_metrics = residual_metrics(np.hypot(momentum_r,momentum_z),force_norm,force_bound,plasma_mask)
    parallel_force_error = parallel_metrics['error']
    momentum_error = momentum_metrics['error']
    skin_depth = np.sqrt(np.divide(ion_mass_kg, MU_0 * ion_density * ion_charge_c ** 2, out=np.zeros_like(b), where=ion_density > 0.0))
    db_dz, db_dr = (_gradient(b, z, axis=0), _gradient(b, r, axis=1))
    gradient_magnitude = _stable_hypot(db_dr, db_dz)
    scale = np.divide(b, gradient_magnitude, out=np.full_like(b, np.inf), where=gradient_magnitude > 0.0)
    hall_ratio = np.divide(skin_depth, scale, out=np.zeros_like(b), where=np.isfinite(scale) & (scale > 0.0))
    electron_skin_depth = skin_depth * np.sqrt(ELECTRON_MASS_KG / ion_mass_kg)
    electron_ratio = np.divide(electron_skin_depth, scale, out=np.zeros_like(b), where=np.isfinite(scale) & (scale > 0.0))
    gyroradius = np.divide(ion_mass_kg * thermal_speed, ion_charge_c * b, out=np.zeros_like(b), where=b > 0.0)
    gyroradius_ratio = np.divide(gyroradius, scale, out=np.zeros_like(b), where=np.isfinite(scale) & (scale > 0.0))
    mach = np.divide(ion_velocity, thermal_speed, out=np.zeros_like(b), where=thermal_speed > 0.0)
    raw_mach = np.divide(raw_velocity, thermal_speed, out=np.zeros_like(b), where=hall_mask & (thermal_speed > 0.0))
    firehose_margin = 1.0 - MU_0 * (p_parallel - p_perpendicular) / np.maximum(b_squared, np.finfo(float).tiny)
    return {'pressure_composition_mode':composition_mode, 'species_pressure_sum_consistent':consistent, 'residual_stress_parallel_pa':residual_parallel, 'residual_stress_perpendicular_pa':residual_perpendicular, 'J_phi': j_phi, 'force_R': target_force_r, 'force_Z': target_force_z, 'pressure_force_R': force_r, 'pressure_force_Z': force_z, 'electron_pressure_force_R': electron_force_r, 'electron_pressure_force_Z': electron_force_z, 'parallel_force': parallel_force, 'parallel_force_error': parallel_force_error, 'parallel_force_diagnostics': parallel_metrics, 'ohm_diagnostics': ohm_metrics, 'momentum_diagnostics': momentum_metrics, 'momentum_residual_R': momentum_r, 'momentum_residual_Z': momentum_z, 'momentum_error': momentum_error, 'ion_toroidal_velocity': ion_velocity, 'electron_toroidal_velocity': electron_velocity, 'raw_ion_toroidal_velocity': raw_velocity, 'ion_toroidal_mach': mach, 'raw_ion_toroidal_mach': raw_mach, 'centrifugal_force_R': centrifugal_force, 'electric_field_R': electric_r, 'electric_field_Z': electric_z, 'hall_electric_field_R': hall_r, 'hall_electric_field_Z': hall_z, 'ohm_residual_R': ohm_r, 'ohm_residual_Z': ohm_z, 'ohm_parallel': ohm_parallel, 'generalized_ohm_error': generalized_ohm_error, 'firehose_margin': firehose_margin, 'ion_skin_depth': skin_depth, 'electron_skin_depth': electron_skin_depth, 'ion_gyroradius': gyroradius, 'magnetic_scale_length': scale, 'hall_scale_ratio': hall_ratio, 'electron_inertia_scale_ratio': electron_ratio, 'ion_gyroradius_scale_ratio': gyroradius_ratio, 'hall_active_mask': hall_mask, 'density_floor_m3': density_floor, 'velocity_cap_fraction': float(np.mean(np.abs(raw_mach[hall_mask]) > maximum_inertial_mach)) if np.any(hall_mask) else 0.0, 'inertia_iterations': iterations, 'inertia_relative_change': change, 'inertia_fixed_point_residual': fixed_point_residual, 'inertia_converged': converged}
__all__ = ['close_reduced_hall_drift']

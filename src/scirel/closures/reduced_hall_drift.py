"""Reduced axisymmetric Hall drift and inertia-corrected toroidal current."""
from scirel._validation import required_finite_scalar as _require_finite_scalar, required_integer_scalar as _require_integer_scalar
import math
import struct
import numpy as np
MU_0 = 4e-07 * np.pi
ELECTRON_MASS_KG = 9.1093837139e-31

def _source_hypot(left, right):
    """Reproduce source ``np.hypot`` without finite-range under/overflow."""
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

def _source_gradient(values, coordinates, axis):
    """Preserve the source ``np.gradient(..., coordinates, edge_order=2)`` stencil."""
    distances = np.diff(coordinates)
    result = np.empty_like(values)
    uniform = (distances == distances[0]).all()
    if axis == 0:
        if uniform:
            spacing = distances[0]
            result[1:-1, :] = (values[2:, :] - values[:-2, :]) / (2.0 * spacing)
            result[0, :] = -1.5 / spacing * values[0, :] + 2.0 / spacing * values[1, :] - 0.5 / spacing * values[2, :]
            result[-1, :] = 0.5 / spacing * values[-3, :] - 2.0 / spacing * values[-2, :] + 1.5 / spacing * values[-1, :]
        else:
            dx1, dx2 = (distances[:-1], distances[1:])
            a = -dx2 / (dx1 * (dx1 + dx2))
            b = (dx2 - dx1) / (dx1 * dx2)
            c = dx1 / (dx2 * (dx1 + dx2))
            result[1:-1, :] = a[:, None] * values[:-2, :] + b[:, None] * values[1:-1, :] + c[:, None] * values[2:, :]
            dx1, dx2 = (distances[0], distances[1])
            a = -(2.0 * dx1 + dx2) / (dx1 * (dx1 + dx2))
            b = (dx1 + dx2) / (dx1 * dx2)
            c = -dx1 / (dx2 * (dx1 + dx2))
            result[0, :] = a * values[0, :] + b * values[1, :] + c * values[2, :]
            dx1, dx2 = (distances[-2], distances[-1])
            a = dx2 / (dx1 * (dx1 + dx2))
            b = -(dx2 + dx1) / (dx1 * dx2)
            c = (2.0 * dx2 + dx1) / (dx2 * (dx1 + dx2))
            result[-1, :] = a * values[-3, :] + b * values[-2, :] + c * values[-1, :]
    elif uniform:
        spacing = distances[0]
        result[:, 1:-1] = (values[:, 2:] - values[:, :-2]) / (2.0 * spacing)
        result[:, 0] = -1.5 / spacing * values[:, 0] + 2.0 / spacing * values[:, 1] - 0.5 / spacing * values[:, 2]
        result[:, -1] = 0.5 / spacing * values[:, -3] - 2.0 / spacing * values[:, -2] + 1.5 / spacing * values[:, -1]
    else:
        dx1, dx2 = (distances[:-1], distances[1:])
        a = -dx2 / (dx1 * (dx1 + dx2))
        b = (dx2 - dx1) / (dx1 * dx2)
        c = dx1 / (dx2 * (dx1 + dx2))
        result[:, 1:-1] = a * values[:, :-2] + b * values[:, 1:-1] + c * values[:, 2:]
        dx1, dx2 = (distances[0], distances[1])
        a = -(2.0 * dx1 + dx2) / (dx1 * (dx1 + dx2))
        b = (dx1 + dx2) / (dx1 * dx2)
        c = -dx1 / (dx2 * (dx1 + dx2))
        result[:, 0] = a * values[:, 0] + b * values[:, 1] + c * values[:, 2]
        dx1, dx2 = (distances[-2], distances[-1])
        a = dx2 / (dx1 * (dx1 + dx2))
        b = -(dx2 + dx1) / (dx1 * dx2)
        c = (2.0 * dx2 + dx1) / (dx2 * (dx1 + dx2))
        result[:, -1] = a * values[:, -3] + b * values[:, -2] + c * values[:, -1]
    return result

def _pressure_force(r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular):
    r_grid, _, r, z = _grid(r_grid, z_grid)
    b_r, b_z, p_parallel, p_perpendicular = np.broadcast_arrays(np.asarray(b_r, dtype=float), np.asarray(b_z, dtype=float), np.asarray(p_parallel, dtype=float), np.asarray(p_perpendicular, dtype=float))
    if b_r.shape != r_grid.shape:
        raise ValueError('field and pressure arrays must match the R-Z grid')
    b = _source_hypot(b_r, b_z)
    inverse_b = np.divide(1.0, b, out=np.zeros_like(b), where=b > np.finfo(float).tiny)
    unit_r, unit_z, delta_p = (b_r * inverse_b, b_z * inverse_b, p_parallel - p_perpendicular)
    p_rr = p_perpendicular + delta_p * unit_r ** 2
    p_zz = p_perpendicular + delta_p * unit_z ** 2
    p_rz, p_phiphi = (delta_p * unit_r * unit_z, p_perpendicular)
    force_r = _source_gradient(p_rr, r, axis=1) + _source_gradient(p_rz, z, axis=0)
    force_z = _source_gradient(p_rz, r, axis=1) + _source_gradient(p_zz, z, axis=0)
    off_axis = r_grid > 0.0
    force_r[off_axis] += (p_rr[off_axis] - p_phiphi[off_axis]) / r_grid[off_axis]
    force_z[off_axis] += p_rz[off_axis] / r_grid[off_axis]
    if r[0] == 0.0:
        force_r[:, 0] = 0.0
    b_squared = b ** 2
    j_phi = np.divide(b_z * force_r - b_r * force_z, b_squared, out=np.zeros_like(b), where=b_squared > np.finfo(float).tiny)
    parallel_force = (b_r * force_r + b_z * force_z) * inverse_b
    if r[0] == 0.0:
        j_phi[:, 0] = 0.0
    return (force_r, force_z, parallel_force, j_phi)

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
    plasma_mask = np.asarray(plasma_mask, dtype=bool)
    if plasma_mask.shape != shape:
        raise ValueError('plasma_mask must match the R-Z grid')
    ion_density = _state_array(closure_state, 'ion_density', shape)
    electron_pressure = _state_array(closure_state, 'electron_pressure', shape)
    electron_parallel = np.broadcast_to(np.asarray(closure_state.get('electron_p_parallel', electron_pressure), dtype=float), shape)
    electron_perpendicular = np.broadcast_to(np.asarray(closure_state.get('electron_p_perpendicular', electron_pressure), dtype=float), shape)
    if not np.all(np.isfinite(electron_parallel)) or not np.all(np.isfinite(electron_perpendicular)):
        raise ValueError('optional electron pressure components must be finite')
    potential = _state_array(closure_state, 'electrostatic_potential', shape)
    if np.any(ion_density < 0.0) or np.any(electron_pressure < 0.0) or np.any(electron_parallel < 0.0) or np.any(electron_perpendicular < 0.0):
        raise ValueError('Hall densities and electron pressures must be nonnegative')
    force_r, force_z, _, j_pressure = _pressure_force(r_grid, z_grid, b_r, b_z, p_parallel, p_perpendicular)
    electron_force_r, electron_force_z, _, _ = _pressure_force(r_grid, z_grid, b_r, b_z, electron_parallel, electron_perpendicular)
    dphi_dz, dphi_dr = (_source_gradient(potential, z, axis=0), _source_gradient(potential, r, axis=1))
    electric_r, electric_z = (-dphi_dr, -dphi_dz)
    b_squared = b_r ** 2 + b_z ** 2
    b = np.sqrt(b_squared)
    peak_density = float(np.max(ion_density[plasma_mask])) if np.any(plasma_mask) else 0.0
    density_floor = hall_density_floor_fraction * peak_density
    hall_mask = plasma_mask & (r_grid > 0.0) & (ion_density > density_floor) & (b_squared > np.finfo(float).tiny)
    charge_density = ion_charge_c * ion_density
    safe_charge_density = np.maximum(charge_density, ion_charge_c * max(density_floor, np.finfo(float).tiny))
    drift_projection = np.divide(b_z * (electric_r + hall_multiplier * electron_force_r / safe_charge_density) - b_r * (electric_z + hall_multiplier * electron_force_z / safe_charge_density), b_squared, out=np.zeros_like(b), where=hall_mask)
    ion_parallel = np.broadcast_to(np.asarray(closure_state.get('ion_p_parallel', p_parallel), dtype=float), shape)
    ion_perpendicular = np.broadcast_to(np.asarray(closure_state.get('ion_p_perpendicular', p_perpendicular), dtype=float), shape)
    if not np.all(np.isfinite(ion_parallel)) or not np.all(np.isfinite(ion_perpendicular)) or np.any(ion_parallel < 0.0) or np.any(ion_perpendicular < 0.0):
        raise ValueError('optional ion pressure components must be finite and nonnegative')
    ion_scalar_pressure = (ion_parallel + 2.0 * ion_perpendicular) / 3.0
    mass_density = ion_mass_kg * ion_density
    thermal_speed = np.sqrt(np.divide(ion_scalar_pressure, mass_density, out=np.zeros_like(b), where=mass_density > 0.0))
    velocity_limit = maximum_inertial_mach * thermal_speed
    j_phi, ion_velocity, centrifugal_force = (np.where(plasma_mask, j_pressure, 0.0), np.zeros_like(b), np.zeros_like(b))
    converged, change, iterations = (not include_toroidal_inertia or not np.any(hall_mask), 0.0, 0)
    for iterations in range(1, int(inertia_max_iterations) + 1):
        raw_velocity = hall_multiplier * j_phi / safe_charge_density - drift_projection
        next_velocity = np.where(hall_mask, np.clip(raw_velocity, -velocity_limit, velocity_limit), 0.0)
        next_centrifugal = np.divide(mass_density * next_velocity ** 2, r_grid, out=np.zeros_like(b), where=hall_mask)
        candidate = np.divide(b_z * (force_r - next_centrifugal) - b_r * force_z, b_squared, out=np.zeros_like(b), where=b_squared > np.finfo(float).tiny) if include_toroidal_inertia else j_pressure
        candidate = np.where(plasma_mask, candidate, 0.0)
        next_current = inertia_relax * j_phi + (1.0 - inertia_relax) * candidate
        change = float(np.linalg.norm(next_current - j_phi) / max(float(np.linalg.norm(next_current)), 1.0))
        j_phi, ion_velocity, centrifugal_force = (next_current, next_velocity, next_centrifugal)
        if not include_toroidal_inertia or change <= inertia_tolerance:
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
    generalized_ohm_error = _rms(_source_hypot(ohm_r, ohm_z), hall_mask) / max(_rms(ohm_scale, hall_mask), np.finfo(float).tiny)
    target_force_r, target_force_z = (force_r - centrifugal_force, force_z)
    momentum_r, momentum_z = (j_phi * b_z - target_force_r, -j_phi * b_r - target_force_z)
    parallel_force = np.divide(b_r * target_force_r + b_z * target_force_z, b, out=np.zeros_like(b), where=b > np.finfo(float).tiny)
    force_norm = _source_hypot(target_force_r, target_force_z)
    parallel_force_error = _rms(parallel_force, plasma_mask) / max(_rms(force_norm, plasma_mask), np.finfo(float).tiny)
    momentum_error = _rms(_source_hypot(momentum_r, momentum_z), plasma_mask) / max(_rms(force_norm, plasma_mask), np.finfo(float).tiny)
    skin_depth = np.sqrt(np.divide(ion_mass_kg, MU_0 * ion_density * ion_charge_c ** 2, out=np.zeros_like(b), where=ion_density > 0.0))
    db_dz, db_dr = (_source_gradient(b, z, axis=0), _source_gradient(b, r, axis=1))
    gradient_magnitude = _source_hypot(db_dr, db_dz)
    scale = np.divide(b, gradient_magnitude, out=np.full_like(b, np.inf), where=gradient_magnitude > 0.0)
    hall_ratio = np.divide(skin_depth, scale, out=np.zeros_like(b), where=np.isfinite(scale) & (scale > 0.0))
    electron_skin_depth = skin_depth * np.sqrt(ELECTRON_MASS_KG / ion_mass_kg)
    electron_ratio = np.divide(electron_skin_depth, scale, out=np.zeros_like(b), where=np.isfinite(scale) & (scale > 0.0))
    gyroradius = np.divide(ion_mass_kg * thermal_speed, ion_charge_c * b, out=np.zeros_like(b), where=b > 0.0)
    gyroradius_ratio = np.divide(gyroradius, scale, out=np.zeros_like(b), where=np.isfinite(scale) & (scale > 0.0))
    mach = np.divide(ion_velocity, thermal_speed, out=np.zeros_like(b), where=thermal_speed > 0.0)
    raw_mach = np.divide(raw_velocity, thermal_speed, out=np.zeros_like(b), where=hall_mask & (thermal_speed > 0.0))
    firehose_margin = 1.0 - MU_0 * (p_parallel - p_perpendicular) / np.maximum(b_squared, np.finfo(float).tiny)
    return {'J_phi': j_phi, 'force_R': target_force_r, 'force_Z': target_force_z, 'pressure_force_R': force_r, 'pressure_force_Z': force_z, 'electron_pressure_force_R': electron_force_r, 'electron_pressure_force_Z': electron_force_z, 'parallel_force': parallel_force, 'parallel_force_error': parallel_force_error, 'momentum_residual_R': momentum_r, 'momentum_residual_Z': momentum_z, 'momentum_error': momentum_error, 'ion_toroidal_velocity': ion_velocity, 'electron_toroidal_velocity': electron_velocity, 'raw_ion_toroidal_velocity': raw_velocity, 'ion_toroidal_mach': mach, 'raw_ion_toroidal_mach': raw_mach, 'centrifugal_force_R': centrifugal_force, 'electric_field_R': electric_r, 'electric_field_Z': electric_z, 'hall_electric_field_R': hall_r, 'hall_electric_field_Z': hall_z, 'ohm_residual_R': ohm_r, 'ohm_residual_Z': ohm_z, 'ohm_parallel': ohm_parallel, 'generalized_ohm_error': generalized_ohm_error, 'firehose_margin': firehose_margin, 'ion_skin_depth': skin_depth, 'electron_skin_depth': electron_skin_depth, 'ion_gyroradius': gyroradius, 'magnetic_scale_length': scale, 'hall_scale_ratio': hall_ratio, 'electron_inertia_scale_ratio': electron_ratio, 'ion_gyroradius_scale_ratio': gyroradius_ratio, 'hall_active_mask': hall_mask, 'density_floor_m3': density_floor, 'velocity_cap_fraction': float(np.mean(np.abs(raw_mach[hall_mask]) > maximum_inertial_mach)) if np.any(hall_mask) else 0.0, 'inertia_iterations': iterations, 'inertia_relative_change': change, 'inertia_converged': converged}
__all__ = ['close_reduced_hall_drift']

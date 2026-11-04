"""Invariant guiding-centre bi-Maxwellian phase-space distribution."""
import math
import numpy as np

def _field(value, psi, name):
    if callable(value):
        value = value(np.asarray(psi, dtype=float))
    try:
        values = np.broadcast_to(np.asarray(value, dtype=float), np.shape(psi))
    except ValueError as exc:
        raise ValueError(f'{name} cannot be broadcast over psi') from exc
    if not np.all(np.isfinite(values)):
        raise ValueError(f'{name} must be finite')
    return values

def _require_finite_scalar(value, name, *, positive=False, nonzero=False):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f'{name} must be a finite scalar')
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} must be a finite scalar') from exc
    if array.ndim != 0 or not np.isrealobj(array) or (not bool(np.all(np.isfinite(array)))):
        raise ValueError(f'{name} must be a finite scalar')
    result = float(array)
    if positive and result <= 0.0:
        raise ValueError(f'{name} must be strictly positive')
    if nonzero and result == 0.0:
        raise ValueError(f'{name} must be non-zero')
    return result

def evaluate_mirror_invariant_distribution(v_parallel_m_s, v_perpendicular_m_s, b_t, psi, potential_v, mass_kg, charge_c, density_ref_m3, temperature_parallel_j, temperature_perpendicular_ref_j, b_ref_t, phi_ref_v=0.0, b_plug_left_t=None, b_plug_right_t=None, phi_plug_left_v=0.0, phi_plug_right_v=0.0, loss_cone_refill=0.0):
    """Evaluate physical ``f0(E,mu,psi)`` in s^3/m^6."""
    mass_kg = _require_finite_scalar(mass_kg, 'mass_kg', positive=True)
    charge_c = _require_finite_scalar(charge_c, 'charge_c', nonzero=True)
    loss_cone_refill = _require_finite_scalar(loss_cone_refill, 'loss_cone_refill')
    if not 0.0 <= loss_cone_refill <= 1.0:
        raise ValueError('mass, charge, or loss_cone_refill is invalid')
    if (b_plug_left_t is None) != (b_plug_right_t is None):
        raise ValueError('both plug fields are required together')
    v_parallel_m_s, v_perpendicular_m_s, b_t, psi, potential_v = np.broadcast_arrays(np.asarray(v_parallel_m_s, dtype=float), np.asarray(v_perpendicular_m_s, dtype=float), np.asarray(b_t, dtype=float), np.asarray(psi, dtype=float), np.asarray(potential_v, dtype=float))
    density_ref, t_parallel, t_perpendicular_ref, b_ref, phi_ref = (_field(value, psi, name) for value, name in ((density_ref_m3, 'density_ref_m3'), (temperature_parallel_j, 'temperature_parallel_j'), (temperature_perpendicular_ref_j, 'temperature_perpendicular_ref_j'), (b_ref_t, 'b_ref_t'), (phi_ref_v, 'phi_ref_v')))
    if np.any(b_t <= 0.0) or np.any(density_ref < 0.0) or np.any(t_parallel <= 0.0) or np.any(t_perpendicular_ref <= 0.0) or np.any(b_ref <= 0.0):
        raise ValueError('field, reference density, or temperatures are invalid')
    coefficient = (b_t - b_ref) / t_parallel + b_ref / t_perpendicular_ref
    if np.any(coefficient <= 0.0):
        raise FloatingPointError('invariant bi-Maxwellian is not integrable')
    mu = mass_kg * v_perpendicular_m_s ** 2 / (2.0 * b_t)
    energy = 0.5 * mass_kg * v_parallel_m_s ** 2 + mu * b_t + charge_c * potential_v
    exponent = -((energy - charge_c * phi_ref) / t_parallel + mu * b_ref * (1.0 / t_perpendicular_ref - 1.0 / t_parallel))
    normalization = density_ref * (mass_kg / (2.0 * math.pi)) ** 1.5 / (t_perpendicular_ref * np.sqrt(t_parallel))
    occupation = 1.0
    if b_plug_left_t is not None:
        b_left, b_right = (_field(b_plug_left_t, psi, 'b_plug_left_t'), _field(b_plug_right_t, psi, 'b_plug_right_t'))
        phi_left, phi_right = (_field(phi_plug_left_v, psi, 'phi_plug_left_v'), _field(phi_plug_right_v, psi, 'phi_plug_right_v'))
        if np.any(b_left <= 0.0) or np.any(b_right <= 0.0):
            raise ValueError('plug fields must be positive')
        barrier = np.minimum(mu * b_left + charge_c * phi_left, mu * b_right + charge_c * phi_right)
        occupation = loss_cone_refill + (1.0 - loss_cone_refill) * (energy < barrier).astype(float)
    return {'f0_s3_m6': normalization * np.exp(np.clip(exponent, -745.0, 700.0)) * occupation, 'energy_j': energy, 'magnetic_moment_j_t': mu, 'occupation': occupation}
__all__ = ['evaluate_mirror_invariant_distribution']

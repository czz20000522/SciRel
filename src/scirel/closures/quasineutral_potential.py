"""Standalone bisection of the kinetic quasineutral-potential relation."""
from __future__ import annotations
from collections.abc import Mapping
import numpy as np
ELEMENTARY_CHARGE_C = 1.602176634e-19

def _field(value, shape, name):
    values = np.asarray(value, dtype=float)
    try:
        values = np.broadcast_to(values, shape)
    except ValueError as exc:
        raise ValueError(f'{name} cannot be broadcast to the declared surface shape') from exc
    if not np.all(np.isfinite(values)):
        raise ValueError(f'{name} must be finite')
    return values

def solve_quasineutral_potential(potential_reference_v, temperature_parallel_j, electron_temperature_j, charge_c, active, residual, potential_tolerance_v=1e-08, quasineutral_tolerance=1e-10, max_iterations=100, initial_bracket_thermal=8.0):
    """Solve ``log(Z*n_i(phi))-log(n_e(phi)) == 0`` by vectorized bisection.

    ``residual`` is a caller-owned source-free evaluator returning a mapping with
    ``logarithmic_charge_residual``.  Positive residuals must be on the lower-
    potential side of the root; the operator owns only bracket expansion and the
    monotone bisection state, not the kinetic or electron relation.
    """
    phi_ref, t_parallel, t_e, active = np.broadcast_arrays(np.asarray(potential_reference_v, dtype=float), np.asarray(temperature_parallel_j, dtype=float), np.asarray(electron_temperature_j, dtype=float), np.asarray(active, dtype=bool))
    if not all((np.all(np.isfinite(value)) for value in (phi_ref, t_parallel, t_e))):
        raise ValueError('potential and temperatures must be finite')
    if np.any(t_parallel <= 0.0) or np.any(t_e <= 0.0):
        raise ValueError('temperatures must be positive')
    charge = float(charge_c)
    if not np.isfinite(charge) or charge <= 0.0:
        raise ValueError('charge_c must be finite and positive')
    tolerance = float(potential_tolerance_v)
    residual_tolerance = float(quasineutral_tolerance)
    if isinstance(max_iterations, (bool, np.bool_)) or not isinstance(max_iterations, (int, np.integer)):
        raise ValueError('max_iterations must be an integer')
    iterations_limit = int(max_iterations)
    bracket_thermal = float(initial_bracket_thermal)
    if not np.isfinite(tolerance) or not np.isfinite(residual_tolerance) or (not np.isfinite(bracket_thermal)) or (tolerance <= 0.0) or (residual_tolerance <= 0.0) or (iterations_limit < 1) or (bracket_thermal <= 0.0):
        raise ValueError('invalid quasineutral solver controls')

    def evaluate(value):
        result = residual(value)
        if not isinstance(result, Mapping) or 'logarithmic_charge_residual' not in result:
            raise ValueError('residual must return logarithmic_charge_residual')
        values = _field(result['logarithmic_charge_residual'], phi_ref.shape, 'logarithmic_charge_residual')
        return values
    thermal_voltage = t_parallel / charge + t_e / ELEMENTARY_CHARGE_C
    lower = phi_ref - bracket_thermal * thermal_voltage
    upper = phi_ref + bracket_thermal * thermal_voltage
    lower_residual, upper_residual = (evaluate(lower), evaluate(upper))
    for _ in range(8):
        missing_lower = active & (lower_residual < 0.0)
        missing_upper = active & (upper_residual > 0.0)
        if not np.any(missing_lower | missing_upper):
            break
        span = upper - lower
        lower = np.where(missing_lower, lower - span, lower)
        upper = np.where(missing_upper, upper + span, upper)
        lower_residual, upper_residual = (evaluate(lower), evaluate(upper))
    if np.any(active & ((lower_residual < 0.0) | (upper_residual > 0.0))):
        raise RuntimeError('failed to bracket ambipolar potential')
    potential = 0.5 * (lower + upper)
    converged = not np.any(active)
    iterations = 0
    current_residual = upper_residual
    for iterations in range(1, iterations_limit + 1):
        current_residual = evaluate(potential)
        lower = np.where(active & (current_residual > 0.0), potential, lower)
        upper = np.where(active & (current_residual <= 0.0), potential, upper)
        next_potential = np.where(active, 0.5 * (lower + upper), phi_ref)
        if not np.any(active) or (np.max(np.abs(next_potential[active] - potential[active])) <= tolerance and np.max(np.abs(current_residual[active])) <= residual_tolerance):
            potential, converged = (next_potential, True)
            break
        potential = next_potential
    if not converged:
        raise RuntimeError('ambipolar potential solve did not converge')
    return {'potential_v': potential, 'logarithmic_charge_residual': evaluate(potential), 'iterations': iterations, 'converged': bool(converged)}
__all__ = ['solve_quasineutral_potential']

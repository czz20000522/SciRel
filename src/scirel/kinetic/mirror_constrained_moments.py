"""Integrate density and gyrotropic pressures of an invariant mirror distribution."""
import numpy as np
from ._mirror_numerics import _trapped_fractions, _density_exponential, _positive_product, _scaled_difference
def _field(value, psi, name):
    if callable(value):
        value = value(np.asarray(psi, dtype=float))
    values = np.asarray(value, dtype=float)
    try:
        values = np.broadcast_to(values, np.shape(psi))
    except ValueError as exc:
        raise ValueError(f'{name} cannot be broadcast over psi') from exc
    if not np.all(np.isfinite(values)):
        raise ValueError(f'{name} must be finite')
    return values

def evaluate_mirror_constrained_moments(b_t, psi, potential_v, mass_kg, charge_c, density_ref_m3, temperature_parallel_j, temperature_perpendicular_ref_j, b_ref_t, phi_ref_v=0.0, b_plug_left_t=None, b_plug_right_t=None, phi_plug_left_v=0.0, phi_plug_right_v=0.0, loss_cone_refill=0.0, quadrature_order=32):
    """Return density and gyrotropic pressure moments of an invariant bi-Maxwellian.

    When both plug fields are supplied, the source's two-barrier pitch integral
    removes unconfined particles; ``loss_cone_refill=1`` restores the full
    bi-Maxwellian.  All profiles are explicit scalar or array inputs. The loss-cone fractions
    use analytic magnetic-only limits or error-controlled quadrature
    (absolute 2e-13, relative 2e-11); quadrature_order controls work budget.
    Potential differences are formed before species scaling, including binary
    scaling when an intermediate subtraction/product exceeds floating-point
    range. Nonfinite/unrepresentable states fail explicitly instead of exponent clipping.
    """
    mass = float(mass_kg)
    charge = float(charge_c)
    refill = float(loss_cone_refill)
    order_value = float(quadrature_order)
    if not np.isfinite(mass) or mass <= 0.0 or (not np.isfinite(charge)) or (charge == 0.0):
        raise ValueError('mass_kg and charge_c must be finite; mass must be positive and charge must be non-zero')
    if not np.isfinite(refill) or not 0.0 <= refill <= 1.0 or (not np.isfinite(order_value)) or (int(order_value) < 8):
        raise ValueError('loss_cone_refill must be finite in [0,1] and quadrature_order must be finite with int value at least 8')
    if (b_plug_left_t is None) != (b_plug_right_t is None):
        raise ValueError('both left and right plug fields are required')
    b_t, psi, potential_v = np.broadcast_arrays(np.asarray(b_t, dtype=float), np.asarray(psi, dtype=float), np.asarray(potential_v, dtype=float))
    if not all((np.all(np.isfinite(value)) for value in (b_t, psi, potential_v))) or np.any(b_t <= 0.0):
        raise ValueError('b_t, psi, and potential_v must be finite; b_t must be positive')
    density_ref = _field(density_ref_m3, psi, 'density_ref_m3')
    t_parallel = _field(temperature_parallel_j, psi, 'temperature_parallel_j')
    t_perpendicular_ref = _field(temperature_perpendicular_ref_j, psi, 'temperature_perpendicular_ref_j')
    b_ref = _field(b_ref_t, psi, 'b_ref_t')
    phi_ref = _field(phi_ref_v, psi, 'phi_ref_v')
    if np.any(density_ref < 0.0) or np.any(t_parallel <= 0.0) or np.any(t_perpendicular_ref <= 0.0) or np.any(b_ref <= 0.0):
        raise ValueError('reference density/temperatures/field are invalid')
    coefficient = (b_t - b_ref) / t_parallel + b_ref / t_perpendicular_ref
    if np.any(coefficient <= 0.0):
        raise FloatingPointError('invariant bi-Maxwellian is not integrable')
    t_perpendicular_local = b_t / coefficient
    exponent = -_scaled_difference(potential_v,phi_ref,charge,t_parallel)
    density_full = _density_exponential(density_ref, t_perpendicular_local / t_perpendicular_ref, exponent)
    density_integral = np.ones_like(b_t)
    parallel_integral = np.ones_like(b_t)
    perpendicular_integral = np.ones_like(b_t)
    if b_plug_left_t is not None and loss_cone_refill != 1.0:
        b_left = _field(b_plug_left_t, psi, 'b_plug_left_t')
        b_right = _field(b_plug_right_t, psi, 'b_plug_right_t')
        phi_left = _field(phi_plug_left_v, psi, 'phi_plug_left_v')
        phi_right = _field(phi_plug_right_v, psi, 'phi_plug_right_v')
        if np.any(b_left <= 0.0) or np.any(b_right <= 0.0):
            raise ValueError('plug magnetic fields must be positive')
        alpha_left = (b_left - b_t) / (coefficient * t_parallel)
        alpha_right = (b_right - b_t) / (coefficient * t_parallel)
        beta_left = _scaled_difference(phi_left,potential_v,charge,t_parallel)
        beta_right = _scaled_difference(phi_right,potential_v,charge,t_parallel)
        density_integral, parallel_integral, perpendicular_integral = _trapped_fractions(
            alpha_left, beta_left, alpha_right, beta_right, int(order_value))
        density_integral = refill + (1.0-refill)*density_integral
        parallel_integral = refill + (1.0-refill)*parallel_integral
        perpendicular_integral = refill + (1.0-refill)*perpendicular_integral
    final_moments = (_positive_product(density_full,density_integral),
        _positive_product(density_full,t_parallel,parallel_integral),
        _positive_product(density_full,t_perpendicular_local,perpendicular_integral))
    return {'density_m3': final_moments[0], 'p_parallel_pa': final_moments[1], 'p_perpendicular_pa': final_moments[2], 'temperature_parallel_j': t_parallel, 'temperature_perpendicular_local_j': t_perpendicular_local, 'untruncated_density_m3': density_full, 'density_pitch_integral': density_integral, 'parallel_pitch_integral': parallel_integral, 'perpendicular_pitch_integral': perpendicular_integral}
__all__ = ['evaluate_mirror_constrained_moments']

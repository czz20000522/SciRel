"""Gyrotropic bi-Maxwellian mirror moments with optional end-loss cones."""
import math
import numpy as np
from scipy.special import erf
_SOURCE_LEGENDRE_16 = (np.asarray([-0.9894009349916499, -0.9445750230732326, -0.8656312023878318, -0.755404408355003, -0.6178762444026438, -0.45801677765722737, -0.2816035507792589, -0.09501250983763745, 0.09501250983763745, 0.2816035507792589, 0.45801677765722737, 0.6178762444026438, 0.755404408355003, 0.8656312023878318, 0.9445750230732326, 0.9894009349916499]), np.asarray([0.027152459411754037, 0.062253523938647706, 0.09515851168249259, 0.12462897125553403, 0.14959598881657676, 0.16915651939500262, 0.1826034150449236, 0.18945061045506859, 0.18945061045506859, 0.1826034150449236, 0.16915651939500262, 0.14959598881657676, 0.12462897125553403, 0.09515851168249259, 0.062253523938647706, 0.027152459411754037]))

def _legendre_quadrature(order):
    """Keep the source-runtime coefficients stable for the shipped order."""
    if int(order) == 16:
        return (_SOURCE_LEGENDRE_16[0].copy(), _SOURCE_LEGENDRE_16[1].copy())
    return np.polynomial.legendre.leggauss(int(order))

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
    bi-Maxwellian.  All profiles are explicit scalar or array inputs.
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
    exponent = np.clip(-charge_c * (potential_v - phi_ref) / t_parallel, -700.0, 700.0)
    density_full = density_ref * (t_perpendicular_local / t_perpendicular_ref) * np.exp(exponent)
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
        beta_left = charge_c * (phi_left - potential_v) / t_parallel
        beta_right = charge_c * (phi_right - potential_v) / t_parallel
        epsilon, cutoff = (np.finfo(float).eps, 40.0)
        root_left = np.divide(-beta_left, alpha_left, out=np.zeros_like(beta_left), where=np.abs(alpha_left) > epsilon)
        root_right = np.divide(-beta_right, alpha_right, out=np.zeros_like(beta_right), where=np.abs(alpha_right) > epsilon)
        delta_alpha = alpha_left - alpha_right
        intersection = np.divide(-(beta_left - beta_right), delta_alpha, out=np.zeros_like(beta_left), where=np.abs(delta_alpha) > epsilon)
        boundaries = np.sort(np.stack((np.zeros_like(b_t), np.clip(root_left, 0.0, cutoff), np.clip(root_right, 0.0, cutoff), np.clip(intersection, 0.0, cutoff), np.full_like(b_t, cutoff)), axis=0), axis=0)
        lower, upper = (boundaries[:-1], boundaries[1:])
        half_width, midpoint = (0.5 * (upper - lower), 0.5 * (upper + lower))
        nodes, weights = _legendre_quadrature(quadrature_order)
        node_shape = (1, int(quadrature_order)) + (1,) * b_t.ndim
        x = midpoint[:, np.newaxis, ...] + half_width[:, np.newaxis, ...] * nodes.reshape(node_shape)
        integration_weights = half_width[:, np.newaxis, ...] * weights.reshape(node_shape)
        barrier_left = alpha_left[np.newaxis, np.newaxis, ...] * x + beta_left[np.newaxis, np.newaxis, ...]
        barrier_right = alpha_right[np.newaxis, np.newaxis, ...] * x + beta_right[np.newaxis, np.newaxis, ...]
        y = np.maximum(np.minimum(barrier_left, barrier_right), 0.0)
        root_y = np.sqrt(y)
        density_fraction = erf(root_y)
        parallel_fraction = density_fraction - 2.0 / math.sqrt(math.pi) * root_y * np.exp(-y)
        density_fraction = loss_cone_refill + (1.0 - loss_cone_refill) * density_fraction
        parallel_fraction = loss_cone_refill + (1.0 - loss_cone_refill) * parallel_fraction
        exponential_weight = integration_weights * np.exp(-x)
        density_integral = np.sum(exponential_weight * density_fraction, axis=(0, 1))
        parallel_integral = np.sum(exponential_weight * parallel_fraction, axis=(0, 1))
        perpendicular_integral = np.sum(exponential_weight * x * density_fraction, axis=(0, 1))
    return {'density_m3': density_full * density_integral, 'p_parallel_pa': density_full * t_parallel * parallel_integral, 'p_perpendicular_pa': density_full * t_perpendicular_local * perpendicular_integral, 'temperature_parallel_j': t_parallel, 'temperature_perpendicular_local_j': t_perpendicular_local, 'untruncated_density_m3': density_full, 'density_pitch_integral': density_integral, 'parallel_pitch_integral': parallel_integral, 'perpendicular_pitch_integral': perpendicular_integral}
__all__ = ['evaluate_mirror_constrained_moments']

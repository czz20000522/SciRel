"""Velocity--pitch hot-ion moments for Frank--Egedal closure."""
import math
import numpy as np

def _mode_sum(xi0, speed, degrees, coefficients, vc, beta_m, n_terms, fractional_mode):
    u = np.power(np.clip((1.0 + vc ** 3) / (speed ** 3 + vc ** 3) * speed ** 3, 0.0, None), beta_m / 3.0)
    total = np.zeros(np.broadcast_shapes(np.shape(xi0), np.shape(speed)), dtype=float)
    for degree, coefficient in zip(degrees, coefficients):
        total += coefficient * fractional_mode(degree, xi0, n_terms) * np.power(u, degree * (degree + 1.0))
    return total

def evaluate_frank_egedal_hot_ion_moments(magnetic_field, params, degrees, source_coefficients, legendre_terms, fractional_mode):
    """Integrate hot moments at each B and normalize all shapes at b=1."""
    magnetic_field = np.asarray(magnetic_field, dtype=float)
    if magnetic_field.ndim != 2 or not np.all(np.isfinite(magnetic_field)):
        raise ValueError('B must be a finite two-dimensional [Z,R] grid')
    reference = float(params.get('B0', np.nanmedian(magnetic_field)))
    if not np.isfinite(reference) or reference <= 0.0 or np.any(magnetic_field <= 0.0):
        raise ValueError('B and B0 must be finite and strictly positive')
    normalized_field = magnetic_field / reference
    mirror_ratio = float(params.get('mirror_ratio', params.get('turning_b', 2.0)))
    if not np.isfinite(mirror_ratio) or mirror_ratio <= 1.0:
        raise ValueError('mirror_ratio must be finite and greater than one')
    xi_tp_mid = math.sqrt(1.0 - 1.0 / mirror_ratio)
    vc = float(params.get('vc_over_v0', 0.25))
    if not np.isfinite(vc) or vc < 0.0:
        raise ValueError('vc_over_v0 must be finite and nonnegative')
    perp_lower = float(params.get('perp_velocity_lower', vc))
    if not 0.0 <= perp_lower <= 1.0:
        raise ValueError('perp_velocity_lower must be between 0 and 1')
    beta_m = float(params.get('beta_m', params.get('zeff', 1.0) / 2.0))
    velocity_nodes = int(params.get('velocity_nodes', 24))
    pitch_nodes = int(params.get('pitch_nodes', 24))
    if not np.isfinite(beta_m) or velocity_nodes < 2 or pitch_nodes < 2:
        raise ValueError('beta_m must be finite and quadrature nodes must be at least two')
    degrees, source_coefficients = (np.asarray(degrees, dtype=float), np.asarray(source_coefficients, dtype=float))
    if degrees.ndim != 1 or source_coefficients.shape != degrees.shape or (not np.all(np.isfinite(degrees))) or (not np.all(np.isfinite(source_coefficients))):
        raise ValueError('degrees and source_coefficients must be finite one-dimensional arrays of equal length')

    def integrals(b):
        xi_tp_loc = math.sqrt(max(0.0, 1.0 - float(b) / max(mirror_ratio, 1e-12)))
        if xi_tp_loc <= 0.0 or xi_tp_mid <= 0.0:
            return (0.0, 0.0, 0.0)
        speed_nodes, speed_weights = np.polynomial.legendre.leggauss(velocity_nodes)
        speed, speed_weights = (0.5 * (speed_nodes + 1.0), 0.5 * speed_weights)
        pitch_nodes_raw, pitch_weights = np.polynomial.legendre.leggauss(pitch_nodes)
        xi, pitch_weights = (0.5 * xi_tp_loc * (pitch_nodes_raw + 1.0), 0.5 * xi_tp_loc * pitch_weights)
        speed_2d, xi_2d = (speed[:, None], xi[None, :])
        xi0 = np.sqrt(np.clip((xi_2d * xi_2d - (1.0 - b)) / b, 0.0, xi_tp_mid * xi_tp_mid))
        distribution = np.maximum(_mode_sum(xi0, speed_2d, degrees, source_coefficients, vc, beta_m, legendre_terms, fractional_mode) / np.maximum(speed_2d ** 3 + vc ** 3, 1e-30), 0.0)
        weights = speed_weights[:, None] * pitch_weights[None, :]
        parallel = 4.0 * math.pi * np.sum(weights * speed_2d ** 4 * xi_2d ** 2 * distribution)
        density = 4.0 * math.pi * np.sum(weights * speed_2d ** 2 * distribution)
        if perp_lower >= 1.0:
            perpendicular = 0.0
        else:
            perp_speed = 0.5 * ((1.0 - perp_lower) * speed_nodes + (1.0 + perp_lower))
            perp_weights = (1.0 - perp_lower) * speed_weights
            perp_2d = perp_speed[:, None]
            perp_distribution = np.maximum(_mode_sum(xi0, perp_2d, degrees, source_coefficients, vc, beta_m, legendre_terms, fractional_mode) / np.maximum(perp_2d ** 3 + vc ** 3, 1e-30), 0.0)
            perpendicular = 2.0 * math.pi * np.sum(perp_weights[:, None] * pitch_weights[None, :] * perp_2d ** 4 * (1.0 - xi_2d ** 2) * perp_distribution)
        return tuple((float(max(value, 0.0)) for value in (parallel, perpendicular, density)))
    cache = {}
    values = []
    for b in normalized_field.ravel():
        key = round(float(b), 12)
        values.append(cache.setdefault(key, integrals(float(b))))
    parallel, perpendicular, density = (np.asarray([value[index] for value in values]).reshape(normalized_field.shape) for index in range(3))
    midplane = integrals(1.0)
    return {'normalized_field': normalized_field, 'xi_tp_mid': xi_tp_mid, 'hot_parallel_shape': parallel / max(midplane[0], 1e-30), 'hot_perpendicular_shape': perpendicular / max(midplane[0], 1e-30), 'hot_density_shape': density / max(midplane[2], 1e-30), 'quadrature': {'velocity_nodes': velocity_nodes, 'pitch_nodes': pitch_nodes}}
__all__ = ['evaluate_frank_egedal_hot_ion_moments']

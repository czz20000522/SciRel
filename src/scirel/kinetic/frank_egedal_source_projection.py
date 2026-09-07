"""Fractional-Legendre source-mode projection for Frank--Egedal closure."""
import math
import numpy as np
from scipy.special import hyp2f1

def _fractional_legendre_p(degree, xi, n_terms, backend='truncated'):
    xi = np.asarray(xi, dtype=float)
    if backend == 'hypergeometric':
        return hyp2f1(-float(degree), float(degree) + 1.0, 1.0, (1.0 - xi) / 2.0)
    z = np.clip((1.0 - xi) / 2.0, 0.0, 1.0)
    result = np.ones_like(z, dtype=float)
    coefficient = 1.0
    for order in range(1, int(n_terms)):
        coefficient *= (-degree + order - 1.0) * (degree + order) / (order * order)
        result = result + coefficient * np.power(z, order)
    return result

def _fractional_legendre_q(degree, xi, n_terms, backend='truncated'):
    degree = float(degree)
    sine = math.sin(math.pi * degree)
    if abs(sine) < 1e-12:
        raise ValueError('fractional Legendre Q requires non-integer degrees')
    return 0.5 * math.pi / sine * (math.cos(math.pi * degree) * _fractional_legendre_p(degree, xi, n_terms, backend) - _fractional_legendre_p(degree, -np.asarray(xi, dtype=float), n_terms, backend))

def _fractional_mode_coefficients(degree, n_terms, backend='truncated'):
    step = 1e-05
    p0 = float(_fractional_legendre_p(degree, 0.0, n_terms, backend))
    q0 = float(_fractional_legendre_q(degree, 0.0, n_terms, backend))
    dp0 = float((_fractional_legendre_p(degree, step, n_terms, backend) - _fractional_legendre_p(degree, -step, n_terms, backend)) / (2.0 * step))
    dq0 = float((_fractional_legendre_q(degree, step, n_terms, backend) - _fractional_legendre_q(degree, -step, n_terms, backend)) / (2.0 * step))
    return np.linalg.solve(np.array([[p0, q0], [dp0, dq0]], dtype=float), np.array([1.0, 0.0]))

def fractional_mode(degree, xi, n_terms, backend='truncated'):
    a_coeff, b_coeff = _fractional_mode_coefficients(float(degree), n_terms, backend)
    return a_coeff * _fractional_legendre_p(degree, xi, n_terms, backend) + b_coeff * _fractional_legendre_q(degree, xi, n_terms, backend)

def project_frank_egedal_source_modes(params, spectrum_operator=None):
    """Select fractional degrees and project the NBI source onto them."""
    if not isinstance(params, dict):
        raise ValueError('params must be a mapping')
    mirror_ratio = float(params.get('mirror_ratio', params.get('turning_b', 2.0)))
    xi_tp_mid = math.sqrt(max(0.0, 1.0 - 1.0 / max(mirror_ratio, 1e-12)))
    if xi_tp_mid <= 0.0:
        return {'degrees': np.empty(0), 'source_coefficients': np.empty(0), 'degree_source': 'inactive_loss_cone', 'legendre_terms': int(params.get('legendre_terms', 15)), 'xi_tp_mid': xi_tp_mid, 'fractional_mode': fractional_mode}
    n_terms = int(params.get('legendre_terms', 15))
    backend = str(params.get('legendre_backend', 'truncated'))
    if backend not in {'truncated', 'hypergeometric'}:
        raise ValueError('legendre_backend must be truncated or hypergeometric')
    explicit = params.get('legendre_degrees')
    if explicit is not None:
        degrees = np.asarray(explicit, dtype=float)
        if degrees.ndim != 1 or degrees.size == 0 or (not np.all(np.isfinite(degrees))):
            raise ValueError('legendre_degrees must be a non-empty finite one-dimensional array')
        degree_source = 'caller_supplied'
    else:
        if spectrum_operator is None:
            raise ValueError('spectrum_operator is required when legendre_degrees is absent')
        spectrum = spectrum_operator(xi_tp_mid, int(params.get('legendre_mode_count', 6)), int(params.get('legendre_spectrum_grid_points', 256)), backend)
        degrees = np.asarray(spectrum['degrees'], dtype=float)
        if degrees.ndim != 1 or degrees.size == 0 or (not np.all(np.isfinite(degrees))):
            raise ValueError('spectrum_operator must return a non-empty finite one-dimensional degrees array')
        degree_source = 'scirel.kinetic.loss_cone_spectrum'
    if n_terms < 2:
        raise ValueError('legendre_terms must be at least two')
    explicit_coefficients = params.get('source_coefficients')
    if explicit_coefficients is not None:
        coefficients = np.asarray(explicit_coefficients, dtype=float)
        if coefficients.shape != degrees.shape or not np.all(np.isfinite(coefficients)):
            raise ValueError('source_coefficients must be finite and match legendre_degrees')
    else:
        pitch_angle_degrees = float(params.get('nbi_pitch_angle_deg', 45.0))
        xi_nbi = float(np.clip(math.cos(math.radians(pitch_angle_degrees)), 0.0, xi_tp_mid))
        nodes, weights = np.polynomial.legendre.leggauss(64)
        xi = 0.5 * xi_tp_mid * (nodes + 1.0)
        quadrature_weights = 0.5 * xi_tp_mid * weights
        coefficients = np.asarray([float(fractional_mode(degree, xi_nbi, n_terms, backend)) / max(4.0 * math.pi * float(np.sum(quadrature_weights * fractional_mode(degree, xi, n_terms, backend) ** 2)), 1e-30) for degree in degrees])
    return {'degrees': degrees, 'source_coefficients': coefficients, 'degree_source': degree_source, 'legendre_terms': n_terms, 'legendre_backend': backend, 'xi_tp_mid': xi_tp_mid, 'fractional_mode': lambda degree, xi, terms: fractional_mode(degree, xi, terms, backend)}
__all__ = ['project_frank_egedal_source_modes']

"""Fractional-Legendre source-mode projection for Frank--Egedal closure."""
import math
import numpy as np

from ._loss_cone_modes import regular_even_mode
from scipy.special import roots_legendre


def fractional_mode(degree, xi, n_terms, backend='truncated'):
    """Regular even angular mode; legacy n_terms does not truncate the solution."""
    if backend not in {'truncated', 'hypergeometric'}:
        raise ValueError('legendre_backend must be truncated or hypergeometric')
    if int(n_terms) != n_terms or n_terms < 2:
        raise ValueError('legendre_terms must be an integer of at least two')
    return regular_even_mode(degree, xi)


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
        coefficients = []
        for degree in degrees:
            previous = None
            start_nodes = 2**int(np.ceil(np.log2(max(32.,8*np.sqrt(degree*(degree+1))*np.arcsin(xi_tp_mid)/np.pi))))
            for node_count in (start_nodes*2**i for i in range(8)):
                if node_count > 8192:
                    raise RuntimeError('source-mode normalization requires unresolved angular resolution')
                nodes, weights = roots_legendre(node_count)
                values = fractional_mode(degree, .5*xi_tp_mid*(nodes+1.), n_terms, backend)
                norm = .5*xi_tp_mid*float(np.dot(weights, values*values))
                if previous is not None and abs(norm-previous) <= 1e-10*abs(norm):
                    break
                previous = norm
            else:
                raise RuntimeError('source-mode normalization quadrature failed to converge')
            if not np.isfinite(norm) or norm <= 0.0:
                raise RuntimeError('source-mode normalization is not finite and positive')
            coefficients.append(float(fractional_mode(degree, xi_nbi, n_terms, backend))/(4*math.pi*norm))
        coefficients = np.asarray(coefficients)
    return {'degrees': degrees, 'source_coefficients': coefficients, 'degree_source': degree_source, 'legendre_terms': n_terms, 'legendre_backend': backend, 'xi_tp_mid': xi_tp_mid, 'fractional_mode': lambda degree, xi, terms: fractional_mode(degree, xi, terms, backend)}
__all__ = ['project_frank_egedal_source_modes']

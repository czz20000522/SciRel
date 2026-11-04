"""Truncated-SVD ideal-conductor boundary flux correction from SciRel."""
import numpy as np

def _finite_array(name, value, ndim):
    array = np.asarray(value, dtype=float)
    if array.ndim != ndim:
        raise ValueError(f'{name} must be a {ndim}-D array')
    if not np.all(np.isfinite(array)):
        raise ValueError(f'{name} must contain only finite values')
    return array

def correct_ideal_conductor_boundary_flux(uncorrected_field_flux, boundary_sample_matrix, green_boundary_to_boundary, green_boundary_to_field, rcond=1e-10):
    """Cancel sampled boundary flux and return the corrected field-flux vector."""
    field_flux = _finite_array('uncorrected_field_flux', uncorrected_field_flux, 1)
    sample_matrix = _finite_array('boundary_sample_matrix', boundary_sample_matrix, 2)
    g_boundary = _finite_array('green_boundary_to_boundary', green_boundary_to_boundary, 2)
    g_field = _finite_array('green_boundary_to_field', green_boundary_to_field, 2)
    if not np.isfinite(rcond) or rcond < 0.0:
        raise ValueError('rcond must be a non-negative finite value')
    if sample_matrix.shape[1] != field_flux.size:
        raise ValueError('boundary_sample_matrix column count must match uncorrected_field_flux')
    if g_boundary.shape[0] != sample_matrix.shape[0]:
        raise ValueError('green_boundary_to_boundary row count must match boundary samples')
    if g_field.shape[1] != g_boundary.shape[1]:
        raise ValueError('green_boundary_to_field must use the same boundary-source axis')
    if g_field.shape[0] != field_flux.size:
        raise ValueError('green_boundary_to_field row count must match uncorrected_field_flux')
    if g_boundary.size == 0:
        raise ValueError('green_boundary_to_boundary must not be empty')
    boundary_flux = sample_matrix @ field_flux
    left, singular_values, right_t = np.linalg.svd(g_boundary, full_matrices=False)
    cutoff = rcond * singular_values[0]
    keep = singular_values > cutoff
    inverse = np.zeros_like(singular_values)
    inverse[keep] = 1.0 / singular_values[keep]
    pseudo_inverse = right_t.T @ (inverse[:, None] * left.T)
    boundary_currents = pseudo_inverse @ -boundary_flux
    boundary_flux_correction = g_boundary @ boundary_currents
    field_flux_correction = g_field @ boundary_currents
    residual = boundary_flux + boundary_flux_correction
    return {'corrected_field_flux': field_flux + field_flux_correction, 'boundary_currents': boundary_currents, 'boundary_flux_correction': boundary_flux_correction, 'field_flux_correction': field_flux_correction, 'singular_values': singular_values, 'effective_rank': int(np.count_nonzero(keep)), 'residual': residual, 'residual_norm': float(np.linalg.norm(residual))}
__all__ = ['correct_ideal_conductor_boundary_flux']

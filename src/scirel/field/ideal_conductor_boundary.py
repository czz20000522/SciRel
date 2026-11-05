"""Finite-dimensional ideal-conductor boundary correction."""

import numpy as np


def _finite_array(name, value, ndim):
    array = np.asarray(value, dtype=float)
    if array.ndim != ndim:
        raise ValueError(f"{name} must be a {ndim}-D array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def correct_ideal_conductor_boundary_flux(
    uncorrected_field_flux,
    boundary_sample_matrix,
    green_boundary_to_boundary,
    green_boundary_to_field,
    rcond=1e-10,
):
    """Cancel sampled boundary flux with a truncated-SVD source solve."""
    field_flux = _finite_array("uncorrected_field_flux", uncorrected_field_flux, 1)
    samples = _finite_array("boundary_sample_matrix", boundary_sample_matrix, 2)
    boundary_green = _finite_array("green_boundary_to_boundary", green_boundary_to_boundary, 2)
    field_green = _finite_array("green_boundary_to_field", green_boundary_to_field, 2)
    if not np.isfinite(rcond) or rcond < 0.0:
        raise ValueError("rcond must be a non-negative finite value")
    if samples.shape[1] != field_flux.size:
        raise ValueError("boundary_sample_matrix column count must match uncorrected_field_flux")
    if boundary_green.shape[0] != samples.shape[0]:
        raise ValueError("green_boundary_to_boundary row count must match boundary samples")
    if field_green.shape[1] != boundary_green.shape[1]:
        raise ValueError("green_boundary_to_field must use the same boundary-source axis")
    if field_green.shape[0] != field_flux.size:
        raise ValueError("green_boundary_to_field row count must match uncorrected_field_flux")
    if boundary_green.size == 0:
        raise ValueError("green_boundary_to_boundary must not be empty")

    boundary_flux = samples @ field_flux
    left, singular_values, right_transpose = np.linalg.svd(boundary_green, full_matrices=False)
    keep = singular_values > rcond * singular_values[0]
    reciprocal = np.zeros_like(singular_values)
    reciprocal[keep] = 1.0 / singular_values[keep]
    pseudo_inverse = right_transpose.T @ (reciprocal[:, None] * left.T)
    boundary_currents = pseudo_inverse @ -boundary_flux
    boundary_correction = boundary_green @ boundary_currents
    field_correction = field_green @ boundary_currents
    residual = boundary_flux + boundary_correction
    return {
        "corrected_field_flux": field_flux + field_correction,
        "boundary_currents": boundary_currents,
        "boundary_flux_correction": boundary_correction,
        "field_flux_correction": field_correction,
        "singular_values": singular_values,
        "effective_rank": int(np.count_nonzero(keep)),
        "residual": residual,
        "residual_norm": float(np.linalg.norm(residual)),
    }


__all__ = ["correct_ideal_conductor_boundary_flux"]

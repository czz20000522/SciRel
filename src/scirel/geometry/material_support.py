"""Classify closed-flux material support on a Cartesian solver grid."""
from __future__ import annotations

import math

import numpy as np

__all__ = ["ALLOWED_CLOSED_FLUX_SIDES", "classify_material_support"]
ALLOWED_CLOSED_FLUX_SIDES = ("less_than", "greater_than")


def _coordinate_array(value, name, shape):
    result = np.asarray(value, dtype=float)
    if result.shape != shape:
        raise ValueError(f"{name} must match the poloidal flux shape {shape}")
    if not np.isfinite(result).all():
        raise ValueError(f"{name} must be finite")
    return result


def _positive_integer(value, name):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"{name} must be a positive integer cell count")
    try:
        integer = int(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{name} must be a positive integer cell count") from None
    if integer != value:
        raise ValueError(f"{name} must be a positive integer cell count")
    if integer < 1:
        raise ValueError(
            "pml_cells must be a positive integer; a zero frame thickness is not a "
            "defined exclusion and the retained slice form silently excluded the "
            "whole solver box"
        )
    return integer


def classify_material_support(
    poloidal_flux_wb_per_rad,
    covered_mask,
    radii_m,
    axial_coordinate_m,
    *,
    separatrix_flux_wb_per_rad,
    closed_flux_side,
    xpoint_half_length_m,
    pml_cells,
    pec_mask,
):
    """Return closed-flux, axis-segment, and material-support masks."""
    flux = np.asarray(poloidal_flux_wb_per_rad, dtype=float)
    if flux.ndim != 3:
        raise ValueError("poloidal_flux_wb_per_rad must be a 3D array")
    shape = flux.shape
    if not np.isfinite(flux).all():
        raise ValueError("poloidal_flux_wb_per_rad must be finite")
    covered = np.asarray(covered_mask, dtype=bool)
    if covered.shape != shape:
        raise ValueError(f"covered_mask must match the poloidal flux shape {shape}")
    radius = _coordinate_array(radii_m, "radii_m", shape)
    if np.any(radius < 0.0):
        raise ValueError("radii_m must be non-negative")
    axial = _coordinate_array(axial_coordinate_m, "axial_coordinate_m", shape)
    separatrix = float(separatrix_flux_wb_per_rad)
    if not math.isfinite(separatrix):
        raise ValueError("separatrix_flux_wb_per_rad must be finite")
    side = str(closed_flux_side)
    if side not in ALLOWED_CLOSED_FLUX_SIDES:
        raise ValueError("closed_flux_side must be less_than or greater_than")
    half_length = float(xpoint_half_length_m)
    if not math.isfinite(half_length) or half_length <= 0.0:
        raise ValueError("xpoint_half_length_m must be finite and strictly positive")
    thickness = _positive_integer(pml_cells, "pml_cells")
    pec = np.asarray(pec_mask, dtype=bool)
    if pec.shape != shape:
        raise ValueError(f"pec_mask must match the solver grid shape {shape}")

    if side == "less_than":
        closed = covered & (flux < separatrix)
    else:
        closed = covered & (flux > separatrix)
    axis = covered & np.isclose(radius, np.min(radius), rtol=0.0, atol=1.0e-15)
    axis &= np.abs(axial) < half_length

    interior = np.ones(shape, dtype=bool)
    interior[:thickness] = False
    interior[-thickness:] = False
    interior[:, :thickness] = False
    interior[:, -thickness:] = False
    interior[:, :, :thickness] = False
    interior[:, :, -thickness:] = False
    support = (closed | axis) & interior & ~pec
    if not np.any(support):
        raise ValueError(
            "material support classification is empty: the selected closed-flux side, "
            "the innermost-radius segment, the PML frame, and the PEC mask leave no "
            "grid point with cold-plasma support"
        )
    return {
        "material_support_mask": support,
        "closed_flux_mask": closed,
        "axis_segment_mask": axis,
    }

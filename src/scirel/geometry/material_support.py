"""Closed-flux and magnetic-axis material-support classification.

This is the second of the two scientific relations that the retained coarse-CAD
full-wave entry performs before any field solve.  Given the poloidal flux already
sampled on a solver grid, the cylindrical coordinates of that grid, and the
caller-owned PML frame and PEC mask, it decides which grid points carry
cold-plasma material support:

    support = (closed_flux | axis_segment) & non_pml & ~pec

``closed_flux`` is the side of the separatrix flux named by the caller.  The
``axis_segment`` term marks the innermost radius present on the grid, restricted
to the poloidal half length around the midplane; it coincides with the magnetic
axis only when the grid actually contains r = 0, and the retained relation
intersects it with ``covered`` as well, so it can only add points when the
equilibrium map's radial axis begins at the grid's minimum radius.

The PML frame is excluded on all six faces of the solver box.  ``pml_cells`` is
required to be a positive integer: the retained implementation expressed the
exclusion as slice assignments, and a frame thickness of zero made every one of
those slices cover the whole box, so a call with ``pml_cells = 0`` could never
produce support.  Rejecting a zero thickness turns that silent total exclusion
into an explicit invalid-input error rather than a misleading downstream one.
"""
from __future__ import annotations

import math

import numpy as np

__all__ = ["ALLOWED_CLOSED_FLUX_SIDES", "classify_material_support"]

ALLOWED_CLOSED_FLUX_SIDES = ("less_than", "greater_than")


def _coordinate_array(value, name, shape):
    array = np.asarray(value, dtype=float)
    if array.shape != shape:
        raise ValueError(f"{name} must match the poloidal flux shape {shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite")
    return array


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
    """Classify cold-plasma material support on a Cartesian solver grid.

    The flux, the two coordinate arrays, the coverage mask, and the PEC mask are
    all caller-owned and must share one shape.  The result is fail-closed: an
    empty support mask is an error, because a solve with no cold-plasma material
    is not a result of this relation.
    """
    flux = np.asarray(poloidal_flux_wb_per_rad, dtype=float)
    if flux.ndim != 3:
        raise ValueError("poloidal_flux_wb_per_rad must be a 3D array")
    shape = flux.shape
    if not np.all(np.isfinite(flux)):
        raise ValueError("poloidal_flux_wb_per_rad must be finite")

    covered = np.asarray(covered_mask, dtype=bool)
    if covered.shape != shape:
        raise ValueError(f"covered_mask must match the poloidal flux shape {shape}")

    radii = _coordinate_array(radii_m, "radii_m", shape)
    if np.any(radii < 0.0):
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

    if isinstance(pml_cells, bool):
        raise ValueError("pml_cells must be a positive integer cell count")
    try:
        thickness = int(pml_cells)
    except (TypeError, ValueError):
        raise ValueError("pml_cells must be a positive integer cell count") from None
    if thickness != pml_cells:
        raise ValueError("pml_cells must be a positive integer cell count")
    if thickness < 1:
        raise ValueError(
            "pml_cells must be a positive integer; a zero frame thickness is not a "
            "defined exclusion and the retained slice form silently excluded the "
            "whole solver box"
        )

    pec = np.asarray(pec_mask, dtype=bool)
    if pec.shape != shape:
        raise ValueError(f"pec_mask must match the solver grid shape {shape}")

    if side == "less_than":
        closed = covered & (flux < separatrix)
    else:
        closed = covered & (flux > separatrix)

    axis_radius = float(np.min(radii))
    axis_segment = covered & np.isclose(radii, axis_radius, rtol=0.0, atol=1.0e-15)
    axis_segment &= np.abs(axial) < half_length

    non_pml = np.ones(shape, dtype=bool)
    non_pml[:thickness, :, :] = False
    non_pml[-thickness:, :, :] = False
    non_pml[:, :thickness, :] = False
    non_pml[:, -thickness:, :] = False
    non_pml[:, :, :thickness] = False
    non_pml[:, :, -thickness:] = False

    support = (closed | axis_segment) & non_pml & ~pec
    if not np.any(support):
        raise ValueError(
            "material support classification is empty: the selected closed-flux side, "
            "the innermost-radius segment, the PML frame, and the PEC mask leave no "
            "grid point with cold-plasma support"
        )

    return {
        "material_support_mask": support,
        "closed_flux_mask": closed,
        "axis_segment_mask": axis_segment,
    }

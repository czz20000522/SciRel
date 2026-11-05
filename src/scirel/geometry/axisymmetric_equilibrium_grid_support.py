"""Compose axisymmetric equilibrium mapping with material classification."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from .axisymmetric_grid_mapping import map_axisymmetric_equilibrium_to_cartesian_grid
from .material_support import classify_material_support

__all__ = ["solve_axisymmetric_equilibrium_grid_mapping"]
_REQUIRED_INPUTS = (
    "equilibrium",
    "x_m",
    "y_m",
    "z_m",
    "xpoint_half_length_m",
    "pml_cells",
    "pec_mask",
)


def _cylindrical_coordinates(x_m, y_m, z_m):
    """Return broadcast views of radius and axial coordinates for a grid."""
    axes = []
    for name, values in (("x_m", x_m), ("y_m", y_m), ("z_m", z_m)):
        axis = np.asarray(values, dtype=float)
        if axis.ndim != 1 or axis.size < 2:
            raise ValueError(f"grid axis {name} must be a 1D array of at least two points")
        axes.append(axis)
    radius_xy = np.hypot(axes[0][:, None], axes[1][None, :])
    shape = (axes[0].size, axes[1].size, axes[2].size)
    radius = np.broadcast_to(radius_xy[..., None], shape)
    axial = np.broadcast_to(axes[2][None, None, :], shape)
    return radius, axial


def _classification_parameters(equilibrium):
    try:
        return equilibrium["separatrix_flux_wb_per_rad"], equilibrium["closed_flux_side"]
    except (KeyError, TypeError) as exc:
        raise ValueError(
            "equilibrium requires separatrix_flux_wb_per_rad and closed_flux_side "
            "for the material-support classification"
        ) from exc


def _run_composition(
    inputs,
    *,
    equilibrium_grid_mapping=map_axisymmetric_equilibrium_to_cartesian_grid,
    material_support_classification=classify_material_support,
):
    """Run mapping followed by material-support classification."""
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be a mapping")
    missing = sorted(set(_REQUIRED_INPUTS).difference(inputs))
    if missing:
        raise ValueError(f"missing required composition inputs: {missing}")
    equilibrium = inputs["equilibrium"]
    if not isinstance(equilibrium, Mapping):
        raise ValueError("equilibrium must be a mapping of caller-owned arrays")

    mapped = equilibrium_grid_mapping(equilibrium, inputs["x_m"], inputs["y_m"], inputs["z_m"])
    radius, axial = _cylindrical_coordinates(inputs["x_m"], inputs["y_m"], inputs["z_m"])
    separatrix, side = _classification_parameters(equilibrium)
    classified = material_support_classification(
        mapped["poloidal_flux_wb_per_rad"],
        mapped["covered_mask"],
        radius,
        axial,
        separatrix_flux_wb_per_rad=separatrix,
        closed_flux_side=side,
        xpoint_half_length_m=inputs["xpoint_half_length_m"],
        pml_cells=inputs["pml_cells"],
        pec_mask=inputs["pec_mask"],
    )
    return {
        "magnetic_flux_density_t": mapped["magnetic_flux_density_t"],
        "poloidal_flux_wb_per_rad": mapped["poloidal_flux_wb_per_rad"],
        "material_support_mask": classified["material_support_mask"],
        "covered_mask": mapped["covered_mask"],
        "radially_clamped_point_count": mapped["radially_clamped_point_count"],
        "axially_clamped_point_count": mapped["axially_clamped_point_count"],
        "closed_flux_mask": classified["closed_flux_mask"],
        "axis_segment_mask": classified["axis_segment_mask"],
    }


def solve_axisymmetric_equilibrium_grid_mapping(inputs=None, **kwargs):
    """Public composition entry point with injectable node implementations."""
    mapping = kwargs.pop("equilibrium_grid_mapping", map_axisymmetric_equilibrium_to_cartesian_grid)
    classification = kwargs.pop("material_support_classification", classify_material_support)
    if kwargs:
        raise ValueError(f"unexpected composition keyword arguments: {sorted(kwargs)}")
    return _run_composition(
        inputs, equilibrium_grid_mapping=mapping, material_support_classification=classification
    )

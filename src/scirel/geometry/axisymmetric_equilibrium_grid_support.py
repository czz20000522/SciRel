"""Ordered composition of the equilibrium mapping and material-support relations.

The retained coarse-CAD full-wave entry owned both relations inside one
scientific operator.  They are independent scientific identities -- the mapping
relation never reads the separatrix flux or the PML frame, and the classification
relation never reads the equilibrium map arrays -- so they are proposed as two
separately reviewable assets, and this TaskGraph is the composition that
reproduces the retained entry's call shape and outputs.

The graph is a pure ordered DAG with no feedback loop: validate the caller's
declarations, reconstruct the static field on the solver grid, build the
cylindrical coordinates of that grid, read the classification parameters off the
equilibrium mapping, classify material support, and return.  Every dependency is
injected as a keyword argument with a default bound to the proposed SciRel
implementation, so the graph imports no source checkout and reads no
configuration file at run time.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from .axisymmetric_grid_mapping import map_axisymmetric_equilibrium_to_cartesian_grid
from .material_support import classify_material_support

__all__ = ["run_graph", "solve_axisymmetric_equilibrium_grid_mapping"]

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
    """Build the cylindrical coordinates of a rectilinear Cartesian grid.

    This is a coordinate transform, not a scientific relation: it validates that
    the three caller-owned axes are one-dimensional and at least two points long,
    then takes the radius and the axial coordinate of every grid point.  The
    ``ij`` indexing and the axis order match the mapping relation's mesh.
    """
    axes = []
    for name, value in (("x_m", x_m), ("y_m", y_m), ("z_m", z_m)):
        array = np.asarray(value, dtype=float)
        if array.ndim != 1 or array.size < 2:
            raise ValueError(f"grid axis {name} must be a 1D array of at least two points")
        axes.append(array)
    # The radius is independent of the axial coordinate, and the axial
    # coordinate is independent of x/y.  Keep those two separable arrays as
    # broadcast views instead of materializing three full 3-D mesh arrays.
    # Consumers only read these coordinates, so the views preserve the
    # numerical contract while avoiding an O(Nx*Ny*Nz) temporary allocation.
    radius_xy = np.hypot(axes[0][:, None], axes[1][None, :])
    shape = (axes[0].size, axes[1].size, axes[2].size)
    return (
        np.broadcast_to(radius_xy[..., None], shape),
        np.broadcast_to(axes[2][None, None, :], shape),
    )


def _classification_parameters(equilibrium):
    """Read the flux-surface classification parameters off the equilibrium mapping.

    This is a field-name adaptation, not a scientific conversion: the two values
    are taken verbatim from the caller's mapping so that the classification
    relation does not have to know the equilibrium mapping's layout.
    """
    try:
        separatrix = equilibrium["separatrix_flux_wb_per_rad"]
        side = equilibrium["closed_flux_side"]
    except (KeyError, TypeError) as exc:
        raise ValueError(
            "equilibrium requires separatrix_flux_wb_per_rad and closed_flux_side "
            "for the material-support classification"
        ) from exc
    return separatrix, side


def run_graph(
    inputs,
    *,
    equilibrium_grid_mapping=map_axisymmetric_equilibrium_to_cartesian_grid,
    material_support_classification=classify_material_support,
):
    """Execute the ordered mapping-then-classification composition once."""
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be a mapping")
    missing = sorted(name for name in _REQUIRED_INPUTS if name not in inputs)
    if missing:
        raise ValueError(f"missing required composition inputs: {missing}")
    equilibrium = inputs["equilibrium"]
    if not isinstance(equilibrium, Mapping):
        raise ValueError("equilibrium must be a mapping of caller-owned arrays")

    mapped = equilibrium_grid_mapping(
        equilibrium, inputs["x_m"], inputs["y_m"], inputs["z_m"]
    )
    radii_m, axial_coordinate_m = _cylindrical_coordinates(
        inputs["x_m"], inputs["y_m"], inputs["z_m"]
    )
    separatrix_flux, closed_flux_side = _classification_parameters(equilibrium)
    classified = material_support_classification(
        mapped["poloidal_flux_wb_per_rad"],
        mapped["covered_mask"],
        radii_m,
        axial_coordinate_m,
        separatrix_flux_wb_per_rad=separatrix_flux,
        closed_flux_side=closed_flux_side,
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
    """Compose the mapping and material-support relations into one call.

    The two bound dependencies may be overridden by keyword for testing and for
    independent reimplementation; unknown keywords are rejected rather than
    ignored, so a misspelled dependency name fails loudly.
    """
    equilibrium_grid_mapping = kwargs.pop(
        "equilibrium_grid_mapping", map_axisymmetric_equilibrium_to_cartesian_grid
    )
    material_support_classification = kwargs.pop(
        "material_support_classification", classify_material_support
    )
    if kwargs:
        raise ValueError(f"unexpected composition keyword arguments: {sorted(kwargs)}")
    return run_graph(
        inputs,
        equilibrium_grid_mapping=equilibrium_grid_mapping,
        material_support_classification=material_support_classification,
    )

"""Ordered composition for a collection of rectangular vacuum coils."""

from __future__ import annotations

import numpy as np


def _attach_coil_current(points, current, weights):
    """Attach dimensionless filament weights while keeping drive current scalar."""
    return np.column_stack((points, weights)), current


def _concatenate_filament_blocks(blocks):
    """Join per-coil source blocks in caller order."""
    return np.concatenate(blocks, axis=0)


def _target_points(r_grid, z_grid):
    """Pack matching grid arrays into the Green target table."""
    return np.column_stack((r_grid.ravel(), z_grid.ravel()))


def _stack_response_columns(responses):
    """Turn one target-ordered response mapping per coil into source columns."""
    return {
        name: np.column_stack([item[name] for item in responses]) for name in ("gpsi", "gBR", "gBZ")
    }


def run_composition(inputs, *, asset_loader):
    """Expand coil records, evaluate local Green blocks, then contract currents."""
    if not isinstance(inputs, dict):
        raise ValueError("r_grid, z_grid, and rectangular_coils are required")
    required_inputs = ("r_grid", "z_grid", "rectangular_coils")
    missing = [name for name in required_inputs if name not in inputs]
    if missing:
        raise ValueError("r_grid, z_grid, and rectangular_coils are required")
    r_grid, z_grid = (
        np.asarray(inputs["r_grid"], dtype=float),
        np.asarray(inputs["z_grid"], dtype=float),
    )
    if (
        r_grid.ndim != 2
        or z_grid.shape != r_grid.shape
        or not np.all(np.isfinite(r_grid))
        or not np.all(np.isfinite(z_grid))
    ):
        raise ValueError("r_grid and z_grid must be equal-shape finite 2-D arrays")
    if not r_grid.size:
        raise ValueError("r_grid and z_grid must be nonempty 2-D arrays")
    r_axis, z_axis = r_grid[0], z_grid[:, 0]
    if (
        np.any(r_axis < 0.0)
        or np.any(np.diff(r_axis) <= 0.0)
        or np.any(np.diff(z_axis) <= 0.0)
        or not np.allclose(r_grid, r_axis[None, :])
        or not np.allclose(z_grid, z_axis[:, None])
    ):
        raise ValueError("r_grid and z_grid must define a strictly increasing rectilinear R-Z grid")
    coils = inputs["rectangular_coils"]
    if not isinstance(coils, (list, tuple)) or not coils:
        raise ValueError("rectangular_coils must be a nonempty list of configuration mappings")

    geometry = asset_loader("scirel.field.rectangular_coil_filaments")
    source_blocks, currents = [], []
    required_coil = {"r0_m", "z0_m", "nr", "nz", "dr_m", "dz_m", "current_a"}
    for index, coil in enumerate(coils):
        missing = (
            sorted(required_coil.difference(coil))
            if isinstance(coil, dict)
            else sorted(required_coil)
        )
        if not isinstance(coil, dict) or missing:
            raise ValueError(f"rectangular_coils[{index}] misses {', '.join(missing)}")
        points = geometry(
            coil["r0_m"],
            coil["z0_m"],
            coil["nr"],
            coil["nz"],
            coil["dr_m"],
            coil["dz_m"],
            coil.get("angle_deg", 0.0),
        )
        current = float(coil["current_a"])
        if not np.isfinite(current):
            raise ValueError(f"rectangular_coils[{index}].current_a must be finite")
        weights = np.asarray(coil.get("weights", np.ones(len(points))), dtype=float)
        if weights.shape != (len(points),) or not np.all(np.isfinite(weights)):
            raise ValueError(
                f"rectangular_coils[{index}].weights must be finite with one value per filament"
            )
        block, drive = _attach_coil_current(points, current, weights)
        source_blocks.append(block)
        currents.append(drive)

    target_points = _target_points(r_grid, z_grid)
    green = asset_loader("scirel.field.circular_filament_green")
    responses = [green(block, target_points) for block in source_blocks]
    stacked = _stack_response_columns(responses)
    superpose = asset_loader("scirel.field.current_green_superposition")
    combined = superpose(np.asarray(currents), stacked["gpsi"], stacked["gBR"], stacked["gBZ"])
    return {
        "psi_vac": combined["psi"].reshape(r_grid.shape),
        "b_r_vac": combined["BR"].reshape(r_grid.shape),
        "b_z_vac": combined["BZ"].reshape(r_grid.shape),
        "filaments": _concatenate_filament_blocks(source_blocks),
    }


def solve_multi_coil_vacuum_field(inputs=None, **kwargs):
    """Compute vacuum fields from ``rectangular_coils`` records.

    The returned ``psi_vac`` is Wb/rad and ``b_r_vac``/``b_z_vac`` are tesla;
    all arrays have the shape of the supplied ``r_grid`` and ``z_grid``.
    Raises ``ValueError`` for missing or malformed grid and coil records.
    """
    from scirel._composition import compose
    from scirel.field.circular_filament_green import circular_filament_green_response
    from scirel.field.current_green_superposition import superpose_current_green_field
    from scirel.field.rectangular_coil_filaments import discretize_rectangular_coil

    return compose(
        run_composition,
        inputs,
        kwargs,
        {
            "asset_loader": {
                "scirel.field.circular_filament_green": circular_filament_green_response,
                "scirel.field.current_green_superposition": superpose_current_green_field,
                "scirel.field.rectangular_coil_filaments": discretize_rectangular_coil,
            }
        },
    )


__all__ = ["solve_multi_coil_vacuum_field"]

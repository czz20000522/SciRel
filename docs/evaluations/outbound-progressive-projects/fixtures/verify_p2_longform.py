"""Examiner-only viability and numeric checks for the long-form P2 fixture."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scirel.geometry.axisymmetric_equilibrium_grid_support import (
    solve_axisymmetric_equilibrium_grid_mapping,
)


ROOT = Path(__file__).resolve().parents[4] / "build" / "verification" / "p2-longform-evaluation"
INITIAL = ROOT / "solver-workspace" / "input"


def load_equilibrium(stem: str) -> dict:
    metadata = json.loads((INITIAL / f"{stem}-export.json").read_text(encoding="utf-8"))
    with (INITIAL / metadata["data_file"]).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    r_column, z_column = metadata["coordinate_columns"]
    scale = 0.01 if r_column.endswith("_cm") else 0.001
    radii = sorted({float(row[r_column]) * scale for row in rows})
    heights = sorted({float(row[z_column]) * scale for row in rows})
    fields = {key: np.full((len(radii), len(heights)), np.nan)
              for key in ("psi_wb_per_rad", "br_t", "bz_t")}
    for row in rows:
        index = (radii.index(float(row[r_column]) * scale),
                 heights.index(float(row[z_column]) * scale))
        fields["psi_wb_per_rad"][index] = float(row["psi_Wb_per_rad"])
        fields["br_t"][index] = float(row["B_R_T"])
        fields["bz_t"][index] = float(row["B_Z_T"])
    assert all(np.isfinite(value).all() for value in fields.values())
    return {
        "r_m": np.asarray(radii), "z_m": np.asarray(heights), **fields,
        "separatrix_flux_wb_per_rad": metadata["separatrix_flux_wb_per_rad"],
        "closed_flux_side": metadata["closed_flux_side"] or "less_than",
    }


def run(stem: str, *, scale: float) -> None:
    grid = json.loads((INITIAL / "grid-initial.json").read_text(encoding="utf-8"))
    axes = [np.asarray(grid[f"{name}_axis"], dtype=float) for name in "xyz"]
    pec = np.zeros(tuple(len(axis) for axis in axes), dtype=bool)
    slices = [slice(*[low, high + 1]) for low, high in
              (grid["pec_index_box_inclusive"][name] for name in "xyz")]
    pec[tuple(slices)] = True
    result = solve_axisymmetric_equilibrium_grid_mapping({
        "equilibrium": load_equilibrium(stem),
        "x_m": axes[0], "y_m": axes[1], "z_m": axes[2],
        "xpoint_half_length_m": grid["xpoint_half_length_m"],
        "pml_cells": grid["pml_cells"], "pec_mask": pec,
    })
    field = result["magnetic_flux_density_t"]
    center = tuple(int(np.flatnonzero(np.isclose(axis, value))[0])
                   for axis, value in zip(axes, (0.5, 0.0, 0.0)))
    np.testing.assert_allclose(field[center], (0.0, 0.0, scale * 0.7), atol=1e-12)
    assert field.shape == (*pec.shape, 3)
    assert result["material_support_mask"].any()
    print(stem, "shape", field.shape, "support", int(result["material_support_mask"].sum()),
          "Bz_at_R_0.5_Z_0", field[center][-1])


if __name__ == "__main__":
    run("alpha", scale=1.0)
    run("beta", scale=1.08)

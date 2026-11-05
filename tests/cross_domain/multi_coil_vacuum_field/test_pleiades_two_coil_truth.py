"""Repeatable Pleiades external-truth probe for the multi-coil field/green path.

The reviewed Pleiades truth is a tracked domain fixture.  The generator in
``scripts/build_pleiades_truth.py`` writes only an explicitly named candidate
output and never vendors Pleiades source or overwrites this fixture.  The fixed
reference constants below are copied from that independent truth so the field
and Green paths retain an external numeric anchor.
"""

from pathlib import Path

import numpy as np

from scirel.field.circular_filament_green import circular_filament_green_response
from scirel.field.dense_axisymmetric_green import dense_axisymmetric_green_response
from scirel.field.multi_coil_vacuum_field import solve_multi_coil_vacuum_field
from scirel.field.rectangular_coil_filaments import discretize_rectangular_coil


ROOT = Path(__file__).resolve().parents[3]
TRUTH_DIR = ROOT / "tests" / "fixtures" / "multi_coil_vacuum_field" / "pleiades_simple_two_coil"

# Independent Pleiades source truth: TRUTH.json grid and rectangular-coil records.
PLEIADES_SOURCE_COMMIT = "0161abb3e9a1d85143c650f068ec524d672fc9ab"
PLEIADES_ARCHIVE_SHA256 = "f86cfec618690e41a669d692ff195a775f756d2a654fc3e41d8175bf328381b3"
GRID = {"rmin": 0.0, "rmax": 0.8, "zmin": -0.4, "zmax": 0.4, "nr": 9, "nz": 9}
COILS = (
    {"r0": 0.45, "z0": -0.15, "nr": 2, "nz": 2, "dr": 0.04, "dz": 0.05, "current": 1000.0},
    {"r0": 0.45, "z0": 0.15, "nr": 2, "nz": 2, "dr": 0.04, "dz": 0.05, "current": -800.0},
)

# [z-index, r-index] spot values copied from truth.npz (Pleiades, not SciRel).
SPOTS = ((0, 0), (2, 5), (4, 4), (6, 3), (8, 8))
REFERENCE = {
    "psi_vac": (
        0.0,
        0.000587742696221485,
        7.745704098639913e-05,
        -0.0001269507971078137,
        -6.66840605058076e-05,
    ),
    "b_r_vac": (
        0.0,
        -0.00618872514320945,
        0.008156685664293324,
        1.7910589076951386e-05,
        -4.742033776858204e-05,
    ),
    "b_z_vac": (
        0.0025936728438303394,
        -0.0064379410605433385,
        0.0007390784959768809,
        -0.004353000325214432,
        0.00031807008303678,
    ),
}
# Full-array magnitude anchors from the same truth.
REFERENCE_MAX_ABS = {
    "psi_vac": 0.000587742696221485,
    "b_r_vac": 0.010073989154850463,
    "b_z_vac": 0.010832518600324654,
}

RTOL = 1.0e-12
ATOL = 1.0e-16


def _grid():
    r_axis = np.linspace(GRID["rmin"], GRID["rmax"], GRID["nr"])
    z_axis = np.linspace(GRID["zmin"], GRID["zmax"], GRID["nz"])
    return np.meshgrid(r_axis, z_axis)


def _coil_records(scale=1.0):
    return [
        {
            "r0_m": coil["r0"],
            "z0_m": coil["z0"],
            "nr": coil["nr"],
            "nz": coil["nz"],
            "dr_m": coil["dr"],
            "dz_m": coil["dz"],
            "current_a": coil["current"] * scale,
        }
        for coil in COILS
    ]


def _filament_table():
    points, currents = [], []
    for coil in COILS:
        block = discretize_rectangular_coil(
            coil["r0"], coil["z0"], coil["nr"], coil["nz"], coil["dr"], coil["dz"]
        )
        points.append(block)
        currents.extend([coil["current"]] * len(block))
    return np.concatenate(points, axis=0), np.asarray(currents, dtype=float)


def _assert_reference(actual, field):
    expected = np.asarray(REFERENCE[field], dtype=float)
    values = np.asarray([actual[index] for index in SPOTS], dtype=float)
    np.testing.assert_allclose(values, expected, rtol=RTOL, atol=ATOL)
    np.testing.assert_allclose(
        np.max(np.abs(actual)), REFERENCE_MAX_ABS[field], rtol=RTOL, atol=ATOL
    )


def test_fixed_reference_values_match_multi_coil_graph():
    r_grid, z_grid = _grid()
    result = solve_multi_coil_vacuum_field(r_grid, z_grid, _coil_records())
    for field in ("psi_vac", "b_r_vac", "b_z_vac"):
        _assert_reference(result[field], field)


def test_fixed_reference_values_match_direct_green_assembly():
    r_grid, z_grid = _grid()
    targets = np.column_stack((r_grid.ravel(), z_grid.ravel()))
    filaments, currents = _filament_table()
    fields = {
        "psi_vac": np.zeros(len(targets)),
        "b_r_vac": np.zeros(len(targets)),
        "b_z_vac": np.zeros(len(targets)),
    }
    start = 0
    for coil in COILS:
        count = coil["nr"] * coil["nz"]
        block = np.column_stack((filaments[start : start + count], np.ones(count)))
        response = circular_filament_green_response(block, targets)
        fields["psi_vac"] += coil["current"] * response["gpsi"]
        fields["b_r_vac"] += coil["current"] * response["gBR"]
        fields["b_z_vac"] += coil["current"] * response["gBZ"]
        start += count
    for field in ("psi_vac", "b_r_vac", "b_z_vac"):
        _assert_reference(fields[field].reshape(r_grid.shape), field)


def test_fixed_reference_values_match_dense_green_matrices():
    r_grid, z_grid = _grid()
    targets = np.column_stack((r_grid.ravel(), z_grid.ravel()))
    filaments, currents = _filament_table()
    sources = np.column_stack((filaments, np.ones(len(filaments))))
    matrices = dense_axisymmetric_green_response(targets, sources)
    fields = {
        "psi_vac": matrices["gpsi"] @ currents,
        "b_r_vac": matrices["gBR"] @ currents,
        "b_z_vac": matrices["gBZ"] @ currents,
    }
    for field in ("psi_vac", "b_r_vac", "b_z_vac"):
        _assert_reference(fields[field].reshape(r_grid.shape), field)


def test_multi_coil_matches_full_pleiades_truth_arrays():
    import json

    truth = json.loads((TRUTH_DIR / "TRUTH.json").read_text(encoding="utf-8"))
    arrays = np.load(TRUTH_DIR / "truth.npz")
    assert truth["source"] == "Pleiades"
    assert truth["source_commit"] == PLEIADES_SOURCE_COMMIT
    assert truth["source_archive_sha256"] == PLEIADES_ARCHIVE_SHA256
    grid = truth["grid"]
    r_axis = np.linspace(grid["rmin"], grid["rmax"], grid["nr"])
    z_axis = np.linspace(grid["zmin"], grid["zmax"], grid["nz"])
    r_grid, z_grid = np.meshgrid(r_axis, z_axis)
    coils = [
        {
            "r0_m": coil["r0"],
            "z0_m": coil["z0"],
            "nr": coil["nr"],
            "nz": coil["nz"],
            "dr_m": coil["dr"],
            "dz_m": coil["dz"],
            "current_a": coil["current"],
        }
        for coil in truth["coils"]
    ]
    result = solve_multi_coil_vacuum_field(r_grid, z_grid, coils)
    for field in ("psi_vac", "b_r_vac", "b_z_vac"):
        np.testing.assert_allclose(result[field], arrays[field], rtol=1.0e-13, atol=1.0e-17)

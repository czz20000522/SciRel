"""Examiner-only comparison of grid-readout delivery with a raw-file reference."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

from check_stage2 import field, rows
from examiner_grid_readout import bracket


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("previous_stage", type=Path)
    parser.add_argument("--preserve", action="append", default=[])
    args = parser.parse_args()
    root, previous = args.project.resolve(), args.previous_stage.resolve()
    source = root / "input"
    sections = rows(source / "sections.csv")
    shares: dict[str, dict[tuple[int, int], float]] = {}
    for row in rows(source / "filament_shares.csv"):
        shares.setdefault(row["section"], {})[
            (int(row["radial_index"]), int(row["axial_index"]))
        ] = float(row["share"])
    drives = {
        (row["setting"], row["section"]): float(row["total_kA_turns"])
        for row in rows(source / "drives.csv")
    }
    r_axis = [float(row["r_m"]) for row in rows(source / "r-axis.csv")]
    z_axis = [float(row["z_m"]) for row in rows(source / "z-axis.csv")]
    sites = {row["site"]: row for row in rows(source / "sites.csv")}
    with (root / "output/grid_readout_comparison.csv").open(newline="", encoding="utf-8") as stream:
        result = list(csv.DictReader(stream))
    assert set(row["site"] for row in result) == set(sites)
    maximum = 0.0
    checked = 0
    for row in result:
        site = sites[row["site"]]
        r, z = float(site["r_m"]), float(site["z_m"])
        if not (r_axis[0] <= r <= r_axis[-1] and z_axis[0] <= z <= z_axis[-1]):
            assert row["in_grid_domain"] == "no"
            assert all(row[key] == "not evaluated" for key in (
                "Bz_reference_grid_readout_T",
                "Bz_trimmed_grid_readout_T",
                "Bz_readout_difference_T",
            ))
            continue
        assert row["in_grid_domain"] == "yes"
        ir, tr = bracket(r_axis, r)
        iz, tz = bracket(z_axis, z)
        expected = {}
        for setting in ("reference", "trimmed"):
            corners = [
                field(sections, shares, drives, setting, r_axis[ir + dr], z_axis[iz + dz])
                for dz, dr in ((0, 0), (0, 1), (1, 0), (1, 1))
            ]
            expected[setting] = (
                (1 - tr) * (1 - tz) * corners[0]
                + tr * (1 - tz) * corners[1]
                + (1 - tr) * tz * corners[2]
                + tr * tz * corners[3]
            )
            difference = abs(
                float(row[f"Bz_{setting}_grid_readout_T"]) - expected[setting]
            )
            maximum = max(maximum, difference)
            assert difference < 1e-9, (row["site"], setting, difference)
            checked += 1
        assert abs(
            float(row["Bz_readout_difference_T"])
            - (expected["trimmed"] - expected["reference"])
        ) < 1e-9

    old_files = args.preserve or [
        path.name for path in (previous / "output").iterdir() if path.is_file()
    ]
    for name in old_files:
        assert digest(root / "output" / name) == digest(previous / "output" / name), name
    print(f"{checked} grid-readout values match raw-loop grid plus bilinear sampling; max difference {maximum:.3e} T")
    print(f"{len(old_files)} previous result files remain byte-identical; outside site has no value")


if __name__ == "__main__":
    main()

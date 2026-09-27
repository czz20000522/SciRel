"""Examiner-only raw-file grid readout reference; not supplied to the solver."""

from __future__ import annotations

import argparse
from bisect import bisect_right
from pathlib import Path

from check_stage2 import field, rows


def bracket(axis: list[float], coordinate: float) -> tuple[int, float]:
    index = min(max(bisect_right(axis, coordinate) - 1, 0), len(axis) - 2)
    fraction = (coordinate - axis[index]) / (axis[index + 1] - axis[index])
    return index, fraction


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    source = args.project / "input"
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
    for site in rows(source / "sites.csv"):
        r, z = float(site["r_m"]), float(site["z_m"])
        if not (r_axis[0] <= r <= r_axis[-1] and z_axis[0] <= z <= z_axis[-1]):
            print(f"{site['site']},outside")
            continue
        ir, tr = bracket(r_axis, r)
        iz, tz = bracket(z_axis, z)
        for setting in ("reference", "trimmed"):
            corners = [
                field(sections, shares, drives, setting, r_axis[ir + dr], z_axis[iz + dz])
                for dz, dr in ((0, 0), (0, 1), (1, 0), (1, 1))
            ]
            value = (
                (1 - tr) * (1 - tz) * corners[0]
                + tr * (1 - tz) * corners[1]
                + (1 - tr) * tz * corners[2]
                + tr * tz * corners[3]
            )
            print(f"{site['site']},{setting},{value:.12e}")


if __name__ == "__main__":
    main()

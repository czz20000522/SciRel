"""Examiner-only axis-field reference from the user's raw section tables."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    root = args.project / "input"
    sections = rows(root / "sections.csv")
    shares = rows(root / "filament_shares.csv")
    drives = rows(root / "drives.csv")
    heights = [float(row["z_m"]) for row in rows(root / "z-axis.csv")]
    drive_by_setting = {
        (row["setting"], row["section"]): float(row["total_kA_turns"])
        for row in drives
    }
    shares_by_section: dict[str, dict[tuple[int, int], float]] = {}
    for row in shares:
        section = row["section"]
        shares_by_section.setdefault(section, {})[
            (int(row["radial_index"]), int(row["axial_index"]))
        ] = float(row["share"])
    settings = list(dict.fromkeys(row["setting"] for row in drives))
    for setting in settings:
        for height in heights:
            total = 0.0
            for section in sections:
                name = section["section"]
                nr, nz = int(section["nr"]), int(section["nz"])
                fractions = shares_by_section[name]
                assert len(fractions) == nr * nz
                assert abs(sum(fractions.values()) - 1.0) < 1e-12
                drive_a = 1000.0 * drive_by_setting[(setting, name)]
                for ir in range(nr):
                    radius = float(section["r0_m"]) + (
                        ir - (nr - 1) / 2.0
                    ) * float(section["dr_m"])
                    for iz in range(nz):
                        z = float(section["z0_m"]) + (
                            iz - (nz - 1) / 2.0
                        ) * float(section["dz_m"])
                        current = drive_a * fractions[(ir, iz)]
                        total += (
                            (2e-7 * math.pi)
                            * current
                            * radius**2
                            / (radius**2 + (height - z) ** 2) ** 1.5
                        )
            print(f"{setting},{height:+.6f},{total:.12e}")


if __name__ == "__main__":
    main()

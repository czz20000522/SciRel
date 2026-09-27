"""Examiner-only raw-file Biot-Savart check of the staged site comparison."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
from pathlib import Path


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def loop_bz(radius: float, filament_z: float, current: float, r: float, z: float) -> float:
    # Direct Biot-Savart angular quadrature, not a SciRel Green response.
    count = 4096
    step = 2.0 * math.pi / count
    total = 0.0
    dz = z - filament_z
    for index in range(count + 1):
        angle = index * step
        cosine = math.cos(angle)
        distance_sq = radius**2 + r**2 - 2.0 * radius * r * cosine + dz**2
        value = (radius**2 - radius * r * cosine) / distance_sq**1.5
        weight = 1 if index in (0, count) else (4 if index % 2 else 2)
        total += weight * value
    return (1e-7 * current) * total * step / 3.0


def field(
    sections: list[dict[str, str]],
    shares: dict[str, dict[tuple[int, int], float]],
    drives: dict[tuple[str, str], float],
    setting: str,
    r: float,
    z: float,
) -> float:
    total = 0.0
    for section in sections:
        name = section["section"]
        nr, nz = int(section["nr"]), int(section["nz"])
        assert len(shares[name]) == nr * nz
        assert abs(sum(shares[name].values()) - 1.0) < 1e-12
        for ir in range(nr):
            radius = float(section["r0_m"]) + (
                ir - (nr - 1) / 2.0
            ) * float(section["dr_m"])
            for iz in range(nz):
                filament_z = float(section["z0_m"]) + (
                    iz - (nz - 1) / 2.0
                ) * float(section["dz_m"])
                current = 1000.0 * drives[(setting, name)] * shares[name][(ir, iz)]
                total += loop_bz(radius, filament_z, current, r, z)
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("first_stage", type=Path)
    parser.add_argument("--preserve", action="append", default=[])
    args = parser.parse_args()
    root, first = args.project.resolve(), args.first_stage.resolve()
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
    sites = {row["site"]: row for row in rows(source / "sites.csv")}
    result = rows(root / "output/settings_comparison.csv")
    assert set(row["site"] for row in result) == set(sites)
    maximum = 0.0
    checked = 0
    for row in result:
        site = sites[row["site"]]
        r, z = float(site["r_m"]), float(site["z_m"])
        if r > 0.4 or z < -0.2 or z > 0.2:
            assert row["in_grid_domain"] == "no"
            assert all(row[key] == "not evaluated" for key in (
                "Bz_reference_T", "Bz_trimmed_T", "Bz_difference_T"
            ))
            continue
        assert row["in_grid_domain"] == "yes"
        expected = {}
        for setting in ("reference", "trimmed"):
            expected[setting] = field(sections, shares, drives, setting, r, z)
            deviation = abs(float(row[f"Bz_{setting}_T"]) - expected[setting])
            maximum = max(maximum, deviation)
            assert deviation < 1e-9, (row["site"], setting, deviation)
            checked += 1
        difference = expected["trimmed"] - expected["reference"]
        assert abs(float(row["Bz_difference_T"]) - difference) < 1e-9

    preserved = args.preserve or (
        "b_z_table.csv", "vacuum_axial_field.png", "vacuum_axial_field_report.html"
    )
    for name in preserved:
        assert digest(root / "output" / name) == digest(first / "output" / name), name
    print(f"{checked} setting-site values match raw-file angular quadrature; max difference {maximum:.3e} T")
    print(f"{len(preserved)} first-delivery user files remain byte-identical; outside site has no value")


if __name__ == "__main__":
    main()

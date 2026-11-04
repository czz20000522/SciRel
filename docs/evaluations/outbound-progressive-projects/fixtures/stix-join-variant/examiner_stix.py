"""Examiner-only raw-table reference for the synthetic Stix fixture."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


EPSILON_0 = 8.8541878128e-12


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def tensor(frequency: float, field: tuple[float, float, float], species: list[dict[str, float]]) -> tuple[complex, complex, complex]:
    omega = 2.0 * math.pi * frequency
    magnitude = math.sqrt(sum(value * value for value in field))
    direction = tuple(value / magnitude for value in field)
    s, d, p = 1.0 + 0j, 0j, 1.0 + 0j
    for item in species:
        plasma = item["density_m3"] * item["charge_c"] ** 2 / (EPSILON_0 * item["mass_kg"])
        cyclotron = item["charge_c"] * magnitude / item["mass_kg"]
        shifted = omega + 1j * item["collision_rate_s_inv"]
        denominator = shifted * shifted - cyclotron * cyclotron
        s -= plasma * shifted / (omega * denominator)
        d += cyclotron * plasma / (omega * denominator)
        p -= plasma / (omega * shifted)
    bx, by, bz = direction
    return (
        s + (p - s) * bx * bx,
        (p - s) * bx * by - 1j * d * bz,
        s + (p - s) * bz * bz,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    root = args.project / "input"
    constants = {row["species_id"]: row for row in rows(root / "species.csv")}
    grouped: dict[str, list[dict[str, float]]] = {}
    for row in rows(root / "settings.csv"):
        source = constants[row["species_id"]]
        grouped.setdefault(row["setting"], []).append({
            "density_m3": float(row["density_m3"]),
            "collision_rate_s_inv": float(row["collision_rate_s_inv"]),
            "charge_c": float(source["charge_c"]),
            "mass_kg": float(source["mass_kg"]),
        })
    for setting, species in grouped.items():
        for point in rows(root / "field-sites.csv"):
            field = tuple(float(point[name]) for name in ("bx_t", "by_t", "bz_t"))
            for frequency in rows(root / "frequencies.csv"):
                values = tensor(float(frequency["frequency_hz"]), field, species)
                print(setting, point["site"], frequency["frequency_id"], *(repr(value) for value in values), sep=",")


if __name__ == "__main__":
    main()

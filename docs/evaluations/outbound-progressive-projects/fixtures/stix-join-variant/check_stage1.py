"""Examiner-only check from fixture CSV inputs to delivered Stix entries."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from examiner_stix import rows, tensor


def main() -> int:
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
    fields = {
        row["site"]: tuple(float(row[name]) for name in ("bx_t", "by_t", "bz_t"))
        for row in rows(root / "field-sites.csv")
    }
    frequencies = {
        row["frequency_id"]: float(row["frequency_hz"])
        for row in rows(root / "frequencies.csv")
    }
    delivered = args.project / "output" / "dielectric_tensors.csv"
    with delivered.open(newline="", encoding="utf-8") as stream:
        actual = list(csv.DictReader(stream))
    expected_keys = {
        (setting, site, frequency)
        for setting in grouped
        for site in fields
        for frequency in frequencies
    }
    actual_keys = {(row["setting"], row["site"], row["frequency_id"]) for row in actual}
    if actual_keys != expected_keys or len(actual) != len(expected_keys):
        print(f"row mismatch: expected {len(expected_keys)}, got {len(actual)}")
        return 1
    maximum = 0.0
    for row in actual:
        key = (row["setting"], row["site"], row["frequency_id"])
        values = tensor(frequencies[key[2]], fields[key[1]], grouped[key[0]])
        for column, expected in zip(("eps_11", "eps_12", "eps_33"), values):
            delivered_value = complex(float(row[column + "_re"]), float(row[column + "_im"]))
            difference = abs(delivered_value - expected)
            maximum = max(maximum, difference)
            if difference > 1e-10 * max(1.0, abs(expected)):
                print(f"{key} {column}: expected {expected}, got {delivered_value}")
                return 1
    print(f"{len(actual)} raw-input tensor rows agree; max absolute difference {maximum:.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

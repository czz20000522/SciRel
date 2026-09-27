"""Examiner-only raw-file loop check for the fractional-ring first delivery."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    root = args.project.resolve()
    rings = read_rows(root / "input/rings.csv")
    settings = {
        (row["setting"], row["bank"]): float(row["total_kA_turns"])
        for row in read_rows(root / "input/settings.csv")
    }
    heights = [float(row["height_m"]) for row in read_rows(root / "input/heights.csv")]
    result = read_rows(root / "output/axial_field_table.csv")
    assert len(result) == len(heights)
    max_delta = 0.0
    for height, actual in zip(heights, result, strict=True):
        assert abs(float(actual["height_m"]) - height) < 1e-9
        expected = 0.0
        for ring in rings:
            current = 1000.0 * settings[("nominal", ring["bank"])] * float(ring["bank_share"])
            radius = float(ring["radius_m"])
            dz = height - float(ring["height_m"])
            expected += (2e-7 * math.pi) * current * radius**2 / (radius**2 + dz**2) ** 1.5
        delta = abs(float(actual["bz_total_T"]) - expected)
        max_delta = max(max_delta, delta)
        assert delta < 1e-9, (height, actual["bz_total_T"], expected)
    print(f"{len(result)} rows match independent raw-input axis formula; max delta {max_delta:.3e} T")


if __name__ == "__main__":
    main()

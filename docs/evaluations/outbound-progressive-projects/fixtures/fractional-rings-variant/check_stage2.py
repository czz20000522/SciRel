"""Examiner-only raw-file and history check for the two-setting delivery."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def field(rings: list[dict[str, str]], settings: dict[tuple[str, str], float], setting: str, height: float) -> float:
    total = 0.0
    for ring in rings:
        current = 1000.0 * settings[(setting, ring["bank"])] * float(ring["bank_share"])
        radius = float(ring["radius_m"])
        dz = height - float(ring["height_m"])
        total += (2e-7 * math.pi) * current * radius**2 / (radius**2 + dz**2) ** 1.5
    return total


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("first_stage", type=Path)
    args = parser.parse_args()
    root = args.project.resolve()
    first = args.first_stage.resolve()
    rings = read_rows(root / "input/rings.csv")
    settings = {
        (row["setting"], row["bank"]): float(row["total_kA_turns"])
        for row in read_rows(root / "input/settings.csv")
    }
    heights = {
        float(row["height_m"])
        for name in ("heights.csv", "extra-heights.csv")
        for row in read_rows(root / "input" / name)
    }
    results = read_rows(root / "output/comparison_table.csv")
    assert len(results) == len(heights) == 5
    max_delta = 0.0
    for row in results:
        height = float(row["height_m"])
        assert height in heights
        expected = {name: field(rings, settings, name, height) for name in ("nominal", "bias")}
        for name in ("nominal", "bias"):
            delta = abs(float(row[f"bz_{name}_T"]) - expected[name])
            max_delta = max(max_delta, delta)
            assert delta < 1e-9, (name, height, row[f"bz_{name}_T"], expected[name])
        difference = float(row["bias_minus_nominal_T"])
        assert abs(difference - (expected["bias"] - expected["nominal"])) < 1e-9

    old_names = ("audit.md", "axial_field_table.csv", "axial_field_table.md", "axial_field.png")
    for name in old_names:
        assert digest(root / "output/original" / name) == digest(first / "output" / name), name
    print(f"{len(results) * 2} setting-height values match raw-input loops; max delta {max_delta:.3e} T")
    print(f"{len(old_names)} original result files remain byte-identical")


if __name__ == "__main__":
    main()

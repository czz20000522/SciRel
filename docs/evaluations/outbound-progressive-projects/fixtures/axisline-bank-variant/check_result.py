"""Independently check the synthetic axisline result from raw user files."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def bank_field(bank: dict[str, str], height: float) -> float:
    nr = int(bank["radial_nodes"])
    nz = int(bank["vertical_nodes"])
    current = float(bank["net_ampere_turns"]) / (nr * nz)
    total = 0.0
    for ir in range(nr):
        radius = float(bank["center_radius_m"]) + (ir - (nr - 1) / 2) * float(bank["radial_pitch_m"])
        for iz in range(nz):
            source_height = float(bank["center_height_m"]) + (iz - (nz - 1) / 2) * float(bank["vertical_pitch_m"])
            separation_sq = radius * radius + (height - source_height) ** 2
            total += (2e-7 * math.pi) * current * radius * radius / separation_sq**1.5
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    root = args.project.resolve()
    banks = rows(root / "input/banks.csv")
    heights = [float(row["height_m"]) for row in rows(root / "input/axisline.csv")]
    result = rows(root / "output/axisline_bz.csv")
    assert len(heights) == len(result)
    max_delta = 0.0
    for height, actual in zip(heights, result, strict=True):
        assert abs(float(actual["height_m"]) - height) < 1e-9
        contributions = [bank_field(bank, height) for bank in banks]
        expected = sum(contributions)
        delta = abs(float(actual["BZ_total_T"]) - expected)
        max_delta = max(max_delta, delta)
        assert delta < 1e-11, (height, expected, actual["BZ_total_T"])
        assert abs(float(actual["BR_total_T"])) < 1e-12
        for bank, contribution in zip(banks, contributions, strict=True):
            assert abs(float(actual[f"BZ_{bank['bank']}_T"]) - contribution) < 1e-11
    print(f"{len(result)} axisline rows match raw-input analytic loops; max delta {max_delta:.3e} T")


if __name__ == "__main__":
    main()

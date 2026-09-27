"""Check the delivered tensor's dissipative quadratic form by case."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    with (args.project / "output" / "dielectric_tensors.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        eps = np.array(
            [
                [complex(float(row[f"eps_{i}{j}_re"]), float(row[f"eps_{i}{j}_im"])) for j in range(1, 4)]
                for i in range(1, 4)
            ]
        )
        dissipative = (eps - eps.conj().T) / (2j)
        eigenvalues = np.linalg.eigvalsh(dissipative)
        print(
            row["setting"], row["site"], row["frequency_id"],
            f"min={eigenvalues.min():.12g}", f"max={eigenvalues.max():.12g}",
        )


if __name__ == "__main__":
    main()

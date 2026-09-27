"""Generate staged synthetic complex-field volumes for an outbound evaluation."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


COARSE_AXES = (
    [-0.30, -0.10, 0.20, 0.50],
    [-0.20, 0.05, 0.30],
    [0.00, 0.15, 0.40],
)
FINE_AXES = (
    [-0.30, -0.20, -0.10, 0.05, 0.20, 0.35, 0.50],
    [-0.20, -0.075, 0.05, 0.175, 0.30],
    [0.00, 0.075, 0.15, 0.275, 0.40],
)


def write_volume(path: Path, axes: tuple[list[float], ...]) -> None:
    x, y, z = (np.asarray(axis, dtype=float) for axis in axes)
    xx, yy, zz = np.meshgrid(x, y, z, indexing="ij")
    phase = 0.7 * xx + 1.1 * yy * zz - 0.35 * zz + 0.4 * xx * yy
    ex = (1.0 + 0.3 * xx + 0.2 * yy**2 + 0.1 * zz + 0.08 * xx * zz) * np.exp(1j * phase)
    ey = (0.5 + 0.1 * yy + 0.2 * xx**2) * np.exp(1j * (phase + 0.7 * zz))
    ez = (0.2 + 0.05 * xx * yy) * np.exp(1j * (-0.3 * xx + 0.4 * zz))
    np.savez_compressed(path, x_m=x, y_m=y, z_m=z, e_v_per_m=np.stack((ex, ey, ez), axis=-1))


def write_stations(path: Path, rows: tuple[tuple[str, float, float, float], ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("station", "x_m", "y_m", "z_m"))
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("solver_root", type=Path)
    parser.add_argument("examiner_root", type=Path)
    args = parser.parse_args()
    solver_input = args.solver_root.resolve() / "input"
    examiner = args.examiner_root.resolve()
    for directory in (solver_input, examiner):
        directory.mkdir(parents=True, exist_ok=True)
        if any(directory.iterdir()):
            raise FileExistsError(f"refusing to overwrite nonempty fixture directory: {directory}")

    write_volume(solver_input / "initial-volume.npz", COARSE_AXES)
    write_stations(solver_input / "stations.csv", (
        ("north", -0.18, -0.05, 0.08),
        ("middle", 0.12, 0.11, 0.20),
        ("east", 0.42, 0.24, 0.34),
        ("corner", 0.50, 0.30, 0.40),
        ("outside", 0.56, 0.00, 0.20),
    ))
    (solver_input / "export-note.md").write_text(
        "# Synthetic phasor export\n\n"
        "`initial-volume.npz` contains Cartesian axes `x_m`, `y_m`, `z_m` "
        "and a complex three-component electric-field phasor array "
        "`e_v_per_m` indexed `[x, y, z, component]`. Axes are in metres; "
        "components are in V/m in the same Cartesian basis. Values are "
        "finite samples from a synthetic test export, not a measured device "
        "or a solved wave-propagation model. Both phases and coordinates use "
        "one common convention across the files. The stations table lists "
        "requested positions, including an intentionally out-of-box row.\n",
        encoding="utf-8",
    )
    (examiner / "opening.txt").write_text(
        "My colleague sent the files in input/. I cannot program, but I need "
        "a small project I can rerun to get the complex three-component "
        "field at each station, plus an openable table and magnitude chart. "
        "Please keep unsupported positions visibly unavailable instead of "
        "filling in zero. Tell me what these synthetic files do and do not "
        "say physically. You can use the installed SciRel development wheel "
        "and its catalog; I do not know its function names.\n",
        encoding="utf-8",
    )

    write_volume(examiner / "refined-volume.npz", FINE_AXES)
    write_stations(examiner / "additional-stations.csv", (
        ("gap", -0.03, 0.00, 0.14),
        ("lower", 0.30, -0.10, 0.10),
        ("beyond", -0.40, 0.00, 0.18),
    ))
    (examiner / "followup.txt").write_text(
        "I added `input/refined-volume.npz` on a denser but same-box grid "
        "and `input/additional-stations.csv`. Please extend the same ordinary "
        "entrypoint to compare the initial and refined exports at all "
        "available stations, including the new ones, and keep the first "
        "delivery's table and chart openable as they were. My colleague asks "
        "whether the largest difference at these stations is a guaranteed "
        "upper bound on field error everywhere inside the box. I need an "
        "honest number and its scope, not a hidden assumption.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

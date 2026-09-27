"""Generate a staged synthetic coil project for a vacuum-field claim check."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


COILS = (
    ("upper", 620, 200, 40, 60, 2, 3),
    ("lower", 620, -200, 40, 60, 2, 3),
    ("center", 450, 0, 40, 100, 2, 5),
)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("solver_root", type=Path)
    parser.add_argument("examiner_root", type=Path)
    args = parser.parse_args()
    solver = args.solver_root.resolve()
    examiner = args.examiner_root.resolve()
    for directory in (solver / "input", examiner):
        directory.mkdir(parents=True, exist_ok=True)
        if any(directory.iterdir()):
            raise FileExistsError(f"refusing to overwrite nonempty fixture directory: {directory}")

    with (solver / "input" / "coil-sections.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.writer(stream)
        writer.writerow((
            "coil_id", "R_center_mm", "Z_center_mm", "width_mm", "height_mm",
            "r_slices", "z_slices",
        ))
        writer.writerows(COILS)
    write_json(solver / "input" / "drives.json", {
        "current_unit": "total_kA_turns_per_section",
        "scenarios": {
            "as_set": {"upper": 8.0, "lower": 8.0, "center": 2.0},
        },
    })
    write_json(solver / "input" / "preview-window.json", {
        "coordinate_system": "cylindrical R-Z in metres",
        "r_m": [0.0, 0.08, 0.16, 0.24, 0.32, 0.40],
        "z_m": [-0.30, -0.20, -0.10, 0.0, 0.10, 0.20, 0.30],
    })
    (solver / "input" / "shop-note.md").write_text(
        "# Synthetic coil-layout handoff\n\nThese are axisymmetric circular "
        "sections, not 3-D winding paths. `R_center_mm` is cylindrical radius "
        "from the common axis. The positive drive sign means the same "
        "toroidal current direction in every section. The currents in "
        "drives.json are **total ampere-turns per section**, not current per "
        "representative filament. For the initial calculation, the section "
        "is represented by `r_slices * z_slices` equal-current filaments. "
        "This is a synthetic design exercise, not a measured machine. "
        "We have no plasma pressure/current profile, measured equilibrium, "
        "RF electric field, or heating measurement.\n",
        encoding="utf-8",
    )
    (examiner / "opening.txt").write_text(
        "I only have the coil section and drive files under input/. Could you "
        "make a small project that gives me a useful field preview I can open "
        "and rerun without editing code? I am also trying to understand "
        "whether this tells us where the plasma would sit and where the RF "
        "heating will land. Please use only what these files really support; "
        "tell me plainly what else would be needed. I do not know the "
        "SciRel function names. The project contains a development wheel, "
        "matching catalog and scientific skills.\n",
        encoding="utf-8",
    )
    write_json(examiner / "additional-drive.json", {
        "current_unit": "total_kA_turns_per_section",
        "scenarios": {
            "as_set": {"upper": 8.0, "lower": 8.0, "center": 2.0},
            "trimmed": {"upper": 9.0, "lower": 7.0, "center": 2.0},
        },
    })
    write_json(examiner / "dense-window.json", {
        "coordinate_system": "cylindrical R-Z in metres",
        "r_m": [round(i * 0.04, 10) for i in range(11)],
        "z_m": [round(-0.30 + i * 0.05, 10) for i in range(13)],
    })
    (examiner / "followup.txt").write_text(
        "I added a second drive setting to input/drives.json and a denser "
        "input/dense-window.json over the **same physical window**. Please "
        "compare the two drive settings, keep the first preview openable, "
        "and make the ordinary rerun entrypoint handle my added data. Can "
        "the difference between coarse and dense grids be reported as a "
        "numerical error *upper bound* for the field? I need a result my "
        "colleague can inspect, not a hidden assumption.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

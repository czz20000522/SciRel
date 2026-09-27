"""Generate a staged synthetic coil-field and off-grid-probe user project."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_probes(path: Path, rows: tuple[tuple[str, float, float], ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("site", "radius_m", "height_m"))
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
            raise FileExistsError(f"refusing nonempty fixture directory: {directory}")

    write_json(solver_input / "coil-layout.json", {
        "coordinate_system": "axisymmetric cylindrical R-Z",
        "current_sign": "positive is one common toroidal winding direction",
        "coil_sections": [
            {
                "section": "high",
                "radius_center_m": 0.64,
                "height_center_m": 0.19,
                "radial_width_m": 0.08,
                "vertical_height_m": 0.04,
                "radial_slices": 2,
                "vertical_slices": 2,
            },
            {
                "section": "low",
                "radius_center_m": 0.64,
                "height_center_m": -0.19,
                "radial_width_m": 0.08,
                "vertical_height_m": 0.04,
                "radial_slices": 2,
                "vertical_slices": 2,
            },
        ],
    })
    write_json(solver_input / "drive-settings.json", {
        "unit": "total_kA_turns_per_section",
        "settings": {"steady": {"high": 4.2, "low": 4.2}},
    })
    write_json(solver_input / "preview-grid.json", {
        "r_m": [0.0, 0.06, 0.14, 0.24, 0.36, 0.48],
        "z_m": [-0.24, -0.12, 0.0, 0.12, 0.24],
    })
    write_probes(solver_input / "probe-sites.csv", (
        ("axis", 0.0, 0.0),
        ("lower", 0.11, -0.07),
        ("middle", 0.23, 0.03),
        ("upper", 0.41, 0.16),
        ("outside", 0.53, 0.0),
    ))
    (solver_input / "source-note.md").write_text(
        "# Synthetic winding-sheet handoff\n\n"
        "These are axisymmetric circular coil sections, not measured 3-D turns. "
        "Each signed drive in drive-settings.json is the **total ampere-turns "
        "for that whole section**, not a current to apply independently to "
        "every representative filament. Use equal shares across the stated "
        "radial_slices x vertical_slices. The preview grid and probe sites "
        "are cylindrical [R,Z] coordinates in metres. The files are synthetic "
        "and contain no plasma current, pressure, density, material boundary, "
        "measured field, RF electric field or heating observations.\n",
        encoding="utf-8",
    )
    (examiner / "opening.txt").write_text(
        "I have the coil and probe files in input/ but do not know Python or "
        "SciRel. Please build a small project I can rerun to compare the "
        "predicted vacuum magnetic field at the listed sites, with an openable "
        "table and a preview image. Keep a site outside the preview region "
        "visibly unavailable. Tell me what the files support physically. "
        "This project includes a development SciRel wheel, matching catalog "
        "and scientific skills.\n",
        encoding="utf-8",
    )

    write_json(examiner / "later-drive-settings.json", {
        "unit": "total_kA_turns_per_section",
        "settings": {
            "steady": {"high": 4.2, "low": 4.2},
            "trim": {"high": 4.8, "low": 3.6},
        },
    })
    write_probes(examiner / "later-probe-sites.csv", (
        ("offset", 0.17, 0.08),
        ("beyond", 0.18, 0.29),
    ))
    (examiner / "followup.txt").write_text(
        "I added a trim drive in input/drive-settings.json and two extra sites "
        "in input/later-probe-sites.csv. Please extend the same ordinary "
        "entrypoint to compare both settings at all sites. Keep the earlier "
        "table and preview image openable so I can see what changed. Is the "
        "largest difference between settings also a guaranteed upper bound "
        "on the numerical error of the field everywhere in the region? "
        "Please explain what I can and cannot conclude.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

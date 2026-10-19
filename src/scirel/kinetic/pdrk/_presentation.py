"""Persist PDRK scientific arrays and an explicit, reviewable plot manifest."""

import hashlib
import json
from pathlib import Path

import numpy as np

from scirel._optional import import_optional_module


def _artifact_manifest(root):
    return [
        {
            "name": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
        for path in sorted(root.iterdir())
    ]


def save_program(model, result, output_dir):
    """Render a result and write terminal numeric artifacts plus metadata."""

    matplotlib = import_optional_module(
        "matplotlib", extra="plot", feature="PDRK scientific presentation"
    )
    matplotlib.use("Agg")
    pyplot = import_optional_module(
        "matplotlib.pyplot", extra="plot", feature="PDRK scientific presentation"
    )
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=False)
    figure, axes = pyplot.subplots(2, 1, figsize=(7, 7), layout="constrained")
    arrays = {}
    carriers = []

    if model == "generator":
        x = np.asarray(result["x"])
        y = np.asarray(result["y"])
        values = np.asarray(result["ZJ"])
        arrays.update(x=x, y=y, ZJ=values, bzj=result["bzj"], czj=result["czj"])
        for axis, image_values, title in zip(
            axes, (values.real, values.imag), ("Re Z_J", "Im Z_J")
        ):
            image = axis.pcolormesh(x, y, image_values, shading="auto")
            figure.colorbar(image, ax=axis)
            axis.set(
                xlabel="Re z (dimensionless)",
                ylabel="Im z (dimensionless)",
                title=title,
            )
    else:
        points = np.asarray(result["points"])
        equilibrium = result["equilibrium"]["state"]
        coordinate = points[:, 0] if model == "es1d" else np.linalg.norm(points, axis=1)
        frequency_scale = 1.0
        coordinate_unit = "dimensionless k"
        if model == "em":
            coordinate = coordinate * float(np.asarray(equilibrium["cwp"]).item())
            frequency_scale = float(np.asarray(equilibrium["wci"]).item())
            coordinate_unit = "k c / omega_pi"
        arrays["points"] = points
        for index, (x_value, point) in enumerate(zip(coordinate, result["spectra"])):
            solution = point["solution"]
            frequencies = solution.get("w", solution.get("omega"))
            arrays[f"omega_{index}"] = frequencies
            if "frequency_base_decimal" in solution:
                carriers.append({
                    "point_index": index,
                    **{
                        key: value
                        for key, value in solution.items()
                        if not isinstance(value, np.ndarray)
                    },
                })
            axes[0].plot(
                np.repeat(x_value, len(frequencies)),
                frequencies.real / frequency_scale,
                ".",
                markersize=2,
            )
            axes[1].plot(
                np.repeat(x_value, len(frequencies)),
                frequencies.imag / frequency_scale,
                ".",
                markersize=2,
            )
        axes[0].set(
            ylabel=(
                "Re omega / omega_ci"
                if model == "em"
                else "Re omega (dimensionless)"
            )
        )
        axes[1].set(
            ylabel=(
                "Im omega / omega_ci"
                if model == "em"
                else "Im omega (dimensionless)"
            )
        )
        for axis in axes:
            axis.set(xlabel=coordinate_unit)
            axis.grid(True, alpha=0.3)

    figure.savefig(root / "corrected-scientific-output.png", dpi=120)
    pyplot.close(figure)
    np.savez(root / "scientific-terminal.npz", **arrays)
    if carriers:
        (root / "complete-frequency-carriers.json").write_text(
            json.dumps(carriers, indent=2) + "\n"
        )

    metadata = {
        "numeric_views": "binary64 rounded frequencies; complete decimal base+offset retained when present",
        "frequency_units": "omega/omega_ci" if model == "em" else "dimensionless omega",
        "coordinate_units": "k c/omega_pi" if model == "em" else "dimensionless k",
        "generator_units": (
            "dimensionless complex z and Z_J" if model == "generator" else None
        ),
        "mode_classification": (
            "per-point physical/canceled/infinite taxonomy in "
            "complete-frequency-carriers.json when applicable; auxiliary aliases "
            "not silently physical waves"
        ),
        "visual_review": "PENDING",
    }
    manifest = {
        "plot_metadata": metadata,
        "model": model,
        "status": "CORRECTED_SCIENTIFIC_PRESENTATION",
        "human_visual_approval": "PENDING",
        "original_PNG_identity": "NOT_CLAIMED",
        "artifacts": _artifact_manifest(root),
    }
    (root / "ARTIFACTS.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    return {"result": result, "artifacts": manifest, "output_dir": str(root)}

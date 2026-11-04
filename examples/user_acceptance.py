"""Platform acceptance: satisfy user goals using preinstalled scientific capabilities.

Users receive result files and explanations; installation and package identity belong
to platform runtime preparation, not to the user task or its agent instructions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path
import zipfile

import numpy as np
import scirel
from scirel.closures import compute_reference_electron_density, solve_quasineutral_potential
from scirel.diagnostics import compute_picard_flux_residual
from scirel.field import (
    compute_poloidal_field_magnitude,
    dense_axisymmetric_green_response,
    solve_multi_coil_vacuum_field,
    superpose_current_green_field,
)
from scirel.geometry import interpolate_complex_rectilinear_field
from scirel.kinetic import (
    assemble_frank_egedal_pressure,
    assemble_mirror_total_pressure,
    evaluate_frank_egedal_radial_envelope,
)


def _sha256_bytes(*chunks: bytes) -> str:
    hasher = hashlib.sha256()
    for chunk in chunks:
        hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def verify_installation(wheel: Path) -> dict:
    distribution = importlib.metadata.distribution('scirel')
    package_root = Path(distribution.locate_file('scirel')).resolve()
    assert Path(scirel.__file__).resolve().parent == package_root
    assert package_root.is_relative_to(Path(sys.prefix).resolve()), 'use the platform-installed wheel, not a source checkout'
    direct = distribution.read_text('direct_url.json')
    assert not direct or not json.loads(direct).get('dir_info', {}).get('editable', False)
    count = 0
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.namelist():
            if member.startswith('scirel/') and member.endswith('.py'):
                assert distribution.locate_file(member).read_bytes() == archive.read(member), member
                count += 1
    return {'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
            'version': distribution.version, 'module_root': str(package_root),
            'verified_python_files': count, 'status': 'development_wheel_not_admitted_release'}


def green_field_synthesis(output: Path) -> dict:
    """User: combine two source responses and export flux and field values."""
    targets = np.array([[0.12, -0.08], [0.22, 0.05], [0.34, -0.03], [0.44, 0.12]])
    sources = np.array([[0.28, -0.04, 1.0], [0.51, 0.09, -0.35]])
    currents = np.array([450.0, -180.0])
    green = dense_axisymmetric_green_response(targets, sources)
    combined = superpose_current_green_field(
        currents,
        green["gpsi"].T,
        green["gBR"].T,
        green["gBZ"].T,
    )
    for key, source_key in (("psi", "gpsi"), ("BR", "gBR"), ("BZ", "gBZ")):
        expected = np.sum(currents[:, None] * green[source_key].T, axis=0)
        np.testing.assert_allclose(combined[key], expected, rtol=2e-15, atol=0.0)
    magnitude = compute_poloidal_field_magnitude(
        combined["BR"].reshape(2, 2),
        combined["BZ"].reshape(2, 2),
    )["B"].ravel()
    rows = [
        {
            "R_m": float(point[0]),
            "Z_m": float(point[1]),
            "psi_Wb": float(combined["psi"][index]),
            "B_R_T": float(combined["BR"][index]),
            "B_Z_T": float(combined["BZ"][index]),
            "B_p_T": float(magnitude[index]),
        }
        for index, point in enumerate(targets)
    ]
    with (output / "green_field_synthesis.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return {
        "passed": True,
        "rows": len(rows),
        "maximum_poloidal_field_T": float(np.max(magnitude)),
        "criteria": "source-axis current contraction and finite poloidal magnitude at four targets",
    }


def quasineutral_profile(output: Path) -> dict:
    """User: solve selected surfaces while preserving inactive reference potentials."""
    reference = compute_reference_electron_density(
        density_ref_m3=np.array([1.0e18, 2.0e18, 0.0]),
        ion_charge_state=np.array([1.0, 2.0, 1.0]),
    )["electron_density_ref_m3"]
    np.testing.assert_array_equal(reference, np.array([1.0e18, 4.0e18, 0.0]))

    target = np.array([0.25, -0.5, 2.0])
    active = np.array([True, True, False])
    state = solve_quasineutral_potential(
        potential_reference_v=np.array([0.0, 0.0, 7.0]),
        temperature_parallel_j=1.0e-19,
        electron_temperature_j=1.0e-19,
        charge_c=1.602176634e-19,
        active=active,
        residual=lambda potential: {
            "logarithmic_charge_residual": target - np.asarray(potential)
        },
    )
    np.testing.assert_allclose(state["potential_v"][active], target[active], atol=1.0e-10)
    np.testing.assert_array_equal(state["potential_v"][~active], np.array([7.0]))
    report = {
        "passed": True,
        "electron_density_ref_m3": reference.tolist(),
        "potential_v": state["potential_v"].tolist(),
        "iterations": state["iterations"],
        "criteria": "active roots converge and inactive surfaces retain their reference potential",
    }
    (output / "quasineutral_profile.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def pressure_state_and_residual(output: Path) -> dict:
    """User: assemble a pressure state and quantify one flux-update residual."""
    psi = np.array([[0.0, 0.25, 0.5], [0.5, 0.75, 1.0]])
    radial = evaluate_frank_egedal_radial_envelope(
        psi, {"psi_axis": 0.0, "psi_edge": 1.0, "alpha": 2.0}
    )
    hot_parallel = np.full_like(psi, 1.5)
    hot_perpendicular = np.full_like(psi, 2.0)
    hot_density = np.full_like(psi, 0.4)
    pressure = assemble_frank_egedal_pressure(
        psi,
        radial,
        hot_parallel,
        hot_perpendicular,
        hot_density,
        {
            "hot_pressure_scale": 3.0,
            "gas_dynamic_pressure": 0.2,
            "gas_dynamic_density": 1.0e18,
            "hot_density_scale": 2.0e18,
            "electron_temperature": 1.0e-19,
        },
    )
    ion_parallel = radial * (0.2 + 3.0 * 1.5)
    ion_perpendicular = radial * (0.2 + 3.0 * 2.0)
    electron_pressure = pressure["density"] * 1.0e-19
    terminal = assemble_mirror_total_pressure(
        {
            "p_parallel_pa": ion_parallel,
            "p_perpendicular_pa": ion_perpendicular,
            "density_m3": pressure["density"],
        },
        {
            "electron_density_m3": pressure["density"],
            "electron_pressure_pa": electron_pressure,
            "relative_charge_residual": np.zeros_like(psi),
            "electrostatic_potential": np.zeros_like(psi),
        },
    )
    np.testing.assert_allclose(terminal["p_parallel"], pressure["p_parallel"])
    np.testing.assert_allclose(terminal["p_perpendicular"], pressure["p_perp"])

    psi_next = psi + 1.0e-3 * radial
    residual = compute_picard_flux_residual(psi, psi_next)["residual"]
    expected = float(np.linalg.norm(psi_next - psi) / np.linalg.norm(psi))
    np.testing.assert_allclose(residual, expected, rtol=2e-14)
    report = {
        "passed": True,
        "maximum_parallel_pressure_Pa": float(np.max(terminal["p_parallel"])),
        "maximum_perpendicular_pressure_Pa": float(np.max(terminal["p_perpendicular"])),
        "picard_flux_residual": residual,
        "criteria": "pressure assembly agrees with terminal state and residual matches an independent L2 ratio",
    }
    (output / "pressure_state_and_residual.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def reusable_complex_field_profile(output: Path) -> dict:
    """User: reuse a saved complex field to sample a later requested profile.

    This is a tiny executable version of the outbound P3 pattern: the first
    stage writes an intermediate field with the metadata required for later
    reuse, and the follow-up stage samples that field instead of recomputing the
    scientific relation at the profile points.
    """
    axes = {
        "x_m": np.array([0.0, 1.0, 2.0]),
        "y_m": np.array([-1.0, 0.5, 3.0]),
        "z_m": np.array([0.0, 0.25, 2.0]),
    }
    field = np.zeros((3, 3, 3), dtype=complex)
    for i, x in enumerate(axes["x_m"]):
        for j, y in enumerate(axes["y_m"]):
            for k, z in enumerate(axes["z_m"]):
                field[i, j, k] = (x + 2.0 * y - z) + 1j * (0.5 * x + z)
    support_mask = np.ones(field.shape, dtype=bool)
    support_mask[0, 0, 0] = False
    reusable_values = field.copy()
    reusable_values[~support_mask] = np.nan + 1j * np.nan

    axis_digest = _sha256_bytes(*(axes[key].tobytes() for key in ("x_m", "y_m", "z_m")))
    support_digest = _sha256_bytes(support_mask.tobytes())
    plan_version = "acceptance.reusable_complex_field_profile.v1"
    intermediate = output / "reusable_complex_field_intermediate.npz"
    np.savez(
        intermediate,
        x_m=axes["x_m"],
        y_m=axes["y_m"],
        z_m=axes["z_m"],
        values=reusable_values,
        support_mask=support_mask,
        coordinate_basis="cartesian_m",
        generation_plan_version=plan_version,
        axis_digest=axis_digest,
        support_mask_digest=support_digest,
    )
    intermediate_digest = "sha256:" + hashlib.sha256(intermediate.read_bytes()).hexdigest()

    with np.load(intermediate, allow_pickle=False) as saved:
        saved_axes = {key: saved[key] for key in ("x_m", "y_m", "z_m")}
        saved_values = saved["values"]
        saved_support = saved["support_mask"]
        assert saved["coordinate_basis"].item() == "cartesian_m"
        assert saved["generation_plan_version"].item() == plan_version
        assert saved["axis_digest"].item() == _sha256_bytes(
            *(saved_axes[key].tobytes() for key in ("x_m", "y_m", "z_m"))
        )
        assert saved["support_mask_digest"].item() == _sha256_bytes(saved_support.tobytes())
        assert saved_values.shape == saved_support.shape

    points = np.array(
        [
            [1.5, 2.0, 1.5],
            [0.25, -0.5, 0.125],
            [5.0, 0.0, 0.0],
        ]
    )
    sampled = interpolate_complex_rectilinear_field(saved_axes, saved_values, points)
    statuses = []
    rows = []
    for index, value in enumerate(sampled["interpolated_values"]):
        if not bool(sampled["valid_mask"][index]):
            status = "outside_grid_box"
        elif not np.isfinite(value):
            status = "stencil_touches_unsupported_cell"
        else:
            status = "sampled"
        statuses.append(status)
        rows.append(
            {
                "point_index": index,
                "x_m": float(points[index, 0]),
                "y_m": float(points[index, 1]),
                "z_m": float(points[index, 2]),
                "status": status,
                "real": None if not np.isfinite(value) else float(value.real),
                "imag": None if not np.isfinite(value) else float(value.imag),
            }
        )

    status_counts = {status: statuses.count(status) for status in sorted(set(statuses))}
    report = {
        "passed": True,
        "reused_intermediate": True,
        "sampling_asset_id": "scirel.geometry.complex-rectilinear-interpolation",
        "rows": len(rows),
        "finite_rows": status_counts.get("sampled", 0),
        "status_counts": status_counts,
        "metadata": {
            "source_axes_m": ["x_m", "y_m", "z_m"],
            "coordinate_basis": "cartesian_m",
            "support_mask_name": "support_mask",
            "generation_plan_version": plan_version,
            "intermediate_digest": intermediate_digest,
            "axis_digest": axis_digest,
            "support_mask_digest": support_digest,
        },
        "criteria": (
            "later profile sampling reuses a metadata-bound complex field, "
            "keeps unsupported cells non-finite, and separates geometric "
            "out-of-box from support-stencil failure"
        ),
        "samples": rows,
    }
    (output / "reusable_complex_field_profile.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def unbound_complex_field_profile(output: Path) -> dict:
    """User: explain why an old complex field cannot support strong reuse.

    This is the negative half of the outbound P3 artifact-format rule. A later
    request may see an older intermediate value file, but if it does not carry
    or strongly bind its axes, coordinate basis, support mask and plan/source
    digests, the run must not silently upgrade it into a strong reusable
    scientific input.
    """
    legacy_intermediate = output / "legacy_complex_field_intermediate.npz"
    np.savez(legacy_intermediate, values=np.ones((2, 2, 2), dtype=complex))

    required_bindings = [
        "source_axes_m",
        "coordinate_basis",
        "support_mask_name",
        "generation_plan_version",
        "axis_digest",
        "support_mask_digest",
    ]
    with np.load(legacy_intermediate) as archive:
        available_bindings = set(archive.files)
    missing_bindings = [
        binding for binding in required_bindings if binding not in available_bindings
    ]

    report = {
        "passed": True,
        "reused_intermediate": False,
        "evidence_ceiling": "insufficient_intermediate_bindings",
        "legacy_intermediate_digest": "sha256:"
        + hashlib.sha256(legacy_intermediate.read_bytes()).hexdigest(),
        "missing_bindings": missing_bindings,
        "rows": 1,
        "finite_rows": 0,
        "status_counts": {"not_sampled": 1},
        "samples": [
            {
                "point_index": 0,
                "status": "not_sampled",
                "reason": (
                    "legacy intermediate lacks the bindings needed to prove "
                    "coordinate axes, basis, support mask and generating plan"
                ),
            }
        ],
        "criteria": (
            "older intermediates with insufficient bindings are reported with "
            "an evidence ceiling instead of being silently reused"
        ),
    }
    (output / "unbound_complex_field_profile.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load_current_settings(rows: list[dict[str, object]]) -> dict[str, dict[str, float]]:
    settings: dict[str, dict[str, float]] = {}
    seen: set[tuple[str, str]] = set()
    for one_based_index, row in enumerate(rows, start=1):
        setting = str(row["setting"]).strip()
        coil_id = str(row["coil_id"]).strip()
        value = row.get("current_kA")
        if value in (None, ""):
            continue
        key = (setting, coil_id)
        if key in seen:
            raise ValueError(
                f"duplicate setting/coil row at line {one_based_index}: "
                f"{setting}/{coil_id}"
            )
        seen.add(key)
        settings.setdefault(setting, {})[coil_id] = float(value) * 1000.0
    return settings


def multi_coil_vacuum_followup(output: Path) -> dict:
    """User: extend a vacuum-coil preview without overwriting prior results.

    This is a small executable version of the outbound P4 pattern. The first
    stage writes a baseline comparison, the follow-up stage adds later current
    settings, and duplicate setting/coil rows are rejected before any field
    calculation can silently overwrite a drive current.
    """
    coil_templates = {
        "upper": {
            "r0_m": 0.72,
            "z0_m": 0.16,
            "nr": 2,
            "nz": 2,
            "dr_m": 0.04,
            "dz_m": 0.04,
            "weights": [0.25, 0.25, 0.25, 0.25],
        },
        "lower": {
            "r0_m": 0.72,
            "z0_m": -0.16,
            "nr": 2,
            "nz": 2,
            "dr_m": 0.04,
            "dz_m": 0.04,
            "weights": [0.25, 0.25, 0.25, 0.25],
        },
    }
    initial_rows = [
        {"setting": "balanced", "coil_id": "upper", "current_kA": 2.4},
        {"setting": "balanced", "coil_id": "lower", "current_kA": 2.4},
        {"setting": "shifted", "coil_id": "upper", "current_kA": 2.7},
        {"setting": "shifted", "coil_id": "lower", "current_kA": 2.1},
    ]
    followup_rows = [
        {"setting": "reverse", "coil_id": "upper", "current_kA": -2.4},
        {"setting": "reverse", "coil_id": "lower", "current_kA": -2.4},
        {"setting": "idle", "coil_id": "upper", "current_kA": 0.0},
        {"setting": "idle", "coil_id": "lower", "current_kA": 0.0},
        {"setting": "lab-note", "coil_id": "upper", "current_kA": ""},
    ]
    duplicate_rows = initial_rows + [
        {"setting": "balanced", "coil_id": "upper", "current_kA": 99.0}
    ]

    r_axis = np.array([0.45, 0.60, 0.75])
    z_axis = np.array([-0.10, 0.0, 0.10])
    r_grid, z_grid = np.meshgrid(r_axis, z_axis)

    def run_settings(rows: list[dict[str, object]], destination: Path) -> list[dict[str, object]]:
        settings = _load_current_settings(rows)
        output_rows = []
        for setting, currents_by_coil in settings.items():
            coils = []
            for coil_id, template in coil_templates.items():
                coil = dict(template)
                coil["current_a"] = currents_by_coil[coil_id]
                coils.append(coil)
            field = solve_multi_coil_vacuum_field(
                {"r_grid": r_grid, "z_grid": z_grid, "rectangular_coils": coils}
            )
            axis_column = 0
            mid_row = 1
            output_rows.append(
                {
                    "setting": setting,
                    "axis_b_r_T": float(field["b_r_vac"][mid_row, axis_column]),
                    "axis_b_z_T": float(field["b_z_vac"][mid_row, axis_column]),
                    "max_abs_b_T": float(
                        np.max(np.hypot(field["b_r_vac"], field["b_z_vac"]))
                    ),
                }
            )
        with destination.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(output_rows[0]))
            writer.writeheader()
            writer.writerows(output_rows)
        return output_rows

    initial_path = output / "multi_coil_initial_summary.csv"
    followup_path = output / "multi_coil_followup_summary.csv"
    initial = run_settings(initial_rows, initial_path)
    initial_digest_before = _sha256_file(initial_path)
    followup = run_settings(followup_rows, followup_path)
    initial_digest_after = _sha256_file(initial_path)

    duplicate_error = ""
    duplicate_rejected = False
    try:
        _load_current_settings(duplicate_rows)
    except ValueError as exc:
        duplicate_rejected = True
        duplicate_error = str(exc)

    report = {
        "passed": True,
        "model_scope": "axisymmetric_vacuum_field_only",
        "settings": [row["setting"] for row in initial + followup],
        "initial_rows": len(initial),
        "followup_rows": len(followup),
        "blank_current_rows_skipped": 1,
        "initial_summary_sha256_before_followup": initial_digest_before,
        "initial_summary_sha256_after_followup": initial_digest_after,
        "duplicate_current_row_rejected": duplicate_rejected,
        "duplicate_current_row_error": duplicate_error,
        "criteria": (
            "follow-up current settings write separate results, preserve the "
            "initial result bytes, distribute each declared total current "
            "across rectangular-coil filaments, and reject duplicate setting/"
            "coil rows before field evaluation"
        ),
    }
    (output / "multi_coil_vacuum_followup.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'installation': verify_installation(args.wheel), 'tasks': {
        'green_field_synthesis': green_field_synthesis(args.output),
        'quasineutral_profile': quasineutral_profile(args.output),
        'pressure_state_and_residual': pressure_state_and_residual(args.output),
        'reusable_complex_field_profile': reusable_complex_field_profile(args.output),
        'unbound_complex_field_profile': unbound_complex_field_profile(args.output),
        'multi_coil_vacuum_followup': multi_coil_vacuum_followup(args.output),
    }}
    (args.output/'acceptance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

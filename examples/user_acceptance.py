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
    superpose_current_green_field,
)
from scirel.kinetic import (
    assemble_frank_egedal_pressure,
    assemble_mirror_total_pressure,
    evaluate_frank_egedal_radial_envelope,
)


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
    }}
    (args.output/'acceptance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

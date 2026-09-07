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
from pathlib import Path
import zipfile

import numpy as np
import scirel
from scirel.field import integrate_filament_vacuum_field, compute_poloidal_field_magnitude, solve_multi_coil_vacuum_field
from scirel.geometry import sample_rectilinear_field
from scirel.diagnostics import synthesize_equilibrium_diagnostics, reduce_observation_residuals, compute_parallel_pressure_residual
from scirel.closures import solve_mirror_quasineutral_closure, solve_mirror_ambipolar_potential


def verify_installation(wheel: Path) -> dict:
    distribution = importlib.metadata.distribution('scirel')
    package_root = Path(distribution.locate_file('scirel')).resolve()
    assert Path(scirel.__file__).resolve().parent == package_root
    assert package_root == Path('/opt/scirel/scirel'), 'use the platform-prepared runtime image'
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


def current_scan(output: Path) -> dict:
    """User: compare three coil currents at fixed probe positions and export a CSV."""
    r, z = np.meshgrid(np.linspace(0., .3, 17), np.linspace(-.2, .2, 9))
    points = np.array([[0., 0.], [.15, .1], [.3, -.1]])
    rows, baseline = [], None
    for current in (100., 250., 500.):
        field = integrate_filament_vacuum_field(r, z, [[.8, -.35, current], [.8, .35, current]])
        magnitude = compute_poloidal_field_magnitude(field['b_r'], field['b_z'])['B']
        probes = sample_rectilinear_field(r, z, magnitude, points)['samples']
        analytic_center = 4e-7*np.pi*current*.8**2/(.8**2+.35**2)**1.5
        np.testing.assert_allclose(probes[0], analytic_center, rtol=2e-14)
        if baseline is None:
            baseline = probes/current
        np.testing.assert_allclose(probes/current, baseline, rtol=2e-14)
        assert np.all(probes > 0.)
        for (radius, axial), value in zip(points, probes):
            rows.append({'current_A': current, 'R_m': radius, 'Z_m': axial, 'B_T': float(value)})
    with (output/'coil_current_scan.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return {'passed': True, 'rows': len(rows), 'center_B_T_at_100A': rows[0]['B_T'],
            'criteria': 'analytic on-axis two-loop field and linear current scaling, rtol=2e-14'}


def composed_graph_diagnostics() -> dict:
    """User: synthesize anti-Helmholtz measurements and quantify known sensor offsets."""
    r, z = np.meshgrid(np.linspace(0., .3, 7), np.linspace(-.25, .25, 11))
    coils = [dict(r0_m=.75, z0_m=axial, nr=1, nz=1, dr_m=.02, dz_m=.02, current_a=current)
             for axial, current in [(-.4, 200.), (.4, -200.)]]
    result = solve_multi_coil_vacuum_field(r_grid=r, z_grid=z, rectangular_coils=coils)
    np.testing.assert_allclose(result['b_z_vac'], -result['b_z_vac'][::-1], atol=2e-18)
    np.testing.assert_allclose(result['b_r_vac'], result['b_r_vac'][::-1], atol=2e-18)
    assert abs(result['b_z_vac'][5, 0]) < 1e-18
    points = np.array([[.1, -.15], [.2, .1], [.3, .2]])
    request = {'flux_loops': {'points': points}}
    predicted = synthesize_equilibrium_diagnostics(equilibrium={'psi': result['psi_vac']}, observations=request, R=r, Z=z)
    sigma = np.array([1e-8, 2e-8, 3e-8])
    offsets = np.array([1., -2., 3.])
    observed = {'flux_loops': {'values': predicted['flux_loops'] - sigma*offsets, 'sigma': sigma}}
    residual = reduce_observation_residuals(predicted=predicted, observations=observed)
    np.testing.assert_allclose(residual['residual_vector'], offsets, atol=2e-12)
    np.testing.assert_allclose(residual['chi2'], 14., atol=2e-11)
    return {'passed': True, 'chi2': residual['chi2'], 'predicted_flux_Wb': predicted['flux_loops'].tolist(),
            'criteria': 'opposing-current reflection symmetry, axial null, known normalized offsets [1,-2,3]'}


def boundary_contracts() -> dict:
    """User: reject unsolvable species inputs and undefined diagnostics before using results."""
    charge = 1.602176634e-19
    valid = dict(b_t=1., psi=np.array([0., 1.]), mass_kg=1.67e-27, charge_c=charge,
                 density_ref_m3=[1e18, 0.], temperature_parallel_j=100*charge,
                 temperature_perpendicular_ref_j=100*charge, b_ref_t=1.,
                 electron_temperature_j=100*charge, electron_density_ref_m3=[1e18, 0.])
    state = solve_mirror_quasineutral_closure(**valid)
    assert state['converged']
    np.testing.assert_allclose(state['relative_charge_residual'], 0., atol=1e-9)
    rejected = []
    calls = [
        ('quasineutral_one_sided_vacuum', lambda: solve_mirror_quasineutral_closure(**{**valid, 'electron_density_ref_m3': [0., 0.]}), 'both positive or both zero'),
        ('end_loss_one_sided_vacuum', lambda: solve_mirror_ambipolar_potential(1., 2., 0., 1.67e-27, charge, 1e18, 100*charge, 100*charge, 100*charge, electron_density_ref_m3=0.), 'both positive or both zero'),
        ('partial_duplicate_field_diagnostic', lambda: compute_parallel_pressure_residual([1., 1., 2., 3.], np.zeros(4), [1., 1., 2., 3.], strict=True), 'unique'),
    ]
    for name, call, message in calls:
        try:
            call()
        except ValueError as error:
            assert message in str(error)
            rejected.append(name)
        else:
            raise AssertionError(f'{name} was incorrectly accepted')
    return {'passed': True, 'rejected': rejected, 'criteria': 'joint vacuum valid; one-sided vacuum and partial duplicate B fail explicitly'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {'installation': verify_installation(args.wheel), 'tasks': {
        'current_scan': current_scan(args.output),
        'graph_diagnostics': composed_graph_diagnostics(),
        'boundary_contracts': boundary_contracts(),
    }}
    (args.output/'acceptance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

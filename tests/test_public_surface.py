import numpy as np

import scirel

from scirel.kinetic.frank_egedal_pressure_state import assemble_frank_egedal_pressure
from scirel.kinetic.frank_egedal_radial_envelope import evaluate_frank_egedal_radial_envelope
from scirel.kinetic.frank_egedal_source_projection import project_frank_egedal_source_modes
from scirel.kinetic.frank_egedal_hot_ion_moments import evaluate_frank_egedal_hot_ion_moments
from scirel.closures.hall_two_fluid_pressure import close_hall_two_fluid_pressure
from scirel.diagnostics.picard_flux_residual import compute_picard_flux_residual
from scirel.closures.quasineutral_reference_density import compute_reference_electron_density
from scirel.closures.quasineutral_potential import solve_quasineutral_potential
from scirel.equilibrium.isotropic_picard_step import pressure_flux_picard_step
from scirel.equilibrium.pressure_flux_state import build_pressure_flux_state
from scirel.kinetic.mirror_invariant_distribution import evaluate_mirror_invariant_distribution
from scirel.kinetic.mirror_total_pressure import assemble_mirror_total_pressure
from scirel.kinetic.mirror_constrained_moments import evaluate_mirror_constrained_moments
from scirel.equilibrium.anisotropic_picard_feedback import update_anisotropic_picard_flux
from scirel.equilibrium.anisotropic_toroidal_current import compute_anisotropic_toroidal_current
from scirel.inference.latin_hypercube_sampling import sample_latin_hypercube
from scirel.inference.anisotropic_parameter_optimization import optimize_anisotropic_parameters
from scirel.diagnostics.observation_residuals import reduce_observation_residuals
from scirel.diagnostics.parallel_pressure_residual import compute_parallel_pressure_residual
from scirel.kinetic.loss_cone_spectrum import solve_loss_cone_spectrum
from scirel.kinetic.plasma_dispersion import evaluate_plasma_dispersion
from scirel.field.poloidal_field_magnitude import compute_poloidal_field_magnitude
from scirel.field.permanent_ring_filaments import discretize_permanent_ring
from scirel.diagnostics.firehose_mirror_margins import compute_firehose_mirror_margins
from scirel.field.ideal_conductor_boundary import correct_ideal_conductor_boundary_flux
from scirel.closures.boltzmann_quasineutrality import compute_boltzmann_electron_state
from scirel.field.rectangular_coil_filaments import discretize_rectangular_coil
from scirel.closures.tabulated_pressure_closure import evaluate_tabulated_pressure
from scirel.field.current_green_superposition import superpose_current_green_field
from scirel.geometry.bilinear_grid_sampling import sample_rectilinear_field
from scirel.geometry.flux_surface_profile import evaluate_flux_surface_profile
from scirel.geometry.axisymmetric_grid_mapping import map_axisymmetric_equilibrium_to_cartesian_grid
from scirel.geometry.material_support import classify_material_support
from scirel.geometry.axisymmetric_equilibrium_grid_support import solve_axisymmetric_equilibrium_grid_mapping
from scirel.geometry.complex_rectilinear_interpolation import interpolate_complex_rectilinear_field
from scirel.diagnostics.species_absorption_fraction import compute_species_absorption_fraction
from scirel.equilibrium.axisymmetric_picard_update import update_axisymmetric_picard_flux
from scirel.geometry.flux_surface_inverse_field_average import compute_flux_surface_inverse_field_average
from scirel.closures.reduced_hall_drift import close_reduced_hall_drift
from scirel.equilibrium.anisotropic_force_balance import compute_anisotropic_force_balance
from scirel.field.filament_vacuum_field import integrate_filament_vacuum_field
from scirel.field.circular_filament_green import circular_filament_green_response
from scirel.field.poloidal_field_from_flux import poloidal_field_from_flux
from scirel.field.dense_axisymmetric_green import dense_axisymmetric_green_response
from scirel.field.mirror_plasma_green import build_mirror_plasma_flux_green
from scirel.closures.mirror_ambipolar_potential import solve_mirror_ambipolar_potential
from scirel.equilibrium.free_boundary_anisotropic_picard import solve_free_boundary_anisotropic_picard
from scirel.equilibrium.isotropic_pressure_flux import solve_isotropic_pressure_flux
from scirel.diagnostics.equilibrium_synthesis_diagnostics import synthesize_equilibrium_diagnostics
from scirel.closures.mirror_quasineutral_closure import solve_mirror_quasineutral_closure
from scirel.kinetic.grid_mirror_kinetic_closure import solve_grid_mirror_kinetic_closure
from scirel.equilibrium.axisymmetric_anisotropic_picard import solve_axisymmetric_anisotropic_picard
from scirel.inference.direct_anisotropic_inversion import solve_direct_anisotropic_inversion
from scirel.inference.anisotropic_trial_evaluation import evaluate_anisotropic_trial
from scirel.equilibrium.reduced_hall_anisotropic_picard import solve_reduced_hall_anisotropic_picard
from scirel.equilibrium.kinetic_mirror_hall_equilibrium import solve_kinetic_mirror_hall_equilibrium
from scirel.field.multi_coil_vacuum_field import solve_multi_coil_vacuum_field
from scirel.kinetic.frank_egedal_pressure_closure import solve_frank_egedal_pressure_closure
from scirel.collisions.relativistic_maxwellian_bessel import (
    BesselBackendEvaluationError,
    InvalidBesselArgumentError,
    relativistic_maxwellian_bessel,
)
from scirel.collisions.momentum_scales import normalized_momentum, thermal_electron_momentum
from scirel.fusion.dd_neutron_lab_energy import calculate_dd_neutron_lab_energy_kev
from scirel.dielectric.cold_plasma_tensor import (
    ColdPlasmaOverflowError,
    ColdPlasmaResonanceError,
    cold_plasma_dielectric_tensor,
)


def test_all_normalized_public_callables_are_importable():
    assert all(callable(value) for value in [
        assemble_frank_egedal_pressure,
        evaluate_frank_egedal_radial_envelope,
        project_frank_egedal_source_modes,
        evaluate_frank_egedal_hot_ion_moments,
        close_hall_two_fluid_pressure,
        compute_picard_flux_residual,
        compute_reference_electron_density,
        solve_quasineutral_potential,
        pressure_flux_picard_step,
        build_pressure_flux_state,
        evaluate_mirror_invariant_distribution,
        assemble_mirror_total_pressure,
        evaluate_mirror_constrained_moments,
        update_anisotropic_picard_flux,
        compute_anisotropic_toroidal_current,
        sample_latin_hypercube,
        optimize_anisotropic_parameters,
        reduce_observation_residuals,
        compute_parallel_pressure_residual,
        solve_loss_cone_spectrum,
        evaluate_plasma_dispersion,
        compute_poloidal_field_magnitude,
        discretize_permanent_ring,
        compute_firehose_mirror_margins,
        correct_ideal_conductor_boundary_flux,
        compute_boltzmann_electron_state,
        discretize_rectangular_coil,
        evaluate_tabulated_pressure,
        superpose_current_green_field,
        sample_rectilinear_field,
        evaluate_flux_surface_profile,
        update_axisymmetric_picard_flux,
        compute_flux_surface_inverse_field_average,
        close_reduced_hall_drift,
        compute_anisotropic_force_balance,
        integrate_filament_vacuum_field,
        circular_filament_green_response,
        poloidal_field_from_flux,
        dense_axisymmetric_green_response,
        build_mirror_plasma_flux_green,
        solve_mirror_ambipolar_potential,
        solve_free_boundary_anisotropic_picard,
        solve_isotropic_pressure_flux,
        synthesize_equilibrium_diagnostics,
        solve_mirror_quasineutral_closure,
        solve_grid_mirror_kinetic_closure,
        solve_axisymmetric_anisotropic_picard,
        solve_direct_anisotropic_inversion,
        evaluate_anisotropic_trial,
        solve_reduced_hall_anisotropic_picard,
        solve_kinetic_mirror_hall_equilibrium,
        solve_multi_coil_vacuum_field,
        solve_frank_egedal_pressure_closure,
        map_axisymmetric_equilibrium_to_cartesian_grid,
        classify_material_support,
        solve_axisymmetric_equilibrium_grid_mapping,
        interpolate_complex_rectilinear_field,
        compute_species_absorption_fraction,
        relativistic_maxwellian_bessel,
        normalized_momentum,
        thermal_electron_momentum,
        calculate_dd_neutron_lab_energy_kev,
        cold_plasma_dielectric_tensor,
    ])
    assert hasattr(scirel, 'field') and hasattr(scirel, 'equilibrium')
    assert hasattr(scirel, 'collisions') and hasattr(scirel, 'fusion')
    assert hasattr(scirel, 'dielectric')
    # The two rejection classes are classes rather than callables, so they are
    # asserted as the ValueError subclasses the relation promises to raise.
    assert issubclass(InvalidBesselArgumentError, ValueError)
    assert issubclass(BesselBackendEvaluationError, ValueError)
    assert issubclass(ColdPlasmaResonanceError, ValueError)
    assert issubclass(ColdPlasmaOverflowError, ValueError)


def test_root_namespace_supports_normal_python_imports():
    namespace = {}
    exec('from scirel import *', namespace)
    assert all(callable(namespace[name]) for name in scirel.__all__ if not hasattr(scirel, name) or not hasattr(getattr(scirel, name), '__path__'))


def test_kinetic_star_exports_keep_existing_scientific_relations():
    assert "evaluate_mirror_constrained_moments" in scirel.kinetic.__all__
    assert "evaluate_plasma_dispersion" in scirel.kinetic.__all__
    assert all(hasattr(scirel.kinetic, name) for name in scirel.kinetic.__all__)


def test_poloidal_field_and_magnitude_smoke():
    r, z = np.meshgrid(np.linspace(0.0, 0.4, 5), np.linspace(-0.2, 0.2, 5))
    field = poloidal_field_from_flux(r, z, 0.5 * r**2)
    assert field['B'].shape == r.shape
    magnitude = compute_poloidal_field_magnitude(field['B_R'], field['B_Z'])
    np.testing.assert_allclose(magnitude['B'], field['B'])


def test_poloidal_field_magnitude_handles_large_finite_components():
    result = compute_poloidal_field_magnitude([[1.0e308]], [[1.0e308]])
    assert np.isfinite(result['B']).all()
    np.testing.assert_allclose(result['B'], [[np.sqrt(2.0) * 1.0e308]])


def test_simple_geometry_and_green_smoke():
    coil = discretize_rectangular_coil(0.3, 0.0, 2, 2, 0.02, 0.02)
    assert coil.shape == (4, 2)
    weighted_coil = np.column_stack((coil, np.ones(coil.shape[0])))
    response = circular_filament_green_response(weighted_coil, coil + np.array([0.0, 0.03]))
    assert response['gpsi'].shape == (4,)


def test_pressure_flux_picard_zero_green_smoke():
    r, z = np.meshgrid(np.linspace(0.1, 0.4, 5), np.linspace(-0.2, 0.2, 5))
    result = solve_isotropic_pressure_flux({
        'r_grid': r, 'z_grid': z, 'psi_vac': 0.5 * r**2,
        'g_psi': np.zeros((r.size, r.size)),
        'pressure_of_radius': lambda radius: np.maximum(0.4 - np.asarray(radius, dtype=float), 0.0),
        'tol': 1.0e-12, 'maxiter': 2, 'relax': 0.2,
    })
    assert result['converged'] and result['psi'].shape == r.shape

"""Scientific Relations Library, with scientific domains loaded on demand.

Prefer domain imports, for example ``from scirel import field``. Existing
top-level function aliases remain available for compatibility. Importing
``scirel`` alone does not import scientific backends.
"""

from importlib import import_module as _import_module

# Explicit bindings keep discovery independent of scientific imports.
_EXPORTS = {
    'closures': ('.closures', None),
    'collisions': ('.collisions', None),
    'diagnostics': ('.diagnostics', None),
    'dielectric': ('.dielectric', None),
    'equilibrium': ('.equilibrium', None),
    'field': ('.field', None),
    'fusion': ('.fusion', None),
    'geometry': ('.geometry', None),
    'inference': ('.inference', None),
    'kinetic': ('.kinetic', None),
    'assemble_frank_egedal_pressure': ('.kinetic.frank_egedal_pressure_state', 'assemble_frank_egedal_pressure'),
    'evaluate_frank_egedal_radial_envelope': ('.kinetic.frank_egedal_radial_envelope', 'evaluate_frank_egedal_radial_envelope'),
    'project_frank_egedal_source_modes': ('.kinetic.frank_egedal_source_projection', 'project_frank_egedal_source_modes'),
    'evaluate_frank_egedal_hot_ion_moments': ('.kinetic.frank_egedal_hot_ion_moments', 'evaluate_frank_egedal_hot_ion_moments'),
    'close_hall_two_fluid_pressure': ('.closures.hall_two_fluid_pressure', 'close_hall_two_fluid_pressure'),
    'compute_picard_flux_residual': ('.diagnostics.picard_flux_residual', 'compute_picard_flux_residual'),
    'compute_reference_electron_density': ('.closures.quasineutral_reference_density', 'compute_reference_electron_density'),
    'solve_quasineutral_potential': ('.closures.quasineutral_potential', 'solve_quasineutral_potential'),
    'pressure_flux_picard_step': ('.equilibrium.isotropic_picard_step', 'pressure_flux_picard_step'),
    'build_pressure_flux_state': ('.equilibrium.pressure_flux_state', 'build_pressure_flux_state'),
    'evaluate_mirror_invariant_distribution': ('.kinetic.mirror_invariant_distribution', 'evaluate_mirror_invariant_distribution'),
    'assemble_mirror_total_pressure': ('.kinetic.mirror_total_pressure', 'assemble_mirror_total_pressure'),
    'evaluate_mirror_constrained_moments': ('.kinetic.mirror_constrained_moments', 'evaluate_mirror_constrained_moments'),
    'update_anisotropic_picard_flux': ('.equilibrium.anisotropic_picard_feedback', 'update_anisotropic_picard_flux'),
    'compute_anisotropic_toroidal_current': ('.equilibrium.anisotropic_toroidal_current', 'compute_anisotropic_toroidal_current'),
    'sample_latin_hypercube': ('.inference.latin_hypercube_sampling', 'sample_latin_hypercube'),
    'optimize_anisotropic_parameters': ('.inference.anisotropic_parameter_optimization', 'optimize_anisotropic_parameters'),
    'evaluate_anisotropic_trial': ('.inference.anisotropic_trial_evaluation', 'evaluate_anisotropic_trial'),
    'reduce_observation_residuals': ('.diagnostics.observation_residuals', 'reduce_observation_residuals'),
    'compute_parallel_pressure_residual': ('.diagnostics.parallel_pressure_residual', 'compute_parallel_pressure_residual'),
    'solve_loss_cone_spectrum': ('.kinetic.loss_cone_spectrum', 'solve_loss_cone_spectrum'),
    'evaluate_plasma_dispersion': ('.kinetic.plasma_dispersion', 'evaluate_plasma_dispersion'),
    'evaluate_bessel_gamma': ('.kinetic.bessel_gamma', 'evaluate_bessel_gamma'),
    'evaluate_kinetic_dispersion_sum': ('.kinetic.kinetic_dispersion_sum_n', 'evaluate_kinetic_dispersion_sum'),
    'derive_species_equilibrium_scales': ('.kinetic.species_equilibrium_scales', 'derive_species_equilibrium_scales'),
    'compute_thermal_speed_m_s': ('.kinetic.thermal_speed_scale', 'compute_thermal_speed_m_s'),
    'reduce_generation_density': ('.kinetic.generation_density_reduction', 'reduce_generation_density'),
    'compute_poloidal_field_magnitude': ('.field.poloidal_field_magnitude', 'compute_poloidal_field_magnitude'),
    'discretize_permanent_ring': ('.field.permanent_ring_filaments', 'discretize_permanent_ring'),
    'compute_firehose_mirror_margins': ('.diagnostics.firehose_mirror_margins', 'compute_firehose_mirror_margins'),
    'correct_ideal_conductor_boundary_flux': ('.field.ideal_conductor_boundary', 'correct_ideal_conductor_boundary_flux'),
    'compute_boltzmann_electron_state': ('.closures.boltzmann_quasineutrality', 'compute_boltzmann_electron_state'),
    'discretize_rectangular_coil': ('.field.rectangular_coil_filaments', 'discretize_rectangular_coil'),
    'evaluate_tabulated_pressure': ('.closures.tabulated_pressure_closure', 'evaluate_tabulated_pressure'),
    'superpose_current_green_field': ('.field.current_green_superposition', 'superpose_current_green_field'),
    'sample_rectilinear_field': ('.geometry.bilinear_grid_sampling', 'sample_rectilinear_field'),
    'evaluate_flux_surface_profile': ('.geometry.flux_surface_profile', 'evaluate_flux_surface_profile'),
    'update_axisymmetric_picard_flux': ('.equilibrium.axisymmetric_picard_update', 'update_axisymmetric_picard_flux'),
    'compute_flux_surface_inverse_field_average': ('.geometry.flux_surface_inverse_field_average', 'compute_flux_surface_inverse_field_average'),
    'map_axisymmetric_equilibrium_to_cartesian_grid': ('.geometry.axisymmetric_grid_mapping', 'map_axisymmetric_equilibrium_to_cartesian_grid'),
    'classify_material_support': ('.geometry.material_support', 'classify_material_support'),
    'solve_axisymmetric_equilibrium_grid_mapping': ('.geometry.axisymmetric_equilibrium_grid_support', 'solve_axisymmetric_equilibrium_grid_mapping'),
    'interpolate_complex_rectilinear_field': ('.geometry.complex_rectilinear_interpolation', 'interpolate_complex_rectilinear_field'),
    'compute_species_absorption_fraction': ('.diagnostics.species_absorption_fraction', 'compute_species_absorption_fraction'),
    'close_reduced_hall_drift': ('.closures.reduced_hall_drift', 'close_reduced_hall_drift'),
    'compute_anisotropic_force_balance': ('.equilibrium.anisotropic_force_balance', 'compute_anisotropic_force_balance'),
    'integrate_filament_vacuum_field': ('.field.filament_vacuum_field', 'integrate_filament_vacuum_field'),
    'circular_filament_green_response': ('.field.circular_filament_green', 'circular_filament_green_response'),
    'poloidal_field_from_flux': ('.field.poloidal_field_from_flux', 'poloidal_field_from_flux'),
    'dense_axisymmetric_green_response': ('.field.dense_axisymmetric_green', 'dense_axisymmetric_green_response'),
    'build_mirror_plasma_flux_green': ('.field.mirror_plasma_green', 'build_mirror_plasma_flux_green'),
    'solve_mirror_ambipolar_potential': ('.closures.mirror_ambipolar_potential', 'solve_mirror_ambipolar_potential'),
    'solve_free_boundary_anisotropic_picard': ('.equilibrium.free_boundary_anisotropic_picard', 'solve_free_boundary_anisotropic_picard'),
    'solve_isotropic_pressure_flux': ('.equilibrium.isotropic_pressure_flux', 'solve_isotropic_pressure_flux'),
    'synthesize_equilibrium_diagnostics': ('.diagnostics.equilibrium_synthesis_diagnostics', 'synthesize_equilibrium_diagnostics'),
    'solve_mirror_quasineutral_closure': ('.closures.mirror_quasineutral_closure', 'solve_mirror_quasineutral_closure'),
    'solve_grid_mirror_kinetic_closure': ('.kinetic.grid_mirror_kinetic_closure', 'solve_grid_mirror_kinetic_closure'),
    'solve_axisymmetric_anisotropic_picard': ('.equilibrium.axisymmetric_anisotropic_picard', 'solve_axisymmetric_anisotropic_picard'),
    'solve_direct_anisotropic_inversion': ('.inference.direct_anisotropic_inversion', 'solve_direct_anisotropic_inversion'),
    'solve_reduced_hall_anisotropic_picard': ('.equilibrium.reduced_hall_anisotropic_picard', 'solve_reduced_hall_anisotropic_picard'),
    'solve_kinetic_mirror_hall_equilibrium': ('.equilibrium.kinetic_mirror_hall_equilibrium', 'solve_kinetic_mirror_hall_equilibrium'),
    'solve_multi_coil_vacuum_field': ('.field.multi_coil_vacuum_field', 'solve_multi_coil_vacuum_field'),
    'solve_frank_egedal_pressure_closure': ('.kinetic.frank_egedal_pressure_closure', 'solve_frank_egedal_pressure_closure'),
    'BesselBackendEvaluationError': ('.collisions.relativistic_maxwellian_bessel', 'BesselBackendEvaluationError'),
    'InvalidBesselArgumentError': ('.collisions.relativistic_maxwellian_bessel', 'InvalidBesselArgumentError'),
    'relativistic_maxwellian_bessel': ('.collisions.relativistic_maxwellian_bessel', 'relativistic_maxwellian_bessel'),
    'normalized_momentum': ('.collisions.momentum_scales', 'normalized_momentum'),
    'thermal_electron_momentum': ('.collisions.momentum_scales', 'thermal_electron_momentum'),
    'calculate_dd_neutron_lab_energy_kev': ('.fusion.dd_neutron_lab_energy', 'calculate_dd_neutron_lab_energy_kev'),
    'ColdPlasmaOverflowError': ('.dielectric.cold_plasma_tensor', 'ColdPlasmaOverflowError'),
    'ColdPlasmaResonanceError': ('.dielectric.cold_plasma_tensor', 'ColdPlasmaResonanceError'),
    'cold_plasma_dielectric_tensor': ('.dielectric.cold_plasma_tensor', 'cold_plasma_dielectric_tensor'),
    'normalize_incoming_neutral_boundary': ('.kinetic.incoming_boundary_flux_normalization', 'normalize_incoming_neutral_boundary'),
    'normalize_spatial_source_shape': ('.kinetic.spatial_source_shape_normalization', 'normalize_spatial_source_shape'),
    'make_cylindrical_velocity_quadrature': ('.kinetic.cylindrical_velocity_quadrature', 'make_cylindrical_velocity_quadrature'),
    'average_cross_section_over_maxwellian': ('.collisions.maxwellian_relative_speed_rate_average', 'average_cross_section_over_maxwellian'),
    'build_shifted_maxwellian_seed': ('.kinetic.shifted_maxwellian_seed', 'build_shifted_maxwellian_seed'),
    'reduce_axisymmetric_neutral_moments': ('.kinetic.axisymmetric_neutral_moments', 'reduce_axisymmetric_neutral_moments'),
    'create_adaptive_neutral_velocity_mesh': ('.kinetic.adaptive_neutral_velocity_mesh', 'create_adaptive_neutral_velocity_mesh'),
    'interpolate_scalar_across_mesh': ('.kinetic.cross_mesh_scalar_interpolation', 'interpolate_scalar_across_mesh'),
    'interp_distribution_across_mesh': ('.kinetic.cross_mesh_distribution_interpolation', 'interp_distribution_across_mesh'),
    'assemble_neutral_upwind_transport_coefficients': ('.kinetic.upwind_transport_coefficients', 'assemble_neutral_upwind_transport_coefficients'),
    'propagate_neutral_generation': ('.kinetic.neutral_generation_propagation', 'propagate_neutral_generation'),
    'assemble_neutral_boltzmann_rhs': ('.kinetic.neutral_boltzmann_rhs', 'assemble_neutral_boltzmann_rhs'),
    'evaluate_neutral_generation_stopping': ('.kinetic.neutral_generation_stopping', 'evaluate_neutral_generation_stopping'),
    'update_neutral_generation_accumulation': ('.kinetic.generation_accumulation_update', 'update_neutral_generation_accumulation'),
    'evaluate_neutral_outer_seed_convergence': ('.kinetic.outer_seed_convergence', 'evaluate_neutral_outer_seed_convergence'),
    'evaluate_kn1d_outer_convergence': ('.kinetic.kn1d_outer_convergence', 'evaluate_kn1d_outer_convergence'),
    'compute_pointwise_firehose_margin': ('.diagnostics.pointwise_firehose_margin', 'compute_pointwise_firehose_margin'),
    'evaluate_h_saha_equilibrium_population': ('.kinetic.hydrogen_saha_equilibrium_population', 'evaluate_h_saha_equilibrium_population'),
    'evaluate_cauchy_transform': ('.kinetic.cauchy_transform', 'evaluate_cauchy_transform'),
    'evaluate_maxwellian_electrostatic': ('.kinetic.maxwellian_electrostatic', 'evaluate_maxwellian_electrostatic'),
    'solve_maxwellian_electrostatic_mode': ('.kinetic.maxwellian_electrostatic', 'solve_maxwellian_electrostatic_mode'),
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    try:
        module, symbol = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = _import_module(module, __name__)
    if symbol is not None:
        value = getattr(value, symbol)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))

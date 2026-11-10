"""Private runtime registry used only by normalized composition wrappers."""

from importlib import import_module

_ASSETS = {
    "scirel.mirror.frank_egedal_pressure_state": (
        "scirel.mirror.frank_egedal_pressure_state",
        "assemble_frank_egedal_pressure",
    ),
    "scirel.mirror.frank_egedal_radial_envelope": (
        "scirel.mirror.frank_egedal_radial_envelope",
        "evaluate_frank_egedal_radial_envelope",
    ),
    "scirel.mirror.frank_egedal_source_projection": (
        "scirel.mirror.frank_egedal_source_projection",
        "project_frank_egedal_source_modes",
    ),
    "scirel.mirror.frank_egedal_hot_ion_moments": (
        "scirel.mirror.frank_egedal_hot_ion_moments",
        "evaluate_frank_egedal_hot_ion_moments",
    ),
    "scirel.closures.hall_two_fluid_pressure": (
        "scirel.closures.hall_two_fluid_pressure",
        "close_hall_two_fluid_pressure",
    ),
    "scirel.diagnostics.picard_flux_residual": (
        "scirel.diagnostics.picard_flux_residual",
        "compute_picard_flux_residual",
    ),
    "scirel.closures.quasineutral_reference_density": (
        "scirel.closures.quasineutral_reference_density",
        "compute_reference_electron_density",
    ),
    "scirel.closures.quasineutral_potential": (
        "scirel.closures.quasineutral_potential",
        "solve_quasineutral_potential",
    ),
    "scirel.equilibrium.isotropic_picard_step": (
        "scirel.equilibrium.isotropic_picard_step",
        "pressure_flux_picard_step",
    ),
    "scirel.equilibrium.pressure_flux_state": (
        "scirel.equilibrium.pressure_flux_state",
        "build_pressure_flux_state",
    ),
    "scirel.mirror.mirror_invariant_distribution": (
        "scirel.mirror.mirror_invariant_distribution",
        "evaluate_mirror_invariant_distribution",
    ),
    "scirel.mirror.mirror_total_pressure": (
        "scirel.mirror.mirror_total_pressure",
        "assemble_mirror_total_pressure",
    ),
    "scirel.mirror.mirror_constrained_moments": (
        "scirel.mirror.mirror_constrained_moments",
        "evaluate_mirror_constrained_moments",
    ),
    "scirel.equilibrium.anisotropic_picard_feedback": (
        "scirel.equilibrium.anisotropic_picard_feedback",
        "update_anisotropic_picard_flux",
    ),
    "scirel.equilibrium.anisotropic_toroidal_current": (
        "scirel.equilibrium.anisotropic_toroidal_current",
        "compute_anisotropic_toroidal_current",
    ),
    "scirel.inference.latin_hypercube_sampling": (
        "scirel.inference.latin_hypercube_sampling",
        "sample_latin_hypercube",
    ),
    "scirel.inference.anisotropic_parameter_optimization": (
        "scirel.inference.anisotropic_parameter_optimization",
        "optimize_anisotropic_parameters",
    ),
    "scirel.inference.anisotropic_trial_evaluation": (
        "scirel.inference.anisotropic_trial_evaluation",
        "evaluate_anisotropic_trial",
    ),
    "scirel.diagnostics.observation_residuals": (
        "scirel.diagnostics.observation_residuals",
        "reduce_observation_residuals",
    ),
    "scirel.diagnostics.parallel_pressure_residual": (
        "scirel.diagnostics.parallel_pressure_residual",
        "compute_parallel_pressure_residual",
    ),
    "scirel.mirror.loss_cone_spectrum": (
        "scirel.mirror.loss_cone_spectrum",
        "solve_loss_cone_spectrum",
    ),
    "scirel.field.poloidal_field_magnitude": (
        "scirel.field.poloidal_field_magnitude",
        "compute_poloidal_field_magnitude",
    ),
    "scirel.field.permanent_ring_filaments": (
        "scirel.field.permanent_ring_filaments",
        "discretize_permanent_ring",
    ),
    "scirel.diagnostics.firehose_mirror_margins": (
        "scirel.diagnostics.firehose_mirror_margins",
        "compute_firehose_mirror_margins",
    ),
    "scirel.field.ideal_conductor_boundary": (
        "scirel.field.ideal_conductor_boundary",
        "correct_ideal_conductor_boundary_flux",
    ),
    "scirel.closures.boltzmann_quasineutrality": (
        "scirel.closures.boltzmann_quasineutrality",
        "compute_boltzmann_electron_state",
    ),
    "scirel.field.rectangular_coil_filaments": (
        "scirel.field.rectangular_coil_filaments",
        "discretize_rectangular_coil",
    ),
    "scirel.closures.tabulated_pressure_closure": (
        "scirel.closures.tabulated_pressure_closure",
        "evaluate_tabulated_pressure",
    ),
    "scirel.field.current_green_superposition": (
        "scirel.field.current_green_superposition",
        "superpose_current_green_field",
    ),
    "scirel.geometry.bilinear_grid_sampling": (
        "scirel.geometry.bilinear_grid_sampling",
        "sample_rectilinear_field",
    ),
    "scirel.geometry.flux_surface_profile": (
        "scirel.geometry.flux_surface_profile",
        "evaluate_flux_surface_profile",
    ),
    "scirel.equilibrium.axisymmetric_picard_update": (
        "scirel.equilibrium.axisymmetric_picard_update",
        "update_axisymmetric_picard_flux",
    ),
    "scirel.geometry.flux_surface_inverse_field_average": (
        "scirel.geometry.flux_surface_inverse_field_average",
        "compute_flux_surface_inverse_field_average",
    ),
    "scirel.closures.reduced_hall_drift": (
        "scirel.closures.reduced_hall_drift",
        "close_reduced_hall_drift",
    ),
    "scirel.equilibrium.anisotropic_force_balance": (
        "scirel.equilibrium.anisotropic_force_balance",
        "compute_anisotropic_force_balance",
    ),
    "scirel.field.filament_vacuum_field": (
        "scirel.field.filament_vacuum_field",
        "integrate_filament_vacuum_field",
    ),
    "scirel.field.circular_filament_green": (
        "scirel.field.circular_filament_green",
        "circular_filament_green_response",
    ),
    "scirel.field.poloidal_field_from_flux": (
        "scirel.field.poloidal_field_from_flux",
        "poloidal_field_from_flux",
    ),
    "scirel.field.dense_axisymmetric_green": (
        "scirel.field.dense_axisymmetric_green",
        "dense_axisymmetric_green_response",
    ),
    "scirel.field.mirror_plasma_green": (
        "scirel.field.mirror_plasma_green",
        "build_mirror_plasma_flux_green",
    ),
    "scirel.mirror.mirror_ambipolar_potential": (
        "scirel.mirror.mirror_ambipolar_potential",
        "solve_mirror_ambipolar_potential",
    ),
}

_COMPOSITIONS = {
    "scirel.equilibrium.compositions.free_boundary_anisotropic_picard": (
        "scirel.equilibrium.free_boundary_anisotropic_picard",
        "solve_free_boundary_anisotropic_picard",
    ),
    "scirel.equilibrium.compositions.isotropic_pressure_flux": (
        "scirel.equilibrium.isotropic_pressure_flux",
        "solve_isotropic_pressure_flux",
    ),
    "scirel.diagnostics.compositions.equilibrium_synthesis_diagnostics": (
        "scirel.diagnostics.equilibrium_synthesis_diagnostics",
        "synthesize_equilibrium_diagnostics",
    ),
    "scirel.mirror.compositions.mirror_quasineutral_closure": (
        "scirel.mirror.mirror_quasineutral_closure",
        "solve_mirror_quasineutral_closure",
    ),
    "scirel.mirror.compositions.grid_mirror_kinetic_closure": (
        "scirel.mirror.grid_mirror_kinetic_closure",
        "solve_grid_mirror_kinetic_closure",
    ),
    "scirel.equilibrium.compositions.axisymmetric_anisotropic_picard": (
        "scirel.equilibrium.axisymmetric_anisotropic_picard",
        "solve_axisymmetric_anisotropic_picard",
    ),
    "scirel.inference.compositions.direct_anisotropic_inversion": (
        "scirel.inference.direct_anisotropic_inversion",
        "solve_direct_anisotropic_inversion",
    ),
    "scirel.equilibrium.compositions.reduced_hall_anisotropic_picard": (
        "scirel.equilibrium.reduced_hall_anisotropic_picard",
        "solve_reduced_hall_anisotropic_picard",
    ),
    "scirel.field.compositions.multi_coil_vacuum_field": (
        "scirel.field.multi_coil_vacuum_field",
        "solve_multi_coil_vacuum_field",
    ),
    "scirel.kinetic.compositions.frank_egedal_pressure_closure": (
        "scirel.mirror.frank_egedal_pressure_closure",
        "solve_frank_egedal_pressure_closure",
    ),
    "scirel.equilibrium.compositions.kinetic_mirror_hall_equilibrium": (
        "scirel.equilibrium.kinetic_mirror_hall_equilibrium",
        "solve_kinetic_mirror_hall_equilibrium",
    ),
}


def _resolve(table, ref, kind):
    try:
        module_name, function_name = table[ref]
    except KeyError as exc:
        raise KeyError(f"unknown {kind} reference: {ref}") from exc
    return getattr(import_module(module_name), function_name)


def load_asset(ref):
    return _resolve(_ASSETS, ref, "asset")


def load_composition(ref):
    return _resolve(_COMPOSITIONS, ref, "composition")


def load_callable(ref, attribute=None):
    function = _resolve(_ASSETS, ref, "asset")
    if attribute is not None and attribute not in {
        function.__name__,
        "scientific_function",
        "latin_hypercube_samples",
    }:
        raise KeyError(f"callable {attribute} is not exported by {ref}")
    return function

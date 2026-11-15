"""Neutral-transport public API with lazy scientific operator exports."""

from importlib import import_module as _import_module

__all__ = [
    "compute_thermal_speed_m_s",
    "reduce_generation_density",
    "normalize_incoming_neutral_boundary",
    "normalize_spatial_source_shape",
    "make_cylindrical_velocity_quadrature",
    "build_shifted_maxwellian_seed",
    "reduce_axisymmetric_neutral_moments",
    "create_adaptive_neutral_velocity_mesh",
    "interpolate_scalar_across_mesh",
    "interp_distribution_across_mesh",
    "assemble_neutral_upwind_transport_coefficients",
    "propagate_neutral_generation",
    "assemble_neutral_boltzmann_rhs",
    "evaluate_neutral_generation_stopping",
    "update_neutral_generation_accumulation",
    "evaluate_neutral_outer_seed_convergence",
    "evaluate_outer_convergence",
    "sum_elastic_frequency_channels",
    "assemble_neutral_total_collision_frequency",
    "reduce_atomic_scattered_sources",
    "reduce_molecular_scattered_sources",
    "aggregate_elastic_regeneration_source",
    "assemble_simple_charge_exchange_source",
    "contract_atomic_hydrogen_alpha_frequencies",
    "contract_molecular_hydrogen_alpha_frequencies",
    "reduce_terminal_molecular_flux_velocity",
    "reduce_terminal_molecular_pressure_temperature",
    "reduce_terminal_molecular_heat_flux",
    "reduce_terminal_molecular_energy_transfer",
    "reduce_qh2_total_conservation_diagnostic",
    "reduce_terminal_molecular_ion_state",
    "compensate_velocity_slice",
    "build_compensated_shifted_maxwellian",
]

_LAZY_EXPORTS = {
    "compute_thermal_speed_m_s": ("thermal_speed_scale", "compute_thermal_speed_m_s"),
    "reduce_generation_density": ("generation_density_reduction", "reduce_generation_density"),
    "normalize_incoming_neutral_boundary": (
        "incoming_boundary_flux_normalization",
        "normalize_incoming_neutral_boundary",
    ),
    "normalize_spatial_source_shape": (
        "spatial_source_shape_normalization",
        "normalize_spatial_source_shape",
    ),
    "make_cylindrical_velocity_quadrature": (
        "cylindrical_velocity_quadrature",
        "make_cylindrical_velocity_quadrature",
    ),
    "build_shifted_maxwellian_seed": ("shifted_maxwellian_seed", "build_shifted_maxwellian_seed"),
    "reduce_axisymmetric_neutral_moments": (
        "axisymmetric_neutral_moments",
        "reduce_axisymmetric_neutral_moments",
    ),
    "create_adaptive_neutral_velocity_mesh": (
        "adaptive_neutral_velocity_mesh",
        "create_adaptive_neutral_velocity_mesh",
    ),
    "interpolate_scalar_across_mesh": (
        "cross_mesh_scalar_interpolation",
        "interpolate_scalar_across_mesh",
    ),
    "interp_distribution_across_mesh": (
        "cross_mesh_distribution_interpolation",
        "interp_distribution_across_mesh",
    ),
    "assemble_neutral_upwind_transport_coefficients": (
        "upwind_transport_coefficients",
        "assemble_neutral_upwind_transport_coefficients",
    ),
    "propagate_neutral_generation": (
        "neutral_generation_propagation",
        "propagate_neutral_generation",
    ),
    "assemble_neutral_boltzmann_rhs": ("neutral_boltzmann_rhs", "assemble_neutral_boltzmann_rhs"),
    "evaluate_neutral_generation_stopping": (
        "neutral_generation_stopping",
        "evaluate_neutral_generation_stopping",
    ),
    "update_neutral_generation_accumulation": (
        "generation_accumulation_update",
        "update_neutral_generation_accumulation",
    ),
    "evaluate_neutral_outer_seed_convergence": (
        "outer_seed_convergence",
        "evaluate_neutral_outer_seed_convergence",
    ),
    "evaluate_outer_convergence": ("outer_convergence", "evaluate_outer_convergence"),
    "sum_elastic_frequency_channels": (
        "elastic_frequency_channels",
        "sum_elastic_frequency_channels",
    ),
    "assemble_neutral_total_collision_frequency": (
        "neutral_total_collision_frequency",
        "assemble_neutral_total_collision_frequency",
    ),
    "reduce_atomic_scattered_sources": (
        "atomic_scattered_sources_reduction",
        "reduce_atomic_scattered_sources",
    ),
    "reduce_molecular_scattered_sources": (
        "molecular_scattered_sources_reduction",
        "reduce_molecular_scattered_sources",
    ),
    "aggregate_elastic_regeneration_source": (
        "elastic_regeneration_aggregation",
        "aggregate_elastic_regeneration_source",
    ),
    "assemble_simple_charge_exchange_source": (
        "simple_charge_exchange_source",
        "assemble_simple_charge_exchange_source",
    ),
    "contract_atomic_hydrogen_alpha_frequencies": (
        "atomic_alpha_contraction",
        "contract_atomic_hydrogen_alpha_frequencies",
    ),
    "contract_molecular_hydrogen_alpha_frequencies": (
        "molecular_alpha_contraction",
        "contract_molecular_hydrogen_alpha_frequencies",
    ),
    "reduce_terminal_molecular_flux_velocity": (
        "terminal_flux_velocity_reduction",
        "reduce_terminal_molecular_flux_velocity",
    ),
    "reduce_terminal_molecular_pressure_temperature": (
        "terminal_pressure_temperature_reduction",
        "reduce_terminal_molecular_pressure_temperature",
    ),
    "reduce_terminal_molecular_heat_flux": (
        "terminal_heat_flux_reduction",
        "reduce_terminal_molecular_heat_flux",
    ),
    "reduce_terminal_molecular_energy_transfer": (
        "terminal_energy_transfer_reduction",
        "reduce_terminal_molecular_energy_transfer",
    ),
    "reduce_qh2_total_conservation_diagnostic": (
        "terminal_conservation_diagnostic",
        "reduce_qh2_total_conservation_diagnostic",
    ),
    "reduce_terminal_molecular_ion_state": (
        "terminal_ion_state_reduction",
        "reduce_terminal_molecular_ion_state",
    ),
    "compensate_velocity_slice": ("moment_compensation", "compensate_velocity_slice"),
    "build_compensated_shifted_maxwellian": (
        "moment_compensation",
        "build_compensated_shifted_maxwellian",
    ),
}

_LAZY_MODULES = frozenset(module for module, _ in _LAZY_EXPORTS.values())


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        module_name, attribute_name = _LAZY_EXPORTS[name]
        module = _import_module(f".{module_name}", __name__)
        value = getattr(module, attribute_name)
        globals()[name] = value
        return value
    if name in _LAZY_MODULES:
        return _import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(__all__) | set(_LAZY_MODULES))

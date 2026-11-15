"""Kinetic-domain public API with lazy scientific operator exports."""

from importlib import import_module as _import_module

# Keep this list as the stable kinetic-domain public contract.
__all__ = [
    "evaluate_plasma_dispersion",
    "evaluate_bessel_gamma",
    "evaluate_kinetic_dispersion_sum",
    "derive_species_equilibrium_scales",
    "evaluate_fluid_kinetic_dispersion_sum",
    "get_z_pole_coefficients",
    "get_gamma_lpole_coefficients",
    "assemble_fluid_dispersion_matrix",
    "solve_fluid_wavevector_eigenproblem",
    "evaluate_ronnmark_r",
    "evaluate_kinetic_dispersion_ronnmark",
    "evaluate_kinetic_dielectric_tensor",
    "solve_kinetic_wavevector_roots",
    "scan_fluid_wavevectors",
    "evaluate_kinetic_dispersion_relation",
    "scan_kinetic_wavevectors",
    "evaluate_h_saha_equilibrium_population",
    "evaluate_cauchy_transform",
    "evaluate_maxwellian_electrostatic",
    "solve_maxwellian_electrostatic_mode",
    "initialize_plasma_state",
    "assemble_spectral_matrix",
    "solve_temporal_spectrum",
    "evaluate_spectral_dispersion",
    "DensityExpression",
    "evaluate_generalized_dispersion",
    "evaluate_generalized_hilbert",
    "evaluate_gpdf_residual",
    "evaluate_gpdf_small_k",
    "scan_gpdf_roots",
    "solve_vlasov_poisson",
    "vp_diagnostic",
    "vp_distribution",
    "vp_envelope",
    "vp_evolve",
    "vp_field",
    "vp_init",
    "vp_rhs",
    "vp_rk4_step",
    "evaluate_fluid_special",
    "derive_fluid_case",
    "evaluate_fluid_dispersion",
    "solve_fluid_bonk",
    "assemble_fluid_em",
    "solve_fluid_em",
    "solve_relativistic_codrift_spectrum",
]

_LAZY_EXPORTS = {
    "evaluate_plasma_dispersion": ("plasma_dispersion", "evaluate_plasma_dispersion"),
    "evaluate_bessel_gamma": ("bessel_gamma", "evaluate_bessel_gamma"),
    "evaluate_kinetic_dispersion_sum": (
        "kinetic_dispersion_sum_n",
        "evaluate_kinetic_dispersion_sum",
    ),
    "derive_species_equilibrium_scales": (
        "species_equilibrium_scales",
        "derive_species_equilibrium_scales",
    ),
    "evaluate_fluid_kinetic_dispersion_sum": (
        "kinetic_dispersion_sum_fluid",
        "evaluate_fluid_kinetic_dispersion_sum",
    ),
    "get_z_pole_coefficients": ("z_pole_coefficients", "get_z_pole_coefficients"),
    "get_gamma_lpole_coefficients": ("gamma_lpole_coefficients", "get_gamma_lpole_coefficients"),
    "assemble_fluid_dispersion_matrix": (
        "fluid_dispersion_matrix",
        "assemble_fluid_dispersion_matrix",
    ),
    "solve_fluid_wavevector_eigenproblem": (
        "fluid_wavevector_eigensolve",
        "solve_fluid_wavevector_eigenproblem",
    ),
    "evaluate_ronnmark_r": ("ronnmark_r_function", "evaluate_ronnmark_r"),
    "evaluate_kinetic_dispersion_ronnmark": (
        "kinetic_dispersion_ronnmark",
        "evaluate_kinetic_dispersion_ronnmark",
    ),
    "evaluate_kinetic_dielectric_tensor": (
        "dielectric_tensor_diagnostic",
        "evaluate_kinetic_dielectric_tensor",
    ),
    "solve_kinetic_wavevector_roots": (
        "kinetic_wavevector_roots",
        "solve_kinetic_wavevector_roots",
    ),
    "scan_fluid_wavevectors": ("fluid_wavevector_scan", "scan_fluid_wavevectors"),
    "evaluate_kinetic_dispersion_relation": (
        "kinetic_dispersion_relation",
        "evaluate_kinetic_dispersion_relation",
    ),
    "scan_kinetic_wavevectors": ("kinetic_wavevector_scan", "scan_kinetic_wavevectors"),
    "evaluate_h_saha_equilibrium_population": (
        "hydrogen_saha_equilibrium_population",
        "evaluate_h_saha_equilibrium_population",
    ),
    "evaluate_cauchy_transform": ("cauchy_transform", "evaluate_cauchy_transform"),
    "evaluate_maxwellian_electrostatic": (
        "maxwellian_electrostatic",
        "evaluate_maxwellian_electrostatic",
    ),
    "solve_maxwellian_electrostatic_mode": (
        "maxwellian_electrostatic",
        "solve_maxwellian_electrostatic_mode",
    ),
    "initialize_plasma_state": ("spectral_evolution", "initialize_plasma_state"),
    "assemble_spectral_matrix": ("spectral_evolution", "assemble_spectral_matrix"),
    "solve_temporal_spectrum": ("spectral_evolution", "solve_temporal_spectrum"),
    "evaluate_spectral_dispersion": ("spectral_evolution", "evaluate_spectral_dispersion"),
    "DensityExpression": ("generalized_dispersion", "DensityExpression"),
    "evaluate_generalized_dispersion": (
        "generalized_dispersion",
        "evaluate_generalized_dispersion",
    ),
    "evaluate_generalized_hilbert": ("generalized_dispersion", "evaluate_generalized_hilbert"),
    "evaluate_gpdf_residual": ("generalized_dispersion", "evaluate_gpdf_residual"),
    "scan_gpdf_roots": ("generalized_dispersion", "scan_gpdf_roots"),
    "solve_vlasov_poisson": ("vlasov_poisson", "solve_vlasov_poisson"),
    "vp_diagnostic": ("vlasov_poisson", "vp_diagnostic"),
    "vp_distribution": ("vlasov_poisson", "vp_distribution"),
    "vp_envelope": ("vlasov_poisson", "vp_envelope"),
    "vp_evolve": ("vlasov_poisson", "vp_evolve"),
    "vp_field": ("vlasov_poisson", "vp_field"),
    "vp_init": ("vlasov_poisson", "vp_init"),
    "vp_rhs": ("vlasov_poisson", "vp_rhs"),
    "vp_rk4_step": ("vlasov_poisson", "vp_rk4_step"),
    "evaluate_fluid_special": ("fluid_spectrum", "evaluate_fluid_special"),
    "derive_fluid_case": ("fluid_spectrum", "derive_fluid_case"),
    "evaluate_fluid_dispersion": ("fluid_spectrum", "evaluate_fluid_dispersion"),
    "solve_fluid_bonk": ("fluid_spectrum", "solve_fluid_bonk"),
    "assemble_fluid_em": ("fluid_spectrum", "assemble_fluid_em"),
    "solve_fluid_em": ("fluid_spectrum", "solve_fluid_em"),
    "solve_relativistic_codrift_spectrum": (
        "relativistic_codrift",
        "solve_relativistic_codrift_spectrum",
    ),
    "evaluate_gpdf_small_k": ("generalized_dispersion", "evaluate_gpdf_small_k"),
}

# Keep the child-module facade discoverable without importing every scientific
# implementation.  All public top-level kinetic modules are represented by at
# least one export above; ``dispersion`` is a nested package with its own lazy
# namespace and therefore needs an explicit entry here.
_LAZY_MODULES = frozenset({module for module, _ in _LAZY_EXPORTS.values()} | {"dispersion"})


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

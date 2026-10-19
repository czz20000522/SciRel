"""Equilibrium-domain public API with lazy scientific operator exports.

Importing :mod:`scirel.equilibrium` discovers the stable equilibrium API
without importing NumPy, SciPy, or any of the numerical implementations.
Each operator module is loaded when its public symbol is first requested;
direct child-module imports retain their normal module identity and import
order semantics.
"""

from importlib import import_module as _import_module


# Keep this list as the stable equilibrium-domain public contract. Child
# module names deliberately stay out of ``__all__``: ``from
# scirel.equilibrium import *`` has historically exported scientific symbols,
# while ordinary imports such as ``from scirel.equilibrium import
# anisotropic_force_balance`` continue to resolve the child module lazily.
__all__ = [
    "pressure_flux_picard_step",
    "build_pressure_flux_state",
    "update_anisotropic_picard_flux",
    "compute_anisotropic_toroidal_current",
    "update_axisymmetric_picard_flux",
    "compute_anisotropic_force_balance",
    "solve_free_boundary_anisotropic_picard",
    "solve_isotropic_pressure_flux",
    "solve_axisymmetric_anisotropic_picard",
    "solve_reduced_hall_anisotropic_picard",
    "solve_kinetic_mirror_hall_equilibrium",
    "EquilibriumResult",
    "compute_equilibrium",
]


_LAZY_EXPORTS = {
    "pressure_flux_picard_step": (
        "isotropic_picard_step",
        "pressure_flux_picard_step",
    ),
    "build_pressure_flux_state": (
        "pressure_flux_state",
        "build_pressure_flux_state",
    ),
    "update_anisotropic_picard_flux": (
        "anisotropic_picard_feedback",
        "update_anisotropic_picard_flux",
    ),
    "compute_anisotropic_toroidal_current": (
        "anisotropic_toroidal_current",
        "compute_anisotropic_toroidal_current",
    ),
    "update_axisymmetric_picard_flux": (
        "axisymmetric_picard_update",
        "update_axisymmetric_picard_flux",
    ),
    "compute_anisotropic_force_balance": (
        "anisotropic_force_balance",
        "compute_anisotropic_force_balance",
    ),
    "solve_free_boundary_anisotropic_picard": (
        "free_boundary_anisotropic_picard",
        "solve_free_boundary_anisotropic_picard",
    ),
    "solve_isotropic_pressure_flux": (
        "isotropic_pressure_flux",
        "solve_isotropic_pressure_flux",
    ),
    "solve_axisymmetric_anisotropic_picard": (
        "axisymmetric_anisotropic_picard",
        "solve_axisymmetric_anisotropic_picard",
    ),
    "solve_reduced_hall_anisotropic_picard": (
        "reduced_hall_anisotropic_picard",
        "solve_reduced_hall_anisotropic_picard",
    ),
    "solve_kinetic_mirror_hall_equilibrium": (
        "kinetic_mirror_hall_equilibrium",
        "solve_kinetic_mirror_hall_equilibrium",
    ),
    "EquilibriumResult": ("equilibrium_state", "EquilibriumResult"),
    "compute_equilibrium": ("equilibrium_state", "compute_equilibrium"),
}


# These are the public child modules corresponding to the stable exports.
# Keeping them separate from ``__all__`` preserves wildcard-import behavior.
_LAZY_MODULES = frozenset(module for module, _ in _LAZY_EXPORTS.values())


def _load_export(name):
    module_name, attribute_name = _LAZY_EXPORTS[name]
    module = _import_module(f".{module_name}", __name__)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        return _load_export(name)
    if name in _LAZY_MODULES:
        return _import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(__all__) | set(_LAZY_MODULES))

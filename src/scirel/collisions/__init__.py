"""Collision-domain public API with lazy scientific operator exports."""

from importlib import import_module as _import_module
from types import ModuleType as _ModuleType
import sys as _sys


__all__ = [
    "BesselBackendEvaluationError",
    "InvalidBesselArgumentError",
    "relativistic_maxwellian_bessel",
    "normalized_momentum",
    "thermal_electron_momentum",
    "average_cross_section_over_maxwellian",
    "evaluate_atomic_hydrogen_charge_exchange_cross_section",
    "evaluate_atomic_hydrogen_charge_exchange_rate",
    "evaluate_hydrogen2_charge_exchange_rate",
    "evaluate_janev_electron_impact_ionization_rate",
    "evaluate_atomic_hydrogen_1s_radiative_recombination_rate",
    "evaluate_molecular_hydrogen_charge_exchange_cross_section",
    "evaluate_atomic_hydrogen_elastic_cross_section",
    "evaluate_hydrogen_h2_elastic_cross_section",
    "evaluate_hydrogen_proton_elastic_cross_section",
    "evaluate_hydrogen2_proton_elastic_cross_section",
    "evaluate_hydrogen2_hydrogen2_elastic_cross_section",
    "assemble_atomic_hydrogen_collision_matrices",
    "assemble_molecular_hydrogen_collision_matrices",
    "assemble_atomic_hydrogen_omega_frequencies",
    "assemble_molecular_hydrogen_omega_frequencies",
]


_LAZY_EXPORTS = {
    "BesselBackendEvaluationError": ("relativistic_maxwellian_bessel", "BesselBackendEvaluationError"),
    "InvalidBesselArgumentError": ("relativistic_maxwellian_bessel", "InvalidBesselArgumentError"),
    "relativistic_maxwellian_bessel": ("relativistic_maxwellian_bessel", "relativistic_maxwellian_bessel"),
    "normalized_momentum": ("momentum_scales", "normalized_momentum"),
    "thermal_electron_momentum": ("momentum_scales", "thermal_electron_momentum"),
    "average_cross_section_over_maxwellian": (
        "maxwellian_relative_speed_rate_average", "average_cross_section_over_maxwellian"
    ),
    "evaluate_atomic_hydrogen_charge_exchange_cross_section": (
        "atomic_hydrogen_charge_exchange_cross_section", "evaluate_atomic_hydrogen_charge_exchange_cross_section"
    ),
    "evaluate_atomic_hydrogen_charge_exchange_rate": (
        "atomic_hydrogen_charge_exchange_rate", "evaluate_atomic_hydrogen_charge_exchange_rate"
    ),
    "evaluate_hydrogen2_charge_exchange_rate": (
        "hydrogen2_charge_exchange_rate", "evaluate_hydrogen2_charge_exchange_rate"
    ),
    "evaluate_janev_electron_impact_ionization_rate": (
        "janev_electron_impact_ionization_rate", "evaluate_janev_electron_impact_ionization_rate"
    ),
    "evaluate_atomic_hydrogen_1s_radiative_recombination_rate": (
        "atomic_hydrogen_1s_radiative_recombination_rate", "evaluate_atomic_hydrogen_1s_radiative_recombination_rate"
    ),
    "evaluate_molecular_hydrogen_charge_exchange_cross_section": (
        "molecular_hydrogen_charge_exchange_cross_section", "evaluate_molecular_hydrogen_charge_exchange_cross_section"
    ),
    "evaluate_atomic_hydrogen_elastic_cross_section": (
        "atomic_hydrogen_elastic_cross_section", "evaluate_atomic_hydrogen_elastic_cross_section"
    ),
    "evaluate_hydrogen_h2_elastic_cross_section": (
        "hydrogen_h2_elastic_cross_section", "evaluate_hydrogen_h2_elastic_cross_section"
    ),
    "evaluate_hydrogen_proton_elastic_cross_section": (
        "hydrogen_proton_elastic_cross_section", "evaluate_hydrogen_proton_elastic_cross_section"
    ),
    "evaluate_hydrogen2_proton_elastic_cross_section": (
        "hydrogen2_proton_elastic_cross_section", "evaluate_hydrogen2_proton_elastic_cross_section"
    ),
    "evaluate_hydrogen2_hydrogen2_elastic_cross_section": (
        "hydrogen2_hydrogen2_elastic_cross_section", "evaluate_hydrogen2_hydrogen2_elastic_cross_section"
    ),
    "assemble_atomic_hydrogen_collision_matrices": (
        "atomic_hydrogen_collision_matrices", "assemble_atomic_hydrogen_collision_matrices"
    ),
    "assemble_molecular_hydrogen_collision_matrices": (
        "molecular_hydrogen_collision_matrices", "assemble_molecular_hydrogen_collision_matrices"
    ),
    "assemble_atomic_hydrogen_omega_frequencies": (
        "atomic_hydrogen_omega_frequencies", "assemble_atomic_hydrogen_omega_frequencies"
    ),
    "assemble_molecular_hydrogen_omega_frequencies": (
        "molecular_hydrogen_omega_frequencies", "assemble_molecular_hydrogen_omega_frequencies"
    ),
}

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


class _LazyCollisionModule(_ModuleType):
    """Keep public callables ahead of same-named child modules.

    Importing ``scirel.collisions.relativistic_maxwellian_bessel`` places the
    child module on this package under the same attribute name as the public
    function. Resolve declared exports first so package-level imports remain
    stable regardless of import order.
    """

    def __getattribute__(self, name):
        namespace = _ModuleType.__getattribute__(self, "__dict__")
        exports = namespace.get("_LAZY_EXPORTS", {})
        if name in exports:
            current = namespace.get(name)
            if current is not None and not isinstance(current, _ModuleType):
                return current
            return _load_export(name)
        modules = namespace.get("_LAZY_MODULES", ())
        if name in modules:
            current = namespace.get(name)
            if isinstance(current, _ModuleType):
                return current
            return _import_module(f".{name}", _ModuleType.__getattribute__(self, "__name__"))
        return _ModuleType.__getattribute__(self, name)


_sys.modules[__name__].__class__ = _LazyCollisionModule

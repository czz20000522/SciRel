"""Lazy access to the closure-domain scientific operators."""

from importlib import import_module as _import_module


__all__ = [
    "close_hall_two_fluid_pressure",
    "compute_reference_electron_density",
    "solve_quasineutral_potential",
    "compute_boltzmann_electron_state",
    "evaluate_tabulated_pressure",
    "close_reduced_hall_drift",
    "solve_mirror_ambipolar_potential",
    "solve_mirror_quasineutral_closure",
]


_LAZY_EXPORTS = {
    "close_hall_two_fluid_pressure": (
        "hall_two_fluid_pressure",
        "close_hall_two_fluid_pressure",
    ),
    "compute_reference_electron_density": (
        "quasineutral_reference_density",
        "compute_reference_electron_density",
    ),
    "solve_quasineutral_potential": (
        "quasineutral_potential",
        "solve_quasineutral_potential",
    ),
    "compute_boltzmann_electron_state": (
        "boltzmann_quasineutrality",
        "compute_boltzmann_electron_state",
    ),
    "evaluate_tabulated_pressure": (
        "tabulated_pressure_closure",
        "evaluate_tabulated_pressure",
    ),
    "close_reduced_hall_drift": (
        "reduced_hall_drift",
        "close_reduced_hall_drift",
    ),
    "solve_mirror_ambipolar_potential": (
        "mirror_ambipolar_potential",
        "solve_mirror_ambipolar_potential",
    ),
    "solve_mirror_quasineutral_closure": (
        "mirror_quasineutral_closure",
        "solve_mirror_quasineutral_closure",
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

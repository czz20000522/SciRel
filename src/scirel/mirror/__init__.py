"""Mirror-confinement-domain public API with lazy scientific operator exports."""

from importlib import import_module as _import_module

# Keep this list as the stable mirror-domain public contract.
__all__ = [
    "assemble_frank_egedal_pressure",
    "evaluate_frank_egedal_radial_envelope",
    "project_frank_egedal_source_modes",
    "evaluate_frank_egedal_hot_ion_moments",
    "evaluate_mirror_invariant_distribution",
    "assemble_mirror_total_pressure",
    "evaluate_mirror_constrained_moments",
    "solve_loss_cone_spectrum",
    "solve_grid_mirror_kinetic_closure",
    "solve_frank_egedal_pressure_closure",
    "solve_mirror_ambipolar_potential",
    "solve_mirror_quasineutral_closure",
]

_LAZY_EXPORTS = {
    "assemble_frank_egedal_pressure": (
        "frank_egedal_pressure_state",
        "assemble_frank_egedal_pressure",
    ),
    "evaluate_frank_egedal_radial_envelope": (
        "frank_egedal_radial_envelope",
        "evaluate_frank_egedal_radial_envelope",
    ),
    "project_frank_egedal_source_modes": (
        "frank_egedal_source_projection",
        "project_frank_egedal_source_modes",
    ),
    "evaluate_frank_egedal_hot_ion_moments": (
        "frank_egedal_hot_ion_moments",
        "evaluate_frank_egedal_hot_ion_moments",
    ),
    "evaluate_mirror_invariant_distribution": (
        "mirror_invariant_distribution",
        "evaluate_mirror_invariant_distribution",
    ),
    "assemble_mirror_total_pressure": ("mirror_total_pressure", "assemble_mirror_total_pressure"),
    "evaluate_mirror_constrained_moments": (
        "mirror_constrained_moments",
        "evaluate_mirror_constrained_moments",
    ),
    "solve_loss_cone_spectrum": ("loss_cone_spectrum", "solve_loss_cone_spectrum"),
    "solve_grid_mirror_kinetic_closure": (
        "grid_mirror_kinetic_closure",
        "solve_grid_mirror_kinetic_closure",
    ),
    "solve_frank_egedal_pressure_closure": (
        "frank_egedal_pressure_closure",
        "solve_frank_egedal_pressure_closure",
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

# Keep the child-module facade discoverable without importing every scientific
# implementation.  All public top-level mirror modules are represented by at
# least one export above.
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

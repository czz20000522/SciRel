"""Field-domain public API with lazy scientific operator exports.

Importing :mod:`scirel.field` discovers the stable field API without importing
every Green-function and geometry implementation. Each operator module is
loaded on first attribute access; direct module imports retain their existing
identity and failure behaviour.
"""

from importlib import import_module as _import_module
from types import ModuleType as _ModuleType
import sys as _sys


__all__ = [
    "compute_poloidal_field_magnitude",
    "discretize_permanent_ring",
    "correct_ideal_conductor_boundary_flux",
    "discretize_rectangular_coil",
    "superpose_current_green_field",
    "integrate_filament_vacuum_field",
    "circular_filament_green_response",
    "poloidal_field_from_flux",
    "dense_axisymmetric_green_response",
    "build_mirror_plasma_flux_green",
    "solve_multi_coil_vacuum_field",
    "compute_axisymmetric_coil_modulus",
    "evaluate_complete_elliptic_integrals",
    "evaluate_filament_coil_green_field",
]


_LAZY_EXPORTS = {
    "compute_poloidal_field_magnitude": (
        "poloidal_field_magnitude",
        "compute_poloidal_field_magnitude",
    ),
    "discretize_permanent_ring": ("permanent_ring_filaments", "discretize_permanent_ring"),
    "correct_ideal_conductor_boundary_flux": (
        "ideal_conductor_boundary",
        "correct_ideal_conductor_boundary_flux",
    ),
    "discretize_rectangular_coil": ("rectangular_coil_filaments", "discretize_rectangular_coil"),
    "superpose_current_green_field": (
        "current_green_superposition",
        "superpose_current_green_field",
    ),
    "integrate_filament_vacuum_field": ("filament_vacuum_field", "integrate_filament_vacuum_field"),
    "circular_filament_green_response": (
        "circular_filament_green",
        "circular_filament_green_response",
    ),
    "poloidal_field_from_flux": ("poloidal_field_from_flux", "poloidal_field_from_flux"),
    "dense_axisymmetric_green_response": (
        "dense_axisymmetric_green",
        "dense_axisymmetric_green_response",
    ),
    "build_mirror_plasma_flux_green": ("mirror_plasma_green", "build_mirror_plasma_flux_green"),
    "solve_multi_coil_vacuum_field": ("multi_coil_vacuum_field", "solve_multi_coil_vacuum_field"),
    "compute_axisymmetric_coil_modulus": (
        "coil_green_geometry",
        "compute_axisymmetric_coil_modulus",
    ),
    "evaluate_complete_elliptic_integrals": (
        "complete_elliptic_integrals_approx",
        "evaluate_complete_elliptic_integrals",
    ),
    "evaluate_filament_coil_green_field": (
        "filament_coil_green_field",
        "evaluate_filament_coil_green_field",
    ),
}

# Keep child implementation modules discoverable without importing them.  The
# callable exports above remain the wildcard API; module names are exposed by
# ``dir`` and ordinary attribute access only, matching the other lazy domain
# facades.
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


class _LazyFieldModule(_ModuleType):
    """Keep package exports stable if a caller imports a child module first.

    Python normally places a child module on its parent package, which would
    otherwise temporarily replace ``field.poloidal_field_from_flux`` with the
    module object.  Resolving mapped names through the same lazy loader keeps
    both import orders equivalent.
    """

    def __getattribute__(self, name):
        namespace = _ModuleType.__getattribute__(self, "__dict__")
        exports = namespace.get("_LAZY_EXPORTS", {})
        if name in exports:
            current = namespace.get(name)
            if current is not None and not isinstance(current, _ModuleType):
                return current
            module_name, attribute_name = exports[name]
            module = _import_module(
                f".{module_name}", _ModuleType.__getattribute__(self, "__name__")
            )
            value = getattr(module, attribute_name)
            namespace[name] = value
            return value
        modules = namespace.get("_LAZY_MODULES", ())
        if name in modules:
            current = namespace.get(name)
            if isinstance(current, _ModuleType):
                return current
            return _import_module(f".{name}", _ModuleType.__getattribute__(self, "__name__"))
        return _ModuleType.__getattribute__(self, name)


_sys.modules[__name__].__class__ = _LazyFieldModule


def __dir__():
    return sorted(set(__all__) | set(_LAZY_MODULES))

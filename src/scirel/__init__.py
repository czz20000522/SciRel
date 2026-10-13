"""Scientific Relations Library, organized into scientific domain subpackages.

Use domain APIs such as ``scirel.field.solve_multi_coil_vacuum_field``.
Importing ``scirel`` alone does not load scientific backends.
"""

from importlib import import_module as _import_module

__all__ = [
    "closures",
    "collisions",
    "diagnostics",
    "dielectric",
    "equilibrium",
    "field",
    "fusion",
    "geometry",
    "inference",
    "kinetic",
]


def __getattr__(name):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = _import_module("." + name, __name__)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))

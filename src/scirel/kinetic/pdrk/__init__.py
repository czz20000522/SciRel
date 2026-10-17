"""Magnetized kinetic, parallel beam and multifluid dispersion capabilities.

The PDRK implementation is split into focused modules so discovery does not
import every numerical backend.  The module names below are the public entry
points; each module keeps its own callable ``__all__`` and is loaded only when
requested.  Scientific limits live in each callable contract.  Native
numerical/support calls require Octave; ordinary Python calls are isolated.
"""

from importlib import import_module as _import_module


__all__ = [
    "magnetized",
    "multifluid",
    "parallel",
    "plotting",
    "rational",
    "reference",
    "special",
    "workflows",
]

_LAZY_MODULES = {name: f".{name}" for name in __all__}


def __getattr__(name):
    try:
        module_path = _LAZY_MODULES[name]
    except KeyError as error:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from error
    module = _import_module(module_path, __name__)
    globals()[name] = module
    return module


def __dir__():
    return sorted(set(globals()) | set(__all__))

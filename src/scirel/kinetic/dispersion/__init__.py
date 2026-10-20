"""Magnetized kinetic, parallel beam and multifluid dispersion capabilities.

The native dispersion implementation is split into focused modules so discovery does not
import every numerical backend.  The module names below are the public entry
points; each module keeps its own callable ``__all__`` and is loaded only when
requested.  Scientific limits live in each callable contract.  Native
numerical/support calls require the reference solver; ordinary Python calls are isolated.
"""

from importlib import import_module as _import_module
from types import ModuleType as _ModuleType
import sys as _sys


__all__ = [
    "magnetized",
    "multifluid",
    "parallel",
    "rational",
]

_LAZY_MODULES = {name: f".{name}" for name in __all__}


class _LazyChildModule(_ModuleType):
    """Proxy a catalogued child module without importing its backend.

    The proxy deliberately is a real ``ModuleType`` so package discovery and
    wildcard imports can expose the complete module catalog in an environment
    that does not have NumPy/SciPy installed.  The target module is imported
    only when one of its members is requested; direct submodule imports still
    receive the ordinary module object from ``sys.modules``.
    """

    def __init__(self, name: str, target: str) -> None:
        super().__init__(name)
        self.__package__ = name.rpartition(".")[0]
        self.__loader__ = None
        self._target = target
        self._loaded = None

    def _load(self):
        module = self._loaded
        if module is None:
            module = _import_module(self._target)
            self._loaded = module
            parent_name, _, child_name = self.__name__.rpartition(".")
            parent = _sys.modules.get(parent_name)
            if parent is not None:
                setattr(parent, child_name, module)
        return module

    def __getattribute__(self, name):
        # Static contract inspection uses ``vars(module)`` to resolve a
        # forwarding delegate.  Treat that introspection as a request for the
        # module namespace while keeping ordinary catalog discovery lazy.
        if name == "__dict__":
            loader = _ModuleType.__getattribute__(self, "_load")
            return vars(loader())
        return _ModuleType.__getattribute__(self, name)

    def __getattr__(self, name):
        return getattr(self._load(), name)

    def __dir__(self):
        return sorted(set(dir(self._load())))


for _name, _module_path in _LAZY_MODULES.items():
    globals()[_name] = _LazyChildModule(
        f"{__name__}.{_name}",
        f"{__name__}{_module_path}",
    )


def __getattr__(name):
    try:
        return globals()[name]
    except KeyError as error:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from error


def __dir__():
    return sorted(set(__all__) | set(_LAZY_MODULES))

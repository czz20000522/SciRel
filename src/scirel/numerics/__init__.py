"""Reusable numerical building blocks that are not tied to one physics model."""

from importlib import import_module as _import_module
from types import ModuleType as _ModuleType
import sys as _sys
from typing import TYPE_CHECKING as _TYPE_CHECKING

if _TYPE_CHECKING:
    from .modal_basis import ModalBasis, modal_basis, modal_projection

__all__ = [
    "ModalBasis",
    "modal_basis",
    "modal_projection",
]

_LAZY_EXPORTS = {
    "ModalBasis": ("modal_basis", "ModalBasis"),
    "modal_basis": ("modal_basis", "modal_basis"),
    "modal_projection": ("modal_basis", "modal_projection"),
}


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        module_name, attribute_name = _LAZY_EXPORTS[name]
        module = _import_module(f".{module_name}", __name__)
        value = getattr(module, attribute_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(__all__)


class _LazyNumericsModule(_ModuleType):
    """Preserve callable facade exports after direct child-module imports."""

    def __getattribute__(self, name):
        namespace = _ModuleType.__getattribute__(self, "__dict__")
        exports = namespace.get("_LAZY_EXPORTS", {})
        if name in exports:
            current = namespace.get(name)
            if current is not None and not isinstance(current, _ModuleType):
                return current
            return __getattr__(name)
        return _ModuleType.__getattribute__(self, name)


_sys.modules[__name__].__class__ = _LazyNumericsModule

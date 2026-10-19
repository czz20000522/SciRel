"""Lazy access to the built-in experimental configuration geometries."""

from importlib import import_module as _import_module


__all__ = ["BRB", "TREXCoil", "WHAM"]

_LAZY_EXPORTS = {
    "BRB": ("brb", "BRB"),
    "TREXCoil": ("brb", "TREXCoil"),
    "WHAM": ("wham", "WHAM"),
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

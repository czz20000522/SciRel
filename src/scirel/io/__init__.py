"""Pleiades extended-dialect scientific exchange helpers."""

from importlib import import_module as _import_module

__all__ = [
    "DIALECT", "EQDSK", "EQDSKFormatError", "read_eqdsk", "read_pleiades_eqdsk",
    "write_eqdsk_fromdict", "write_pleiades_eqdsk", "write_pleiades_eqdsk_legacy_raw",
    "write_pressure_equilibrium_eqdsk", "write_eqdsk",
]
_LAZY_EXPORTS = {name: ("eqdsk", name) for name in __all__}
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

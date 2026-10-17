"""Finite-volume cell, flux, and single-channel theta-step operators."""

from importlib import import_module as _import_module

__all__ = ["CellVariable", "TriDiagonal", "make_diffusion_terms", "make_convection_terms", "theta_step"]
_LAZY_EXPORTS = {
    "CellVariable": ("cell_variable", "CellVariable"),
    "TriDiagonal": ("diffusion", "TriDiagonal"),
    "make_diffusion_terms": ("diffusion", "make_diffusion_terms"),
    "make_convection_terms": ("convection", "make_convection_terms"),
    "theta_step": ("implicit", "theta_step"),
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
    return sorted(set(globals()) | set(__all__) | set(_LAZY_MODULES))

"""Anisotropic inference helpers with lazy scientific exports."""

from importlib import import_module as _import_module

__all__ = ["sample_latin_hypercube", "optimize_anisotropic_parameters", "evaluate_anisotropic_trial", "solve_direct_anisotropic_inversion"]
_LAZY_EXPORTS = {
    "sample_latin_hypercube": ("latin_hypercube_sampling", "sample_latin_hypercube"),
    "optimize_anisotropic_parameters": ("anisotropic_parameter_optimization", "optimize_anisotropic_parameters"),
    "evaluate_anisotropic_trial": ("anisotropic_trial_evaluation", "evaluate_anisotropic_trial"),
    "solve_direct_anisotropic_inversion": ("direct_anisotropic_inversion", "solve_direct_anisotropic_inversion"),
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

"""Lazy access to algebraic plasma-physics relations."""

from importlib import import_module as _import_module

__all__ = ["calculate_stored_thermal_energy", "calculate_main_ion_dilution_factor", "calculate_log_lambda_ee", "calculate_log_lambda_ei", "calculate_log_lambda_ii"]
_LAZY_EXPORTS = {
    "calculate_stored_thermal_energy": ("thermal_energy", "calculate_stored_thermal_energy"),
    "calculate_main_ion_dilution_factor": ("dilution", "calculate_main_ion_dilution_factor"),
    "calculate_log_lambda_ee": ("coulomb_logs", "calculate_log_lambda_ee"),
    "calculate_log_lambda_ei": ("coulomb_logs", "calculate_log_lambda_ei"),
    "calculate_log_lambda_ii": ("coulomb_logs", "calculate_log_lambda_ii"),
}
_LAZY_MODULES = frozenset(module for module, _ in _LAZY_EXPORTS.values())

def _load_export(name):
    module_name, attribute_name = _LAZY_EXPORTS[name]
    module = _import_module(f".{module_name}", __name__)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value

_HELD = frozenset({"calculate_log_lambda_ii"})

def __getattr__(name):
    if name in _HELD:
        from scirel._hold import require_review_call
        require_review_call(name)
    if name in _LAZY_EXPORTS:
        return _load_export(name)
    if name in _LAZY_MODULES:
        return _import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __dir__():
    return sorted(set(__all__) | set(_LAZY_MODULES))

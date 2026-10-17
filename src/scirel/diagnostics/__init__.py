"""Validated equilibrium diagnostics with lazy scientific exports."""

from importlib import import_module as _import_module

__all__ = [
    "compute_picard_flux_residual",
    "reduce_observation_residuals",
    "compute_parallel_pressure_residual",
    "compute_firehose_mirror_margins",
    "compute_pointwise_firehose_margin",
    "synthesize_equilibrium_diagnostics",
    "compute_species_absorption_fraction",
]

_LAZY_EXPORTS = {
    "compute_picard_flux_residual": ("picard_flux_residual", "compute_picard_flux_residual"),
    "reduce_observation_residuals": ("observation_residuals", "reduce_observation_residuals"),
    "compute_parallel_pressure_residual": ("parallel_pressure_residual", "compute_parallel_pressure_residual"),
    "compute_firehose_mirror_margins": ("firehose_mirror_margins", "compute_firehose_mirror_margins"),
    "compute_pointwise_firehose_margin": ("pointwise_firehose_margin", "compute_pointwise_firehose_margin"),
    "synthesize_equilibrium_diagnostics": ("equilibrium_synthesis_diagnostics", "synthesize_equilibrium_diagnostics"),
    "compute_species_absorption_fraction": ("species_absorption_fraction", "compute_species_absorption_fraction"),
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

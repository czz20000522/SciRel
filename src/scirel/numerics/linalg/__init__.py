"""Linear algebra operators with dependency-light public discovery."""

from importlib import import_module as _import_module


__all__ = ["compute_truncated_pseudoinverse"]

_LAZY_EXPORTS = {
    "compute_truncated_pseudoinverse": (
        "truncated_pseudoinverse",
        "compute_truncated_pseudoinverse",
    ),
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

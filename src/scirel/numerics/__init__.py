"""Reusable numerical building blocks that are not tied to one physics model."""

from importlib import import_module as _import_module
from types import ModuleType as _ModuleType
import sys as _sys
from typing import TYPE_CHECKING as _TYPE_CHECKING

if _TYPE_CHECKING:
    from .basis import (
        NaturalCubicSpline,
        ClampedCubicSpline,
        FirstClampedCubicSpline,
        SecondClampedCubicSpline,
        build_basis,
        BasisMatrix,
    )
    from .interpolate import (
        face_to_cell,
        interpolate_complex_rectilinear_field,
        sample_rectilinear_field,
    )
    from .linalg import compute_truncated_pseudoinverse
    from .modal_basis import ModalBasis, modal_basis, modal_projection

__all__ = [
    "NaturalCubicSpline",
    "ClampedCubicSpline",
    "FirstClampedCubicSpline",
    "SecondClampedCubicSpline",
    "build_basis",
    "BasisMatrix",
    "face_to_cell",
    "sample_rectilinear_field",
    "interpolate_complex_rectilinear_field",
    "compute_truncated_pseudoinverse",
    "ModalBasis",
    "modal_basis",
    "modal_projection",
]

_LAZY_EXPORTS = {
    "NaturalCubicSpline": ("basis", "NaturalCubicSpline"),
    "ClampedCubicSpline": ("basis", "ClampedCubicSpline"),
    "FirstClampedCubicSpline": ("basis", "FirstClampedCubicSpline"),
    "SecondClampedCubicSpline": ("basis", "SecondClampedCubicSpline"),
    "build_basis": ("basis", "build_basis"),
    "BasisMatrix": ("basis", "BasisMatrix"),
    "face_to_cell": ("interpolate", "face_to_cell"),
    "sample_rectilinear_field": ("interpolate", "sample_rectilinear_field"),
    "interpolate_complex_rectilinear_field": (
        "interpolate",
        "interpolate_complex_rectilinear_field",
    ),
    "compute_truncated_pseudoinverse": ("linalg", "compute_truncated_pseudoinverse"),
    "ModalBasis": ("modal_basis", "ModalBasis"),
    "modal_basis": ("modal_basis", "modal_basis"),
    "modal_projection": ("modal_basis", "modal_projection"),
}
_LAZY_MODULES = frozenset({"basis", "interpolate", "linalg"})


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        module_name, attribute_name = _LAZY_EXPORTS[name]
        module = _import_module(f".{module_name}", __name__)
        value = getattr(module, attribute_name)
        globals()[name] = value
        return value
    if name in _LAZY_MODULES:
        return _import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(__all__) | set(_LAZY_MODULES))


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

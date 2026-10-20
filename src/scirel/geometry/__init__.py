"""Geometry-domain public API with lazy scientific operator exports.

The package exposes the same names that were historically imported eagerly,
but importing :mod:`scirel.geometry` itself does not import NumPy, SciPy, or
the optional plotting backend. A child module and its implementation are
loaded when a public name is first requested. Direct child-module imports
retain their normal module identity and import order semantics.
"""

from importlib import import_module as _import_module
from types import ModuleType as _ModuleType
import sys as _sys


# Keep this list as the stable geometry-domain public contract. Child module
# names deliberately stay out of ``__all__``: ``from scirel.geometry import
# *`` has always exported the scientific names below, while ordinary imports
# such as ``from scirel.geometry import sampling`` continue to resolve the
# child module through the lazy module loader.
__all__ = [
    "sample_rectilinear_field",
    "evaluate_flux_surface_profile",
    "compute_flux_surface_inverse_field_average",
    "map_axisymmetric_equilibrium_to_cartesian_grid",
    "classify_material_support",
    "solve_axisymmetric_equilibrium_grid_mapping",
    "interpolate_complex_rectilinear_field",
    "project_planar_wavevector",
    "face_to_cell",
    "Mesh",
    "PointsMesh",
    "RChord",
    "ZChord",
    "SphericalRChord",
    "ThetaChord",
    "RectMesh",
    "rotate",
    "NaturalCubicSpline",
    "ClampedCubicSpline",
    "FirstClampedCubicSpline",
    "SecondClampedCubicSpline",
    "build_basis",
    "BasisMatrix",
    "d_ds_arclength",
    "FieldLineSet",
    "FieldLine",
    "HelperFieldLine",
    "Boundary",
    "contour_points",
    "helper_contour_points",
    "NumericalContractError",
    "diff_12_central",
    "truncated_svd_inverse",
    "transform_to_rtheta",
    "transform_to_rhoz",
    "regular_grid",
    "poly_fit",
    "reflect_and_hstack",
    "locs_to_vals",
    "locs_to_vals_griddata",
    "locs_to_vals1D",
    "get_fieldlines",
    "parse_segment",
    "get_fieldline_distance",
    "interp",
    "flux_surface_avg",
    "diff_central",
    "get_gpsi",
]


_LAZY_EXPORTS = {
    "sample_rectilinear_field": ("bilinear_grid_sampling", "sample_rectilinear_field"),
    "evaluate_flux_surface_profile": ("flux_surface_profile", "evaluate_flux_surface_profile"),
    "compute_flux_surface_inverse_field_average": (
        "flux_surface_inverse_field_average",
        "compute_flux_surface_inverse_field_average",
    ),
    "map_axisymmetric_equilibrium_to_cartesian_grid": (
        "axisymmetric_grid_mapping",
        "map_axisymmetric_equilibrium_to_cartesian_grid",
    ),
    "classify_material_support": ("material_support", "classify_material_support"),
    "solve_axisymmetric_equilibrium_grid_mapping": (
        "axisymmetric_equilibrium_grid_support",
        "solve_axisymmetric_equilibrium_grid_mapping",
    ),
    "interpolate_complex_rectilinear_field": (
        "complex_rectilinear_interpolation",
        "interpolate_complex_rectilinear_field",
    ),
    "project_planar_wavevector": ("planar_wavevector", "project_planar_wavevector"),
    "face_to_cell": ("face_to_cell", "face_to_cell"),
    "Mesh": ("mesh", "Mesh"),
    "PointsMesh": ("mesh", "PointsMesh"),
    "RChord": ("mesh", "RChord"),
    "ZChord": ("mesh", "ZChord"),
    "SphericalRChord": ("mesh", "SphericalRChord"),
    "ThetaChord": ("mesh", "ThetaChord"),
    "RectMesh": ("mesh", "RectMesh"),
    "rotate": ("transforms", "rotate"),
    "NaturalCubicSpline": ("basis", "NaturalCubicSpline"),
    "ClampedCubicSpline": ("basis", "ClampedCubicSpline"),
    "FirstClampedCubicSpline": ("basis", "FirstClampedCubicSpline"),
    "SecondClampedCubicSpline": ("basis", "SecondClampedCubicSpline"),
    "build_basis": ("basis", "build_basis"),
    "BasisMatrix": ("basis", "BasisMatrix"),
    "d_ds_arclength": ("fieldline", "d_ds_arclength"),
    "FieldLineSet": ("fieldline", "FieldLineSet"),
    "FieldLine": ("fieldline", "FieldLine"),
    "HelperFieldLine": ("fieldline", "HelperFieldLine"),
    "Boundary": ("fieldline", "Boundary"),
    "contour_points": ("fieldline", "contour_points"),
    "helper_contour_points": ("fieldline", "helper_contour_points"),
    "NumericalContractError": ("numerics", "NumericalContractError"),
    "diff_12_central": ("numerics", "diff_12_central"),
    "truncated_svd_inverse": ("truncated_svd_inverse", "truncated_svd_inverse"),
    "transform_to_rtheta": ("sampling", "transform_to_rtheta"),
    "transform_to_rhoz": ("sampling", "transform_to_rhoz"),
    "regular_grid": ("sampling", "regular_grid"),
    "poly_fit": ("sampling", "poly_fit"),
    "reflect_and_hstack": ("sampling", "reflect_and_hstack"),
    "locs_to_vals": ("sampling", "locs_to_vals"),
    "locs_to_vals_griddata": ("sampling", "locs_to_vals_griddata"),
    "locs_to_vals1D": ("sampling", "locs_to_vals1D"),
    "get_fieldlines": ("sampling", "get_fieldlines"),
    "parse_segment": ("sampling", "parse_segment"),
    "get_fieldline_distance": ("sampling", "get_fieldline_distance"),
    "interp": ("sampling", "interp"),
    "flux_surface_avg": ("sampling", "flux_surface_avg"),
    "diff_central": ("sampling", "diff_central"),
    "get_gpsi": ("analysis", "get_gpsi"),
}


_LAZY_MODULES = frozenset(
    {
        "analysis",
        "axisymmetric_equilibrium_grid_support",
        "axisymmetric_grid_mapping",
        "basis",
        "bilinear_grid_sampling",
        "complex_rectilinear_interpolation",
        "face_to_cell",
        "fieldline",
        "flux_surface_inverse_field_average",
        "flux_surface_profile",
        "material_support",
        "mesh",
        "numerics",
        "planar_wavevector",
        "sampling",
        "transforms",
    }
)


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


class _LazyGeometryModule(_ModuleType):
    """Keep exports and child modules stable across import orders.

    Importing a child module causes Python to place that module on its parent
    package. For an exported symbol with the same historical name, resolve
    through ``_LAZY_EXPORTS`` so importing ``scirel.geometry.mesh`` before
    accessing ``geometry.Mesh`` has the same result as the reverse order.
    """

    def __getattribute__(self, name):
        namespace = _ModuleType.__getattribute__(self, "__dict__")
        exports = namespace.get("_LAZY_EXPORTS", {})
        if name in exports:
            current = namespace.get(name)
            if current is not None and not isinstance(current, _ModuleType):
                return current
            return _load_export(name)
        modules = namespace.get("_LAZY_MODULES", ())
        if name in modules:
            current = namespace.get(name)
            if isinstance(current, _ModuleType):
                return current
            return _import_module(f".{name}", _ModuleType.__getattribute__(self, "__name__"))
        return _ModuleType.__getattribute__(self, name)


_sys.modules[__name__].__class__ = _LazyGeometryModule


def __dir__():
    return sorted(set(__all__) | set(_LAZY_MODULES))

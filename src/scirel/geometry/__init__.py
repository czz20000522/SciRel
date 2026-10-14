from .bilinear_grid_sampling import sample_rectilinear_field
from .flux_surface_profile import evaluate_flux_surface_profile
from .flux_surface_inverse_field_average import compute_flux_surface_inverse_field_average
from .axisymmetric_grid_mapping import map_axisymmetric_equilibrium_to_cartesian_grid
from .material_support import classify_material_support
from .axisymmetric_equilibrium_grid_support import solve_axisymmetric_equilibrium_grid_mapping
from .complex_rectilinear_interpolation import interpolate_complex_rectilinear_field
from .planar_wavevector import project_planar_wavevector
from .face_to_cell import face_to_cell

__all__ = [
    'sample_rectilinear_field',
    'evaluate_flux_surface_profile',
    'compute_flux_surface_inverse_field_average',
    'map_axisymmetric_equilibrium_to_cartesian_grid',
    'classify_material_support',
    'solve_axisymmetric_equilibrium_grid_mapping',
    'interpolate_complex_rectilinear_field',
    'project_planar_wavevector',
    'face_to_cell',
]

# Repaired Pleiades geometry addition; existing maintained contracts retained.
from .mesh import Mesh, PointsMesh, RChord, ZChord, SphericalRChord, ThetaChord, RectMesh
from .transforms import rotate
__all__.extend(["Mesh", "PointsMesh", "RChord", "ZChord", "SphericalRChord", "ThetaChord", "RectMesh", "rotate"])

# Domain-organized general primitives.  Legacy top-level modules re-export these
# names so existing callers keep working while new code can depend on geometry.
from .basis import (
    NaturalCubicSpline, ClampedCubicSpline, FirstClampedCubicSpline,
    SecondClampedCubicSpline, build_basis, BasisMatrix,
)
from .fieldline import (
    d_ds_arclength, FieldLineSet, FieldLine, HelperFieldLine, Boundary,
    contour_points, helper_contour_points,
)
from .numerics import NumericalContractError, diff_12_central
from .plotting import scale_patches, get_mirror_patches, transpose_patches
from .sampling import (
    transform_to_rtheta, transform_to_rhoz, regular_grid, poly_fit,
    reflect_and_hstack, locs_to_vals, locs_to_vals_griddata, locs_to_vals1D,
    get_fieldlines, parse_segment, get_fieldline_distance, interp,
    flux_surface_avg, diff_central,
)
from .analysis import get_gpsi
__all__.extend([
    "NaturalCubicSpline", "ClampedCubicSpline", "FirstClampedCubicSpline",
    "SecondClampedCubicSpline", "build_basis", "BasisMatrix", "d_ds_arclength",
    "FieldLineSet", "FieldLine", "HelperFieldLine", "Boundary",
    "contour_points", "helper_contour_points", "NumericalContractError",
    "diff_12_central", "scale_patches", "get_mirror_patches",
    "transpose_patches", "transform_to_rtheta", "transform_to_rhoz",
    "regular_grid", "poly_fit", "reflect_and_hstack", "locs_to_vals",
    "locs_to_vals_griddata", "locs_to_vals1D", "get_fieldlines",
    "parse_segment", "get_fieldline_distance", "interp", "flux_surface_avg",
    "diff_central", "get_gpsi",
])

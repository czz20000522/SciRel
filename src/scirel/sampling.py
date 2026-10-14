"""Compatibility imports for the domain-organized SciRel API.

The implementation lives in ``scirel.geometry.sampling``; this module remains as a stable
bridge for callers using the pre-domain package paths.
"""

from .geometry.sampling import transform_to_rtheta, transform_to_rhoz, regular_grid, poly_fit, reflect_and_hstack, locs_to_vals, locs_to_vals_griddata, locs_to_vals1D, get_fieldlines, parse_segment, get_fieldline_distance, interp, flux_surface_avg, diff_central

__all__ = ['transform_to_rtheta', 'transform_to_rhoz', 'regular_grid', 'poly_fit', 'reflect_and_hstack', 'locs_to_vals', 'locs_to_vals_griddata', 'locs_to_vals1D', 'get_fieldlines', 'parse_segment', 'get_fieldline_distance', 'interp', 'flux_surface_avg', 'diff_central']

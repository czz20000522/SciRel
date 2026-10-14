"""Compatibility imports for the domain-organized SciRel API.

The implementation lives in ``scirel.geometry.fieldline``; this module remains as a stable
bridge for callers using the pre-domain package paths.
"""

from .geometry.fieldline import d_ds_arclength, FieldLineSet, FieldLine, HelperFieldLine, Boundary, contour_points, helper_contour_points

__all__ = ['d_ds_arclength', 'FieldLineSet', 'FieldLine', 'HelperFieldLine', 'Boundary', 'contour_points', 'helper_contour_points']

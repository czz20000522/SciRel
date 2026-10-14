"""Compatibility imports for the domain-organized SciRel API.

The implementation lives in ``scirel.geometry.basis``; this module remains as a stable
bridge for callers using the pre-domain package paths.
"""

from .geometry.basis import NaturalCubicSpline, ClampedCubicSpline, FirstClampedCubicSpline, SecondClampedCubicSpline, build_basis, BasisMatrix

__all__ = ['NaturalCubicSpline', 'ClampedCubicSpline', 'FirstClampedCubicSpline', 'SecondClampedCubicSpline', 'build_basis', 'BasisMatrix']

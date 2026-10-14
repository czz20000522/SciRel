"""Compatibility imports for the domain-organized SciRel API.

The implementation lives in ``scirel.geometry.plotting``; this module remains as a stable
bridge for callers using the pre-domain package paths.
"""

from .geometry.plotting import scale_patches, get_mirror_patches, transpose_patches

__all__ = ['scale_patches', 'get_mirror_patches', 'transpose_patches']

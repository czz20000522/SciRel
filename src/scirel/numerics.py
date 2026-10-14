"""Compatibility imports for the domain-organized SciRel API.

The implementation lives in ``scirel.geometry.numerics``; this module remains as a stable
bridge for callers using the pre-domain package paths.
"""

from .geometry.numerics import NumericalContractError, diff_12_central

__all__ = ['NumericalContractError', 'diff_12_central']

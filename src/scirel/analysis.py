"""Compatibility imports for the domain-organized SciRel API.

The implementation lives in ``scirel.geometry.analysis``; this module remains as a stable
bridge for callers using the pre-domain package paths.
"""

from .geometry.analysis import get_gpsi, NumericalContractError, d_ds_arclength, diff_12_central

__all__ = ['get_gpsi', 'NumericalContractError', 'd_ds_arclength', 'diff_12_central']

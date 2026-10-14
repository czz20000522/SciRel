"""Compatibility imports for the domain-organized SciRel API.

The implementation lives in ``scirel.equilibrium.api``; this module remains as a stable
bridge for callers using the pre-domain package paths.
"""

from .equilibrium.api import EquilibriumResult, compute_equilibrium

__all__ = ['EquilibriumResult', 'compute_equilibrium']

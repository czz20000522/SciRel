"""Public circular parallel Maxwellian dispersion operators."""

from ._fluid_parallel import ContinuationFailure, em1d_parallel_residual
from .parallel_continuation import continue_em1d

__all__ = ["em1d_parallel_residual", "ContinuationFailure", "continue_em1d"]

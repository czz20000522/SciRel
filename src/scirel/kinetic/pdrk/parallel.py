"""Public circular parallel Maxwellian dispersion operators."""

from . import _fluid_parallel as _core
from ._fluid_parallel import ContinuationFailure, em1d_parallel_residual

__all__ = ["em1d_parallel_residual", "continue_em1d", "ContinuationFailure"]


def continue_em1d(inputs):
    """Continue a seeded parallel root across an explicit wave-number grid."""

    return _core.continue_em1d(**inputs)

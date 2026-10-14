"""Circular parallel EM modes of isotropic drifting Maxwellian species."""
from ._fluid_parallel import em1d_parallel_residual, ContinuationFailure
from . import _fluid_parallel as _core

def continue_em1d(inputs):
    """Ordered seeded root continuation from explicit scientific ports."""
    return _core.continue_em1d(**inputs)
__all__=["em1d_parallel_residual","continue_em1d","ContinuationFailure"]

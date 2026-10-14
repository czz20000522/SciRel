"""SI gyrotropic multifluid frequency pencils with explicit collision closure."""
from ._fluid_parallel import fluid_equilibrium_si, fluid_equilibrium_relative_rates, fluid_frequency_pencil, fluid_solve_state
from ._example_support import fluid_deck
from . import _fluid_parallel as _core

def scan_fluid_corrected(inputs):
    """Explicit scan ports; grid_controls packs the declared source grid inputs."""
    ports=dict(inputs);grid=ports.pop("grid_controls",{})
    return _core.scan_fluid_corrected(**ports,**grid)
__all__=["fluid_equilibrium_si","fluid_equilibrium_relative_rates","fluid_frequency_pencil","fluid_solve_state","scan_fluid_corrected","fluid_deck"]

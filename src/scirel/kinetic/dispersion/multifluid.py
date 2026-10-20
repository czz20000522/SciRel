"""Public multifluid the kinetic dispersion formulation operators and the packaged SI example deck."""

from . import _fluid_parallel as _core
from ._example_support import fluid_deck
from ._fluid_parallel import (
    fluid_equilibrium_relative_rates,
    fluid_equilibrium_si,
    fluid_frequency_pencil,
    fluid_solve_state,
)

__all__ = [
    "fluid_equilibrium_si",
    "fluid_equilibrium_relative_rates",
    "fluid_frequency_pencil",
    "fluid_solve_state",
    "scan_fluid_corrected",
    "fluid_deck",
]


def scan_fluid_corrected(inputs):
    """Run one declared fluid scan from a single explicit port mapping."""

    ports = dict(inputs)
    grid_controls = ports.pop("grid_controls", {})
    return _core.scan_fluid_corrected(**ports, **grid_controls)

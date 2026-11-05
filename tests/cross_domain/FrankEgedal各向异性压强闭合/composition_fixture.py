from scirel.kinetic.frank_egedal_pressure_closure import (
    solve_frank_egedal_pressure_closure as _public_function,
)


def run_composition(inputs, **_ignored_loaders):
    return _public_function(inputs)

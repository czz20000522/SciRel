from scirel.mirror.grid_mirror_kinetic_closure import (
    solve_grid_mirror_kinetic_closure as _public_function,
)


def run_composition(inputs, **_ignored_loaders):
    return _public_function(inputs)

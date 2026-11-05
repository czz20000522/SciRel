from scirel.equilibrium.free_boundary_anisotropic_picard import (
    solve_free_boundary_anisotropic_picard as _public_function,
)


def run_composition(inputs, **_ignored_loaders):
    return _public_function(inputs)

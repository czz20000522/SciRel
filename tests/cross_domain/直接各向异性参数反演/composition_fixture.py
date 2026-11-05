from scirel.inference.direct_anisotropic_inversion import (
    solve_direct_anisotropic_inversion as _public_function,
)


def run_composition(inputs, **_ignored_loaders):
    return _public_function(inputs)

from scirel.equilibrium.isotropic_pressure_flux import (
    solve_isotropic_pressure_flux as _public_function,
)


def run_composition(inputs, **_ignored_loaders):
    return _public_function(**inputs)

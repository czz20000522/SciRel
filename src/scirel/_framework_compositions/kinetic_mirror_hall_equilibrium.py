"""Source-free cross-domain framework composition for mirror equilibrium."""
from __future__ import annotations
from collections.abc import Callable, Mapping
from scirel.equilibrium.reduced_hall_anisotropic_picard import solve_reduced_hall_anisotropic_picard
from scirel.kinetic.grid_mirror_kinetic_closure import solve_grid_mirror_kinetic_closure

def compose_kinetic_mirror_hall_equilibrium(inputs: Mapping[str, object], *, kinetic_graph: Callable[[Mapping[str, object]], Mapping[str, object]]=solve_grid_mirror_kinetic_closure, hall_graph: Callable[[Mapping[str, object]], Mapping[str, object]]=solve_reduced_hall_anisotropic_picard) -> Mapping[str, object]:
    """Compose the kinetic closure and Hall graph through explicit state feedback."""
    if not isinstance(inputs, Mapping):
        raise TypeError('inputs must be a mapping')
    required = ('r_grid', 'z_grid', 'psi_vac', 'g_psi', 'ion_mass_kg', 'ion_charge_c', 'kinetic_config')
    missing = [name for name in required if name not in inputs]
    if missing:
        raise ValueError(f'missing required composition inputs: {missing}')
    kinetic_config = inputs['kinetic_config']
    if not isinstance(kinetic_config, Mapping):
        raise ValueError('kinetic_config must be a mapping')
    fixed_config = dict(kinetic_config)

    def pressure_closure(b_t, psi):
        kinetic_inputs = dict(fixed_config)
        kinetic_inputs.update({'r_grid': inputs['r_grid'], 'z_grid': inputs['z_grid'], 'b_t': b_t, 'psi': psi})
        return kinetic_graph(kinetic_inputs)
    hall_inputs = {key: value for key, value in inputs.items() if key != 'kinetic_config'}
    hall_inputs['pressure_closure'] = pressure_closure
    return hall_graph(hall_inputs)
__all__ = ['compose_kinetic_mirror_hall_equilibrium']

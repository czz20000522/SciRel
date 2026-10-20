"""Composition boundary joining a kinetic mirror closure to Hall feedback."""
from __future__ import annotations

__all__ = ["solve_kinetic_mirror_hall_equilibrium"]


def run_composition(inputs, *, composition_loader):
    """Bind each Hall field iterate into the nested kinetic composition."""
    if not isinstance(inputs, dict) or not isinstance(inputs.get("kinetic_config"), dict):
        raise ValueError("inputs.kinetic_config must be a mapping")
    required = ("r_grid", "z_grid", "psi_vac", "g_psi", "ion_mass_kg", "ion_charge_c")
    missing = [name for name in required if name not in inputs]
    if missing:
        raise ValueError(f"{missing[0]} is required")
    kinetic = composition_loader("scirel.kinetic.compositions.grid_mirror_kinetic_closure")
    hall = composition_loader("scirel.equilibrium.compositions.reduced_hall_anisotropic_picard")
    kinetic_config = dict(inputs["kinetic_config"])

    def pressure_closure(B, psi):
        return kinetic({
            **kinetic_config,
            "r_grid": inputs["r_grid"],
            "z_grid": inputs["z_grid"],
            "b_t": B,
            "psi": psi,
        })

    hall_inputs = {key: value for key, value in inputs.items() if key != "kinetic_config"}
    hall_inputs["pressure_closure"] = pressure_closure
    return hall(hall_inputs)


def solve_kinetic_mirror_hall_equilibrium(
    inputs=None, *, kinetic_composition=None, hall_composition=None, **kwargs
):
    """Run the nested kinetic and Hall compositions with explicit dependency ports."""
    from scirel._composition import compose
    from scirel.equilibrium.reduced_hall_anisotropic_picard import solve_reduced_hall_anisotropic_picard
    from scirel.kinetic.grid_mirror_kinetic_closure import solve_grid_mirror_kinetic_closure

    return compose(
        run_composition, inputs, kwargs,
        {"composition_loader": {
            "scirel.kinetic.compositions.grid_mirror_kinetic_closure": kinetic_composition or solve_grid_mirror_kinetic_closure,
            "scirel.equilibrium.compositions.reduced_hall_anisotropic_picard": hall_composition or solve_reduced_hall_anisotropic_picard,
        }},
    )

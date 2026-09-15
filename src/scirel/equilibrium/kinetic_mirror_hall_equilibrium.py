"""Kinetic-mirror reduced-Hall composition over admitted nested task graphs."""

from __future__ import annotations


def run_graph(inputs, *, task_graph_loader):
    """Bind the current Hall field into the nested grid kinetic closure."""
    if (
        not isinstance(inputs, dict)
        or "kinetic_config" not in inputs
        or not isinstance(inputs["kinetic_config"], dict)
    ):
        raise ValueError("inputs.kinetic_config must be a mapping")
    for name in (
        "r_grid",
        "z_grid",
        "psi_vac",
        "g_psi",
        "ion_mass_kg",
        "ion_charge_c",
    ):
        if name not in inputs:
            raise ValueError(f"{name} is required")
    kinetic = task_graph_loader("scirel.kinetic.graphs.grid_mirror_kinetic_closure")
    hall = task_graph_loader(
        "scirel.equilibrium.graphs.reduced_hall_anisotropic_picard"
    )
    kinetic_config = dict(inputs["kinetic_config"])

    def pressure_closure(b_t, psi):
        return kinetic(
            {
                **kinetic_config,
                "r_grid": inputs["r_grid"],
                "z_grid": inputs["z_grid"],
                "b_t": b_t,
                "psi": psi,
            }
        )

    hall_inputs = {key: value for key, value in inputs.items() if key != "kinetic_config"}
    hall_inputs["pressure_closure"] = pressure_closure
    return hall(hall_inputs)


def solve_kinetic_mirror_hall_equilibrium(
    inputs=None, *, kinetic_graph=None, hall_graph=None, **kwargs
):
    """Run the nested kinetic and Hall graphs using explicit dependency bindings."""
    from scirel._composition import compose
    from scirel.equilibrium.reduced_hall_anisotropic_picard import (
        solve_reduced_hall_anisotropic_picard,
    )
    from scirel.kinetic.grid_mirror_kinetic_closure import (
        solve_grid_mirror_kinetic_closure,
    )

    return compose(
        run_graph,
        inputs,
        kwargs,
        {
            "task_graph_loader": {
                "scirel.kinetic.graphs.grid_mirror_kinetic_closure": (
                    kinetic_graph or solve_grid_mirror_kinetic_closure
                ),
                "scirel.equilibrium.graphs.reduced_hall_anisotropic_picard": (
                    hall_graph or solve_reduced_hall_anisotropic_picard
                ),
            }
        },
    )


__all__ = ["solve_kinetic_mirror_hall_equilibrium"]

"""FIDASIM N3 DCX/halo marker initial-state composition.

Source: the saved FIDASIM ``DCXHalo标记初态图`` TaskGraph (framework node
N3 ``neutral_population_transport``).  The graph replays the source
marker-initialization order ``mc_beam_grid -> get_plasma -> mc_halo ->
track/get_total_cx_rate -> states`` by composing already-integrated
leaves: the beam-grid cell position from caller uniform draws, the
caller's plasma-state provider callback invoked at the sampled position,
the thermal-species mass selection, the thermal Maxwellian halo velocity
from caller normal draws, the caller's level-resolved CX-rate provider
invoked at the sampled position and velocity, and the DCX/halo
collisional-radiative initial-state weighting.  The node order is
non-interchangeable and enforced.

Caller-owned boundaries: RNG algorithm and continuation, ``get_plasma``
and ``get_total_cx_rate`` state (the two provider callables), track
geometry, ``colrad`` advancement, neutral-reservoir updates, photon
storage and MPI reduction.  Callback results are not cached as hidden
state, and no full DCX/halo Monte-Carlo parity is claimed.

Registered hardenings against the saved arm: provider contract violations
raise ValueError (the saved arm lets a raw TypeError or KeyError escape),
and the plasma snapshot must carry the declared finite fields.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np

__all__ = ["initialize_dcx_halo_marker", "run_graph"]

_GRAPH_ORDER = ["cell_position", "local_plasma", "thermal_species_selection", "halo_velocity", "cx_rate", "initial_state"]


def run_graph(inputs, *, asset_loader):
    """Run the DCX/halo marker-initialization graph with explicit asset bindings."""
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be a mapping")
    for name in (
        "cell_center_cm", "cell_width_cm", "uniform_draws",
        "plasma_state_provider", "standard_normal_draw",
        "selected_thermal_species_index", "beam_mass_amu",
        "fast_ion_density_cm3", "velocity_squared_to_kev_per_amu",
        "cx_rate_provider",
    ):
        if name not in inputs:
            raise ValueError(f"{name} is required")
    plasma_provider = inputs["plasma_state_provider"]
    rate_provider = inputs["cx_rate_provider"]
    if not callable(plasma_provider) or not callable(rate_provider):
        raise ValueError("plasma_state_provider and cx_rate_provider must be callable")
    sample_cell = asset_loader("scirel.fusion.beam_grid_cell_sampling")
    position = sample_cell(
        cell_center_cm=inputs["cell_center_cm"],
        cell_width_cm=inputs["cell_width_cm"],
        uniform_draws=inputs["uniform_draws"],
    )
    plasma = plasma_provider(position)
    if not isinstance(plasma, Mapping):
        raise ValueError("plasma_state_provider must return a mapping")
    for key in ("plasma_rotation_cm_s", "ion_temperature_kev", "thermal_ion_density_cm3", "thermal_mass_amu"):
        if key not in plasma:
            raise ValueError(f"plasma_state_provider snapshot is missing {key}")
    if not np.all(np.isfinite(np.asarray(plasma["plasma_rotation_cm_s"], dtype=float))):
        raise ValueError("plasma_state_provider rotation must be finite")
    if not np.isfinite(plasma["ion_temperature_kev"]) or plasma["ion_temperature_kev"] <= 0:
        raise ValueError("plasma_state_provider ion temperature must be finite positive")
    select_mass = asset_loader("scirel.fusion.dcx_thermal_species_selection")
    selected_mass = select_mass(plasma["thermal_mass_amu"], inputs["selected_thermal_species_index"])
    sample_halo = asset_loader("scirel.fusion.halo_velocity_sampling")
    velocity = sample_halo(
        plasma_rotation_cm_s=plasma["plasma_rotation_cm_s"],
        ion_temperature_kev=plasma["ion_temperature_kev"],
        ion_mass_amu=selected_mass,
        velocity_squared_to_kev_per_amu=inputs["velocity_squared_to_kev_per_amu"],
        standard_normal_draw=inputs["standard_normal_draw"],
    )
    rates = rate_provider(position, velocity["halo_velocity_cm_s"])
    rates = np.asarray(rates, dtype=float)
    if (rates.ndim != 1 or rates.size == 0 or not np.all(np.isfinite(rates)) or np.any(rates < 0.0)):
        raise ValueError("cx_rate_provider must return finite nonnegative level-resolved rates")
    prepare = asset_loader("scirel.fusion.dcx_halo_colrad_initial_state")
    initial = prepare(
        cx_rate_per_s=rates,
        thermal_ion_density_cm3=plasma["thermal_ion_density_cm3"],
        thermal_mass_amu=plasma["thermal_mass_amu"],
        selected_thermal_species_index=inputs["selected_thermal_species_index"],
        fast_ion_density_cm3=inputs["fast_ion_density_cm3"],
        beam_mass_amu=inputs["beam_mass_amu"],
    )
    return {
        "guiding_center_position_cm": position,
        "plasma_state": dict(plasma),
        "halo_velocity_cm_s": velocity["halo_velocity_cm_s"],
        "thermal_speed_cm_s": velocity["thermal_speed_cm_s"],
        "cx_rate_per_s": rates,
        **initial,
        "diagnostics": {"graph_order": list(_GRAPH_ORDER)},
    }


def initialize_dcx_halo_marker(inputs=None, **kwargs):
    """Run the DCX/halo marker-initialization graph with explicit dependency bindings."""
    from scirel._composition import compose
    from scirel.fusion.beam_grid_cell_sampling import sample_beam_grid_cell as _dependency_0
    from scirel.fusion.dcx_halo_colrad_initial_state import prepare_dcx_colrad_initial_state as _dependency_1
    from scirel.fusion.dcx_thermal_species_selection import select_dcx_thermal_species_mass as _dependency_2
    from scirel.fusion.halo_velocity_sampling import sample_halo_velocity as _dependency_3
    return compose(run_graph, inputs, kwargs, {
        "asset_loader": {
            "scirel.fusion.beam_grid_cell_sampling": _dependency_0,
            "scirel.fusion.dcx_halo_colrad_initial_state": _dependency_1,
            "scirel.fusion.dcx_thermal_species_selection": _dependency_2,
            "scirel.fusion.halo_velocity_sampling": _dependency_3,
        },
    })

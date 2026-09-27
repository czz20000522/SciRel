"""FIDASIM N2 NBI trajectory-initialization graph (caller-random paths).

Source: the saved FIDASIM ``NBI轨迹初始化图`` TaskGraph (framework node N2
``neutral_beam_source_sampling``).  Inside one frozen NBI configuration
snapshot the graph first forms the marker-loop neutral-rate normalization
(``ndmc``), then executes exactly one of the two source-mutually-exclusive
trajectory branches:

- ``source_ray``: the ``mc_nbi`` source-plane ray (caller uniform/normal
  variates), aperture acceptance, energy-component velocity scaling of the
  same accepted unit ray, and an optional finite beam-grid entry/exit handoff
  (``grid_intersect``); the N1 ``in_plasma`` check stays a framework edge.
- ``cell_directed``: the ``mc_nbi_cell`` cell-targeted ray with its Gaussian
  divergence weight.

The saved graph's serial ``utilities.f90`` two-word RNG paths (seed,
captured state, 1000-rejection fallback) are controlled glue owned by the
source runtime, not a scientific relation; consistent with the NBI leaf
family's caller-owned randomness convention they are a declared non-ported
boundary here, and supplying their state keys is rejected.  Callers who need
the rejection loop resupply variates and consume the ``accepted`` flag.
"""
from __future__ import annotations

from collections.abc import Mapping

__all__ = ["initialize_nbi_trajectory", "run_graph"]

_SERIAL_RNG_STATE_KEYS = ("source_serial_rng_seed", "source_rng_state", "source_fallback_axis_beam")


def run_graph(inputs, *, asset_loader):
    """Run the N2 initialization slice with explicit asset bindings."""
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be a mapping")
    for name in ("sampling_mode", "injected_power_mw", "injection_energy_kev", "current_fractions", "beam_grid_cell_volume_cm3"):
        if name not in inputs:
            raise ValueError(f"{name} is required")
    mode = inputs["sampling_mode"]
    if mode not in ("source_ray", "cell_directed"):
        raise ValueError("sampling_mode must be source_ray or cell_directed")
    normalize = asset_loader("scirel.fusion.nbi_injected_neutrals_normalization")
    result = dict(normalize(
        inputs["injected_power_mw"],
        inputs["injection_energy_kev"],
        inputs["current_fractions"],
        inputs["beam_grid_cell_volume_cm3"],
    ))
    if mode == "source_ray":
        state = inputs.get("source_ray_state")
        if not isinstance(state, Mapping):
            raise ValueError("source_ray_state is required for the source_ray branch")
        state = dict(state)
        for key in _SERIAL_RNG_STATE_KEYS:
            if key in state:
                raise ValueError(
                    f"{key} belongs to the source serial RNG runtime boundary, "
                    "which this graph does not port; supply caller random "
                    "records source_uniform and divergence_normal instead")
        for key in ("injection_speed_cm_s", "energy_component", "source_uniform", "divergence_normal"):
            if key not in state:
                raise ValueError(f"source_ray_state.{key} is required")
        speed = state.pop("injection_speed_cm_s")
        component = state.pop("energy_component")
        construct = asset_loader("scirel.fusion.nbi_source_plane_ray")
        source, ray, accepted = construct(**state)
        scale = asset_loader("scirel.fusion.nbi_energy_component_velocity")
        velocity = scale(ray, speed, component)
        entry_state = inputs.get("beam_grid_entry_state")
        if entry_state is None:
            entry = {"entry_point_cm": None, "exit_point_cm": None, "intersection_length_cm": None, "intersects_grid": None}
        else:
            if not isinstance(entry_state, Mapping):
                raise ValueError("beam_grid_entry_state must be a mapping")
            intersect = asset_loader("scirel.fusion.beam_grid_ray_intersection")
            entry = intersect(ray_origin_cm=source, ray_direction=ray, **entry_state)
        result.update(
            source_beam_cm=source,
            unit_ray_beam=ray,
            velocity_cm_s=velocity,
            accepted=accepted,
            trajectory_weight=None,
            initial_grid_entry_cm=entry["entry_point_cm"],
            grid_exit_cm=entry["exit_point_cm"],
            grid_intersection_length_cm=entry["intersection_length_cm"],
            intersects_beam_grid=entry["intersects_grid"],
        )
        return result
    state = inputs.get("cell_directed_state")
    if not isinstance(state, Mapping):
        raise ValueError("cell_directed_state is required for the cell_directed branch")
    cell = asset_loader("scirel.fusion.nbi_cell_directed_ray")(**state)
    result.update(
        source_beam_cm=None,
        unit_ray_beam=None,
        velocity_cm_s=cell["velocity_uvw_cm_s"],
        accepted=cell["accepted"],
        trajectory_weight=cell["trajectory_weight"],
        initial_grid_entry_cm=None,
        grid_exit_cm=None,
        grid_intersection_length_cm=None,
        intersects_beam_grid=None,
    )
    return result


def initialize_nbi_trajectory(inputs=None, **kwargs):
    """Run the NBI trajectory-initialization graph with explicit dependency bindings."""
    from scirel._composition import compose
    from scirel.fusion.beam_grid_ray_intersection import intersect_ray_with_rectilinear_grid as _dependency_0
    from scirel.fusion.nbi_cell_directed_ray import nbi_cell_directed_ray as _dependency_1
    from scirel.fusion.nbi_energy_component_velocity import scale_nbi_velocity_for_energy_component as _dependency_2
    from scirel.fusion.nbi_injected_neutrals_normalization import normalize_nbi_injected_neutrals as _dependency_3
    from scirel.fusion.nbi_source_plane_ray import construct_nbi_source_ray as _dependency_4
    return compose(run_graph, inputs, kwargs, {
        "asset_loader": {
            "scirel.fusion.beam_grid_ray_intersection": _dependency_0,
            "scirel.fusion.nbi_cell_directed_ray": _dependency_1,
            "scirel.fusion.nbi_energy_component_velocity": _dependency_2,
            "scirel.fusion.nbi_injected_neutrals_normalization": _dependency_3,
            "scirel.fusion.nbi_source_plane_ray": _dependency_4,
        },
    })

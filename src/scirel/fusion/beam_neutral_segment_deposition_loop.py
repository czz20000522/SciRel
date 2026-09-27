"""FIDASIM N3 beam-neutral segment deposition composition.

Source: the saved FIDASIM ``束中性逐段碰撞辐射沉积图`` TaskGraph (framework
node N3 ``neutral_population_transport``; source order
``track -> get_plasma -> colrad -> dens/nlaunch -> flux*dv`` per
src/fidasim.f90:9346-9461, 9980-10067, 11776-11837, 13041-13057).  The
graph composes already-integrated leaves: the beam-grid DDA segment
traversal, and per segment (in enforced source order) the explicit
caller-owned local plasma/atomic snapshot, the caller's N4 cell-update
result record, and the marker-normalized N3/N4 deposition handoff.  The
node order is non-interchangeable and enforced.

Graph-internal validation nodes (registered deviation from the saved
packaging, reviewer finding): the saved bundle declares the deposition
initial-state materialization (``N3逐段沉积初态规范化``) and the local
plasma/atomic snapshot normalization (``N3局域等离子体原子快照规范化``)
as separate saved operators.  Both are data-edge validation gates -- they
return caller data essentially unchanged and compute no scientific
relation -- and no integrated SciRel public operator is a pure
pass-through validator, so they execute here as graph-internal helpers
instead of being published as standalone assets.  Promotion to public
operators is deferred until a second standalone consumer exists; the
saved implementations' contracts are reproduced verbatim by the helpers.

External boundaries: the N4 colrad cell update is an explicit caller
capability -- the graph consumes N4 result records and never executes
colrad, plasma/field lookup, HDF5/grid interpolation, RNG, MPI,
reservoir writes or whole-program parity.  Under the frozen r77
``collisional-radiative-state-advance`` document contract (states labeled
cm^-3, photons s^-1) its outputs could not legally populate the N4
records as declared here (rate-density states cm^-3 s^-1, cm^-3
integrated density, cm^-3 s^-1 photons); the unit-label question is
retained for expert adjudication and no direct composition is implied.

Registered hardenings against the saved arm: record-sequence inputs must
be genuine ordered mappings (the saved arm accepted any Sequence);
count mismatches between tracks, snapshots and N4 records fail closed.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

__all__ = ["deposit_beam_neutral_segments", "run_graph"]

_GRAPH_ORDER = ["deposition_initialization", "beam_grid_track", "local_state_sequence",
                "n4_cell_update_handoff", "deposition"]

_SNAPSHOT_KEYS = (
    "position_cm", "in_plasma", "thermal_density_cm3", "thermal_mass_amu", "ion_temperature_kev",
    "electron_density_cm3", "electron_temperature_kev", "impurity_density_cm3", "fast_ion_density_cm3",
    "beam_mass_amu", "beam_energy_kev", "hydrogen_table", "electron_table", "impurity_table",
    "einstein_s_inv", "snapshot_provenance",
)

_TABLE_KEYS = (
    "nenergy", "ntemp", "logemin", "logtmin", "dlogE", "dlogT",
    "minlog_pop", "minlog_depop", "log_pop", "log_depop",
)


def _finite_vector(value, name, *, size=None, positive=False, nonnegative=False):
    array = np.asarray(value, dtype=float)
    if array.ndim != 1 or (size is not None and array.size != size) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite one-dimensional vector")
    if positive and np.any(array <= 0.0):
        raise ValueError(f"{name} must be positive")
    if nonnegative and np.any(array < 0.0):
        raise ValueError(f"{name} must be nonnegative")
    return array


def _transition_table(table, name, nlevels):
    if not isinstance(table, Mapping) or set(_TABLE_KEYS) - set(table):
        raise ValueError(f"{name} must contain the declared transition-table fields")
    # Registered hardening: the saved arm's int() silently truncated
    # fractional knot counts such as 2.0; genuine integers are required.
    for key in ("nenergy", "ntemp"):
        value = table[key]
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
            raise ValueError(f"{name} {key} must be a genuine integer knot count (registered hardening)")
    nenergy, ntemp = int(table["nenergy"]), int(table["ntemp"])
    if nenergy < 2 or ntemp < 2:
        raise ValueError(f"{name} must provide at least two energy and temperature knots")
    if any(not np.isfinite(float(table[key])) for key in ("logemin", "logtmin", "dlogE", "dlogT", "minlog_pop", "minlog_depop")):
        raise ValueError(f"{name} log-grid metadata must be finite")
    if float(table["dlogE"]) <= 0.0 or float(table["dlogT"]) <= 0.0:
        raise ValueError(f"{name} log-grid increments must be positive")
    population = np.asarray(table["log_pop"], dtype=float)
    depopulation = np.asarray(table["log_depop"], dtype=float)
    if population.shape != (nlevels, nlevels, nenergy, ntemp) or depopulation.shape != (nlevels, nenergy, ntemp):
        raise ValueError(f"{name} transition-table axes do not match n_levels, nenergy, ntemp")
    if not np.all(np.isfinite(population)) or not np.all(np.isfinite(depopulation)):
        raise ValueError(f"{name} transition-table values must be finite")
    return table


def _initialize_deposition_state(initial_states_cm_inv3_s_inv, nlaunch, beam_grid_cell_volume_cm3):
    """Graph-internal executable form of the saved N3逐段沉积初态规范化 contract."""
    states = np.asarray(initial_states_cm_inv3_s_inv, dtype=float)
    if states.ndim != 1 or states.size == 0 or not np.all(np.isfinite(states)) or np.any(states < 0.0):
        raise ValueError("initial_states_cm_inv3_s_inv must be a finite nonnegative one-dimensional vector")
    for name, value in (("nlaunch", nlaunch), ("beam_grid_cell_volume_cm3", beam_grid_cell_volume_cm3)):
        if isinstance(value, (bool, np.bool_)) or not np.isscalar(value) or isinstance(value, (str, bytes)):
            raise ValueError(f"{name} must be a genuine finite positive scalar")
        number = float(value)
        if not np.isfinite(number) or number <= 0.0:
            raise ValueError(f"{name} must be a genuine finite positive scalar")
    return {
        "initial_states_cm_inv3_s_inv": states,
        "nlaunch": float(nlaunch),
        "beam_grid_cell_volume_cm3": float(beam_grid_cell_volume_cm3),
        "deposited_particles_per_s": 0.0,
    }


def _normalize_local_state_sample(record, normalizer):
    """Graph-internal executable form of the saved N3局域等离子体原子快照规范化 contract."""
    if not isinstance(record, Mapping):
        raise ValueError("each local_state_samples item must be a mapping")
    try:
        return normalizer(**{key: record[key] for key in _SNAPSHOT_KEYS})
    except KeyError as error:
        raise ValueError(f"local state sample misses declared field {error.args[0]}") from error


def _normalizer(**record):
    """Validate one caller-owned N3/N4 local snapshot without file or global-state access."""
    position = _finite_vector(record["position_cm"], "position_cm", size=3)
    if not isinstance(record["in_plasma"], (bool, np.bool_)):
        raise ValueError("in_plasma must be boolean")
    density = _finite_vector(record["thermal_density_cm3"], "thermal_density_cm3", nonnegative=True)
    mass = _finite_vector(record["thermal_mass_amu"], "thermal_mass_amu", positive=True)
    if density.size == 0 or mass.shape != density.shape:
        raise ValueError("thermal density and mass must be nonempty, same-axis vectors")
    scalar_names = (
        "ion_temperature_kev", "electron_density_cm3", "electron_temperature_kev",
        "impurity_density_cm3", "fast_ion_density_cm3", "beam_mass_amu", "beam_energy_kev",
    )
    for name in scalar_names:
        value = record[name]
        if isinstance(value, (bool, np.bool_)) or not np.isscalar(value) or isinstance(value, (str, bytes)):
            raise ValueError(f"{name} must be a genuine finite scalar")
        if not np.isfinite(float(value)):
            raise ValueError("local scalar plasma and beam values must be finite")
    if min(float(record["beam_mass_amu"]), float(record["beam_energy_kev"])) <= 0.0:
        raise ValueError("beam mass and beam energy must be positive")
    if record["in_plasma"] and min(float(record["ion_temperature_kev"]), float(record["electron_temperature_kev"])) <= 0.0:
        raise ValueError("in-plasma temperatures must be positive")
    if not record["in_plasma"] and min(float(record["ion_temperature_kev"]), float(record["electron_temperature_kev"])) < 0.0:
        raise ValueError("out-of-plasma temperatures must be nonnegative")
    if min(float(record["electron_density_cm3"]), float(record["impurity_density_cm3"]), float(record["fast_ion_density_cm3"])) < 0.0:
        raise ValueError("local densities must be nonnegative")
    einstein = np.asarray(record["einstein_s_inv"], dtype=float)
    if einstein.ndim != 2 or einstein.shape[0] == 0 or einstein.shape[0] != einstein.shape[1] or not np.all(np.isfinite(einstein)):
        raise ValueError("einstein_s_inv must be a finite nonempty square matrix")
    if not isinstance(record["snapshot_provenance"], str) or not record["snapshot_provenance"].strip():
        raise ValueError("snapshot_provenance must be a nonempty caller-owned data identity")
    nlevels = einstein.shape[0]
    _transition_table(record["hydrogen_table"], "hydrogen_table", nlevels)
    _transition_table(record["electron_table"], "electron_table", nlevels)
    _transition_table(record["impurity_table"], "impurity_table", nlevels)
    return {
        "position_cm": position,
        "in_plasma": bool(record["in_plasma"]),
        "thermal_density_cm3": density,
        "thermal_mass_amu": mass,
        "ion_temperature_kev": float(record["ion_temperature_kev"]),
        "electron_density_cm3": float(record["electron_density_cm3"]),
        "electron_temperature_kev": float(record["electron_temperature_kev"]),
        "impurity_density_cm3": float(record["impurity_density_cm3"]),
        "fast_ion_density_cm3": float(record["fast_ion_density_cm3"]),
        "beam_mass_amu": float(record["beam_mass_amu"]),
        "beam_energy_kev": float(record["beam_energy_kev"]),
        "hydrogen_table": record["hydrogen_table"],
        "electron_table": record["electron_table"],
        "impurity_table": record["impurity_table"],
        "einstein_s_inv": einstein,
        "snapshot_provenance": record["snapshot_provenance"].strip(),
    }


def run_graph(inputs, *, asset_loader):
    """Run the beam-neutral segment-deposition graph with explicit asset bindings."""
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be a mapping")
    for name in (
        "start_position_cm", "neutral_velocity_cm_s", "initial_grid_index_one_based",
        "beam_grid", "initial_states_cm_inv3_s_inv", "nlaunch", "beam_grid_cell_volume_cm3",
        "local_state_samples", "n4_cell_update_records",
    ):
        if name not in inputs:
            raise ValueError(f"{name} is required")
    beam_grid = inputs["beam_grid"]
    if not isinstance(beam_grid, Mapping) or not callable(beam_grid.get("in_plasma_at")):
        raise ValueError("beam_grid must be a mapping with a callable in_plasma_at predicate")
    if isinstance(inputs["local_state_samples"], (str, bytes)) or isinstance(inputs["n4_cell_update_records"], (str, bytes)):
        raise ValueError("local-state and N4-update inputs must be ordered record sequences")
    if (not isinstance(inputs["local_state_samples"], Sequence)
            or not isinstance(inputs["n4_cell_update_records"], Sequence)):
        raise ValueError("local-state and N4-update inputs must be ordered record sequences")
    track = asset_loader("scirel.fusion.beam_grid_ray_segment_tracking")
    deposit = asset_loader("scirel.fusion.n3_n4_segment_deposition")
    initial = _initialize_deposition_state(
        inputs["initial_states_cm_inv3_s_inv"], inputs["nlaunch"], inputs["beam_grid_cell_volume_cm3"])
    tracks = track(
        start_position_cm=inputs["start_position_cm"],
        velocity_cm_s=inputs["neutral_velocity_cm_s"],
        initial_grid_index_one_based=inputs["initial_grid_index_one_based"],
        **beam_grid,
    )
    segments = tracks["segments"]
    if len(inputs["local_state_samples"]) != len(segments) or len(inputs["n4_cell_update_records"]) != len(segments):
        raise ValueError("N3 local-state and N4-result record counts must equal track segment count")
    states, records, deposited = initial["initial_states_cm_inv3_s_inv"], [], initial["deposited_particles_per_s"]
    for index, segment in enumerate(segments):
        local = _normalize_local_state_sample(inputs["local_state_samples"][index], _normalizer)
        update = deposit(
            expected_position_cm=segment["position_cm"], actual_position_cm=local["position_cm"],
            n4_cell_update_record=inputs["n4_cell_update_records"][index], local_state_sample_index=index,
            previous_states_cm_inv3_s_inv=states, segment_duration_s=segment["duration_s"],
            nlaunch=initial["nlaunch"],
            beam_grid_cell_volume_cm3=initial["beam_grid_cell_volume_cm3"],
            previous_deposited_particles_per_s=deposited,
        )
        states, deposited = update["next_states_cm_inv3_s_inv"], update["deposited_particles_per_s"]
        records.append({
            "position_cm": segment["position_cm"], "duration_s": segment["duration_s"],
            "grid_index_one_based": segment["grid_index_one_based"],
            "normalized_density_cm_inv3": update["normalized_density_cm_inv3"],
            "photons_per_cm3_s": update["normalized_photons_per_cm3_s"],
            "segment_flux_per_cm3_s": update["segment_flux_per_cm3_s"],
        })
    return {"segment_depositions": records, "final_states_cm_inv3_s_inv": states,
            "deposited_particles_per_s": deposited, "track_terminal_reason": tracks["terminal_reason"],
            "diagnostics": {"graph_order": list(_GRAPH_ORDER)}}


def deposit_beam_neutral_segments(inputs=None, **kwargs):
    """Run the beam-neutral segment-deposition graph with explicit dependency bindings."""
    from scirel._composition import compose
    from scirel.fusion.beam_grid_ray_segment_tracking import trace_beam_grid_ray_segments as _dependency_0
    from scirel.fusion.n3_n4_segment_deposition import assemble_n3_n4_segment_deposition as _dependency_1
    return compose(run_graph, inputs, kwargs, {
        "asset_loader": {
            "scirel.fusion.beam_grid_ray_segment_tracking": _dependency_0,
            "scirel.fusion.n3_n4_segment_deposition": _dependency_1,
        },
    })

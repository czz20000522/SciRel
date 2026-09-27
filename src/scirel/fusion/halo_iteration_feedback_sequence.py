"""FIDASIM bounded explicit multi-round N3 DCX/HALO feedback sequence.

Source: the saved FIDASIM ``DCXHalo迭代反馈序列图`` TaskGraph (framework
node N3 ``neutral_population_transport``, source anchor
``src/fidasim.f90:13293-13420``).  The graph replays the source-ordered
HALO population feedback recurrence over a caller-provided sequence of
explicit current-generation densities: each round consumes the fixed DCX
seed density, the current density, the running previous/merged state and
the fixed source ``inputs%n_halo`` base budget; the requested marker
budgets must follow the source recurrence (base budget first, then each
round's ``next_halo_marker_count``) and drift fails closed.  The feedback
is explicit and bounded: state, order, stop branches
(``density_growth_exceeded`` / ``seed_below_threshold``) and the iteration
bound (the provided sequence length) are declared, and the sequence must
end exactly at a source stop branch -- continuing inputs after a stop or
ending while still continuing fail closed.  MC markers, plasma, track,
colrad, reservoir, MPI and HDF5 producers stay outside this graph.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np

__all__ = ["advance_halo_iteration_feedback_sequence", "run_graph"]


def _positive_integer(value, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or int(value) <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _scalar(value, name: str, *, positive: bool = False, nonnegative: bool = False) -> float:
    if isinstance(value, (bool, np.bool_)) or not (np.asarray(value).shape == ()):
        raise ValueError(f"{name} must be a scalar")
    result = float(value)
    if not np.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if positive and result <= 0.0:
        raise ValueError(f"{name} must be positive")
    if nonnegative and result < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _integer_vector(value, name: str, *, nonnegative: bool) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if array.ndim != 1 or array.size < 1 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a non-empty finite vector")
    if np.any(array != array.astype(np.int64)) or (nonnegative and np.any(array < 0.0)):
        raise ValueError(f"{name} must contain nonnegative integers")
    return array.astype(np.int64)


def run_graph(inputs, *, asset_loader):
    """Run the bounded HALO feedback sequence with explicit asset bindings."""
    if not isinstance(inputs, Mapping):
        raise ValueError("inputs must be a mapping")
    for name in (
        "dcx_density_cm3",
        "initial_previous_halo_density_cm3",
        "initial_merged_halo_density_cm3",
        "current_halo_densities_cm3",
        "requested_halo_marker_budgets",
        "source_halo_marker_budget",
    ):
        if name not in inputs:
            raise ValueError(f"{name} is required")
    dcx = _scalar(inputs["dcx_density_cm3"], "dcx_density_cm3", positive=True)
    previous = _scalar(inputs["initial_previous_halo_density_cm3"], "initial_previous_halo_density_cm3", positive=True)
    merged = _scalar(inputs["initial_merged_halo_density_cm3"], "initial_merged_halo_density_cm3", nonnegative=True)
    base_budget = _positive_integer(inputs["source_halo_marker_budget"], "source_halo_marker_budget")
    current = np.asarray(inputs["current_halo_densities_cm3"], dtype=float)
    if current.ndim != 1 or current.size < 1 or (not np.all(np.isfinite(current))) or np.any(current < 0.0):
        raise ValueError("current_halo_densities_cm3 must be a non-empty finite nonnegative vector")
    requested = _integer_vector(inputs["requested_halo_marker_budgets"], "requested_halo_marker_budgets", nonnegative=True)
    if requested.shape != current.shape:
        raise ValueError("requested_halo_marker_budgets must match current_halo_densities_cm3")
    feedback = asset_loader("scirel.fusion.halo_iteration_feedback")
    records: list[dict[str, object]] = []
    branch_counts: dict[str, int] = {}
    for index, current_density in enumerate(current):
        expected_requested = base_budget if index == 0 else records[-1]["next_halo_marker_count"]
        if expected_requested is None or int(requested[index]) != int(expected_requested):
            raise ValueError(f"requested marker budget drift at iteration {index + 1}")
        result = feedback(dcx, previous, float(current_density), merged, base_budget)
        record = {
            "iteration": index + 1,
            "requested_halo_marker_budget": int(requested[index]),
            "previous_halo_density_cm3": previous,
            "current_halo_density_cm3": float(current_density),
            "previous_merged_halo_density_cm3": merged,
            **result,
        }
        records.append(record)
        branch_counts[result["stop_reason"]] = branch_counts.get(result["stop_reason"], 0) + 1
        if not result["continue_iteration"]:
            if index != current.size - 1:
                raise ValueError("current density sequence continues after source stop")
            break
        previous = float(result["next_previous_halo_density_cm3"])
        merged = float(result["merged_halo_density_after_cm3"])
    if not records or records[-1]["continue_iteration"]:
        raise ValueError("current density sequence ended before a source stop branch")
    terminal = records[-1]
    return {
        "iterations": records,
        "final_state": {
            "iterations_completed": len(records),
            "previous_halo_density_cm3": terminal["next_previous_halo_density_cm3"],
            "merged_halo_density_cm3": terminal["merged_halo_density_after_cm3"],
            "next_halo_marker_count": terminal["next_halo_marker_count"],
            "stop_reason": terminal["stop_reason"],
            "continue_iteration": terminal["continue_iteration"],
        },
        "diagnostics": {
            "graph_order": ["halo_iteration_feedback_sequence"],
            "iteration_order": [record["iteration"] for record in records],
            "framework_mapping": "N3.neutral_population_transport",
            "branch_counts": branch_counts,
            "explicit_current_density": True,
            "explicit_requested_marker_budget": True,
            "cross_pfm_edges": [],
        },
    }


def advance_halo_iteration_feedback_sequence(inputs=None, **kwargs):
    """Run the HALO feedback-sequence graph with explicit dependency bindings."""
    from scirel._composition import compose
    from scirel.fusion.halo_iteration_feedback import advance_halo_iteration_feedback as _dependency_0
    return compose(run_graph, inputs, kwargs, {
        "asset_loader": {
            "scirel.fusion.halo_iteration_feedback": _dependency_0,
        },
    })

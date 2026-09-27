"""FIDASIM N3 explicit-state neutral population and reservoir merge composition.

Source: the saved FIDASIM ``中性库种群合并图`` TaskGraph (framework node
N3 ``neutral_population_transport``; source anchors
``src/fidasim.f90:10343-10392`` reservoir merge, ``10484-10498``
population-density merge).  The saved source relation
``merge_neutral_populations`` performs two halves on one explicit
target/source pair: the six-level population-density addition and the
local reservoir-sampling merge.  The graph composes the two integrated
leaves with both state pieces caller-owned: the density half runs first
(density addition, source preserved), then the reservoir half consumes
its explicit state and RNG records; the two are independent explicit
inputs, and neither result feeds the other's arithmetic (the source
relation keeps the same separation).

Registered deviation from the saved packaging: the saved bundle's
single-step delegation graph ``中性库合并图`` (one node calling
``merge_neutral_reservoirs`` and attaching diagnostics) is not ported as
a separate asset -- its ports equal the operator's contract one-to-one,
following the established DCXHalo迭代反馈图 precedent -- so the graph's
second node binds directly to the integrated
``scirel.fusion.neutral-reservoir-merge`` operator and the
``res2 = res1`` local feedback stays declared in the diagnostics.
The saved ``reservoir_merge_inputs`` mapping must be a real mapping;
every other port validation is performed by the leaves themselves.
"""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from scirel.fusion.neutral_population_density_merge import merge_neutral_population_density
from scirel.fusion.neutral_reservoir_merge import merge_neutral_reservoirs

__all__ = ["merge_neutral_population_state", "run_graph"]

_GRAPH_ORDER = ["population_density_merge", "reservoir_merge"]


def merge_neutral_population_state(
    *,
    target_population_density,
    source_population_density,
    reservoir_merge_inputs,
):
    """Compose the density merge and the local reservoir merge in source order."""
    density_result = merge_neutral_population_density(
        target_population_density=target_population_density,
        source_population_density=source_population_density,
    )
    if not isinstance(reservoir_merge_inputs, Mapping):
        raise ValueError("reservoir_merge_inputs must be an explicit mapping")
    reservoir_result = merge_neutral_reservoirs(**reservoir_merge_inputs)
    if not isinstance(reservoir_result.get("branch"), str) or reservoir_result["branch"] not in (
        "source_empty",
        "both_nonfull",
        "target_nonfull_source_full",
        "target_full_source_nonfull",
        "both_full",
    ):
        raise ValueError(f"reservoir leaf returned an undeclared branch: {reservoir_result.get('branch')!r}")
    return {
        **density_result,
        "reservoir_merge": reservoir_result,
        "diagnostics": {
            "graph_order": list(_GRAPH_ORDER),
            "framework_mapping": "N3.neutral_population_transport",
            "local_feedback": "reservoir_merge_res2_equals_res1_after_nonempty_merge",
            "source_density_ownership": "target_updated_source_preserved",
            "cross_pfm_edges": [],
        },
    }


def run_graph(**state):
    """Saved-graph entrypoint shim: forward the explicit state to the composition."""
    expected = {
        "target_population_density",
        "source_population_density",
        "reservoir_merge_inputs",
    }
    if set(state) != expected:
        raise ValueError(
            "graph ports must be exactly ("
            + ", ".join(sorted(expected))
            + f"); got ({', '.join(sorted(state))})"
        )
    return merge_neutral_population_state(**state)

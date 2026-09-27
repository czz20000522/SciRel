"""Direct contract tests for the r76 FIDASIM N3 DCX/HALO iteration-feedback
family: ``advance_halo_iteration_feedback`` (one ``halo`` density-feedback
round) and the bounded sequence graph
``advance_halo_iteration_feedback_sequence``.

The saved packages' own probes (the 0.559 seed case with marker count 22,
ratio=1 continuing, the 0.01 seed-equality boundary continuing, the
density-growth fail-closed exit with None projections, and the bounded
sequence reaching seed_below_threshold with preserved budget recurrence)
are reproduced.  Registered hardenings -- non-finite ratio/seed/merge
overflow failing closed instead of the saved arm's silent Inf or
``int(Inf)`` crash -- discriminate without changing ordinary-domain
arithmetic.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from scirel.fusion import (
    advance_halo_iteration_feedback,
    advance_halo_iteration_feedback_sequence,
)


def _feedback_kwargs(**overrides):
    kwargs = dict(
        dcx_density_cm3=100.0,
        previous_halo_density_cm3=100.0,
        current_halo_density_cm3=55.9,
        previous_merged_halo_density_cm3=10.0,
        source_halo_marker_budget=40,
    )
    kwargs.update(overrides)
    return kwargs


# --------------------------- one feedback round ---------------------------

def test_feedback_matches_the_saved_seed_probe():
    result = advance_halo_iteration_feedback(**_feedback_kwargs())
    assert math.isclose(result["density_ratio"], 0.559, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(result["seed_dcx_fraction"], 0.559, rel_tol=0.0, abs_tol=1e-15)
    assert result["next_halo_marker_count"] == 22
    assert result["next_previous_halo_density_cm3"] == 55.9
    assert result["merged_halo_density_after_cm3"] == 65.9
    assert result["merge_applied"] is True
    assert result["continue_iteration"] is True
    assert result["stop_reason"] == "continue"


def test_ratio_one_continues_and_seed_boundary_equality_continues():
    result = advance_halo_iteration_feedback(**_feedback_kwargs(current_halo_density_cm3=100.0))
    assert result["density_ratio"] == 1.0
    assert result["continue_iteration"] is True and result["stop_reason"] == "continue"
    # seed_dcx == 0.01 exactly continues (source: exit only when strictly below).
    result = advance_halo_iteration_feedback(**_feedback_kwargs(
        current_halo_density_cm3=1.0, source_halo_marker_budget=100))
    assert math.isclose(result["seed_dcx_fraction"], 0.01, rel_tol=0.0, abs_tol=1e-15)
    assert result["next_halo_marker_count"] == 1
    assert result["continue_iteration"] is True


def test_density_growth_exits_before_merge_with_null_projections():
    result = advance_halo_iteration_feedback(**_feedback_kwargs(current_halo_density_cm3=100.1))
    assert result["stop_reason"] == "density_growth_exceeded"
    assert result["merge_applied"] is False
    assert result["seed_dcx_fraction"] is None
    assert result["next_halo_marker_count"] is None
    assert result["merged_halo_density_after_cm3"] is None
    # previous state is kept, not updated to current.
    assert result["next_previous_halo_density_cm3"] == 100.0
    assert result["continue_iteration"] is False


def test_seed_below_threshold_stops_after_merge():
    result = advance_halo_iteration_feedback(**_feedback_kwargs(
        current_halo_density_cm3=0.999, source_halo_marker_budget=100))
    assert result["stop_reason"] == "seed_below_threshold"
    assert result["merge_applied"] is True
    assert result["merged_halo_density_after_cm3"] == 10.999
    assert result["continue_iteration"] is False


def test_marker_count_uses_fortran_truncation():
    result = advance_halo_iteration_feedback(**_feedback_kwargs(
        current_halo_density_cm3=55.9999, source_halo_marker_budget=40))
    assert result["next_halo_marker_count"] == int(40 * 0.559999) == 22
    result = advance_halo_iteration_feedback(**_feedback_kwargs(
        current_halo_density_cm3=1.0, source_halo_marker_budget=99))
    assert result["next_halo_marker_count"] == 0


def test_feedback_rejects_bad_contracts():
    for overrides in (
        {"dcx_density_cm3": 0.0}, {"dcx_density_cm3": -1.0}, {"dcx_density_cm3": np.nan},
        {"previous_halo_density_cm3": 0.0}, {"previous_halo_density_cm3": np.inf},
        {"current_halo_density_cm3": -1.0}, {"current_halo_density_cm3": np.nan},
        {"previous_merged_halo_density_cm3": -1.0}, {"previous_merged_halo_density_cm3": np.nan},
        {"source_halo_marker_budget": 0}, {"source_halo_marker_budget": -3},
        {"source_halo_marker_budget": 2.5}, {"source_halo_marker_budget": True},
        {"source_halo_marker_budget": np.bool_(True)},
        {"dcx_density_cm3": [100.0]}, {"previous_merged_halo_density_cm3": "10"},
    ):
        with pytest.raises(ValueError):
            advance_halo_iteration_feedback(**_feedback_kwargs(**overrides))


def test_feedback_overflow_fails_closed_not_silent():
    # current/dcx overflows the seed fraction; the saved arm crashes inside
    # int(Inf) with OverflowError instead of a contract error.
    with pytest.raises(ValueError, match="registered hardening"):
        advance_halo_iteration_feedback(**_feedback_kwargs(
            current_halo_density_cm3=1.0e308, previous_halo_density_cm3=1.0e308,
            dcx_density_cm3=1.0e-308))
    # current/previous overflows the ratio; the saved arm returns Inf as the
    # ratio with a growth stop instead of failing closed.
    with pytest.raises(ValueError, match="registered hardening"):
        advance_halo_iteration_feedback(**_feedback_kwargs(
            current_halo_density_cm3=1.0e308, previous_halo_density_cm3=1.0e-300))
    # the merge overflows; the saved arm returns Inf density silently.
    with pytest.raises(ValueError, match="registered hardening"):
        advance_halo_iteration_feedback(**_feedback_kwargs(
            current_halo_density_cm3=1.0e308, previous_halo_density_cm3=1.0e308,
            previous_merged_halo_density_cm3=1.5e308))


def test_budget_seed_product_overflow_fails_closed():
    # A finite seed times the budget can still overflow the marker product;
    # the saved arm raises a bare OverflowError inside int(inf) instead of a
    # contract error.  Documented numerical bound: the product must stay
    # representable in double precision.
    with pytest.raises(ValueError, match="registered hardening"):
        advance_halo_iteration_feedback(1.0, 1.0e308, 1.0e308, 0.0, 40)


# ------------------------------ sequence graph ------------------------------

def _sequence_inputs(current, requested, **overrides):
    values = dict(
        dcx_density_cm3=100.0,
        initial_previous_halo_density_cm3=100.0,
        initial_merged_halo_density_cm3=0.0,
        current_halo_densities_cm3=current,
        requested_halo_marker_budgets=requested,
        source_halo_marker_budget=40,
    )
    values.update(overrides)
    return values


def test_sequence_reaches_seed_stop_and_preserves_budget_recurrence():
    result = advance_halo_iteration_feedback_sequence(_sequence_inputs(
        [55.9, 27.4, 15.7, 3.55, 0.315], [40, 22, 10, 6, 1]))
    assert result["final_state"]["stop_reason"] == "seed_below_threshold"
    assert result["diagnostics"]["branch_counts"] == {"continue": 4, "seed_below_threshold": 1}
    assert [item["requested_halo_marker_budget"] for item in result["iterations"]] == [40, 22, 10, 6, 1]
    assert result["final_state"]["iterations_completed"] == 5
    # the recurrence state matches direct one-round calls round by round.
    previous, merged = 100.0, 0.0
    for record, current_density in zip(result["iterations"], [55.9, 27.4, 15.7, 3.55, 0.315]):
        expected = advance_halo_iteration_feedback(100.0, previous, current_density, merged, 40)
        assert record["density_ratio"] == expected["density_ratio"]
        assert record["next_halo_marker_count"] == expected["next_halo_marker_count"]
        assert record["merged_halo_density_after_cm3"] == expected["merged_halo_density_after_cm3"]
        previous = expected["next_previous_halo_density_cm3"]
        merged = expected["merged_halo_density_after_cm3"]


def test_sequence_growth_stop_and_contract_fail_closed():
    growth = advance_halo_iteration_feedback_sequence(_sequence_inputs([100.1], [40]))
    assert growth["final_state"]["stop_reason"] == "density_growth_exceeded"
    assert growth["iterations"][0]["merge_applied"] is False
    assert growth["final_state"]["previous_halo_density_cm3"] == 100.0
    with pytest.raises(ValueError, match="drift"):
        advance_halo_iteration_feedback_sequence(_sequence_inputs([55.9, 27.4], [40, 40]))
    with pytest.raises(ValueError, match="ended before a source stop"):
        advance_halo_iteration_feedback_sequence(_sequence_inputs([55.9, 55.9], [40, 22]))
    with pytest.raises(ValueError, match="continues after source stop"):
        advance_halo_iteration_feedback_sequence(_sequence_inputs([0.999, 0.5], [40, 0]))


def test_sequence_rejects_bad_contracts():
    with pytest.raises(ValueError, match="must match"):
        advance_halo_iteration_feedback_sequence(_sequence_inputs([55.9, 27.4], [40]))
    with pytest.raises(ValueError, match="nonnegative integers"):
        advance_halo_iteration_feedback_sequence(_sequence_inputs([55.9], [40.5]))
    with pytest.raises(ValueError, match="nonnegative integers"):
        advance_halo_iteration_feedback_sequence(_sequence_inputs([0.0], [True]))
    with pytest.raises(ValueError, match="non-empty finite"):
        advance_halo_iteration_feedback_sequence(_sequence_inputs([], []))
    with pytest.raises(ValueError, match="non-empty finite nonnegative"):
        advance_halo_iteration_feedback_sequence(_sequence_inputs([55.9, -1.0], [40, 22]))
    with pytest.raises(ValueError, match="positive integer"):
        advance_halo_iteration_feedback_sequence(_sequence_inputs([55.9], [40], source_halo_marker_budget=0))
    with pytest.raises(ValueError, match="nonnegative"):
        advance_halo_iteration_feedback_sequence(_sequence_inputs(
            [55.9], [40], initial_merged_halo_density_cm3=-1.0))
    with pytest.raises(ValueError, match="required"):
        advance_halo_iteration_feedback_sequence({"dcx_density_cm3": 100.0})


def test_sequence_preserves_integer_budgets_beyond_double_precision():
    # Exact integers keep full precision (no float64 roundtrip); a float
    # entry that cannot represent the integer drifts and fails closed.
    big = 9007199254740993  # 2**53 + 1
    result = advance_halo_iteration_feedback_sequence(_sequence_inputs(
        [0.0], [big], source_halo_marker_budget=big))
    assert result["final_state"]["stop_reason"] == "seed_below_threshold"
    assert result["iterations"][0]["requested_halo_marker_budget"] == big
    assert result["final_state"]["next_halo_marker_count"] == 0
    with pytest.raises(ValueError, match="drift"):
        advance_halo_iteration_feedback_sequence(_sequence_inputs(
            [0.0], [float(big)], source_halo_marker_budget=big))


def test_sequence_same_inputs_replay_identically():
    inputs = _sequence_inputs([55.9, 27.4, 0.315], [40, 22, 10])
    first = advance_halo_iteration_feedback_sequence(inputs)
    second = advance_halo_iteration_feedback_sequence(inputs)
    assert first == second

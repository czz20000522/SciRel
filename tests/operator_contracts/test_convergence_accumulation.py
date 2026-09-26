"""Direct contract tests for the r64 convergence/accumulation family:
``evaluate_neutral_generation_stopping``, ``update_neutral_generation_accumulation``,
``evaluate_neutral_outer_seed_convergence``, ``evaluate_kn1d_outer_convergence``.

The saved KN1DPy implementations (SHA-256 pinned in the L1 replay) are
reproduced bit for bit on the declared domain; no repair is claimed.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import (
    evaluate_neutral_generation_stopping,
    update_neutral_generation_accumulation,
    evaluate_neutral_outer_seed_convergence,
    evaluate_kn1d_outer_convergence,
)


def test_generation_stopping_returns_delta_and_status():
    gen = np.array([10.0, 20.0])
    acc = np.array([100.0, 200.0])
    delta, done, reason = evaluate_neutral_generation_stopping(gen, acc, truncate=0.05)
    assert delta == pytest.approx(20.0 / 200.0)
    assert done is False
    assert reason == "continue"


def test_generation_stopping_truncate_path():
    gen = np.array([0.001, 0.001])
    acc = np.array([100.0, 200.0])
    delta, done, reason = evaluate_neutral_generation_stopping(gen, acc, truncate=0.1)
    assert done is True
    assert reason == "truncate"


def test_generation_stopping_rejects_nonpositive_accumulated():
    gen = np.array([1.0])
    acc = np.array([0.0])
    with pytest.raises(ValueError, match="positive value"):
        evaluate_neutral_generation_stopping(gen, acc, truncate=0.1)


def test_accumulation_first_call_creates_state():
    dist = np.ones((2, 3, 4))
    density = np.array([1.0, 2.0, 3.0, 4.0])
    state = update_neutral_generation_accumulation(None, dist, density)
    assert state["completed_generation_index"] == 0
    np.testing.assert_array_equal(state["total_distribution"], dist)
    np.testing.assert_array_equal(state["total_density_m3"], density)
    assert state["generation_distributions"].shape == (1, 2, 3, 4)
    assert state["generation_density_m3"].shape == (1, 4)


def test_accumulation_second_call_accumulates():
    dist = np.ones((2, 3, 4))
    density = np.array([1.0, 2.0, 3.0, 4.0])
    state1 = update_neutral_generation_accumulation(None, dist, density)
    state2 = update_neutral_generation_accumulation(state1, dist * 2, density * 2)
    assert state2["completed_generation_index"] == 1
    np.testing.assert_array_equal(state2["total_distribution"], dist * 3)
    np.testing.assert_array_equal(state2["total_density_m3"], density * 3)


def test_outer_seed_convergence_returns_dict_with_reentry_flag():
    prev = np.array([100.0, 200.0])
    curr = np.array([100.5, 200.5])
    result = evaluate_neutral_outer_seed_convergence(prev, curr, truncate=0.1)
    assert set(result) == {"seed_error", "reentry_threshold", "should_reiterate", "reason"}
    assert result["should_reiterate"] is False
    assert result["reentry_threshold"] == 1.0
    # large change but still within the 10*truncate threshold (1.0)
    curr2 = np.array([150.0, 200.0])
    result2 = evaluate_neutral_outer_seed_convergence(prev, curr2, truncate=0.1)
    assert result2["should_reiterate"] is False
    # the reentry threshold is 10*truncate = 1.0; the ratio-of-max formula
    # gives seed_error = max(abs(diff))/max(curr) = 200/300 = 0.667, below
    # the threshold, so no re-entry
    curr3 = np.array([300.0, 200.0])
    result3 = evaluate_neutral_outer_seed_convergence(prev, curr3, truncate=0.1)
    assert result3["should_reiterate"] is False
    assert result3["reentry_threshold"] == 1.0
    # a dramatic decrease crosses the threshold: prev=1000, curr=100 gives
    # seed_error = max(abs(diff))/max(curr) = 900/200 = 4.5 > 1.0 -> re-enters
    prev2 = np.array([1000.0, 200.0])
    curr4 = np.array([100.0, 200.0])
    result4 = evaluate_neutral_outer_seed_convergence(prev2, curr4, truncate=0.1)
    assert result4["should_reiterate"] is True


def test_kn1d_outer_convergence_returns_dict_with_reentry_flag():
    prev = np.array([100.0])
    curr = np.array([100.05])
    result = evaluate_kn1d_outer_convergence(prev, curr, truncate=0.1)
    assert set(result) == {"seed_error", "reentry_threshold", "should_reiterate", "reason"}
    assert result["should_reiterate"] is False
    assert result["reentry_threshold"] == 0.1
    curr2 = np.array([120.0])
    result2 = evaluate_kn1d_outer_convergence(prev, curr2, truncate=0.1)
    assert result2["should_reiterate"] is True

def test_outer_seed_uses_ratio_of_max_not_per_node():
    """Discriminating regression: seed_error = max(abs(diff)) / max(current).
    prev=[300,200], curr=[100,200]: abs(diff)=[200,0], max(diff)=200,
    max(curr)=200 -> seed_error=1.0, NOT > 1.0, so should_reiterate=False.
    A per-node formula (200/100=2.0) would incorrectly give True."""
    prev = np.array([300.0, 200.0])
    curr = np.array([100.0, 200.0])
    result = evaluate_neutral_outer_seed_convergence(prev, curr, truncate=0.1)
    assert result["seed_error"] == pytest.approx(1.0)
    assert result["should_reiterate"] is False


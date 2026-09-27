"""FIDASIM neutral-reservoir/population merge family (r79).

Saved probes for the single-cell density merge, the beam-grid density
merge, the local reservoir merge, and the population-state composition,
plus the registered hardenings (genuine-integer reservoir metadata and
capacity, bool rejection for W and boolean array entries, genuine
integer replacement indices) and the end-to-end composition witness
over two NDMC-produced population grids.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.fusion.neutral_population_density_merge import merge_neutral_population_density
from scirel.fusion.neutral_population_grid_merge import merge_neutral_population_cells
from scirel.fusion.neutral_population_state_merge import merge_neutral_population_state
from scirel.fusion.neutral_reservoir_merge import merge_neutral_reservoirs
from scirel.fusion.ndmc_deposition_producer import run_ndmc_deposition_producer

K = 50


# ------------------------------ shared reservoir fixtures ------------------------------

def _reservoir_state(n, offset, i=101, W=0.91, size=K):
    weights = np.ones(size)
    velocities = np.zeros((size, 3))
    for index in range(1, min(n, size) + 1):
        weights[index - 1] = offset + index
        velocities[index - 1] = [
            1.0e6 * offset + index,
            2.0e6 * offset + 2.0 * index,
            -3.0e6 * offset - index,
        ]
    return {"n": n, "i": i, "W": W, "slot_weights": weights, "slot_velocities_cm_s": velocities}


def _merge(left, right, *, full_full_uniforms=None, transfer_indices=None, transfer_uniforms=None):
    transfer_indices = np.asarray([] if transfer_indices is None else transfer_indices)
    transfer_uniforms = np.empty((0, 2)) if transfer_uniforms is None else np.asarray(transfer_uniforms)
    full_full_uniforms = np.asarray([] if full_full_uniforms is None else full_full_uniforms)
    return merge_neutral_reservoirs(
        target_n=left["n"], target_i=left["i"], target_W=left["W"],
        target_slot_weights=left["slot_weights"],
        target_slot_velocities_cm_s=left["slot_velocities_cm_s"],
        source_n=right["n"], source_i=right["i"], source_W=right["W"],
        source_slot_weights=right["slot_weights"],
        source_slot_velocities_cm_s=right["slot_velocities_cm_s"],
        target_initialization_uniforms=[0.5, 0.5],
        transfer_replacement_indices=transfer_indices,
        transfer_replacement_uniforms=transfer_uniforms,
        full_full_uniforms=full_full_uniforms,
    )


# --------------------------- single-cell density merge ---------------------------

def test_density_merge_preserves_source_and_adds_componentwise():
    target = np.asarray([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    source = np.asarray([0.5, 1.5, 2.5, 3.5, 4.5, 5.5])
    result = merge_neutral_population_density(
        target_population_density=target,
        source_population_density=source,
    )
    assert np.array_equal(result["target_population_density_after"], target + source)
    assert np.array_equal(result["source_population_density_after"], source)
    assert result["density_contribution_sum"] == 18.0
    assert np.array_equal(result["target_population_density_before"], target)
    assert np.array_equal(target, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])


def test_density_merge_does_not_clip_signed_finite_source_values():
    result = merge_neutral_population_density(
        target_population_density=np.ones(6),
        source_population_density=np.asarray([1.0, -1.0, 0.0, 2.0, -2.0, 0.5]),
    )
    assert np.array_equal(result["target_population_density_after"], [2.0, 0.0, 1.0, 3.0, -1.0, 1.5])
    assert np.array_equal(result["density_contribution"], [1.0, -1.0, 0.0, 2.0, -2.0, 0.5])


def test_density_merge_rejects_shape_and_nonfinite_inputs():
    with pytest.raises(ValueError):
        merge_neutral_population_density(
            target_population_density=np.ones(5),
            source_population_density=np.ones(6),
        )
    with pytest.raises(ValueError):
        merge_neutral_population_density(
            target_population_density=np.ones(6),
            source_population_density=[1.0, 2.0, 3.0, 4.0, 5.0, float("nan")],
        )


def test_density_merge_rejects_boolean_entries():
    with pytest.raises(ValueError):
        merge_neutral_population_density(
            target_population_density=np.ones(6, dtype=bool),
            source_population_density=np.ones(6),
        )
    with pytest.raises(ValueError):
        merge_neutral_population_density(
            target_population_density=np.ones(6),
            source_population_density=np.array([True] * 5 + [False]),
        )


# ----------------------------- grid density merge -----------------------------

def test_grid_merge_adds_each_level_and_cell_without_mixing_or_clipping():
    target = np.arange(24.0).reshape(6, 4, 1, 1)
    source = np.full((6, 4, 1, 1), -0.25)
    result = merge_neutral_population_cells(
        target_population_density=target,
        source_population_density=source,
    )
    assert np.array_equal(result["target_population_density_after"], target + source)
    assert np.array_equal(result["source_population_density_after"], source)
    assert result["cell_shape"] == [4, 1, 1]
    assert result["cell_count"] == 4
    assert result["density_contribution_sum"] == pytest.approx(-6.0)


def test_grid_merge_rejects_shape_level_and_nonfinite_mismatch():
    with pytest.raises(ValueError):
        merge_neutral_population_cells(
            target_population_density=np.ones((5, 4, 1, 1)),
            source_population_density=np.ones((5, 4, 1, 1)),
        )
    with pytest.raises(ValueError):
        merge_neutral_population_cells(
            target_population_density=np.ones((6, 4, 1, 1)),
            source_population_density=np.ones((6, 3, 1, 1)),
        )
    invalid = np.ones((6, 4, 1, 1))
    invalid[0, 0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        merge_neutral_population_cells(
            target_population_density=invalid,
            source_population_density=np.ones((6, 4, 1, 1)),
        )


def test_grid_merge_rejects_boolean_entries_and_zero_extent():
    with pytest.raises(ValueError):
        merge_neutral_population_cells(
            target_population_density=np.ones((6, 4, 1, 1), dtype=bool),
            source_population_density=np.ones((6, 4, 1, 1)),
        )
    with pytest.raises(ValueError):
        merge_neutral_population_cells(
            target_population_density=np.ones((6, 0, 1, 1)),
            source_population_density=np.ones((6, 0, 1, 1)),
        )


# ------------------------------ reservoir merge ------------------------------

def test_reservoir_merge_both_nonfull_appends_source_prefix_in_order():
    out = _merge(_reservoir_state(4, 0), _reservoir_state(5, 100))
    assert out["branch"] == "both_nonfull"
    assert out["target_n"] == 9 and out["transfer_actions"] == ["fill"] * 5
    # The first append writes R(res1%n), so the old fourth slot is replaced
    # before the remaining source records occupy the following slots.
    assert np.array_equal(out["target_slot_weights"][3:8], [101, 102, 103, 104, 105])
    assert np.array_equal(out["source_slot_weights"], out["target_slot_weights"])


def test_reservoir_merge_mixed_orientation_swaps_or_appends_source_in_order():
    swapped = _merge(_reservoir_state(4, 0), _reservoir_state(60, 100))
    direct = _merge(_reservoir_state(60, 0), _reservoir_state(4, 100))
    assert swapped["branch"] == "target_nonfull_source_full"
    assert direct["branch"] == "target_full_source_nonfull"
    assert swapped["target_n"] == direct["target_n"] == 64
    # In both orientations the already-full reservoir receives four skipped
    # updates; the selected full reservoir therefore remains unchanged.
    assert np.allclose(swapped["target_slot_weights"], _reservoir_state(60, 100)["slot_weights"])
    assert np.allclose(direct["target_slot_weights"], _reservoir_state(60, 0)["slot_weights"])
    assert np.allclose(swapped["target_slot_velocities_cm_s"], _reservoir_state(60, 100)["slot_velocities_cm_s"])
    assert np.allclose(direct["target_slot_velocities_cm_s"], _reservoir_state(60, 0)["slot_velocities_cm_s"])


def test_reservoir_merge_both_full_uses_strict_float32_source_probability():
    uniforms = np.array([0.0 if index % 2 == 0 else 0.99 for index in range(K)])
    out = _merge(_reservoir_state(60, 0), _reservoir_state(70, 100), full_full_uniforms=uniforms)
    assert out["branch"] == "both_full"
    assert np.isclose(out["full_full_probability"], np.float32(60.0) / np.float32(130.0))
    assert np.array_equal(out["target_slot_weights"][0::2], _reservoir_state(60, 0)["slot_weights"][0::2])
    assert np.array_equal(out["target_slot_weights"][1::2], _reservoir_state(70, 100)["slot_weights"][1::2])
    assert np.array_equal(out["source_slot_weights"], out["target_slot_weights"])


def test_reservoir_merge_source_empty_and_rng_shape_errors_fail_closed():
    empty = _merge(_reservoir_state(4, 0), _reservoir_state(0, 100))
    assert empty["branch"] == "source_empty" and empty["target_n"] == 4
    with pytest.raises(ValueError):
        _merge(_reservoir_state(60, 0), _reservoir_state(70, 100), full_full_uniforms=np.zeros(K - 1))
    with pytest.raises(ValueError):
        _merge(_reservoir_state(4, 0), _reservoir_state(5, 100), full_full_uniforms=[0.5])


def test_reservoir_merge_lazy_initialization_consumes_the_uniform_pair():
    empty_target = _reservoir_state(0, 0)
    out = _merge(empty_target, _reservoir_state(0, 100))
    assert out["branch"] == "source_empty"
    assert out["target_n"] == 1
    assert out["target_W"] == pytest.approx(np.exp(np.log(0.5) / K))
    assert out["target_i"] == K + np.floor(np.log(0.5) / np.log(1.0 - out["target_W"])) + 1


def test_reservoir_merge_replacement_updates_w_before_the_next_horizon():
    # target full (n=k+1), horizon at the next record: the appended record
    # replaces slot 7 and the next horizon is drawn from the UPDATED W.
    left = _reservoir_state(K + 1, 0, i=K + 1, W=0.5)
    right = _reservoir_state(1, 100)
    out = _merge(left, right, transfer_indices=[7], transfer_uniforms=[[0.25, 0.75]])
    assert out["transfer_actions"] == ["replace"]
    assert out["transfer_updated_slots"] == [7]
    assert out["transfer_replacement_count"] == 1
    expected_w = 0.5 * np.exp(np.log(0.25) / K)
    assert out["target_W"] == pytest.approx(expected_w)
    expected_i = (K + 1) + np.floor(np.log(0.75) / np.log(1.0 - expected_w)) + 1
    assert out["target_i"] == expected_i


def test_reservoir_merge_transfer_record_mismatch_fails_closed():
    left = _reservoir_state(K + 2, 0, i=K + 2, W=0.5)
    right = _reservoir_state(1, 100)
    # one replacement is needed (the record hits slot 6, the next horizon
    # moves past the remaining records) but none is supplied
    with pytest.raises(ValueError):
        _merge(left, right, transfer_indices=[], transfer_uniforms=np.empty((0, 2)))
    # supplying more replacement records than the merge consumes also fails
    with pytest.raises(ValueError):
        _merge(_reservoir_state(K + 1, 0, i=K + 1, W=0.5), _reservoir_state(1, 100),
               transfer_indices=[7, 6], transfer_uniforms=[[0.25, 0.75], [0.5, 0.5]])


# ------------------------- registered hardenings (r79) -------------------------

def test_reservoir_metadata_accept_numpy_integers_but_reject_bools_and_floats():
    left = _reservoir_state(4, 0)
    right = _reservoir_state(5, 100)
    ok = merge_neutral_reservoirs(
        target_n=np.int64(4), target_i=np.int64(101), target_W=0.91,
        target_slot_weights=left["slot_weights"],
        target_slot_velocities_cm_s=left["slot_velocities_cm_s"],
        source_n=np.int64(5), source_i=101, source_W=np.float64(0.91),
        source_slot_weights=right["slot_weights"],
        source_slot_velocities_cm_s=right["slot_velocities_cm_s"],
        target_initialization_uniforms=[0.5, 0.5],
        transfer_replacement_indices=[], transfer_replacement_uniforms=np.empty((0, 2)),
        full_full_uniforms=[],
    )
    assert ok["target_n"] == 9
    for bad_n in (True, np.bool_(False), 4.0):
        with pytest.raises(ValueError):
            _merge(_reservoir_state(4, 0), _reservoir_state(5, 100)) if False else merge_neutral_reservoirs(
                target_n=bad_n, target_i=101, target_W=0.91,
                target_slot_weights=left["slot_weights"],
                target_slot_velocities_cm_s=left["slot_velocities_cm_s"],
                source_n=5, source_i=101, source_W=0.91,
                source_slot_weights=right["slot_weights"],
                source_slot_velocities_cm_s=right["slot_velocities_cm_s"],
                target_initialization_uniforms=[0.5, 0.5],
                transfer_replacement_indices=[], transfer_replacement_uniforms=np.empty((0, 2)),
                full_full_uniforms=[],
            )
    with pytest.raises(ValueError):
        merge_neutral_reservoirs(
            target_n=4, target_i=101, target_W=True,  # the saved arm accepted W=True
            target_slot_weights=left["slot_weights"],
            target_slot_velocities_cm_s=left["slot_velocities_cm_s"],
            source_n=5, source_i=101, source_W=0.91,
            source_slot_weights=right["slot_weights"],
            source_slot_velocities_cm_s=right["slot_velocities_cm_s"],
            target_initialization_uniforms=[0.5, 0.5],
            transfer_replacement_indices=[], transfer_replacement_uniforms=np.empty((0, 2)),
            full_full_uniforms=[],
        )
    with pytest.raises(ValueError):
        merge_neutral_reservoirs(
            target_n=4, target_i=101, target_W=0.91,
            target_slot_weights=left["slot_weights"],
            target_slot_velocities_cm_s=left["slot_velocities_cm_s"],
            source_n=5, source_i=101, source_W=0.91,
            source_slot_weights=right["slot_weights"],
            source_slot_velocities_cm_s=right["slot_velocities_cm_s"],
            target_initialization_uniforms=[0.5, 0.5],
            transfer_replacement_indices=[], transfer_replacement_uniforms=np.empty((0, 2)),
            full_full_uniforms=[], reservoir_size=50.0,
        )
    with pytest.raises(ValueError):
        merge_neutral_reservoirs(
            target_n=4, target_i=101, target_W=0.91,
            target_slot_weights=left["slot_weights"],
            target_slot_velocities_cm_s=left["slot_velocities_cm_s"],
            source_n=5, source_i=101, source_W=0.91,
            source_slot_weights=right["slot_weights"],
            source_slot_velocities_cm_s=right["slot_velocities_cm_s"],
            target_initialization_uniforms=[0.5, 0.5],
            transfer_replacement_indices=[], transfer_replacement_uniforms=np.empty((0, 2)),
            full_full_uniforms=[], reservoir_size=np.bool_(True),
        )


def test_replacement_indices_reject_whole_number_floats_and_bools():
    left = _reservoir_state(K + 1, 0, i=K + 1, W=0.5)
    right = _reservoir_state(1, 100)
    with pytest.raises(ValueError):
        _merge(left, right, transfer_indices=np.asarray([7.0]), transfer_uniforms=[[0.25, 0.75]])
    with pytest.raises(ValueError):
        _merge(left, right, transfer_indices=np.asarray([True]), transfer_uniforms=[[0.25, 0.75]])
    # the genuine-integer form still works
    out = _merge(left, right, transfer_indices=np.asarray([7], dtype=np.int64),
                 transfer_uniforms=[[0.25, 0.75]])
    assert out["transfer_updated_slots"] == [7]


def test_slot_state_arrays_reject_boolean_entries():
    left = _reservoir_state(4, 0)
    right = _reservoir_state(5, 100)
    bool_weights = np.ones(K, dtype=bool)
    with pytest.raises(ValueError):
        merge_neutral_reservoirs(
            target_n=4, target_i=101, target_W=0.91,
            target_slot_weights=bool_weights,
            target_slot_velocities_cm_s=left["slot_velocities_cm_s"],
            source_n=5, source_i=101, source_W=0.91,
            source_slot_weights=right["slot_weights"],
            source_slot_velocities_cm_s=right["slot_velocities_cm_s"],
            target_initialization_uniforms=[0.5, 0.5],
            transfer_replacement_indices=[], transfer_replacement_uniforms=np.empty((0, 2)),
            full_full_uniforms=[],
        )


def test_mixed_object_boolean_entries_are_numerification_rejected_everywhere():
    # np.asarray([True, 1.0], dtype=object).astype(float) silently coerces
    # True to 1.0; the registered hardening must reject the mixed object
    # form in weights, velocities, and the uniform records alike.
    left = _reservoir_state(4, 0)
    right = _reservoir_state(5, 100)
    base = dict(
        target_n=4, target_i=101, target_W=0.91,
        target_slot_weights=left["slot_weights"],
        target_slot_velocities_cm_s=left["slot_velocities_cm_s"],
        source_n=5, source_i=101, source_W=0.91,
        source_slot_weights=right["slot_weights"],
        source_slot_velocities_cm_s=right["slot_velocities_cm_s"],
        target_initialization_uniforms=[0.5, 0.5],
        transfer_replacement_indices=[], transfer_replacement_uniforms=np.empty((0, 2)),
        full_full_uniforms=[],
    )

    def call(**overrides):
        return merge_neutral_reservoirs(**{**base, **overrides})

    mixed_weight = np.asarray([True] + [1.0] * (K - 1), dtype=object)
    with pytest.raises(ValueError):
        call(target_slot_weights=mixed_weight)
    mixed_velocity = np.asarray([[True, 1.0, 1.0]] + [[1.0, 1.0, 1.0]] * (K - 1), dtype=object)
    with pytest.raises(ValueError):
        call(target_slot_velocities_cm_s=mixed_velocity)
    with pytest.raises(ValueError):
        call(target_initialization_uniforms=np.asarray([True, 0.5], dtype=object))
    with pytest.raises(ValueError):
        call(transfer_replacement_uniforms=np.asarray([[True, 0.5]], dtype=object),
             transfer_replacement_indices=[0])
    # the plain bool dtype form stays rejected too
    with pytest.raises(ValueError):
        call(full_full_uniforms=np.ones(K, dtype=bool))


# --------------------------- population-state graph ---------------------------

def _reservoir_inputs(left, right, full_full_uniforms=None):
    return {
        "target_n": left["n"],
        "target_i": left["i"],
        "target_W": left["W"],
        "target_slot_weights": left["slot_weights"],
        "target_slot_velocities_cm_s": left["slot_velocities_cm_s"],
        "source_n": right["n"],
        "source_i": right["i"],
        "source_W": right["W"],
        "source_slot_weights": right["slot_weights"],
        "source_slot_velocities_cm_s": right["slot_velocities_cm_s"],
        "target_initialization_uniforms": [0.5, 0.5],
        "transfer_replacement_indices": np.asarray([], dtype=np.int64),
        "transfer_replacement_uniforms": np.empty((0, 2)),
        "full_full_uniforms": np.asarray([] if full_full_uniforms is None else full_full_uniforms),
    }


def _graph_call(target_density, source_density, left, right, full_full_uniforms=None):
    return merge_neutral_population_state(
        target_population_density=target_density,
        source_population_density=source_density,
        reservoir_merge_inputs=_reservoir_inputs(left, right, full_full_uniforms),
    )


def test_graph_adds_density_and_reuses_same_pfm_reservoir_merge():
    target = np.arange(1.0, 7.0)
    source = np.arange(0.5, 6.5, 1.0)
    result = _graph_call(target, source, _reservoir_state(4, 0), _reservoir_state(5, 100))
    assert np.array_equal(result["target_population_density_after"], target + source)
    assert np.array_equal(result["source_population_density_after"], source)
    assert result["reservoir_merge"]["branch"] == "both_nonfull"
    assert result["diagnostics"]["cross_pfm_edges"] == []
    assert result["diagnostics"]["graph_order"] == ["population_density_merge", "reservoir_merge"]


def test_graph_density_addition_is_independent_of_source_empty_reservoir():
    result = _graph_call(np.ones(6), np.full(6, 2.0), _reservoir_state(4, 0), _reservoir_state(0, 100))
    assert np.array_equal(result["target_population_density_after"], np.full(6, 3.0))
    assert result["reservoir_merge"]["branch"] == "source_empty"
    assert result["diagnostics"]["local_feedback"] == "reservoir_merge_res2_equals_res1_after_nonempty_merge"


def test_graph_delegates_both_full_branch_with_explicit_uniforms():
    result = _graph_call(np.ones(6), np.full(6, 2.0), _reservoir_state(60, 0),
                         _reservoir_state(70, 100), np.zeros(K))
    assert result["reservoir_merge"]["branch"] == "both_full"
    assert result["reservoir_merge"]["source_n"] == result["reservoir_merge"]["target_n"] == 60


def test_graph_rejects_non_six_level_density_and_missing_reservoir_mapping():
    with pytest.raises(ValueError):
        _graph_call(np.ones(5), np.ones(6), _reservoir_state(1, 0), _reservoir_state(1, 100))
    with pytest.raises(ValueError):
        merge_neutral_population_state(
            target_population_density=np.ones(6),
            source_population_density=np.ones(6),
            reservoir_merge_inputs=None,
        )
    with pytest.raises(ValueError):
        merge_neutral_population_state(
            target_population_density=np.ones(6),
            source_population_density=np.ones(6),
            reservoir_merge_inputs=[1, 2, 3],
        )


# ----------------------- NDMC composition witness (r79) -----------------------

def test_grid_merge_composes_with_two_ndmc_produced_population_grids():
    fractions = (0.528113, 0.268704, 0.203183)
    kwargs = dict(
        injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=fractions,
        beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=6, grid_shape=(2, 2, 2),
    )
    states = np.zeros((3, 6))
    for q in (1, 2, 3):
        states[q - 1, 0] = 1e6 * 1.7 / (1e3 * 72.5 * 1.60217733e-19
                                       * (fractions[0] + fractions[1] / 2 + fractions[2] / 3)) \
            * fractions[q - 1] / 8.0
    records_a = {1: [{"grid_index_one_based": (1, 1, 1),
                      "normalized_density_cm_inv3": np.full(6, 2.0),
                      "segment_flux_per_cm3_s": 0.5}]}
    records_b = {1: [{"grid_index_one_based": (2, 2, 2),
                      "normalized_density_cm_inv3": np.full(6, 1.0),
                      "segment_flux_per_cm3_s": 0.25}]}
    zero = np.zeros((6, 2, 2, 2))
    run_a = run_ndmc_deposition_producer(
        **kwargs, initial_states_cm_inv3_s_inv=states,
        initial_population_density_full=zero, initial_population_density_half=zero,
        initial_population_density_third=zero, per_fraction_segment_depositions=records_a)
    run_b = run_ndmc_deposition_producer(
        **kwargs, initial_states_cm_inv3_s_inv=states,
        initial_population_density_full=zero, initial_population_density_half=zero,
        initial_population_density_third=zero, per_fraction_segment_depositions=records_b)
    merged = merge_neutral_population_cells(
        target_population_density=run_a["population_density_full"],
        source_population_density=run_b["population_density_full"],
    )
    assert np.allclose(merged["target_population_density_after"][:, 0, 0, 0], 2.0)
    assert np.allclose(merged["target_population_density_after"][:, 1, 1, 1], 1.0)
    assert np.allclose(merged["target_population_density_after"][:, 0, 1, 0], 0.0)
    assert merged["source_population_density_after"] is not None
    # the source grid is unchanged (observation ownership)
    assert np.allclose(run_b["population_density_full"][:, 1, 1, 1], 1.0)

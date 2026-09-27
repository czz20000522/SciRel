"""Graph contract tests for the r75 FIDASIM N2 trajectory-initialization
TaskGraph (``initialize_nbi_trajectory``), ported from the saved bundle's
``NBI轨迹初始化图`` caller-random paths.

The graph composes already-integrated leaves: the ndmc neutral-rate
normalization must precede both sampling branches, the ``source_ray`` branch
feeds the same accepted unit ray into the energy-component velocity scaling
and (optionally) the finite beam-grid entry handoff, and the ``cell_directed``
branch consumes the cell-directed ray leaf.  The branches are mutually
exclusive; the serial RNG state keys are a declared non-ported runtime
boundary and are rejected.  Inputs are deterministic, so the same variates
replay bit-identically.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.fusion import (
    construct_nbi_source_ray,
    initialize_nbi_trajectory,
    intersect_ray_with_rectilinear_grid,
    nbi_cell_directed_ray,
    normalize_nbi_injected_neutrals,
    scale_nbi_velocity_for_energy_component,
)


def _source_ray_state(**overrides):
    state = dict(
        source_uniform=[0.5, 0.5], divergence_normal=[0.0, 0.0],
        source_shape=1, half_width_y_cm=2.0, half_width_z_cm=3.0,
        focus_y_cm=100.0, focus_z_cm=100.0,
        divergence_y_rad=0.1, divergence_z_rad=0.1,
        aperture_distance_cm=[5.0], aperture_shape=[1],
        aperture_offset_y_cm=[0.0], aperture_offset_z_cm=[0.0],
        aperture_half_width_y_cm=[2.0], aperture_half_width_z_cm=[2.0],
        beam_basis=np.eye(3), beam_source_cm=[0.0, 0.0, 0.0],
        injection_speed_cm_s=1.0e8, energy_component=1,
    )
    state.update(overrides)
    return state


def _cell_directed_state(**overrides):
    state = dict(
        cell_center_uvw_cm=[10.0, 0.0, 0.0], cell_offset_cm=[0.0, 0.0, 0.0],
        source_xyz_cm=[0.0, 0.0, 0.0], beam_origin_uvw_cm=[0.0, 0.0, 0.0],
        inverse_beam_basis=np.eye(3), beam_basis=np.eye(3),
        injection_speed_cm_s=1.0e8, neutral_type=1,
        aperture_distance_cm=[5.0], aperture_shape=[1],
        aperture_offset_y_cm=[0.0], aperture_offset_z_cm=[0.0],
        aperture_half_width_y_cm=[2.0], aperture_half_width_z_cm=[2.0],
        focus_y_cm=100.0, focus_z_cm=100.0,
        divergence_y_rad=[0.1, 0.1, 0.1], divergence_z_rad=[0.1, 0.1, 0.1],
    )
    state.update(overrides)
    return state


def _inputs(mode="source_ray", **overrides):
    values = dict(
        sampling_mode=mode,
        injected_power_mw=2.0,
        injection_energy_kev=80.0,
        current_fractions=[0.5, 0.3, 0.2],
        beam_grid_cell_volume_cm3=125.0,
    )
    values.update(overrides)
    return values


def _operator_state():
    """Graph state minus the two keys the graph itself consumes."""
    state = dict(_source_ray_state())
    del state["injection_speed_cm_s"], state["energy_component"]
    return state


def _assert_same_state(first, second):
    assert set(first) == set(second)
    for key, value in first.items():
        other = second[key]
        if value is None or other is None:
            assert value is None and other is None, key
        elif isinstance(value, np.ndarray) or isinstance(other, np.ndarray):
            np.testing.assert_array_equal(value, other, err_msg=key)
        else:
            assert value == other, key


def test_source_ray_branch_normalizes_first_then_composes_ray_and_velocity():
    result = initialize_nbi_trajectory(_inputs(source_ray_state=_source_ray_state()))
    expected = normalize_nbi_injected_neutrals(2.0, 80.0, [0.5, 0.3, 0.2], 125.0)
    for key, value in expected.items():
        np.testing.assert_allclose(result[key], value, rtol=1e-15)
    # Same accepted unit ray must be consumed by the velocity scaling edge.
    _, ray, accepted = construct_nbi_source_ray(**_operator_state())
    assert accepted
    np.testing.assert_allclose(result["source_beam_cm"], [0.0, 0.0, 0.0], rtol=1e-15)
    np.testing.assert_allclose(result["unit_ray_beam"], ray, rtol=1e-15)
    np.testing.assert_allclose(
        result["velocity_cm_s"],
        scale_nbi_velocity_for_energy_component(ray, 1.0e8, 1), rtol=1e-15)
    assert result["accepted"] is True
    # Branch-excluded outputs stay null without the optional grid handoff.
    assert result["trajectory_weight"] is None
    assert result["initial_grid_entry_cm"] is None
    assert result["grid_exit_cm"] is None
    assert result["grid_intersection_length_cm"] is None
    assert result["intersects_beam_grid"] is None


def test_source_ray_branch_optional_grid_entry_handoff_matches_the_leaf():
    entry_state = {"grid_center_cm": [0.0, 0.0, 0.0], "grid_lengths_cm": [4.0, 4.0, 4.0]}
    result = initialize_nbi_trajectory(_inputs(
        source_ray_state=_source_ray_state(), beam_grid_entry_state=entry_state))
    expected = intersect_ray_with_rectilinear_grid(
        ray_origin_cm=[0.0, 0.0, 0.0], ray_direction=[1.0, 0.0, 0.0], **entry_state)
    assert result["intersects_beam_grid"] is True
    np.testing.assert_allclose(result["initial_grid_entry_cm"], expected["entry_point_cm"], rtol=1e-15)
    np.testing.assert_allclose(result["grid_exit_cm"], expected["exit_point_cm"], rtol=1e-15)
    assert result["grid_intersection_length_cm"] == expected["intersection_length_cm"]


def test_source_ray_branch_returns_rejected_ray_without_raising():
    result = initialize_nbi_trajectory(_inputs(
        source_ray_state=_source_ray_state(aperture_offset_y_cm=[50.0])))
    assert result["accepted"] is False
    # The rejected branch still reports the sampled geometry for the caller.
    np.testing.assert_allclose(result["unit_ray_beam"][0], 1.0, rtol=1e-15)


def test_cell_directed_branch_uses_the_cell_leaf_and_nulls_source_fields():
    state = _cell_directed_state()
    result = initialize_nbi_trajectory(_inputs(mode="cell_directed", cell_directed_state=state))
    expected = nbi_cell_directed_ray(**state)
    np.testing.assert_allclose(result["velocity_cm_s"], expected["velocity_uvw_cm_s"], rtol=1e-15)
    assert result["accepted"] == expected["accepted"]
    assert result["trajectory_weight"] == expected["trajectory_weight"]
    assert result["source_beam_cm"] is None
    assert result["unit_ray_beam"] is None
    assert result["initial_grid_entry_cm"] is None
    assert result["intersects_beam_grid"] is None
    # The normalization is branch-independent and still present.
    np.testing.assert_allclose(
        result["total_neutral_rate_s_inv"],
        normalize_nbi_injected_neutrals(2.0, 80.0, [0.5, 0.3, 0.2], 125.0)["total_neutral_rate_s_inv"],
        rtol=1e-15)


def test_zero_power_is_legal_and_still_produces_the_ray_branch():
    result = initialize_nbi_trajectory(_inputs(
        injected_power_mw=0.0, source_ray_state=_source_ray_state()))
    assert result["total_neutral_rate_s_inv"] == 0.0
    np.testing.assert_allclose(result["initial_state_rate_per_volume_cm_inv3_s_inv"], [0.0, 0.0, 0.0], atol=0.0)
    assert result["accepted"] is True


def test_same_variates_replay_bit_identically():
    first = initialize_nbi_trajectory(_inputs(source_ray_state=_source_ray_state()))
    second = initialize_nbi_trajectory(_inputs(source_ray_state=_source_ray_state()))
    _assert_same_state(first, second)


def test_unknown_mode_missing_states_and_missing_keys_are_rejected():
    with pytest.raises(ValueError, match="sampling_mode"):
        initialize_nbi_trajectory(_inputs(mode="both"))
    with pytest.raises(ValueError, match="source_ray_state"):
        initialize_nbi_trajectory(_inputs())
    with pytest.raises(ValueError, match="cell_directed_state"):
        initialize_nbi_trajectory(_inputs(mode="cell_directed"))
    state = _source_ray_state()
    del state["source_uniform"]
    with pytest.raises(ValueError, match="source_uniform"):
        initialize_nbi_trajectory(_inputs(source_ray_state=state))


def test_serial_rng_state_keys_are_a_declared_non_ported_boundary():
    for key, value in (
        ("source_serial_rng_seed", 42),
        ("source_rng_state", {"seed": 42, "state": [1, 2]}),
        ("source_fallback_axis_beam", [1.0, 0.0, 0.0]),
    ):
        state = _source_ray_state(**{key: value})
        with pytest.raises(ValueError, match="runtime boundary"):
            initialize_nbi_trajectory(_inputs(source_ray_state=state))


def test_bad_normalization_contract_propagates():
    with pytest.raises(ValueError):
        initialize_nbi_trajectory(_inputs(
            injected_power_mw=-1.0, source_ray_state=_source_ray_state()))
    with pytest.raises(ValueError):
        initialize_nbi_trajectory(_inputs(
            source_ray_state=_source_ray_state(energy_component=4)))

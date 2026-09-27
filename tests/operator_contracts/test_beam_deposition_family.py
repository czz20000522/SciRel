"""FIDASIM beam-neutral multi-segment deposition family (r78).

Saved probes for the DDA segment traversal, the N3/N4 deposition
handoff, the NDMC producer, and the beam-neutral segment-deposition
composition, plus the registered hardenings and the reviewer-finding
regressions (negative N4 density/photons fail closed; np.bool_ scalars
rejected; precise rate-density field names).
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from scirel.fusion.beam_grid_ray_segment_tracking import trace_beam_grid_ray_segments
from scirel.fusion.n3_n4_segment_deposition import assemble_n3_n4_segment_deposition
from scirel.fusion.ndmc_deposition_producer import ELEMENTARY_CHARGE_C, run_ndmc_deposition_producer
from scirel.fusion.beam_neutral_segment_deposition_loop import deposit_beam_neutral_segments


# --------------------------- beam-grid ray segment tracking ---------------------------

def _track_base(**overrides):
    values = dict(
        start_position_cm=[0.0, 0.1, 0.1], velocity_cm_s=[1.0, 0.1, 0.1],
        initial_grid_index_one_based=[1, 1, 1],
        x_cell_centers_cm=[0.0, 1.0, 2.0], y_cell_centers_cm=[0.0, 1.0, 2.0],
        z_cell_centers_cm=[0.0, 1.0, 2.0], cell_width_cm=[1.0, 1.0, 1.0],
        in_plasma_at=lambda _point: False,
    )
    values.update(overrides)
    return values


def test_track_matches_the_saved_regular_probe():
    regular = trace_beam_grid_ray_segments(**_track_base(), max_track_segments=2, max_crossings=2)
    assert regular["ntrack"] == 2
    assert regular["segments"][0]["grid_index_one_based"] == (1, 1, 1)
    assert regular["segments"][1]["grid_index_one_based"] == (2, 1, 1)
    assert np.isclose(regular["segments"][0]["duration_s"], 0.5)


def test_track_matches_the_saved_plasma_crossing_probe():
    crossing = trace_beam_grid_ray_segments(
        **_track_base(in_plasma_at=lambda point: point[0] < 0.25),
        max_track_segments=2, max_crossings=2)
    assert crossing["plasma_crossings"] == 1 and crossing["ntrack"] == 2
    assert np.allclose([record["duration_s"] for record in crossing["segments"]], [0.25, 0.25])


def test_track_matches_the_saved_adaptive_probe():
    adaptive = trace_beam_grid_ray_segments(
        **_track_base(), max_track_segments=3, max_crossings=2,
        adaptive_mode=1, max_cell_splits=3, split_tolerance=0.1,
        adaptive_parameter_at=lambda point, _mode: 1.0 + 4.0 * point[0])
    assert adaptive["ntrack"] == 3
    assert np.allclose([record["duration_s"] for record in adaptive["segments"]], [1 / 6] * 3)


def test_track_zero_velocity_returns_the_saved_empty_traversal():
    zero = trace_beam_grid_ray_segments(
        **_track_base(velocity_cm_s=[0.0, 0.0, 0.0]), max_track_segments=2, max_crossings=1)
    assert zero == {"segments": [], "ntrack": 0, "plasma_crossings": 0, "terminal_reason": "zero_velocity"}


def test_track_rejects_fractional_index_and_bool_limits():
    with pytest.raises(ValueError):
        trace_beam_grid_ray_segments(
            **_track_base(initial_grid_index_one_based=[1.5, 1, 1]), max_track_segments=2, max_crossings=1)
    # Registered hardening: bools are not genuine integers (the saved arm
    # accepted True as 1 because bool subclasses int).
    with pytest.raises(ValueError, match="registered hardening"):
        trace_beam_grid_ray_segments(**_track_base(), max_track_segments=True, max_crossings=1)
    with pytest.raises(ValueError, match="registered hardening"):
        trace_beam_grid_ray_segments(**_track_base(), max_track_segments=2, max_crossings=np.bool_(True))


# --------------------------- N3/N4 segment deposition ---------------------------

def _handoff_record(previous, next_states, *, index=0, duration=0.5, density=None, photons=2.5):
    return {
        "local_state_sample_index": index,
        "input_neutral_states_cm_inv3_s_inv": previous,
        "dt_s": duration,
        "next_states_cm_inv3_s_inv": next_states,
        "dens_cm_inv3": np.asarray(next_states, dtype=float) * 3.0 if density is None else density,
        "photons_per_cm3_s": photons,
        "n4_result_provenance": "case:n4-v1",
    }


def test_deposition_handoff_matches_the_saved_state_and_normalization_probe():
    out = assemble_n3_n4_segment_deposition(
        expected_position_cm=[1.0, 0.0, 0.0], actual_position_cm=[1.0, 0.0, 0.0],
        n4_cell_update_record=_handoff_record([10.0, 20.0], [9.5, 19.0]),
        local_state_sample_index=0, previous_states_cm_inv3_s_inv=[10.0, 20.0],
        segment_duration_s=0.5, nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
        previous_deposited_particles_per_s=1.0,
    )
    assert np.allclose(out["next_states_cm_inv3_s_inv"], [9.5, 19.0])
    assert np.isclose(out["segment_flux_per_cm3_s"], 0.75)
    assert np.isclose(out["deposited_particles_per_s"], 4.0)
    assert np.allclose(out["normalized_density_cm_inv3"], np.asarray([9.5, 19.0]) * 3.0 / 2.0)


def test_deposition_handoff_rejects_state_or_position_drift():
    record = _handoff_record([0.0, 0.0], [9.5, 19.0])
    with pytest.raises(ValueError):
        assemble_n3_n4_segment_deposition(
            expected_position_cm=[1.0, 0.0, 0.0], actual_position_cm=[1.1, 0.0, 0.0],
            n4_cell_update_record=record, local_state_sample_index=0,
            previous_states_cm_inv3_s_inv=[10.0, 20.0], segment_duration_s=0.5,
            nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
            previous_deposited_particles_per_s=0.0)


def test_deposition_handoff_rejects_negative_density_or_photons_per_review():
    # Reviewer finding, pinned: the saved arm's operator contract declares
    # the density and photon handoff fields nonnegative, but its
    # implementation only rejected negative next states.
    with pytest.raises(ValueError, match="registered hardening"):
        assemble_n3_n4_segment_deposition(
            expected_position_cm=[1.0, 0.0, 0.0], actual_position_cm=[1.0, 0.0, 0.0],
            n4_cell_update_record=_handoff_record([10.0], [9.0], density=[-1.0]),
            local_state_sample_index=0, previous_states_cm_inv3_s_inv=[10.0],
            segment_duration_s=0.5, nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
            previous_deposited_particles_per_s=0.0)
    with pytest.raises(ValueError, match="registered hardening"):
        assemble_n3_n4_segment_deposition(
            expected_position_cm=[1.0, 0.0, 0.0], actual_position_cm=[1.0, 0.0, 0.0],
            n4_cell_update_record=_handoff_record([10.0], [9.0], photons=-2.5),
            local_state_sample_index=0, previous_states_cm_inv3_s_inv=[10.0],
            segment_duration_s=0.5, nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
            previous_deposited_particles_per_s=0.0)


def test_deposition_handoff_rejects_bool_and_noninteger_sample_indices():
    # Reviewer finding, pinned: np.bool_(True) passed the saved arm's
    # int(record) != index comparison as 1; a genuine integer is required.
    with pytest.raises(ValueError, match="registered hardening"):
        assemble_n3_n4_segment_deposition(
            expected_position_cm=[1.0, 0.0, 0.0], actual_position_cm=[1.0, 0.0, 0.0],
            n4_cell_update_record=_handoff_record([10.0], [9.0], index=1),
            local_state_sample_index=np.bool_(True), previous_states_cm_inv3_s_inv=[10.0],
            segment_duration_s=0.5, nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
            previous_deposited_particles_per_s=0.0)


def test_deposition_handoff_rejects_np_bool_scalars_per_review():
    # Reviewer finding, pinned: np.bool_(True) passed the scalar gates as
    # 1.0 despite the documented bool rejection; np.bool_ is now rejected.
    with pytest.raises(ValueError, match="registered hardening"):
        assemble_n3_n4_segment_deposition(
            expected_position_cm=[1.0, 0.0, 0.0], actual_position_cm=[1.0, 0.0, 0.0],
            n4_cell_update_record=_handoff_record([10.0], [9.0]),
            local_state_sample_index=0, previous_states_cm_inv3_s_inv=[10.0],
            segment_duration_s=0.5, nlaunch=np.bool_(True),
            beam_grid_cell_volume_cm3=4.0, previous_deposited_particles_per_s=0.0)
    with pytest.raises(ValueError, match="registered hardening"):
        assemble_n3_n4_segment_deposition(
            expected_position_cm=[1.0, 0.0, 0.0], actual_position_cm=[1.0, 0.0, 0.0],
            n4_cell_update_record=_handoff_record([10.0], [9.0]),
            local_state_sample_index=0, previous_states_cm_inv3_s_inv=[10.0],
            segment_duration_s=0.5, nlaunch=2.0,
            beam_grid_cell_volume_cm3=np.bool_(True),
            previous_deposited_particles_per_s=0.0)


# --------------------------- NDMC deposition producer ---------------------------

def _fractions():
    return (0.528113, 0.268704, 0.203183)


def _formula_initial_states(power=1.7, energy=72.5, fractions=None, dv=8.0, nlevels=6):
    fractions = _fractions() if fractions is None else tuple(fractions)
    energy_factor = fractions[0] + fractions[1] / 2 + fractions[2] / 3
    nneutrals = 1e6 * power / (1e3 * energy * ELEMENTARY_CHARGE_C * energy_factor)
    states = np.zeros((3, nlevels), dtype=float)
    for q in (1, 2, 3):
        states[q - 1, 0] = nneutrals * fractions[q - 1] / dv
    return states


def _population(shape):
    return np.zeros(shape, dtype=float)


def _segment(ix, iy, iz, density, flux, nlevels=6):
    return {
        "grid_index_one_based": (ix, iy, iz),
        "normalized_density_cm_inv3": np.full(nlevels, float(density)),
        "segment_flux_per_cm3_s": float(flux),
    }


def test_producer_initial_state_matches_the_saved_source_e0_probe():
    result = run_ndmc_deposition_producer(
        injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=_fractions(),
        beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=6, grid_shape=(50, 60, 70),
        initial_states_cm_inv3_s_inv=_formula_initial_states(),
        initial_population_density_full=_population((6, 50, 60, 70)),
        initial_population_density_half=_population((6, 50, 60, 70)),
        initial_population_density_third=_population((6, 50, 60, 70)),
        per_fraction_segment_depositions={
            1: [_segment(1, 1, 1, 1.0, 0.5)],
            2: [_segment(1, 1, 2, 2.0, 0.5)],
            3: [_segment(1, 1, 3, 3.0, 0.5)],
        },
    )
    assert result["elementary_charge_c"] == ELEMENTARY_CHARGE_C == 1.60217733e-19
    nneutrals = 1e6 * 1.7 / (1e3 * 72.5 * ELEMENTARY_CHARGE_C * (0.528113 + 0.268704 / 2 + 0.203183 / 3))
    assert np.isclose(result["nneutrals_s_inv"], nneutrals, rtol=1e-15)
    assert np.isclose(result["initial_state_rate_per_volume_cm_inv3_s_inv"][0, 0], 1.3231215306280405e19, rtol=1e-15)
    assert np.isclose(result["initial_state_rate_per_volume_cm_inv3_s_inv"][1, 0], 6.732044993512316e18, rtol=1e-15)
    assert np.isclose(result["initial_state_rate_per_volume_cm_inv3_s_inv"][2, 0], 5.090497714648137e18, rtol=1e-15)


def test_producer_population_and_flux_tot_accumulation():
    result = run_ndmc_deposition_producer(
        injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=_fractions(),
        beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=2, grid_shape=(2, 2, 2),
        initial_states_cm_inv3_s_inv=_formula_initial_states(nlevels=2),
        initial_population_density_full=_population((2, 2, 2, 2)),
        initial_population_density_half=_population((2, 2, 2, 2)),
        initial_population_density_third=_population((2, 2, 2, 2)),
        per_fraction_segment_depositions={
            1: [_segment(1, 1, 1, 2.0, 0.25, 2), _segment(2, 1, 1, 3.0, 0.75, 2)],
            2: [_segment(1, 1, 2, 4.0, 0.5, 2)],
            3: [_segment(1, 1, 2, 1.0, 0.125, 2)],
        },
    )
    assert np.allclose(result["population_density_full"][:, 0, 0, 0], 2.0)
    assert np.allclose(result["population_density_full"][:, 1, 0, 0], 3.0)
    assert np.allclose(result["population_density_half"][:, 0, 0, 1], 4.0)
    assert np.allclose(result["population_density_third"][:, 0, 0, 1], 1.0)
    assert np.allclose(result["flux_tot_per_fraction"], [8.0, 4.0, 1.0], rtol=1e-12)
    assert np.isclose(result["deposited_particles_per_s"], 13.0, rtol=1e-12)


def test_producer_initial_population_continuation():
    base = np.ones((2, 2, 2, 2))
    result = run_ndmc_deposition_producer(
        injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=_fractions(),
        beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=2, grid_shape=(2, 2, 2),
        initial_states_cm_inv3_s_inv=_formula_initial_states(nlevels=2),
        initial_population_density_full=base, initial_population_density_half=base,
        initial_population_density_third=base,
        per_fraction_segment_depositions={1: [_segment(1, 1, 1, 2.0, 0.5, 2)]},
    )
    assert np.allclose(result["population_density_full"][:, 0, 0, 0], 3.0)
    assert np.allclose(result["population_density_full"][:, 1, 1, 1], 1.0)


def test_producer_expected_flux_tot_cross_check():
    run_ndmc_deposition_producer(
        injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=_fractions(),
        beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=2, grid_shape=(2, 2, 2),
        initial_states_cm_inv3_s_inv=_formula_initial_states(nlevels=2),
        initial_population_density_full=_population((2, 2, 2, 2)),
        initial_population_density_half=_population((2, 2, 2, 2)),
        initial_population_density_third=_population((2, 2, 2, 2)),
        per_fraction_segment_depositions={1: [_segment(1, 1, 1, 2.0, 0.5, 2)]},
        expected_deposited_particles_per_s_per_fraction=[4.0, 0.0, 0.0],
    )


def test_producer_accepts_negative_expected_flux_tot_per_review():
    # Pre-freeze review follow-up, pinned: the accumulation is signed, so a
    # negative expected total for a net-population-gain slice must pass the
    # cross-check instead of being rejected by a nonnegativity gate.
    run_ndmc_deposition_producer(
        injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=_fractions(),
        beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=2, grid_shape=(2, 2, 2),
        initial_states_cm_inv3_s_inv=_formula_initial_states(nlevels=2),
        initial_population_density_full=_population((2, 2, 2, 2)),
        initial_population_density_half=_population((2, 2, 2, 2)),
        initial_population_density_third=_population((2, 2, 2, 2)),
        per_fraction_segment_depositions={1: [_segment(1, 1, 1, 2.0, -0.5, 2)]},
        expected_deposited_particles_per_s_per_fraction=[-4.0, 0.0, 0.0],
    )


def test_producer_rejects_index_out_of_grid():
    with pytest.raises(ValueError, match="grid_index_one_based"):
        run_ndmc_deposition_producer(
            injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=_fractions(),
            beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=2, grid_shape=(2, 2, 2),
            initial_states_cm_inv3_s_inv=_formula_initial_states(nlevels=2),
            initial_population_density_full=_population((2, 2, 2, 2)),
            initial_population_density_half=_population((2, 2, 2, 2)),
            initial_population_density_third=_population((2, 2, 2, 2)),
            per_fraction_segment_depositions={1: [_segment(3, 1, 1, 2.0, 0.5, 2)]},
        )


def test_producer_rejects_zero_fraction_with_records():
    fractions = list(_fractions())
    fractions[1] = 0.0
    with pytest.raises(ValueError, match="zero current_fraction"):
        run_ndmc_deposition_producer(
            injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=fractions,
            beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=2, grid_shape=(2, 2, 2),
            initial_states_cm_inv3_s_inv=_formula_initial_states(fractions=fractions, nlevels=2),
            initial_population_density_full=_population((2, 2, 2, 2)),
            initial_population_density_half=_population((2, 2, 2, 2)),
            initial_population_density_third=_population((2, 2, 2, 2)),
            per_fraction_segment_depositions={2: [_segment(1, 1, 1, 2.0, 0.5, 2)]},
        )


def test_producer_rejects_codata_e0_initial_state():
    # Source-faithful gate: a CODATA-e0 normalization yields rel ~4.34e-7
    # deviation from the frozen trace and must fail closed; the e0 fork
    # between nbi-injected-neutrals-normalization (CODATA) and
    # nbi-component-initial-state (source) stays with expert adjudication.
    codata = 1.602176634e-19
    fractions = _fractions()
    energy_factor = fractions[0] + fractions[1] / 2 + fractions[2] / 3
    nneutrals_codata = 1e6 * 1.7 / (1e3 * 72.5 * codata * energy_factor)
    states = np.zeros((3, 6), dtype=float)
    for q in (1, 2, 3):
        states[q - 1, 0] = nneutrals_codata * fractions[q - 1] / 8.0
    with pytest.raises(ValueError, match="initial_states_cm_inv3_s_inv"):
        run_ndmc_deposition_producer(
            injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=fractions,
            beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=6, grid_shape=(50, 60, 70),
            initial_states_cm_inv3_s_inv=states,
            initial_population_density_full=_population((6, 50, 60, 70)),
            initial_population_density_half=_population((6, 50, 60, 70)),
            initial_population_density_third=_population((6, 50, 60, 70)),
            per_fraction_segment_depositions={
                1: [_segment(1, 1, 1, 1.0, 0.5)],
                2: [_segment(1, 1, 2, 1.0, 0.5)],
                3: [_segment(1, 1, 3, 1.0, 0.5)],
            },
        )


def test_producer_rejects_float_grid_shape_per_review():
    # Registered hardening: the saved arm's astype(int) silently truncated
    # whole-number floats such as 2.0; a genuine integer triple is required.
    with pytest.raises(ValueError, match="registered hardening"):
        run_ndmc_deposition_producer(
            injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=_fractions(),
            beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=2, grid_shape=(2.0, 2, 2),
            initial_states_cm_inv3_s_inv=_formula_initial_states(nlevels=2),
            initial_population_density_full=_population((2, 2, 2, 2)),
            initial_population_density_half=_population((2, 2, 2, 2)),
            initial_population_density_third=_population((2, 2, 2, 2)),
            per_fraction_segment_depositions={1: [_segment(1, 1, 1, 2.0, 0.5, 2)]},
        )


def test_producer_accepts_signed_segment_flux_per_cross_asset_review():
    # Cross-asset review finding, pinned: the N3/N4 handoff computes the
    # SIGNED segment_flux = (sum(previous) - sum(next))/nlaunch, and colrad
    # with loss-only transition tables can drive a net level-population gain
    # over a segment, so a valid N3 handoff may carry a negative segment
    # flux.  The producer accepts it source-faithfully (source
    # flux = (iflux - sum(states))/nlaunch is signed); the saved arm's
    # documented nonnegativity is a bounded incompatibility recorded for
    # expert adjudication.
    result = run_ndmc_deposition_producer(
        injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=_fractions(),
        beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=2, grid_shape=(2, 2, 2),
        initial_states_cm_inv3_s_inv=_formula_initial_states(nlevels=2),
        initial_population_density_full=_population((2, 2, 2, 2)),
        initial_population_density_half=_population((2, 2, 2, 2)),
        initial_population_density_third=_population((2, 2, 2, 2)),
        per_fraction_segment_depositions={1: [_segment(1, 1, 1, 2.0, -0.5, 2)]},
    )
    assert np.isclose(result["flux_tot_per_fraction"][0], -4.0)
    assert np.isclose(result["deposited_particles_per_s"], -4.0)
    # Non-finite flux still fails closed.
    with pytest.raises(ValueError, match="finite"):
        run_ndmc_deposition_producer(
            injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=_fractions(),
            beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=2, grid_shape=(2, 2, 2),
            initial_states_cm_inv3_s_inv=_formula_initial_states(nlevels=2),
            initial_population_density_full=_population((2, 2, 2, 2)),
            initial_population_density_half=_population((2, 2, 2, 2)),
            initial_population_density_third=_population((2, 2, 2, 2)),
            per_fraction_segment_depositions={1: [_segment(1, 1, 1, 2.0, np.nan, 2)]},
        )


def test_producer_colrad_population_gain_path_is_consistent():
    # Signed-handoff witness with an actual colrad advance: the integrated
    # collisional-radiative eigen-advance driven by a physically shaped
    # rate matrix whose inflow (population) terms outweigh losses produces
    # a net level-population gain over the step (the source flux
    # (iflux - sum(states))/nlaunch is signed), and the N3 handoff for
    # that result must flow through the producer without rejection.
    # A loss-only matrix (all column sums <= 0) cannot produce a gain.
    from scirel.fusion import advance_collisional_radiative_states

    # rows = target levels, columns = source levels; column 1's inflow
    # (2.0) exceeds its losses (1.0), so the total population grows.
    matrix = ((-0.5, 2.0), (0.0, -1.0))
    previous = [0.0, 1.0]
    next_states, integrated_density, photons = advance_collisional_radiative_states(
        previous, matrix, 0.5, True, 1, 3.0)
    assert np.sum(next_states) > np.sum(previous)
    record = {
        "local_state_sample_index": 0,
        "input_neutral_states_cm_inv3_s_inv": previous,
        "dt_s": 0.5,
        "next_states_cm_inv3_s_inv": next_states,
        "dens_cm_inv3": integrated_density,
        "photons_per_cm3_s": photons,
        "n4_result_provenance": "case:colrad-gain-v1",
    }
    update = assemble_n3_n4_segment_deposition(
        expected_position_cm=[1.0, 0.0, 0.0], actual_position_cm=[1.0, 0.0, 0.0],
        n4_cell_update_record=record, local_state_sample_index=0,
        previous_states_cm_inv3_s_inv=previous, segment_duration_s=0.5,
        nlaunch=2.0, beam_grid_cell_volume_cm3=4.0, previous_deposited_particles_per_s=0.0)
    assert update["segment_flux_per_cm3_s"] < 0.0
    producer = run_ndmc_deposition_producer(
        injected_power_mw=1.7, injection_energy_kev=72.5, current_fractions=_fractions(),
        beam_grid_cell_volume_cm3=8.0, nlaunch=10.0, nlevels=2, grid_shape=(2, 2, 2),
        initial_states_cm_inv3_s_inv=_formula_initial_states(nlevels=2),
        initial_population_density_full=_population((2, 2, 2, 2)),
        initial_population_density_half=_population((2, 2, 2, 2)),
        initial_population_density_third=_population((2, 2, 2, 2)),
        per_fraction_segment_depositions={1: [{
            "grid_index_one_based": (1, 1, 1),
            "normalized_density_cm_inv3": update["normalized_density_cm_inv3"],
            "segment_flux_per_cm3_s": update["segment_flux_per_cm3_s"],
        }]},
    )
    assert np.isclose(producer["flux_tot_per_fraction"][0], update["segment_flux_per_cm3_s"] * 8.0)


# --------------------------- beam-neutral deposition loop graph ---------------------------

def _snapshot_table():
    return {"nenergy": 2, "ntemp": 2, "logemin": 0.0, "logtmin": 0.0, "dlogE": 1.0, "dlogT": 1.0,
            "minlog_pop": -99.0, "minlog_depop": -99.0, "log_pop": np.full((2, 2, 2, 2), -99.0),
            "log_depop": np.full((2, 2, 2), -99.0)}


def _snapshot(position):
    values = _snapshot_table()
    return {"position_cm": position, "in_plasma": True, "thermal_density_cm3": (1.0,),
            "thermal_mass_amu": (2.0,), "ion_temperature_kev": 1.0, "electron_density_cm3": 1.0,
            "electron_temperature_kev": 1.0, "impurity_density_cm3": 0.0, "fast_ion_density_cm3": 0.0,
            "beam_mass_amu": 2.0, "beam_energy_kev": 1.0, "hydrogen_table": values,
            "electron_table": values, "impurity_table": values,
            "einstein_s_inv": ((0.0, 0.0), (0.0, 0.0)),
            "snapshot_provenance": "case:nbi-local-state-v1"}


def _n4_update(index, previous, duration):
    next_states = np.asarray(previous, dtype=float) - np.array([duration, 2.0 * duration])
    return {"local_state_sample_index": index,
            "input_neutral_states_cm_inv3_s_inv": previous, "dt_s": duration,
            "next_states_cm_inv3_s_inv": next_states, "dens_cm_inv3": next_states * 3.0,
            "photons_per_cm3_s": 5.0 * duration, "n4_result_provenance": "case:n4-cell-update-v1"}


def _graph_beam_grid():
    return dict(x_cell_centers_cm=[0.0, 1.0, 2.0], y_cell_centers_cm=[0.0], z_cell_centers_cm=[0.0],
                cell_width_cm=[1.0, 1.0, 1.0], max_track_segments=2, max_crossings=2,
                in_plasma_at=lambda _point: True)


def test_deposition_loop_matches_the_saved_two_segment_probe():
    first = _n4_update(0, [10.0, 20.0], 0.5)
    second = _n4_update(1, first["next_states_cm_inv3_s_inv"], 1.0)
    out = deposit_beam_neutral_segments(
        start_position_cm=[0.0, 0.0, 0.0], neutral_velocity_cm_s=[1.0, 0.1, 0.1],
        initial_grid_index_one_based=[1, 1, 1], beam_grid=_graph_beam_grid(),
        initial_states_cm_inv3_s_inv=[10.0, 20.0], nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
        local_state_samples=[_snapshot((0.25, 0.025, 0.025)), _snapshot((1.0, 0.1, 0.1))],
        n4_cell_update_records=[first, second])
    assert np.allclose(out["final_states_cm_inv3_s_inv"], second["next_states_cm_inv3_s_inv"])
    assert np.allclose([record["segment_flux_per_cm3_s"] for record in out["segment_depositions"]], [0.75, 1.5])
    assert np.isclose(out["deposited_particles_per_s"], 9.0)
    assert np.allclose(out["segment_depositions"][0]["normalized_density_cm_inv3"], first["dens_cm_inv3"] / 2.0)
    assert out["diagnostics"]["graph_order"] == ["deposition_initialization", "beam_grid_track",
                                                 "local_state_sequence", "n4_cell_update_handoff", "deposition"]


def test_deposition_loop_rejects_mismatched_carried_state():
    bad = dict(_n4_update(0, [10.0, 20.0], 0.5))
    bad["input_neutral_states_cm_inv3_s_inv"] = [0.0, 0.0]
    second = _n4_update(1, [9.5, 19.0], 1.0)
    with pytest.raises(ValueError):
        deposit_beam_neutral_segments(
            start_position_cm=[0.0, 0.0, 0.0], neutral_velocity_cm_s=[1.0, 0.1, 0.1],
            initial_grid_index_one_based=[1, 1, 1], beam_grid=_graph_beam_grid(),
            initial_states_cm_inv3_s_inv=[10.0, 20.0], nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
            local_state_samples=[_snapshot((0.25, 0.025, 0.025)), _snapshot((1.0, 0.1, 0.1))],
            n4_cell_update_records=[bad, second])


def test_deposition_loop_rejects_record_count_mismatch():
    first = _n4_update(0, [10.0, 20.0], 0.5)
    with pytest.raises(ValueError, match="segment count"):
        deposit_beam_neutral_segments(
            start_position_cm=[0.0, 0.0, 0.0], neutral_velocity_cm_s=[1.0, 0.1, 0.1],
            initial_grid_index_one_based=[1, 1, 1], beam_grid=_graph_beam_grid(),
            initial_states_cm_inv3_s_inv=[10.0, 20.0], nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
            local_state_samples=[_snapshot((0.25, 0.025, 0.025))],
            n4_cell_update_records=[first])


def test_deposition_loop_rejects_snapshot_contract_violations():
    first = _n4_update(0, [10.0, 20.0], 0.5)
    one_segment_grid = dict(_graph_beam_grid(), max_track_segments=1)
    bad_snapshot = dict(_snapshot((0.25, 0.025, 0.025)))
    del bad_snapshot["snapshot_provenance"]
    with pytest.raises(ValueError, match="snapshot_provenance"):
        deposit_beam_neutral_segments(
            start_position_cm=[0.0, 0.0, 0.0], neutral_velocity_cm_s=[1.0, 0.1, 0.1],
            initial_grid_index_one_based=[1, 1, 1], beam_grid=one_segment_grid,
            initial_states_cm_inv3_s_inv=[10.0, 20.0], nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
            local_state_samples=[bad_snapshot], n4_cell_update_records=[first])
    axis_snapshot = dict(_snapshot((0.25, 0.025, 0.025)))
    axis_snapshot["hydrogen_table"] = dict(axis_snapshot["hydrogen_table"], log_pop=np.zeros((1, 1, 2, 2)))
    with pytest.raises(ValueError, match="transition-table axes"):
        deposit_beam_neutral_segments(
            start_position_cm=[0.0, 0.0, 0.0], neutral_velocity_cm_s=[1.0, 0.1, 0.1],
            initial_grid_index_one_based=[1, 1, 1], beam_grid=one_segment_grid,
            initial_states_cm_inv3_s_inv=[10.0, 20.0], nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
            local_state_samples=[axis_snapshot], n4_cell_update_records=[first])


def test_deposition_loop_rejects_fractional_knot_counts_per_review():
    # Review finding, pinned: the saved arm's int() silently truncated
    # fractional knot counts such as 2.0; genuine integers are required.
    first = _n4_update(0, [10.0, 20.0], 0.5)
    one_segment_grid = dict(_graph_beam_grid(), max_track_segments=1)
    fractional = dict(_snapshot((0.25, 0.025, 0.025)))
    fractional["hydrogen_table"] = dict(
        fractional["hydrogen_table"], log_pop=np.full((2, 2, 2, 2), -99.0), nenergy=2.0)
    with pytest.raises(ValueError, match="registered hardening"):
        deposit_beam_neutral_segments(
            start_position_cm=[0.0, 0.0, 0.0], neutral_velocity_cm_s=[1.0, 0.1, 0.1],
            initial_grid_index_one_based=[1, 1, 1], beam_grid=one_segment_grid,
            initial_states_cm_inv3_s_inv=[10.0, 20.0], nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
            local_state_samples=[fractional], n4_cell_update_records=[first])
    bool_count = dict(_snapshot((0.25, 0.025, 0.025)))
    bool_count["hydrogen_table"] = dict(bool_count["hydrogen_table"], ntemp=True)
    with pytest.raises(ValueError, match="registered hardening"):
        deposit_beam_neutral_segments(
            start_position_cm=[0.0, 0.0, 0.0], neutral_velocity_cm_s=[1.0, 0.1, 0.1],
            initial_grid_index_one_based=[1, 1, 1], beam_grid=one_segment_grid,
            initial_states_cm_inv3_s_inv=[10.0, 20.0], nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
            local_state_samples=[bool_count], n4_cell_update_records=[first])


def test_deposition_loop_rejects_np_bool_normalization_scalars_per_review():
    # Pre-freeze review follow-up, pinned: np.bool_(True) passed the
    # graph-internal initialization and snapshot scalar gates as 1.0 even
    # though both contracts require genuine finite scalars.
    first = _n4_update(0, [10.0, 20.0], 0.5)
    one_segment_grid = dict(_graph_beam_grid(), max_track_segments=1)
    with pytest.raises(ValueError, match="genuine finite positive scalar"):
        deposit_beam_neutral_segments(
            start_position_cm=[0.0, 0.0, 0.0], neutral_velocity_cm_s=[1.0, 0.1, 0.1],
            initial_grid_index_one_based=[1, 1, 1], beam_grid=one_segment_grid,
            initial_states_cm_inv3_s_inv=[10.0, 20.0], nlaunch=np.bool_(True),
            beam_grid_cell_volume_cm3=4.0,
            local_state_samples=[_snapshot((0.25, 0.025, 0.025))], n4_cell_update_records=[first])
    with pytest.raises(ValueError, match="genuine finite positive scalar"):
        deposit_beam_neutral_segments(
            start_position_cm=[0.0, 0.0, 0.0], neutral_velocity_cm_s=[1.0, 0.1, 0.1],
            initial_grid_index_one_based=[1, 1, 1], beam_grid=one_segment_grid,
            initial_states_cm_inv3_s_inv=[10.0, 20.0], nlaunch=2.0,
            beam_grid_cell_volume_cm3=np.bool_(True),
            local_state_samples=[_snapshot((0.25, 0.025, 0.025))], n4_cell_update_records=[first])
    bool_snapshot = dict(_snapshot((0.25, 0.025, 0.025)))
    bool_snapshot["electron_density_cm3"] = np.bool_(True)
    with pytest.raises(ValueError, match="genuine finite scalar"):
        deposit_beam_neutral_segments(
            start_position_cm=[0.0, 0.0, 0.0], neutral_velocity_cm_s=[1.0, 0.1, 0.1],
            initial_grid_index_one_based=[1, 1, 1], beam_grid=one_segment_grid,
            initial_states_cm_inv3_s_inv=[10.0, 20.0], nlaunch=2.0,
            beam_grid_cell_volume_cm3=4.0,
            local_state_samples=[bool_snapshot], n4_cell_update_records=[first])


def test_deposition_loop_accepts_vacuum_temperature_payload():
    # Source quirk preserved: out-of-plasma segments may carry zero temperatures.
    vacuum = dict(_snapshot((0.25, 0.025, 0.025)))
    vacuum.update(in_plasma=False, ion_temperature_kev=0.0, electron_temperature_kev=0.0)
    first = _n4_update(0, [10.0, 20.0], 0.5)
    grid = dict(_graph_beam_grid(), max_track_segments=1, in_plasma_at=lambda _point: False)
    out = deposit_beam_neutral_segments(
        start_position_cm=[0.0, 0.0, 0.0], neutral_velocity_cm_s=[1.0, 0.1, 0.1],
        initial_grid_index_one_based=[1, 1, 1], beam_grid=grid,
        initial_states_cm_inv3_s_inv=[10.0, 20.0], nlaunch=2.0, beam_grid_cell_volume_cm3=4.0,
        local_state_samples=[vacuum], n4_cell_update_records=[first])
    assert out["track_terminal_reason"] == "ntrack_limit"
    # segment flux = (sum([10,20]) - sum([9.5,19]))/2 = 0.75 cm^-3 s^-1;
    # deposited += 0.75 * 4.0 = 3.0 particles/s.
    assert np.isclose(out["deposited_particles_per_s"], 3.0)

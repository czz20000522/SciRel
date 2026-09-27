"""Direct contract tests for the r77 FIDASIM N3 colrad family:
``select_dcx_thermal_species_mass``, ``prepare_dcx_colrad_initial_state``,
``assemble_collisional_radiative_rate_matrix``,
``advance_collisional_radiative_states``, and the
``initialize_dcx_halo_marker`` composition graph.

The saved packages' own probes (isotope correction shares, the table
interpolation oracle with the fast-ion density addition and Einstein
diagonal rewrite, the upper-table-edge zero-rate policy, the diagonal
eigen-advance with photon projection, and the outside-plasma ballistic
rule) are reproduced.  The zero-eigenvalue branch is pinned as a
documented registered divergence from the Fortran source (see
test_advance_pins_saved_arm_zero_eigen_boundary).
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from scirel.fusion import (
    advance_collisional_radiative_states,
    assemble_collisional_radiative_rate_matrix,
    initialize_dcx_halo_marker,
    prepare_dcx_colrad_initial_state,
    select_dcx_thermal_species_mass,
)


def _table(log_pop, log_depop):
    return {
        "nenergy": 2, "ntemp": 2, "logemin": 0.0, "logtmin": 0.0,
        "dlogE": 1.0, "dlogT": 1.0, "minlog_pop": -99.0, "minlog_depop": -99.0,
        "log_pop": np.full((2, 2, 2, 2), log_pop),
        "log_depop": np.full((2, 2, 2), log_depop),
    }


_EINSTEIN = ((0.0, 7.0), (11.0, 0.0))


# --------------------------- thermal species selection ---------------------------

def test_species_selection_matches_the_saved_probe():
    assert select_dcx_thermal_species_mass([1.0, 2.0], 1) == 2.0
    assert select_dcx_thermal_species_mass([3.0], 0) == 3.0


def test_species_selection_rejects_bad_contracts():
    for args in (([1.0, 2.0], 2), ([1.0, 2.0], -1), ([1.0, 2.0], True),
                 ([1.0, 2.0], 0.5), ([0.0], 0), ([-1.0], 0),
                 ([np.nan], 0), ([], 0), ([[1.0, 2.0]], 0)):
        with pytest.raises(ValueError):
            select_dcx_thermal_species_mass(*args)


# --------------------------- DCX/halo initial state ---------------------------

def test_initial_state_matches_the_saved_isotope_probes():
    matched = prepare_dcx_colrad_initial_state(
        cx_rate_per_s=[1.0, 2.0], thermal_ion_density_cm3=[3.0, 5.0], thermal_mass_amu=[1.0, 2.0],
        selected_thermal_species_index=1, fast_ion_density_cm3=7.0, beam_mass_amu=2.0)
    np.testing.assert_allclose(matched["initial_states"], [12.0, 24.0], rtol=1e-15)
    assert matched["same_isotope"] is True
    assert math.isclose(matched["photon_fast_ion_correction"], 5.0 / 12.0, rel_tol=1e-15)
    assert matched["source_density_cm3"] == 12.0 and matched["eligible"] is True

    different = prepare_dcx_colrad_initial_state(
        cx_rate_per_s=[1.0, 2.0], thermal_ion_density_cm3=[3.0, 5.0], thermal_mass_amu=[1.0, 2.0],
        selected_thermal_species_index=0, fast_ion_density_cm3=7.0, beam_mass_amu=2.0)
    np.testing.assert_allclose(different["initial_states"], [3.0, 6.0], rtol=1e-15)
    assert different["same_isotope"] is False
    assert different["photon_fast_ion_correction"] == 1.0
    assert different["source_density_cm3"] == 3.0


def test_initial_state_all_zero_rates_are_ineligible_not_errors():
    empty = prepare_dcx_colrad_initial_state(
        cx_rate_per_s=[0.0, 0.0], thermal_ion_density_cm3=[3.0], thermal_mass_amu=[2.0],
        selected_thermal_species_index=0, fast_ion_density_cm3=7.0, beam_mass_amu=2.0)
    assert empty["eligible"] is False
    np.testing.assert_array_equal(empty["initial_states"], [0.0, 0.0])


def test_initial_state_rejects_bad_contracts():
    for overrides in (
        {"cx_rate_per_s": []}, {"cx_rate_per_s": [-1.0, 0.0]}, {"cx_rate_per_s": np.nan},
        {"thermal_ion_density_cm3": [-1.0]}, {"thermal_mass_amu": [0.0]},
        {"thermal_mass_amu": [1.0, 2.0]},
        {"selected_thermal_species_index": 0.5}, {"selected_thermal_species_index": True},
        {"selected_thermal_species_index": 2}, {"selected_thermal_species_index": -1},
        {"fast_ion_density_cm3": -1.0}, {"beam_mass_amu": 0.0},
        {"beam_mass_amu": np.nan}, {"fast_ion_density_cm3": np.inf},
    ):
        kwargs = dict(cx_rate_per_s=[1.0], thermal_ion_density_cm3=[3.0], thermal_mass_amu=[2.0],
                      selected_thermal_species_index=0, fast_ion_density_cm3=0.0, beam_mass_amu=2.0)
        kwargs.update(overrides)
        with pytest.raises(ValueError):
            prepare_dcx_colrad_initial_state(**kwargs)


def test_initial_state_extreme_products_fail_closed():
    # rates * source_density overflows for finite extremes; the saved arm
    # returns Inf states with eligible=True silently.
    with pytest.raises(ValueError, match="registered hardening"):
        prepare_dcx_colrad_initial_state(
            cx_rate_per_s=[1.0e308], thermal_ion_density_cm3=[1.0e308], thermal_mass_amu=[2.0],
            selected_thermal_species_index=0, fast_ion_density_cm3=0.0, beam_mass_amu=2.0)


# --------------------------- rate-matrix assembly ---------------------------

def test_matrix_matches_the_saved_fast_ion_and_diagonal_probe():
    result = assemble_collisional_radiative_rate_matrix(
        (3.0,), (2.0,), 2.0, 4.0, 1.0, 5.0, 1.0, 2.0, 2.0,
        _table(np.log10(2.0), np.log10(2.0)), _table(np.log10(3.0), np.log10(3.0)),
        _table(0.0, 0.0), _EINSTEIN)
    np.testing.assert_array_equal(result, ((-36.0, 32.0), (36.0, -32.0)))


def test_matrix_upper_table_edge_uses_the_source_zero_rate_policy():
    result = assemble_collisional_radiative_rate_matrix(
        (1.0,), (1.0,), 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 100.0,
        _table(0.0, 0.0), _table(0.0, 0.0), _table(0.0, 0.0), _EINSTEIN)
    np.testing.assert_array_equal(result, ((-11.0, 7.0), (11.0, -7.0)))


def test_matrix_rejects_bad_contracts():
    good = dict(thermal_density_cm3=(3.0,), thermal_mass_amu=(2.0,), ion_temperature_kev=2.0,
                electron_density_cm3=4.0, electron_temperature_kev=1.0, impurity_density_cm3=5.0,
                fast_ion_density_cm3=1.0, beam_mass_amu=2.0, beam_energy_kev=2.0,
                hydrogen_table=_table(0.0, 0.0), electron_table=_table(0.0, 0.0),
                impurity_table=_table(0.0, 0.0), einstein_s_inv=_EINSTEIN)
    for overrides in (
        {"thermal_density_cm3": (-1.0,)}, {"thermal_density_cm3": (np.nan,)},
        {"thermal_mass_amu": (0.0,)}, {"thermal_mass_amu": (np.nan,)},
        {"ion_temperature_kev": 0.0}, {"ion_temperature_kev": np.nan},
        {"electron_temperature_kev": 0.0}, {"beam_mass_amu": 0.0}, {"beam_energy_kev": 0.0},
        {"electron_density_cm3": -1.0}, {"impurity_density_cm3": np.nan},
        {"fast_ion_density_cm3": np.inf},
        {"einstein_s_inv": ((0.0, 7.0), (11.0, 0.0), (1.0, 2.0))},
        {"einstein_s_inv": ((0.0, np.nan), (11.0, 0.0))},
        {"hydrogen_table": {"nenergy": 2}},
    ):
        kwargs = dict(good)
        kwargs.update(overrides)
        with pytest.raises(ValueError):
            assemble_collisional_radiative_rate_matrix(**kwargs)


def test_matrix_extreme_table_entries_fail_closed():
    with pytest.raises(ValueError, match="registered hardening"):
        assemble_collisional_radiative_rate_matrix(
            (1.0,), (1.0,), 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0,
            _table(310.0, 310.0), _table(0.0, 0.0), _table(0.0, 0.0), _EINSTEIN)


# --------------------------- eigenstate advance ---------------------------

def test_advance_matches_the_saved_diagonal_probe():
    next_state, density, photons = advance_collisional_radiative_states(
        (1.0, 3.0), ((-2.0, 0.0), (0.0, -1.0)), 0.5, True, 0, 7.0)
    np.testing.assert_allclose(next_state, (math.exp(-1.0), 3.0 * math.exp(-0.5)), rtol=0, atol=1e-14)
    np.testing.assert_allclose(density, ((1.0 - math.exp(-1.0)) / 2.0, 3.0 * (1.0 - math.exp(-0.5))), rtol=0, atol=1e-14)
    assert abs(photons - density[0] * 7.0) < 1e-14


def test_advance_outside_plasma_keeps_the_ballistic_rule():
    next_state, density, photons = advance_collisional_radiative_states(
        (2.0, 1.0), ((-1.0, 0.0), (0.0, -1.0)), 0.25, False, 0, 3.0)
    np.testing.assert_array_equal(next_state, (2.0, 1.0))
    np.testing.assert_array_equal(density, (0.5, 0.25))
    assert photons == 0.0


def test_advance_pins_saved_arm_zero_eigen_boundary():
    # Registered saved-arm semantics, pinned (pre-freeze review): at an
    # exact zero eigenvalue the saved arm's (exp(0)-1)/1 rule zeroes that
    # mode's integrated density, while the Fortran source uses a +1-before-
    # exp avoidance quirk.  The saved bundle's own ledger registers the
    # divergence and shows it never triggered in 823 bounded replay events
    # (240 synthetic + 583 real-HDF5-table, all with non-zero eigenvalues);
    # this port reproduces the saved arm and the divergence is documented
    # for expert adjudication, not silently repaired.
    matrix = ((0.0, 0.0), (0.0, -1.0))
    next_state, density, photons = advance_collisional_radiative_states(
        (2.0, 3.0), matrix, 0.5, True, 0, 7.0)
    # zero mode: exp(0)=1 -> state component unchanged, integrated = 0.
    np.testing.assert_allclose(next_state, (2.0, 3.0 * math.exp(-0.5)), rtol=1e-14)
    np.testing.assert_allclose(density, (0.0, 3.0 * (1.0 - math.exp(-0.5))), rtol=1e-14)


def test_advance_rejects_bad_contracts_and_extremes():
    with pytest.raises(ValueError, match="real-eigenstate"):
        advance_collisional_radiative_states((1.0, 1.0), ((0.0, -1.0), (1.0, 0.0)), 0.5, True, 0, 7.0)
    with pytest.raises(ValueError, match="emitting_state_index"):
        advance_collisional_radiative_states((1.0, 3.0), ((-2.0, 0.0), (0.0, -1.0)), 0.5, True, True, 7.0)
    with pytest.raises(ValueError, match="emitting_state_index"):
        advance_collisional_radiative_states((1.0, 3.0), ((-2.0, 0.0), (0.0, -1.0)), 0.5, True, 2, 7.0)
    with pytest.raises(ValueError):
        advance_collisional_radiative_states((1.0, 3.0), ((-2.0, 0.0), (0.0, -1.0)), 0.5, "yes", 0, 7.0)
    with pytest.raises(ValueError):
        advance_collisional_radiative_states((1.0, -3.0), ((-2.0, 0.0), (0.0, -1.0)), 0.5, True, 0, 7.0)
    with pytest.raises(ValueError, match="registered hardening"):
        # a positive eigenvalue with a large dt overflows exp: the saved arm
        # returns Inf silently.
        advance_collisional_radiative_states((1.0, 3.0), ((2.0, 0.0), (0.0, -1.0)), 500.0, True, 0, 7.0)
    with pytest.raises(ValueError, match="registered hardening"):
        advance_collisional_radiative_states((1.0, 3.0), ((-np.inf, 0.0), (0.0, -1.0)), 0.5, True, 0, 7.0)
    with pytest.raises(ValueError, match="registered hardening"):
        advance_collisional_radiative_states((1.0, 3.0), ((-2.0, 0.0), (0.0, -1.0)), np.nan, True, 0, 7.0)


# --------------------------- marker-initialization graph ---------------------------

def _plasma_provider(position):
    return {
        "plasma_rotation_cm_s": [0.0, 0.0, 0.0],
        "ion_temperature_kev": 2.0,
        "thermal_ion_density_cm3": [3.0, 5.0],
        "thermal_mass_amu": [1.0, 2.0],
    }


def _rate_provider(position, velocity):
    return [1.0, 2.0, 0.0, 0.0, 0.0, 0.0]


def _marker_inputs(**overrides):
    values = dict(
        cell_center_cm=[10.0, 0.0, 0.0], cell_width_cm=[2.0, 2.0, 2.0],
        uniform_draws=[0.5, 0.5, 0.5],
        plasma_state_provider=_plasma_provider,
        standard_normal_draw=[0.0, 0.0, 0.0],
        selected_thermal_species_index=1, beam_mass_amu=2.0,
        fast_ion_density_cm3=7.0, velocity_squared_to_kev_per_amu=1.0 / 1e12,
        cx_rate_provider=_rate_provider,
    )
    values.update(overrides)
    return values


def test_marker_graph_matches_the_saved_probe_flow():
    result = initialize_dcx_halo_marker(_marker_inputs())
    assert result["diagnostics"]["graph_order"] == [
        "cell_position", "local_plasma", "thermal_species_selection",
        "halo_velocity", "cx_rate", "initial_state"]
    # position is inside the declared cell (zero-mean affine draw at 0.5).
    np.testing.assert_allclose(result["guiding_center_position_cm"], [10.0, 0.0, 0.0], atol=1e-12)
    # zero rotation and zero normal draw give a zero halo velocity.
    np.testing.assert_allclose(result["halo_velocity_cm_s"], [0.0, 0.0, 0.0], atol=1e-12)
    # direct leaf equivalence for the initial state.
    expected = prepare_dcx_colrad_initial_state(
        cx_rate_per_s=result["cx_rate_per_s"], thermal_ion_density_cm3=[3.0, 5.0],
        thermal_mass_amu=[1.0, 2.0], selected_thermal_species_index=1,
        fast_ion_density_cm3=7.0, beam_mass_amu=2.0)
    assert result["eligible"] == expected["eligible"]
    np.testing.assert_allclose(result["initial_states"], expected["initial_states"], rtol=1e-15)
    assert math.isclose(result["photon_fast_ion_correction"],
                        expected["photon_fast_ion_correction"], rel_tol=1e-15)


def test_marker_graph_enforces_source_node_order():
    seen = []

    def recording_rate_provider(position, velocity):
        seen.append("cx_rate")
        return [1.0, 2.0]

    def recording_plasma_provider(position):
        seen.append("plasma")
        return _plasma_provider(position)

    initialize_dcx_halo_marker(_marker_inputs(
        plasma_state_provider=recording_plasma_provider, cx_rate_provider=recording_rate_provider))
    assert seen == ["plasma", "cx_rate"]


def test_marker_graph_rejects_bad_providers_and_inputs():
    with pytest.raises(ValueError, match="callable"):
        initialize_dcx_halo_marker(_marker_inputs(plasma_state_provider="not-callable"))
    with pytest.raises(ValueError, match="callable"):
        initialize_dcx_halo_marker(_marker_inputs(cx_rate_provider=None))
    with pytest.raises(ValueError, match="missing ion_temperature_kev"):
        initialize_dcx_halo_marker(_marker_inputs(
            plasma_state_provider=lambda position: {
                "plasma_rotation_cm_s": [0.0, 0.0, 0.0],
                "thermal_ion_density_cm3": [3.0], "thermal_mass_amu": [2.0]}))
    with pytest.raises(ValueError, match="finite nonnegative level-resolved"):
        initialize_dcx_halo_marker(_marker_inputs(cx_rate_provider=lambda position, velocity: [-1.0]))
    with pytest.raises(ValueError, match="cx_rate_provider"):
        initialize_dcx_halo_marker({key: value for key, value in _marker_inputs().items()
                                    if key != "cx_rate_provider"})
    with pytest.raises(ValueError):
        initialize_dcx_halo_marker(_marker_inputs(uniform_draws=[1.0, 0.5, 0.5]))

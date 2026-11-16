"""Independent evidence for the multi-coil vacuum field composition.

Asset: ``scirel.field.multi-coil-vacuum-field``.

The maintained tests cover the composition graph and a two-coil truth case.  This
file adds three things that composition tests cannot give themselves.

1. **An independent total field.**  The test builds the filament table from its own
   exact rational formula (the centres are ``r0 +- dr (nr - 1)/2`` and
   ``z0 +- dz (nz - 1)/2``), assigns each filament its current, and integrates the
   Biot-Savart law for the whole set with ``_biot_savart_reference``.  That total
   is then compared with the returned ``psi_vac``, ``b_r_vac`` and ``b_z_vac`` at
   every grid node.  Nothing in that path calls this asset, the rectangular-coil
   geometry asset, or the Green kernel, so a shared error in the composition chain
   cannot hide.
2. **The two current conventions, decided bitwise.**  With ``nr * nz`` filaments of
   unit weight, ``ampere_turns_a = nr * nz * J`` must produce *exactly* the same
   arrays as ``current_a = J``: the split divides by the weight sum, which is an
   exact integer here, and every downstream quantity is identical.  The equal
   arrays are the statement that the two keys differ only in bookkeeping.
3. **The documented unit trap, as a measurement.**  Passing the coil total as
   ``current_a`` instead multiplies the field by exactly ``nr * nz``, which the
   contract warns about in words; the test asserts the factor rather than trusting
   the warning.
4. **Exact power-of-two linearity** across the whole composition, and the
   coincidence guard with and without a drive current.

Budget: ``_RELATIVE_BUDGET = 64 eps`` from ``_biot_savart_reference``, the same
allowance the single-kernel assets use; the composition adds one concatenation and
one contraction per coil, well inside that.  The convention identities are exact
equalities.  The observed maximum on this grid is reported by the assertion
message; it is an observed maximum, not a proven bound.

Evidence ceiling: vacuum filament fields only.  Nothing here covers a finite
conductor cross-section, a permeable material, or a device-verified coil set.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import _biot_savart_reference as reference
from scirel._result import Result
from scirel.field import solve_multi_coil_vacuum_field

RELATIVE_BUDGET = reference._RELATIVE_BUDGET

RADIAL = np.array([0.0, 0.2, 0.35])
AXIAL = np.array([-0.3, 0.0, 0.3])

COILS = [
    {"r0_m": 0.45, "z0_m": -0.1, "nr": 2, "nz": 1, "dr_m": 0.1, "dz_m": 0.2, "current_a": 1000.0},
    {"r0_m": 0.55, "z0_m": 0.15, "nr": 1, "nz": 2, "dr_m": 0.2, "dz_m": 0.1, "current_a": -500.0},
]


def _grids():
    return np.meshgrid(RADIAL, AXIAL)


def _exact_filaments(coils):
    """Return the ``(R, Z, current)`` rows from the exact rational centres."""
    rows = []
    for coil in coils:
        radial = [
            Fraction(coil["r0_m"])
            + (Fraction(index) - Fraction(coil["nr"] - 1, 2)) * Fraction(coil["dr_m"])
            for index in range(coil["nr"])
        ]
        axial = [
            Fraction(coil["z0_m"])
            + (Fraction(index) - Fraction(coil["nz"] - 1, 2)) * Fraction(coil["dz_m"])
            for index in range(coil["nz"])
        ]
        drive = Fraction(coil.get("current_a", coil.get("ampere_turns_a")))
        if "ampere_turns_a" in coil:
            drive = drive / (coil["nr"] * coil["nz"])
        for radius in radial:
            for height in axial:
                rows.append((float(radius), float(height), float(drive)))
    return rows


def test_the_total_field_matches_the_biot_savart_quadrature_at_every_node():
    """Evidence 1: the composed field against an independent quadrature total."""
    radius, height = _grids()
    result = solve_multi_coil_vacuum_field(radius, height, COILS)
    filaments = _exact_filaments(COILS)
    # The returned table agrees with the independently computed one, so the
    # comparison below is about the field and not about the source list.
    assert result["filaments"].shape == (len(filaments), 3)
    assert [tuple(row) for row in result["filaments"][:, :2]] == [
        (row[0], row[1]) for row in filaments
    ]
    observed = 0.0
    for row in range(radius.shape[0]):
        for column in range(radius.shape[1]):
            expected = reference.filament_field(
                filaments, float(radius[row, column]), float(height[row, column])
            )
            for name, got_value, want in (
                ("psi_vac", float(result["psi_vac"][row, column]), float(expected[0])),
                ("b_r_vac", float(result["b_r_vac"][row, column]), float(expected[1])),
                ("b_z_vac", float(result["b_z_vac"][row, column]), float(expected[2])),
            ):
                if want == 0.0:
                    assert got_value == 0.0, (name, row, column)
                    continue
                deviation = abs(got_value - want) / abs(want)
                assert deviation <= RELATIVE_BUDGET, (name, row, column, deviation)
                observed = max(observed, deviation)
    assert observed > 0.0
    # Anchors: the two coils drive opposite signs, so the composed axial field
    # changes sign across the grid and is not merely a scaled copy of one coil.
    assert np.any(result["b_z_vac"] > 0.0) and np.any(result["b_z_vac"] < 0.0)


def test_the_two_current_keys_give_bitwise_identical_results():
    """Evidence 2: current_a = J equals ampere_turns_a = nr * nz * J."""
    per_filament = [dict(coil) for coil in COILS]
    totals = []
    for coil in COILS:
        total = dict(coil)
        del total["current_a"]
        total["ampere_turns_a"] = coil["current_a"] * coil["nr"] * coil["nz"]
        totals.append(total)
    radius, height = _grids()
    base = solve_multi_coil_vacuum_field(radius, height, per_filament)
    other = solve_multi_coil_vacuum_field(radius, height, totals)
    for name in ("psi_vac", "b_r_vac", "b_z_vac", "filaments"):
        np.testing.assert_array_equal(other[name], base[name]), name
    assert np.any(base["b_z_vac"] != 0.0)


def test_passing_the_coil_total_as_current_a_multiplies_the_field_by_the_filament_count():
    """Evidence 3: the documented unit trap, measured."""
    radius, height = _grids()
    base = solve_multi_coil_vacuum_field(radius, height, COILS)
    inflated = []
    for coil in COILS:
        inflated_coil = dict(coil)
        inflated_coil["current_a"] = coil["current_a"] * coil["nr"] * coil["nz"]
        inflated.append(inflated_coil)
    wrong = solve_multi_coil_vacuum_field(radius, height, inflated)
    for index, coil in enumerate(COILS):
        expected_factor = coil["nr"] * coil["nz"]
        # Fields are linear in the drive, so the ratio recovers the factor exactly
        # for the nodes this coil dominates only by construction; the reliable
        # statement is the composition identity below, checked node by node.
        del expected_factor
    # The total field of the inflated set is not a simple multiple of the total
    # field of the correct set, because the two coils are inflated by different
    # factors; assert each single-coil case separately instead.
    for coil in COILS:
        single = solve_multi_coil_vacuum_field(radius, height, [coil])
        inflated_coil = dict(coil)
        inflated_coil["current_a"] = coil["current_a"] * coil["nr"] * coil["nz"]
        scaled = solve_multi_coil_vacuum_field(radius, height, [inflated_coil])
        factor = float(coil["nr"] * coil["nz"])
        for name in ("psi_vac", "b_r_vac", "b_z_vac"):
            np.testing.assert_allclose(
                scaled[name], factor * single[name], rtol=8 * RELATIVE_BUDGET, atol=0.0
            )
        assert np.any(single["b_z_vac"] != 0.0)
    assert not np.array_equal(wrong["b_z_vac"], base["b_z_vac"])


def test_power_of_two_current_scaling_is_exact():
    """Evidence 4: exact linearity across the whole composition."""
    radius, height = _grids()
    base = solve_multi_coil_vacuum_field(radius, height, COILS)
    doubled_coils = []
    for coil in COILS:
        scaled = dict(coil)
        scaled["current_a"] = 2.0 * coil["current_a"]
        doubled_coils.append(scaled)
    doubled = solve_multi_coil_vacuum_field(radius, height, doubled_coils)
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        np.testing.assert_array_equal(doubled[name], 2.0 * base[name]), name
    # The filament table does not change, because it carries weights not currents.
    np.testing.assert_array_equal(doubled["filaments"], base["filaments"])


def test_the_named_result_keeps_its_declared_keys():
    """The mapping/attribute contract the asset promises."""
    radius, height = _grids()
    result = solve_multi_coil_vacuum_field(radius, height, COILS)
    assert isinstance(result, Result)
    assert list(result) == ["psi_vac", "b_r_vac", "b_z_vac", "filaments"]
    for name in ("psi_vac", "b_r_vac", "b_z_vac"):
        assert getattr(result, name) is result[name]
        assert result[name].shape == radius.shape
    assert result["filaments"].shape == (4, 3)


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    radius, height = _grids()
    good = [dict(coil) for coil in COILS]
    with pytest.raises(ValueError, match="equal-shape finite 2-D arrays"):
        solve_multi_coil_vacuum_field(radius, height[1:], good)
    with pytest.raises(ValueError, match="equal-shape finite 2-D arrays"):
        solve_multi_coil_vacuum_field(radius, np.full_like(height, np.nan), good)
    with pytest.raises(ValueError, match="nonempty 2-D arrays"):
        solve_multi_coil_vacuum_field(np.empty((0, 0)), np.empty((0, 0)), good)
    with pytest.raises(ValueError, match="strictly increasing rectilinear"):
        solve_multi_coil_vacuum_field(*np.meshgrid(RADIAL[::-1], AXIAL), good)
    with pytest.raises(ValueError, match="nonempty list of configuration mappings"):
        solve_multi_coil_vacuum_field(radius, height, [])
    with pytest.raises(ValueError, match="nonempty list of configuration mappings"):
        solve_multi_coil_vacuum_field(radius, height, {"current_a": 1.0})
    # A missing required key names the key.
    missing = dict(good[0])
    del missing["nr"]
    with pytest.raises(ValueError, match="misses nr"):
        solve_multi_coil_vacuum_field(radius, height, [missing])
    # Both current keys, or neither, is rejected.
    both = dict(good[0])
    both["ampere_turns_a"] = 1.0
    with pytest.raises(ValueError, match="exactly one of current_a"):
        solve_multi_coil_vacuum_field(radius, height, [both])
    neither = dict(good[0])
    del neither["current_a"]
    with pytest.raises(ValueError, match="exactly one of current_a"):
        solve_multi_coil_vacuum_field(radius, height, [neither])
    # A nonfinite current.
    bad_current = dict(good[0])
    bad_current["current_a"] = np.nan
    with pytest.raises(ValueError, match="must be finite"):
        solve_multi_coil_vacuum_field(radius, height, [bad_current])
    # Weights must be one finite value per filament.
    bad_weights = dict(good[0])
    bad_weights["weights"] = [1.0]
    with pytest.raises(ValueError, match="one value per filament"):
        solve_multi_coil_vacuum_field(radius, height, [bad_weights])
    # ampere_turns_a needs weights with a nonzero finite sum.
    zero_sum = dict(good[0])
    del zero_sum["current_a"]
    zero_sum["ampere_turns_a"] = 10.0
    zero_sum["weights"] = [1.0, -1.0]
    with pytest.raises(ValueError, match="nonzero finite sum"):
        solve_multi_coil_vacuum_field(radius, height, [zero_sum])
    # An active filament exactly on a grid node is rejected...
    coincident = [
        {"r0_m": 0.2, "z0_m": 0.0, "nr": 1, "nz": 1, "dr_m": 0.1, "dz_m": 0.1, "current_a": 1.0}
    ]
    with pytest.raises(ValueError, match="coincident with a target grid node"):
        solve_multi_coil_vacuum_field(radius, height, coincident)
    # ...but the same geometry with zero drive is accepted, so the guard is
    # about the active source and not about the coordinates.
    idle = [dict(coincident[0], current_a=0.0)]
    accepted = solve_multi_coil_vacuum_field(radius, height, idle)
    np.testing.assert_array_equal(accepted["b_z_vac"], 0.0)
    # Unknown keywords are a TypeError, not a silently ignored call.
    with pytest.raises(TypeError):
        solve_multi_coil_vacuum_field(radius, height, good, unknown_keyword=1)

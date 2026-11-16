"""Independent evidence for the mirror total-pressure assembly.

Asset: ``scirel.mirror.mirror-total-pressure``.

The maintained tests in ``test_mirror_total_pressure.py`` compare the assembled
pressures against a few hand-computed float sums and pin the failure paths.  A
float sum compared with a float sum is the same algorithm on both sides, so it
cannot decide a sign, a swapped component or a unit factor: a signed or scaled
assembly reproduces the same handful of expected numbers whenever the fixture
was derived from that assembly.

The evidence here is the exact-rational recomputation in
:mod:`fractions`.  The relation the contract states is pure addition of two
species pressures,

``p_parallel = p_parallel_ion + p_electron``,  ``p_perpendicular = p_perpendicular_ion + p_electron``,

so on dyadic inputs (sums of powers of two, exactly representable in binary64)
``Fraction`` gives the exact result and binary64 addition of those inputs is
also exact.  The comparison is therefore bitwise equality, not a tolerance.

Five statements, each of which a wrong implementation cannot pass:

1. **Exact component sums.**  Both assembled components equal the
   ``Fraction``-exact sum bit for bit, on a fixture whose ion parallel and
   perpendicular values differ and whose electron pressure is nonzero.  This
   rejects a subtraction, a swapped component, a component dropped altogether
   and any multiplicative unit factor.
2. **The zero-electron-pressure identity.**  With ``electron_pressure_pa = 0``
   the returned components are bitwise equal to the supplied ion components.
   Together with statement 1 this separates "adds nothing" from "adds the
   electron pressure" instead of accepting either.
3. **No unit conversion.**  Adding a pressure of ``1.0`` Pa raises both
   components by exactly ``1.0`` Pa; an implementation that scaled eV to Pa
   would move them by ``1.602176634e-19`` and an implementation working in
   keV would move them by ``1000``.  Both are far outside the exact assertion.
4. **Pass-through identity.**  The ion density object, the electron density
   object, the observational residual object and the optional potential are
   returned by object identity, and every unrecognised ion field survives.  The
   contract promises pass-through, so identity is the assertion, not equality.
5. **The one rounding the addition may cost.**  For non-dyadic binary64 inputs
   the exact ``Fraction`` sum is not representable, so the budget is one final
   rounding: ``|float(sum) - exact| <= 0.5 * eps * |exact|``.  This is the only
   tolerance in the file and it is derived from the operation, not measured.

Budgets, fixed before the comparison was run:

* statements 1, 2 and 4 are exact equalities and carry no budget at all;
* statement 5 uses ``_HALF_EPS = 2.220446049250313e-16 / 2``, the half-ULP
  rounding of one binary64 addition, and asserts the deviation is inside it for
  every component of a non-dyadic fixture.  No threshold was adjusted after
  observing a result.

Failure channels, one executable assertion each (contract ``failure_semantics``):

* ``invalid_input`` -- missing required fields, a nonbroadcastable shape, a
  nonfinite pressure, a negative species pressure and an unconvertible value all
  raise ``ValueError``.
* ``runtime_failure`` -- two finite pressures whose sum overflows raise
  ``FloatingPointError`` rather than returning ``inf``.
* ``partial_results`` -- no mapping is returned on any of those raises; the
  assertion is that the call raises, so a partially assembled mapping would have
  to escape ``pytest.raises`` to be observed.
* ``nonconvergence`` -- declared not applicable.  The assertion that remains
  executable is that the returned mapping carries no convergence or iteration
  field, so a caller cannot mistake this algebraic assembly for a solved state.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
import pytest

from scirel.mirror import assemble_mirror_total_pressure

# One binary64 addition rounds once: the largest error is half an ulp.
_HALF_EPS = math.ulp(1.0) / 2.0

# Dyadic fixture: every value is an exact binary64 number, so the exact rational
# sum is representable and the implementation's own addition is exact too.
ION_PARALLEL = [2.0, 3.5, 0.125]
ION_PERPENDICULAR = [4.25, 5.75, 1.5]
ELECTRON_PRESSURE = 1.5
ION_DENSITY = [1.0, 2.0, 0.25]
ELECTRON_DENSITY = [6.0, 7.5, 0.5]
RESIDUAL = [0.125, -0.25, 0.5]


def _dyadic_state():
    ion = {
        "p_parallel_pa": list(ION_PARALLEL),
        "p_perpendicular_pa": list(ION_PERPENDICULAR),
        "density_m3": np.array(ION_DENSITY),
        "marker": "ion-metadata",
    }
    electron = {
        "electron_density_m3": np.array(ELECTRON_DENSITY),
        "electron_pressure_pa": ELECTRON_PRESSURE,
        "relative_charge_residual": np.array(RESIDUAL),
    }
    return ion, electron


def test_both_components_equal_the_exact_rational_sum_bitwise():
    ion, electron = _dyadic_state()
    result = assemble_mirror_total_pressure(ion, electron)
    for name, ion_values in (
        ("p_parallel", ION_PARALLEL),
        ("p_perpendicular", ION_PERPENDICULAR),
    ):
        for index, (ion_value, returned) in enumerate(zip(ion_values, result[name], strict=True)):
            exact = Fraction(ion_value) + Fraction(ELECTRON_PRESSURE)
            assert returned == float(exact), (name, index, returned, float(exact))
            # The available double is the exact double; nothing was rounded.
            assert exact.denominator & (exact.denominator - 1) == 0


def test_zero_electron_pressure_returns_the_ion_components_exactly():
    ion, electron = _dyadic_state()
    electron["electron_pressure_pa"] = 0.0
    result = assemble_mirror_total_pressure(ion, electron)
    np.testing.assert_array_equal(result["p_parallel"], np.array(ION_PARALLEL))
    np.testing.assert_array_equal(result["p_perpendicular"], np.array(ION_PERPENDICULAR))
    # A vanished electron pressure is still a converted array of the common shape.
    assert result["electron_pressure"].shape == (3,)
    assert np.all(result["electron_pressure"] == 0.0)


def test_one_pascal_moves_both_components_by_exactly_one_pascal():
    ion, electron = _dyadic_state()
    base = assemble_mirror_total_pressure(ion, electron)
    for offset in (1.0, 8.0, 1024.0):
        electron_offset = dict(electron)
        electron_offset["electron_pressure_pa"] = ELECTRON_PRESSURE + offset
        moved = assemble_mirror_total_pressure(ion, electron_offset)
        for name in ("p_parallel", "p_perpendicular"):
            # Dyadic offsets keep the subtraction exact.
            np.testing.assert_array_equal(moved[name] - base[name], np.full(3, offset))


def test_pass_through_fields_retain_object_identity():
    ion, electron = _dyadic_state()
    result = assemble_mirror_total_pressure(ion, electron)
    assert result["ion_density"] is ion["density_m3"]
    assert result["electron_density"] is electron["electron_density_m3"]
    assert result["relative_charge_residual"] is electron["relative_charge_residual"]
    assert result["kinetic_moments"] is ion
    assert result["marker"] == "ion-metadata"
    assert result["electrostatic_potential"] is None

    potential = np.array([10.0, -10.0, 0.0])
    electron["electrostatic_potential"] = potential
    with_potential = assemble_mirror_total_pressure(ion, electron)
    assert with_potential["electrostatic_potential"] is potential
    np.testing.assert_array_equal(with_potential["p_parallel"], result["p_parallel"])


def test_a_non_dyadic_sum_stays_within_one_half_ulp_rounding():
    ion_values = [0.1, 1e-17, 12345.6789]
    perp_values = [2.718281828459045, 1e17, 6.02214076e-3]
    pressure = 0.3
    ion = {
        "p_parallel_pa": ion_values,
        "p_perpendicular_pa": perp_values,
        "density_m3": [1.0, 1.0, 1.0],
    }
    electron = {
        "electron_density_m3": [1.0, 1.0, 1.0],
        "electron_pressure_pa": pressure,
        "relative_charge_residual": 0.0,
    }
    result = assemble_mirror_total_pressure(ion, electron)
    for name, values in (("p_parallel", ion_values), ("p_perpendicular", perp_values)):
        for index, (ion_value, returned) in enumerate(zip(values, result[name], strict=True)):
            exact = Fraction(ion_value) + Fraction(pressure)
            deviation = abs(Fraction(returned) - exact)
            budget = _HALF_EPS * abs(exact)
            assert deviation <= budget, (name, index, float(deviation), float(budget))


def test_returned_mapping_carries_no_convergence_channel():
    # The contract declares nonconvergence "not applicable" because nothing is
    # iterated.  This asserts the other half of that claim: no field exists that
    # a caller could read as a solved or converged state.
    ion, electron = _dyadic_state()
    result = assemble_mirror_total_pressure(ion, electron)
    for forbidden in ("converged", "iterations", "residual", "status", "convergence"):
        assert forbidden not in result


def test_invalid_input_channel_raises_value_error():
    ion, electron = _dyadic_state()

    with pytest.raises(ValueError, match="kinetic_moments is missing required ion moment fields"):
        assemble_mirror_total_pressure({"p_parallel_pa": [1.0]}, electron)
    with pytest.raises(ValueError, match="electron_state is missing required electron fields"):
        assemble_mirror_total_pressure(ion, {"electron_pressure_pa": 1.0})

    nonfinite = _dyadic_state()
    nonfinite[0]["p_parallel_pa"] = [1.0, np.nan, 2.0]
    with pytest.raises(ValueError, match="pressure state must be finite"):
        assemble_mirror_total_pressure(*nonfinite)

    infinite = _dyadic_state()
    infinite[1]["electron_pressure_pa"] = np.inf
    with pytest.raises(ValueError, match="pressure state must be finite"):
        assemble_mirror_total_pressure(*infinite)

    negative = _dyadic_state()
    negative[0]["p_perpendicular_pa"] = [1.0, -1.0, 2.0]
    with pytest.raises(ValueError, match="species pressures must be nonnegative"):
        assemble_mirror_total_pressure(*negative)

    negative_density = _dyadic_state()
    negative_density[0]["density_m3"] = [1.0, -1.0, 2.0]
    with pytest.raises(ValueError, match="ion density must be finite and nonnegative"):
        assemble_mirror_total_pressure(*negative_density)

    # A density that cannot broadcast is rejected by the common-shape step, so
    # the channel is ValueError even though the message is NumPy's.
    unmatchable = _dyadic_state()
    unmatchable[0]["density_m3"] = [1.0, 2.0]
    with pytest.raises(ValueError, match="shape mismatch|cannot be broadcast"):
        assemble_mirror_total_pressure(*unmatchable)

    unconvertible = _dyadic_state()
    unconvertible[0]["p_parallel_pa"] = ["a", "b", "c"]
    with pytest.raises((TypeError, ValueError)):
        assemble_mirror_total_pressure(*unconvertible)


def test_runtime_failure_channel_raises_floating_point_error():
    # Both species pressures are finite; only their sum leaves the finite range.
    big = np.finfo(float).max
    ion = {
        "p_parallel_pa": [big],
        "p_perpendicular_pa": [big],
        "density_m3": [1.0],
    }
    electron = {
        "electron_density_m3": [1.0],
        "electron_pressure_pa": big,
        "relative_charge_residual": 0.0,
    }
    with pytest.raises(FloatingPointError, match="exceeds the finite output range"):
        assemble_mirror_total_pressure(ion, electron)

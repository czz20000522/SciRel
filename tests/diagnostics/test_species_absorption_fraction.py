"""Direct contract tests for SciRel's species absorption fraction relation."""
from __future__ import annotations

import importlib
import math

import numpy as np
import pytest

MODULE = importlib.import_module("scirel.diagnostics.species_absorption_fraction")
COMPUTE = MODULE.compute_species_absorption_fraction

# --- Test U3-T01: the closure follows its documented arithmetic. ---------------
@pytest.mark.parametrize(
    "ledger",
    [
        [1.0, 2.0, 3.0, 4.0],
        [4.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 7.5],
        [-1.0, 2.5, 0.0, 0.5],
        [-1.0, 2.0, 3.0, 0.5],
        [1.0e-12, 2.0e-12, 3.0e-12, 4.0e-12],
        [1.0e12, 2.0e12, 3.0e12, 4.0e12],
        [0.1, 0.2, 0.30000000000000004, 0.4],
        [np.float32(1.0), np.float32(2.0), np.float32(3.0), np.float32(4.0)],
    ],
)
def test_u3_t01_fraction_uses_the_derived_total(ledger):
    result = COMPUTE(ledger)
    values = np.asarray(ledger, dtype=float)
    total = float(np.sum(values, dtype=float))
    fractions = values / total * 100.0
    assert result["branch"] == "nonzero_total"
    assert result["total_power"] == total
    np.testing.assert_array_equal(result["species_fraction_percent"], fractions)
    assert result["total_fraction_percent"] == float(np.sum(fractions, dtype=float))
    assert result["fraction_sum_residual_percent"] == result["total_fraction_percent"] - 100.0


# --- Test U3-T02: the closure is source-ordered and sums to 100 percent. -------
def test_u3_t02_closure_is_source_ordered_and_complete():
    result = COMPUTE([1.0, 2.0, 3.0, 4.0])
    np.testing.assert_allclose(result["species_fraction_percent"], [10.0, 20.0, 30.0, 40.0], rtol=0.0, atol=1e-12)
    assert result["total_power"] == 10.0
    assert result["total_fraction_percent"] == pytest.approx(100.0, rel=0.0, abs=1e-12)
    assert result["fraction_sum_residual_percent"] == pytest.approx(0.0, rel=0.0, abs=1e-12)
    assert result["branch"] == "nonzero_total"


# --- Test U3-T03: a single non-zero species gets the whole split. -------------
@pytest.mark.parametrize("index", [0, 1, 2, 3])
def test_u3_t03_single_nonzero_species_absorbs_everything(index):
    ledger = [0.0, 0.0, 0.0, 0.0]
    ledger[index] = 7.5
    result = COMPUTE(ledger)
    expected = np.zeros(4)
    expected[index] = 100.0
    np.testing.assert_allclose(result["species_fraction_percent"], expected, rtol=0.0, atol=0.0)
    assert result["total_power"] == 7.5


# --- Test U3-T04: the zero-total boundary fails closed. -----------------------
def test_u3_t04_zero_total_fails_closed():
    with pytest.raises(ValueError, match="zero total_power"):
        COMPUTE([0.0, 0.0, 0.0, 0.0])


# --- Test U3-T05: the zero-total boundary is exact, not a tolerance test. ----
def test_u3_t05_zero_total_boundary_is_exact_and_signed_cancellation_is_rejected():
    with pytest.raises(ValueError, match="zero total_power"):
        COMPUTE([1.0, -1.0, 2.0, -2.0])
    # Cancellation to a non-zero but tiny total is a legal ledger.
    result = COMPUTE([1.0, -1.0, 0.0, 1.0e-30])
    assert result["total_power"] == pytest.approx(1.0e-30, rel=1e-9)


# --- Test U3-T06: negative ledgers are computed, not silently repaired. ------
def test_u3_t06_negative_ledgers_are_reported_not_repaired():
    result = COMPUTE([-1.0, 2.0, 3.0, 0.5])
    assert result["total_power"] == 4.5
    np.testing.assert_allclose(
        result["species_fraction_percent"], [-200.0 / 9.0, 400.0 / 9.0, 600.0 / 9.0, 100.0 / 9.0], rtol=1e-13
    )
    assert result["total_fraction_percent"] == pytest.approx(100.0, rel=0.0, abs=1e-12)


# --- Test U3-T07: ledger validation is fail-closed. ---------------------------
@pytest.mark.parametrize(
    "ledger, message",
    [
        ([1.0, 2.0, 3.0], "length-four vector"),
        ([1.0, 2.0, 3.0, 4.0, 5.0], "length-four vector"),
        (1.0, "length-four vector"),
        ([[1.0, 2.0], [3.0, 4.0]], "length-four vector"),
        ([1.0, 2.0, 3.0, 4.0j], "real-valued and non-boolean"),
        (np.array([1.0, 2.0, 3.0, True], dtype=bool), "real-valued and non-boolean"),
        (["1.0", "2.0", "3.0", "4.0"], "real-valued and non-boolean"),
        ([1.0, 2.0, 3.0, np.nan], "must be finite"),
        ([1.0, 2.0, 3.0, np.inf], "must be finite"),
        ([1.0, 2.0, 3.0, None], "must be finite"),
        ([1.0, 2.0, 3.0, object()], "must be numeric"),
    ],
)
def test_u3_t07_ledger_validation_is_fail_closed(ledger, message):
    with pytest.raises(ValueError, match=message):
        COMPUTE(ledger)


# --- Test U3-T08: the relation exposes one public callable. ------------------
def test_u3_t08_relation_exposes_one_public_callable():
    assert MODULE.__all__ == ["compute_species_absorption_fraction"]


# --- Test U3-T09: the residual is the reported sum minus 100, not a rerun. ---
def test_u3_t09_residual_is_consistent_with_the_reported_sum():
    result = COMPUTE([1.0, 2.0, 3.0, 4.0])
    assert result["fraction_sum_residual_percent"] == result["total_fraction_percent"] - 100.0
    assert math.isclose(
        float(np.sum(result["species_fraction_percent"])),
        result["total_fraction_percent"],
        rel_tol=0.0,
        abs_tol=0.0,
    )

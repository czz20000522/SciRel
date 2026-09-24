"""Direct contract tests for the U3 merged species absorption fraction relation.

The observed source carries two byte-different implementations of the same
closure.  The discriminating question for a merge is therefore not "does the new
code run" but "does one merged identity reproduce *both* source routes exactly".
These tests load all three modules -- the candidate plus both observed routes --
side by side and compare them on identical ledgers.

The observed routes live in a read-only L1 checkout outside this repository, so
they are located through ``SCIREL_L1_AORSA3D`` or a small set of conventional
paths.  When they cannot be found the comparison tests skip loudly rather than
silently passing; the self-contained contract tests still run either way, and
``evidence/u3-observed-route-comparison.json`` records the comparison that was
actually executed for this review.
"""
from __future__ import annotations

import importlib
import importlib.util
import math
import os
from pathlib import Path

import numpy as np
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANDIDATE = Path(
    importlib.import_module(
        "scirel.diagnostics.species_absorption_fraction"
    ).__file__
).resolve() if os.environ.get("SCIREL_INSTALLED_RUNTIME") == "1" else (
    Path(__file__).resolve().parents[2]
    / "src/scirel/diagnostics/species_absorption_fraction.py"
)
_ROUTE_NAMES = {
    "estardotj": ("AORSA E-star-dot-J物种吸收占比", "compute_aorsa_estardotj_species_fractions"),
    "wdot": ("AORSA Wdot物种吸收占比", "compute_aorsa_wdot_species_fractions"),
}
_L1_CANDIDATES = (
    os.environ.get("SCIREL_L1_AORSA3D"),
    r"D:\Users\26569\Desktop\归档_项目\codefusion\最小闭环压测环境\aorsa3d",
    str(_REPO_ROOT.parent / "aorsa3d"),
    str(_REPO_ROOT / "build" / "l1" / "aorsa3d"),
)


def _l1_root() -> Path | None:
    for raw in _L1_CANDIDATES:
        if not raw:
            continue
        candidate = Path(raw)
        if all((candidate / "operators" / name).is_dir() for name, _ in _ROUTE_NAMES.values()):
            return candidate
    return None


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = _load(_CANDIDATE, "scirel_candidate_u3_species_absorption_fraction")
COMPUTE = MODULE.compute_species_absorption_fraction

_L1_ROOT = _l1_root()
OBSERVED = {}
OBSERVED_PATHS = {}
if _L1_ROOT is not None:
    for route, (directory, symbol) in _ROUTE_NAMES.items():
        path = _L1_ROOT / "operators" / directory / "scientific_operator.py"
        OBSERVED[route] = getattr(_load(path, f"scirel_observed_u3_{route}"), symbol)
        OBSERVED_PATHS[route] = path

_NEEDS_OBSERVED = pytest.mark.skipif(
    not OBSERVED, reason="read-only L1 aorsa3d checkout not found; set SCIREL_L1_AORSA3D"
)


@_NEEDS_OBSERVED
def test_u3_t00_the_two_observed_routes_are_present_and_distinct_files():
    """Guard: the merge claim is only meaningful if both routes really exist."""
    assert OBSERVED, "the observed-route comparison could not be loaded"
    assert set(OBSERVED) == {"estardotj", "wdot"}
    assert OBSERVED_PATHS["estardotj"].read_bytes() != OBSERVED_PATHS["wdot"].read_bytes()


# --- Test U3-T01: the merged identity reproduces both observed routes. ---------
@_NEEDS_OBSERVED
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
def test_u3_t01_merged_identity_reproduces_both_observed_routes(ledger):
    candidate = COMPUTE(ledger)
    for route, function in OBSERVED.items():
        observed = function(ledger)
        assert set(candidate) == set(observed), route
        assert candidate["branch"] == observed["branch"] == "nonzero_total", route
        assert candidate["total_power"] == observed["total_power"], route
        assert candidate["total_fraction_percent"] == observed["total_fraction_percent"], route
        assert (
            candidate["fraction_sum_residual_percent"]
            == observed["fraction_sum_residual_percent"]
        ), route
        np.testing.assert_array_equal(
            candidate["species_fraction_percent"], observed["species_fraction_percent"], err_msg=route
        )


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


# --- Test U3-T04: the zero-total boundary fails closed on every route. -------
@_NEEDS_OBSERVED
def test_u3_t04_zero_total_fails_closed_on_all_routes():
    with pytest.raises(ValueError, match="zero total_power"):
        COMPUTE([0.0, 0.0, 0.0, 0.0])
    for route, function in OBSERVED.items():
        with pytest.raises(ValueError, match="zero total_power"):
            function([0.0, 0.0, 0.0, 0.0])


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


# --- Test U3-T07: ledger validation is fail-closed and route-independent. ----
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
@_NEEDS_OBSERVED
def test_u3_t07_ledger_validation_is_fail_closed(ledger, message):
    with pytest.raises(ValueError, match=message):
        COMPUTE(ledger)
    for route, function in OBSERVED.items():
        with pytest.raises(ValueError, match=message):
            function(ledger)


# --- Test U3-T08: the merge must not keep two competing public callables. ----
def test_u3_t08_merge_exposes_exactly_one_public_callable():
    assert MODULE.__all__ == ["compute_species_absorption_fraction"]
    assert not hasattr(MODULE, "compute_aorsa_estardotj_species_fractions")
    assert not hasattr(MODULE, "compute_aorsa_wdot_species_fractions")
    source = _CANDIDATE.read_text(encoding="utf-8")
    assert "estardotj" not in source.replace("E-star-dot-J", "")


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

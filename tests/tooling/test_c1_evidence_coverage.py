"""Guards for the C1 evidence-coverage report.

The report exists so the closeout count can be reproduced instead of quoted.  A
report that overstates is worse than no report, so the tests pin the direction
that matters: a contract saying "no independent implementation exists" must not
count as evidence, while a genuine basis claim still must.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "c1_evidence_coverage.py"

specification = importlib.util.spec_from_file_location("c1_evidence_coverage", SCRIPT)
coverage = importlib.util.module_from_spec(specification)
specification.loader.exec_module(coverage)


def test_a_negated_basis_claim_counts_as_a_gap_not_as_evidence() -> None:
    # A contract may say the opposite of "an independent source exists"; that is
    # a recorded absence, and counting it as basis inflates the closeout number.
    for sentence in (
        "No independent implementation exists for this relation.",
        "There is not an independent reference for these values.",
        "No closed-form solution exists; only the observed behaviour is described.",
        "Fraction arithmetic is not used here.",
    ):
        basis, gap = coverage.classify(sentence)
        assert basis is False, sentence
        assert gap is True, sentence


def test_a_genuine_basis_claim_still_counts_as_evidence() -> None:
    # The positive control: without this, the negation rule could silence every
    # contract and the report would look reassuringly empty.
    for sentence in (
        "An independent 40-digit mpmath recomputation agrees.",
        "The exact rational recomputation matches.",
        "Fraction arithmetic gives the exact answer, not the rounded one.",
        "An analytic identity fixes the value.",
        # A negation in an earlier clause must not swallow a later basis claim;
        # "and"/"while" are clause boundaries for exactly this reason.
        "The implementation does not model damping and an independent reference agrees.",
    ):
        basis, gap = coverage.classify(sentence)
        assert basis is True, sentence


def test_the_reported_totals_are_derived_from_the_tracked_contracts() -> None:
    completed = subprocess.run(
        [sys.executable, "-B", str(SCRIPT), "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert completed.returncode == 0, (
        f"coverage script failed with {completed.returncode}: {completed.stderr!r}"
    )
    payload = json.loads(completed.stdout)
    totals = payload["totals"]
    assert totals["contracts"] == len(payload["rows"])
    assert totals["either"] + totals["neither"] == totals["contracts"]
    assert totals["basis"] + totals["gap"] >= totals["either"]
    assert payload["gate"] is False
    assert "not a gate" in payload["note"]
    assert payload["neither"] == [
        row["asset_id"] for row in payload["rows"] if not row["basis"] and not row["gap"]
    ]


def test_the_report_does_not_fail_by_default_but_can_be_asked_to(
    tmp_path: Path, monkeypatch
) -> None:
    # The report is not a gate: outstanding gaps must not turn unrelated runs red.
    default = subprocess.run(
        [sys.executable, "-B", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert default.returncode == 0
    assert "NOTE: Text match only, not a gate." in default.stdout

    # The strict flag is driven against a synthetic catalog, not against "the real catalog happens to
    # contain a neither contract".  Pinning the real catalog's gap count here made this guard decay
    # into an assertion about a data state: once the C1 batch named a basis for the last four
    # contracts, `--fail-on-neither` correctly returned 0 and this test failed while the flag itself
    # was still working.
    catalog = tmp_path / "catalog" / "examples"
    catalog.mkdir(parents=True)
    silent = {
        "asset_id": "scirel.test.silent",
        "verification": {
            "scope": ["Observed behaviour only."],
            "evidence_ceiling": "Bounded to observed behaviour.",
            "known_limitations": ["Nothing is claimed."],
        },
    }
    (catalog / "scirel.test.silent.json").write_text(
        json.dumps(silent, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(coverage, "ROOT", tmp_path)

    monkeypatch.setattr(sys, "argv", ["c1_evidence_coverage.py", "--fail-on-neither"])
    assert coverage.main() == 1
    monkeypatch.setattr(sys, "argv", ["c1_evidence_coverage.py"])
    assert coverage.main() == 0

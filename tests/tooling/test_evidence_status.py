"""`evidence_status` reports what a contract says; it must not upgrade a gap to proof.

Two failure modes matter here:

* reporting `gap` as if the capability were verified -- the whole point of the word;
* reporting `gap` as if no evidence existed -- it only means the recogniser did not
  find a phrase it knows, and 106 assets carry wording it does not know.

The second is why the record carries `weak_basis_phrases`: a reader gets a lead,
not a verdict.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import evidence_status  # noqa: E402


def _contract(root: Path, asset: str, scope: list[str], ceiling: str = "") -> None:
    directory = root / evidence_status.CATALOG
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{asset}.json").write_text(
        json.dumps(
            {
                "asset_id": asset,
                "verification": {
                    "scope": scope,
                    "known_limitations": [],
                    "evidence_ceiling": ceiling,
                },
            }
        ),
        encoding="utf-8",
    )


def test_a_recognised_basis_phrase_is_reported_as_basis(tmp_path):
    _contract(
        tmp_path,
        "scirel.x.independent",
        ["Checked against an independent high-precision reference."],
    )
    record = evidence_status.describe("scirel.x.independent", tmp_path)
    assert record["state"] == "basis"
    assert "not an audit" in record["verdict"]


def test_a_recorded_ceiling_is_reported_as_gap_and_never_as_proof(tmp_path):
    _contract(
        tmp_path,
        "scirel.x.ceiling",
        ["Fit reproduces the table."],
        ceiling="cannot establish beyond 20 keV",
    )
    record = evidence_status.describe("scirel.x.ceiling", tmp_path)
    assert record["state"] == "gap"
    assert "NOT proof" in record["verdict"]


def test_unrecognised_basis_wording_becomes_a_lead_not_a_verdict(tmp_path):
    """The text asserts a comparison in words the recogniser does not know."""
    _contract(tmp_path, "scirel.x.weak", ["Compared with independent Gauss-Legendre quadrature."])
    record = evidence_status.describe("scirel.x.weak", tmp_path)
    # No gap phrase either, so the label is `neither`: nothing in the recogniser fired.
    assert record["state"] == "neither", "the phrase list does not know this wording"
    assert record["weak_basis_phrases"], "the reader must still be told where to look"


def test_negated_basis_wording_is_not_reported_as_a_lead(tmp_path):
    _contract(tmp_path, "scirel.x.negated", ["No independent comparison was performed."])
    record = evidence_status.describe("scirel.x.negated", tmp_path)
    assert record["weak_basis_phrases"] == []


def test_an_unknown_asset_is_unobserved_not_a_pass(tmp_path):
    assert evidence_status.main(["--asset", "scirel.x.missing", "--root", str(tmp_path)]) == 2


def test_the_repository_scans_without_crashing():
    """The scan must run on the real catalog; its count is a lead, so it is not pinned."""
    assert evidence_status.main(["--scan-weak-basis", "--root", str(ROOT)]) == 0

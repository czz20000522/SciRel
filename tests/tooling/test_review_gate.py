"""Every catalog asset has an explicit admission verdict; exposure is gated."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import review_gate


def test_audit_verdict_gate_passes():
    assert review_gate.check() == []


def test_held_assets_are_not_exposed():
    hold = json.loads((ROOT / "catalog" / "review" / "HOLD.json").read_text())
    verdicts = json.loads((ROOT / "catalog" / "review" / "VERDICTS.json").read_text())
    for asset in hold["assets"]:
        assert verdicts["assets"][asset]["status"] == "human-review"


@pytest.fixture
def verdict_fixture(tmp_path, monkeypatch):
    catalog = tmp_path / "catalog" / "examples"
    catalog.mkdir(parents=True)
    (catalog / "scirel.test.asset.json").write_text("{}")
    review = tmp_path / "catalog" / "review"
    review.mkdir()
    hold = review / "HOLD.json"
    hold.write_text(json.dumps({"schema": "scirel.exposure-hold", "assets": {}}))
    evidence = review / "evidence.md"
    evidence.write_text("Bounded retained evidence.\n")
    verdicts = review / "VERDICTS.json"
    data = {"schema": "scirel.audit-verdicts", "assets": {"scirel.test.asset": {
        "status": "pass-with-limits",
        "evidence": [{"report": "catalog/review/evidence.md", "verdict": "pass-with-limits"}],
    }}}
    monkeypatch.setattr(review_gate, "ROOT", tmp_path)
    monkeypatch.setattr(review_gate, "HOLD", hold)
    monkeypatch.setattr(review_gate, "VERDICTS", verdicts)
    monkeypatch.setattr(review_gate, "CATALOG", catalog)
    monkeypatch.setattr(review_gate, "REVIEW_CATALOG", review / "examples")
    return verdicts, data


def test_gate_accepts_a_resolvable_evidence_reference(verdict_fixture):
    path, data = verdict_fixture
    path.write_text(json.dumps(data))
    assert review_gate.check() == []


@pytest.mark.parametrize("report", [
    "catalog/review/missing.md",
    "catalog/review/evidence.md + missing.md",
    "../external-evidence.md",
    "/tmp/external-evidence.md",
    "",
    ["catalog/review/evidence.md"],
])
def test_gate_rejects_missing_or_invalid_evidence_paths(verdict_fixture, report):
    path, data = verdict_fixture
    data["assets"]["scirel.test.asset"]["evidence"][0]["report"] = report
    path.write_text(json.dumps(data))
    errors = review_gate.check()
    assert errors
    assert any("scirel.test.asset" in error and "evidence report" in error for error in errors)


def test_gate_rejects_a_verdict_without_evidence(verdict_fixture):
    path, data = verdict_fixture
    data["assets"]["scirel.test.asset"]["evidence"] = []
    path.write_text(json.dumps(data))
    assert any("evidence must be a nonempty array" in error for error in review_gate.check())

"""The review gate binds registry structure and nothing outside the repository."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import review_gate  # noqa: E402

EXPOSED = "scirel.test.exposed"
HELD = "scirel.test.held"
HOLD_RECORD = {"status": "human-review", "reason": "why", "required_decision": "what"}


@pytest.fixture
def registry(tmp_path, monkeypatch):
    catalog = tmp_path / "examples"
    review = tmp_path / "review"
    catalog.mkdir()
    review.mkdir()
    (catalog / f"{EXPOSED}.json").write_text("{}")
    (review / f"{HELD}.json").write_text("{}")
    hold = {"schema": "scirel.exposure-hold", "assets": {HELD: HOLD_RECORD}}
    verdicts = {
        "schema": "scirel.audit-verdicts",
        "assets": {EXPOSED: {"status": "pass"}, HELD: dict(HOLD_RECORD)},
    }
    monkeypatch.setattr(review_gate, "CATALOG", catalog)
    monkeypatch.setattr(review_gate, "REVIEW_CATALOG", review)
    monkeypatch.setattr(review_gate, "HOLD", tmp_path / "hold.json")
    monkeypatch.setattr(review_gate, "VERDICTS", tmp_path / "verdicts.json")

    def write(hold_data=hold, verdict_data=verdicts):
        (tmp_path / "hold.json").write_text(json.dumps(hold_data))
        (tmp_path / "verdicts.json").write_text(json.dumps(verdict_data))

    write()
    return write, hold, verdicts, catalog, review


def test_repository_registry_passes_the_gate():
    assert review_gate.check() == []


def test_held_assets_are_absent_from_the_exposed_catalog():
    hold = json.loads((ROOT / "catalog/review/HOLD.json").read_text(encoding="utf-8"))
    verdicts = json.loads((ROOT / "catalog/review/VERDICTS.json").read_text(encoding="utf-8"))
    for asset in hold["assets"]:
        assert verdicts["assets"][asset]["status"] == "human-review"
        assert not (ROOT / "catalog/examples" / f"{asset}.json").exists()
        assert (ROOT / "catalog/review/examples" / f"{asset}.json").exists()


def test_consistent_fixture_passes(registry):
    assert review_gate.check() == []


def test_contract_without_status_fails(registry):
    write, hold, verdicts, catalog, _ = registry
    (catalog / "scirel.test.new.json").write_text("{}")
    assert any("without a status" in error for error in review_gate.check())


def test_status_without_contract_fails(registry):
    write, hold, verdicts, *_ = registry
    write(
        verdict_data={
            **verdicts,
            "assets": {**verdicts["assets"], "scirel.test.gone": {"status": "pass"}},
        }
    )
    assert any("without a contract" in error for error in review_gate.check())


@pytest.mark.parametrize("status", ["human-review", "blocked", "not-audited", None])
def test_exposed_asset_needs_a_release_status(registry, status):
    write, hold, verdicts, *_ = registry
    write(verdict_data={**verdicts, "assets": {**verdicts["assets"], EXPOSED: {"status": status}}})
    assert any("non-release status" in error for error in review_gate.check())


def test_held_asset_cannot_be_marked_as_passing(registry):
    write, hold, verdicts, *_ = registry
    write(
        verdict_data={
            **verdicts,
            "assets": {**verdicts["assets"], HELD: {**HOLD_RECORD, "status": "pass"}},
        }
    )
    assert any("held asset must be" in error for error in review_gate.check())


def test_held_asset_needs_a_reason_and_decision(registry):
    write, hold, verdicts, *_ = registry
    write(
        verdict_data={
            **verdicts,
            "assets": {**verdicts["assets"], HELD: {"status": "human-review"}},
        }
    )
    assert any("needs reason" in error for error in review_gate.check())


def test_held_asset_cannot_stay_in_the_exposed_catalog(registry):
    _, _, _, catalog, _ = registry
    (catalog / f"{HELD}.json").write_text("{}")
    errors = review_gate.check()
    assert any("both exposed and in review" in error for error in errors)
    assert any("still exposed" in error for error in errors)


def test_review_contract_must_be_listed_in_the_hold(registry):
    _, _, _, _, review = registry
    (review / "scirel.test.unlisted.json").write_text("{}")
    assert any("missing from HOLD.json" in error for error in review_gate.check())


def test_unrecognized_record_fields_are_rejected(registry):
    write, hold, verdicts, *_ = registry
    write(
        verdict_data={
            **verdicts,
            "assets": {**verdicts["assets"], EXPOSED: {"status": "pass", "evidence": []}},
        }
    )
    assert any("record fields" in error for error in review_gate.check())


def test_malformed_registry_fails_closed(registry):
    write, hold, verdicts, *_ = registry
    write(verdict_data={"schema": "other", "assets": {}})
    assert review_gate.check() == ["invalid verdict schema/assets"]


def test_cli_reports_pass_and_failure(registry, capsys):
    assert review_gate.main([]) == 0
    assert "PASS" in capsys.readouterr().out
    write, hold, verdicts, *_ = registry
    write(verdict_data={"schema": "scirel.audit-verdicts", "assets": {}})
    assert review_gate.main([]) == 1
    assert "ERROR" in capsys.readouterr().out

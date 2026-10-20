"""Receiver-side disposition review records (existing / partial / new)."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_disposition", ROOT / "scripts" / "validate_disposition.py")
disposition = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(disposition)


def _review(**overrides):
    review = {
        "schema": "scirel.disposition-review",
        "schema_version": "1.0",
        "package": {"package_id": "acme-d3", "payload_digest": "a" * 64, "layer": "d3"},
        "reviewer_role": "integration-reviewer",
        "decision_ceiling": "review record only; no automatic merge, endorsement or release",
        "summary": {"existing": 1, "partial": 1, "new": 1},
        "dispositions": [
            {"incoming_asset_id": "acme.cap.a", "disposition": "existing",
             "matched_asset_ids": ["scirel.field.cap-a"], "overlap": "same relation",
             "differences": [], "required_changes": [], "evidence": ["contract diff"],
             "notes": "already covered"},
            {"incoming_asset_id": "acme.cap.b", "disposition": "partial",
             "matched_asset_ids": ["scirel.field.cap-b"], "overlap": "same kernel, different ports",
             "differences": ["units"], "required_changes": ["widen port units"],
             "evidence": ["numeric comparison"], "notes": "merge into existing"},
            {"incoming_asset_id": "acme.cap.c", "disposition": "new",
             "matched_asset_ids": [], "overlap": "no counterpart",
             "differences": [], "required_changes": ["rename", "add contract", "add tests"],
             "evidence": ["catalog search"], "notes": "import as new asset"},
        ],
    }
    review.update(overrides)
    return review


def test_valid_disposition_review_passes():
    result = disposition.validate_review(_review())
    assert result["status"] == "PASS", result["errors"]


def test_existing_requires_match_and_new_forbids_match():
    review = _review()
    review["dispositions"][0]["matched_asset_ids"] = []
    review["dispositions"][2]["matched_asset_ids"] = ["scirel.field.cap-a"]
    result = disposition.validate_review(review)
    assert result["status"] == "FAIL"
    assert any("existing requires" in e for e in result["errors"])
    assert any("new requires" in e for e in result["errors"])


def test_summary_must_match_dispositions():
    review = _review()
    review["summary"] = {"existing": 3, "partial": 0, "new": 0}
    result = disposition.validate_review(review)
    assert result["status"] == "FAIL"
    assert any("summary.existing" in e for e in result["errors"])


def test_review_binds_to_d3_package(tmp_path):
    package = tmp_path / "d3"
    package.mkdir()
    manifest = {
        "package_id": "acme-d3",
        "payload_digest": "b" * 64,
        "delivery": {"assets": [{"asset_id": "acme.cap.a"},
                                {"asset_id": "acme.cap.b"},
                                {"asset_id": "acme.cap.c"}]},
    }
    (package / "handoff.json").write_text(json.dumps(manifest))
    result = disposition.validate_review(_review(), package_dir=package)
    assert result["status"] == "FAIL"
    assert any("payload_digest" in e for e in result["errors"])
    review = _review()
    review["package"]["payload_digest"] = "b" * 64
    result = disposition.validate_review(review, package_dir=package)
    assert result["status"] == "PASS", result["errors"]

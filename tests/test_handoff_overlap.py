"""Overlap records state catalog overlap only; they carry no merge decision."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_overlap_record", ROOT / "scripts" / "validate_overlap_record.py")
overlap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(overlap)


def _record():
    return {
        "schema": "scirel.overlap-record",
        "schema_version": "1.0",
        "records": [
            {"incoming_capability_id": "acme.cap.a", "overlap": "same-relation",
             "matched_asset_ids": ["scirel.field.cap-a"],
             "difference_note": "same relation; naming and load wording differ",
             "evidence": ["contract and numeric comparison"]},
            {"incoming_capability_id": "acme.cap.b", "overlap": "wider-coverage",
             "matched_asset_ids": ["scirel.field.cap-b"],
             "difference_note": "adds a boundary case; coverage only, no merge decision"},
            {"incoming_capability_id": "acme.cap.c", "overlap": "none",
             "matched_asset_ids": [],
             "difference_note": "no counterpart in the current catalog"},
        ],
    }


def test_valid_overlap_record_passes():
    result = overlap.validate_record(_record())
    assert result["status"] == "PASS", result["errors"]


def test_none_requires_no_matches():
    payload = _record()
    payload["records"][2]["matched_asset_ids"] = ["scirel.field.cap-a"]
    result = overlap.validate_record(payload)
    assert result["status"] == "FAIL"
    assert any("overlap=none" in error for error in result["errors"])


def test_overlap_requires_matches():
    payload = _record()
    payload["records"][0]["matched_asset_ids"] = []
    result = overlap.validate_record(payload)
    assert result["status"] == "FAIL"
    assert any("same-relation" in error for error in result["errors"])


def test_duplicate_incoming_ids_rejected():
    payload = _record()
    payload["records"][1]["incoming_capability_id"] = payload["records"][0]["incoming_capability_id"]
    result = overlap.validate_record(payload)
    assert result["status"] == "FAIL"
    assert any("duplicate" in error for error in result["errors"])


def test_unknown_overlap_rejected():
    payload = _record()
    payload["records"][0]["overlap"] = "partial"
    result = overlap.validate_record(payload)
    assert result["status"] == "FAIL"

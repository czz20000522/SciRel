"""Reception overlap records state overlap only; they carry no merge decision."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validate_overlap_record", ROOT / "scripts" / "validate_overlap_record.py"
)
overlap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(overlap)


def _record():
    return {
        "schema": "scirel.overlap-record",
        "records": [
            {
                "incoming_capability_id": "acme.cap.a",
                "overlap": "same-relation",
                "matched_asset_ids": ["scirel.field.cap-a"],
                "difference_note": "same relation; naming differs",
            },
            {
                "incoming_capability_id": "acme.cap.b",
                "overlap": "wider-coverage",
                "matched_asset_ids": ["scirel.field.cap-b"],
                "difference_note": "adds a boundary case; record only",
            },
            {
                "incoming_capability_id": "acme.cap.c",
                "overlap": "none",
                "matched_asset_ids": [],
                "difference_note": "no counterpart in the current catalog",
            },
        ],
    }


def test_valid_overlap_record_passes():
    result = overlap.validate_record(_record())
    assert result["status"] == "PASS", result["errors"]


def test_schema_and_validator_share_unversioned_contract():
    schema = json.loads(
        (ROOT / "contracts" / "reception" / "overlap-record.schema.json").read_text()
    )
    assert schema["required"] == ["schema", "records"]
    assert "schema_version" not in schema["properties"]
    versioned = _record()
    versioned["schema_version"] = "1.0"
    result = overlap.validate_record(versioned)
    assert result["status"] == "FAIL"
    assert any("allowed properties" in error for error in result["errors"])


def test_none_requires_no_matches():
    payload = _record()
    payload["records"][2]["matched_asset_ids"] = ["scirel.field.cap-a"]
    result = overlap.validate_record(payload)
    assert result["status"] == "FAIL" and any("overlap=none" in e for e in result["errors"])


def test_overlap_requires_matches():
    payload = _record()
    payload["records"][0]["matched_asset_ids"] = []
    result = overlap.validate_record(payload)
    assert result["status"] == "FAIL" and any("same-relation" in e for e in result["errors"])


def test_duplicate_ids_and_unknown_overlap_rejected():
    payload = _record()
    payload["records"][1]["incoming_capability_id"] = payload["records"][0][
        "incoming_capability_id"
    ]
    payload["records"][0]["overlap"] = "partial"
    result = overlap.validate_record(payload)
    assert result["status"] == "FAIL"
    assert any("duplicate" in e for e in result["errors"])
    assert any("unknown overlap" in e for e in result["errors"])


def test_missing_difference_note_rejected():
    payload = _record()
    payload["records"][0].pop("difference_note")
    result = overlap.validate_record(payload)
    assert result["status"] == "FAIL"
    assert any("difference_note" in e for e in result["errors"])

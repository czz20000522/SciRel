"""Validate an incoming-capability overlap record.

The record only states overlap with the current SciRel catalog. It carries no
merge decision, capability-gain claim, stage-package requirement or release
authorization.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "reception" / "overlap-record.schema.json"
OVERLAPS = {"none", "same-relation", "convention-only", "wider-coverage"}


def validate_record(record):
    errors = []
    if not isinstance(record, dict):
        return {"status": "FAIL", "errors": ["record: expected an object"]}
    if set(record) != {"schema", "records"}:
        errors.append("record: allowed properties are schema and records")
    if record.get("schema") != "scirel.overlap-record":
        errors.append("record: schema must be scirel.overlap-record")
    records = record.get("records")
    if not isinstance(records, list) or not records:
        errors.append("record: records must be a non-empty array")
        records = []
    ids = []
    for index, item in enumerate(records):
        if not isinstance(item, dict):
            errors.append(f"records[{index}]: expected an object")
            continue
        if set(item) - {
            "incoming_capability_id",
            "overlap",
            "matched_asset_ids",
            "difference_note",
            "evidence",
        }:
            errors.append(f"records[{index}]: unknown properties")
        for key in ("incoming_capability_id", "overlap", "matched_asset_ids", "difference_note"):
            if key not in item:
                errors.append(f"records[{index}]: missing {key}")
        identifier = item.get("incoming_capability_id")
        if isinstance(identifier, str) and identifier:
            ids.append(identifier)
        if not isinstance(item.get("difference_note"), str) or not item.get("difference_note"):
            errors.append(f"records[{index}]: difference_note must be a non-empty string")
        matched = item.get("matched_asset_ids")
        if not isinstance(matched, list) or not all(isinstance(x, str) and x for x in matched):
            errors.append(f"records[{index}]: matched_asset_ids must be a string list")
            matched = []
        overlap = item.get("overlap")
        if overlap not in OVERLAPS:
            errors.append(f"records[{index}]: unknown overlap {overlap!r}")
        elif overlap == "none" and matched:
            errors.append(f"records[{index}]: overlap=none requires empty matched_asset_ids")
        elif overlap != "none" and not matched:
            errors.append(f"records[{index}]: overlap={overlap} requires matched_asset_ids")
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list) or not all(isinstance(x, str) and x for x in evidence):
            errors.append(f"records[{index}]: evidence must be a string list")
    if len(ids) != len(set(ids)):
        errors.append("record: duplicate incoming_capability_id")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = validate_record(json.loads(args.record.read_text(encoding="utf-8")))
    if args.output:
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

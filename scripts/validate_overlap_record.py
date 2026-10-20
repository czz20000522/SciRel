"""Validate an incoming-capability overlap record.

The record only states overlap with the current SciRel catalog. It carries no
merge decision, capability-gain claim or release authorization.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "handoff" / "overlap-record.schema.json"


def _load_handoff():
    spec = importlib.util.spec_from_file_location(
        "validate_handoff", ROOT / "scripts" / "validate_handoff.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_record(record):
    """Return {'status': 'PASS'|'FAIL', 'errors': [...]}."""
    errors = []
    handoff = _load_handoff()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    handoff._schema_errors(record, schema, "record", errors)
    ids = [item.get("incoming_capability_id") for item in record.get("records", [])]
    if len(ids) != len(set(ids)):
        errors.append("records: duplicate incoming_capability_id")
    for index, item in enumerate(record.get("records", [])):
        overlap = item.get("overlap")
        matched = item.get("matched_asset_ids", [])
        if overlap == "none" and matched:
            errors.append(f"records[{index}]: overlap=none requires empty matched_asset_ids")
        if overlap in {"same-relation", "convention-only", "wider-coverage"} and not matched:
            errors.append(f"records[{index}]: overlap={overlap} requires matched_asset_ids")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.record.read_text(encoding="utf-8"))
    result = validate_record(payload)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                               encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

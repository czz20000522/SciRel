"""Validate a D3 disposition review record (receiver-side, human/agent judgment)."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts" / "handoff" / "disposition.schema.json"


def _load_handoff():
    spec = importlib.util.spec_from_file_location(
        "validate_handoff", ROOT / "scripts" / "validate_handoff.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_review(review, package_dir=None):
    errors = []
    handoff = _load_handoff()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    handoff._schema_errors(review, schema, "review", errors)
    dispositions = review.get("dispositions", [])
    incoming = [d.get("incoming_asset_id") for d in dispositions]
    if len(incoming) != len(set(incoming)):
        errors.append("dispositions: duplicate incoming_asset_id")
    summary = review.get("summary", {})
    counts = {name: 0 for name in ("existing", "partial", "new")}
    for index, item in enumerate(dispositions):
        kind = item.get("disposition")
        if kind in counts:
            counts[kind] += 1
        matched = item.get("matched_asset_ids", [])
        changes = item.get("required_changes", [])
        gain = item.get("capability_gain", {})
        extends = gain.get("extends")
        if kind == "existing":
            if not matched:
                errors.append(f"dispositions[{index}]: existing requires matched_asset_ids")
            if extends is not False:
                errors.append(f"dispositions[{index}]: existing must declare capability_gain.extends=false")
            if changes:
                errors.append(f"dispositions[{index}]: existing must not require changes")
        if kind == "partial":
            if not matched:
                errors.append(f"dispositions[{index}]: partial requires matched_asset_ids")
            if extends is True and not changes:
                errors.append(f"dispositions[{index}]: partial with capability gain requires required_changes")
            if extends is False and changes:
                errors.append(f"dispositions[{index}]: partial without capability gain must not require changes")
        if kind == "new":
            if matched:
                errors.append(f"dispositions[{index}]: new requires empty matched_asset_ids")
            if extends is not True:
                errors.append(f"dispositions[{index}]: new must declare capability_gain.extends=true")
            if not changes:
                errors.append(f"dispositions[{index}]: new requires required_changes")
    for name, value in counts.items():
        if summary.get(name) != value:
            errors.append(f"summary.{name}: expected {value}, got {summary.get(name)}")
    if package_dir is not None:
        manifest_path = Path(package_dir) / "handoff.json"
        if not manifest_path.is_file():
            errors.append(f"package not found: {manifest_path}")
        else:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            bound = review.get("package", {})
            if bound.get("package_id") != manifest.get("package_id"):
                errors.append("package.package_id: does not match D3 package")
            if bound.get("payload_digest") != manifest.get("payload_digest"):
                errors.append("package.payload_digest: does not match D3 package")
            delivered = {a.get("asset_id") for a in manifest.get("delivery", {}).get("assets", [])}
            unknown = sorted(set(incoming) - delivered)
            if unknown:
                errors.append(f"dispositions: unknown incoming assets {unknown}")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors,
            "counts": counts}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path)
    parser.add_argument("--package-dir", type=Path)
    args = parser.parse_args(argv)
    review = json.loads(args.review.read_text(encoding="utf-8"))
    result = validate_review(review, package_dir=args.package_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

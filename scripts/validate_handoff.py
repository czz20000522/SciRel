"""Validate a SciRel handoff package at one decomposition layer.

Layers are independent packages: each declares its identity, payload digest and
a parent_handoff reference. Validation is structural (the layer schema) plus a
few cross-file closure checks; it never inspects how the producer decomposed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "contracts" / "handoff"
LAYERS = ("d0", "d1", "d2", "d3")
PARENT = {"d1": "d0", "d2": "d1", "d3": "d2"}
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
REL_RE = re.compile(r"^(?!.*(?:^|/)\.\.(?:/|$))(?!\/).+$")


def _type_ok(value, name):
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    return True


def _schema_errors(value, schema, path, errors):
    if "type" in schema and not _type_ok(value, schema["type"]):
        errors.append(f"{path}: expected {schema['type']}")
        return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: expected one of {schema['enum']}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            errors.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(value, int) and "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{path}: below minimum {schema['minimum']}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                _schema_errors(item, item_schema, f"{path}[{index}]", errors)
    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing field {key}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = sorted(set(value) - set(properties))
            for key in unknown:
                errors.append(f"{path}: unknown field {key}")
        for key, item in value.items():
            if key in properties:
                _schema_errors(item, properties[key], f"{path}.{key}", errors)


def compute_payload_digest(artifacts):
    lines = "".join(f"{item['sha256']}  {item['path']}\n"
                    for item in sorted(artifacts, key=lambda x: x["path"]))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def _check_artifacts(package_dir, artifacts, errors):
    seen = set()
    for index, item in enumerate(artifacts):
        rel = item["path"]
        if rel in seen:
            errors.append(f"declarations.artifacts[{index}]: duplicate path {rel}")
        seen.add(rel)
        if not REL_RE.fullmatch(rel):
            errors.append(f"declarations.artifacts[{index}]: unsafe path {rel}")
            continue
        target = package_dir / rel
        if not target.is_file():
            errors.append(f"declarations.artifacts[{index}]: missing file {rel}")
            continue
        if hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]:
            errors.append(f"declarations.artifacts[{index}]: digest mismatch {rel}")


def _check_d3(package_dir, manifest, errors):
    delivery = manifest.get("delivery", {})
    if delivery.get("contract_schema") != "scirel.asset-document":
        errors.append("delivery.contract_schema: must be scirel.asset-document")
    asset_ids = set()
    for index, asset in enumerate(delivery.get("assets", [])):
        asset_id = asset.get("asset_id", "")
        if asset_id in asset_ids:
            errors.append(f"delivery.assets[{index}]: duplicate asset_id {asset_id}")
        asset_ids.add(asset_id)
        for key in ("contract_path", "implementation_paths", "test_paths", "evidence_paths"):
            values = asset.get(key)
            values = values if isinstance(values, list) else [values]
            for value in values:
                if isinstance(value, str) and not (package_dir / value).exists():
                    errors.append(f"delivery.assets[{index}].{key}: missing {value}")
        contract = package_dir / str(asset.get("contract_path", ""))
        if contract.is_file():
            try:
                document = json.loads(contract.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"delivery.assets[{index}]: invalid contract JSON: {exc}")
                continue
            if document.get("schema") != "scirel.asset-document":
                errors.append(f"delivery.assets[{index}]: contract schema mismatch")
            if document.get("asset_id") != asset_id:
                errors.append(f"delivery.assets[{index}]: contract asset_id mismatch")
    for index, evidence in enumerate(manifest.get("application_evidence", [])):
        if evidence.get("status") not in ("pass", "not_run", "fail"):
            errors.append(f"application_evidence[{index}]: invalid status")
        if evidence.get("status") == "fail":
            errors.append(f"application_evidence[{index}]: declared failure")


def validate_package(package_dir, *, expected_layer=None, parent_dir=None):
    package_dir = Path(package_dir)
    errors = []
    manifest_path = package_dir / "handoff.json"
    if not manifest_path.is_file():
        return {"status": "FAIL", "errors": [f"missing {manifest_path}"]}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"status": "FAIL", "errors": [f"invalid JSON: {exc}"]}
    layer = manifest.get("layer")
    if layer not in LAYERS:
        return {"status": "FAIL", "errors": [f"invalid layer {layer!r}"]}
    if expected_layer and layer != expected_layer:
        errors.append(f"layer: expected {expected_layer}, got {layer}")
    schema_path = SCHEMA_DIR / f"{layer}-package.schema.json"
    if not schema_path.is_file():
        return {"status": "FAIL", "errors": [f"missing schema {schema_path.name}"]}
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    _schema_errors(manifest, schema, "handoff", errors)

    parent = manifest.get("parent_handoff")
    if layer == "d0":
        if parent is not None:
            errors.append("parent_handoff: d0 must be null")
    else:
        if not isinstance(parent, dict):
            errors.append("parent_handoff: required for non-d0 layer")
        else:
            if parent.get("layer") != PARENT[layer]:
                errors.append(f"parent_handoff.layer: expected {PARENT[layer]}")
            if not SHA_RE.fullmatch(str(parent.get("payload_digest", ""))):
                errors.append("parent_handoff.payload_digest: invalid sha256")
            if parent_dir is not None:
                parent_manifest = Path(parent_dir) / "handoff.json"
                if not parent_manifest.is_file():
                    errors.append(f"parent package not found: {parent_manifest}")
                else:
                    upstream = json.loads(parent_manifest.read_text(encoding="utf-8"))
                    if upstream.get("package_id") != parent.get("package_id"):
                        errors.append("parent_handoff.package_id: does not match parent package")
                    if upstream.get("payload_digest") != parent.get("payload_digest"):
                        errors.append("parent_handoff.payload_digest: does not match parent package")

    declarations = manifest.get("declarations")
    if isinstance(declarations, dict):
        artifacts = declarations.get("artifacts")
        if isinstance(artifacts, list):
            _check_artifacts(package_dir, artifacts, errors)
            if any(isinstance(a, dict) and "sha256" in a and "path" in a for a in artifacts):
                try:
                    expected = compute_payload_digest(artifacts)
                except (KeyError, TypeError):
                    expected = None
                if expected and manifest.get("payload_digest") != expected:
                    errors.append("payload_digest: does not match declarations.artifacts")
        license_info = manifest.get("license")
        if isinstance(license_info, dict):
            for notice in license_info.get("notice_paths", []):
                if not (package_dir / notice).is_file():
                    errors.append(f"license.notice_paths: missing {notice}")
    if layer == "d0":
        source = manifest.get("source", {})
        digest = source.get("source_digest")
        if isinstance(digest, str) and SHA_RE.fullmatch(digest):
            digests = {a.get("sha256") for a in (declarations or {}).get("artifacts", [])}
            if digest not in digests:
                errors.append("source.source_digest: not present in declarations.artifacts")
    if layer == "d3":
        _check_d3(package_dir, manifest, errors)
    return {"status": "PASS" if not errors else "FAIL", "layer": layer,
            "package_id": manifest.get("package_id"), "errors": errors}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--layer", choices=LAYERS)
    parser.add_argument("--parent-dir", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = validate_package(args.package, expected_layer=args.layer,
                              parent_dir=args.parent_dir)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

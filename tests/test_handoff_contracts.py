"""Layer handoff packages: independent schemas with a declared parent chain."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_handoff", ROOT / "scripts" / "validate_handoff.py")
handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handoff)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())


def _artifacts(root):
    items = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "handoff.json":
            items.append({"path": path.relative_to(root).as_posix(),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return items


def _manifest(layer, root, parent=None, artifacts=None):
    artifacts = artifacts if artifacts is not None else _artifacts(root)
    manifest = {
        "schema": "scirel.handoff-package",
        "schema_version": "1.0",
        "layer": layer,
        "package_id": f"pilot-{layer}",
        "package_version": "1.0",
        "producer_role": "pilot",
        "payload_digest": handoff.compute_payload_digest(artifacts),
        "parent_handoff": None if layer == "d0" else {
            "layer": {"d1": "d0", "d2": "d1", "d3": "d2"}[layer],
            "package_id": parent["package_id"],
            "payload_digest": parent["payload_digest"],
            "schema_version": parent["schema_version"]},
        "declarations": {
            "scope": "bounded pilot",
            "coverage": {"covered": 1, "failed": 0, "blocked": 0,
                         "not_run": 0, "inapplicable": 0},
            "claim_ceiling": "bounded test fixture only",
            "not_run": [], "untested_scope": [],
            "rights": {"redistribution": "pending", "notes": "fixture"},
            "runtime": {"dependencies": []},
            "artifacts": artifacts,
        },
    }
    if layer in ("d0", "d3"):
        manifest["license"] = {"notice_paths": ["LICENSE"]}
    if layer == "d0":
        manifest["source"] = {
            "upstream_identity": "fixture upstream",
            "source_digest": next(a["sha256"] for a in artifacts
                                  if a["path"] == "source.tar.gz"),
            "delta": {"rationale": "none", "patched_files": []},
            "retained_scope": ["one"], "excluded_scope": []}
    if layer == "d1":
        manifest["denominator"] = {"declared_scope": "one relation",
                                   "retained_relations": ["one"], "excluded": []}
        manifest["source_issues"] = []
    if layer == "d2":
        manifest["claims"] = [{"claim_id": "c1", "relation": "one",
                               "assumptions": ["a"], "boundary": "b",
                               "failure": "f", "oracle": "o",
                               "observations": ["x"]}]
        manifest["evidence_gaps"] = []
    if layer == "d3":
        manifest["delivery"] = {
            "contract_schema": "scirel.asset-document",
            "assets": [{"asset_id": "scirel.pilot.one",
                        "contract_path": "assets/one.json",
                        "implementation_paths": ["src/one.py"],
                        "test_paths": ["tests/test_one.py"],
                        "evidence_paths": ["assets/evidence.json"]}],
            "example_policy": "declared_not_run",
            "runtime_closure": {"dependencies": []}}
        manifest["application_evidence"] = [{
            "case_id": "app-1", "status": "pass",
            "evidence_digest": next(a["sha256"] for a in artifacts
                                    if a["path"] == "assets/evidence.json"),
            "notes": "fixture"}]
    _write(root / "handoff.json", json.dumps(manifest, indent=1))
    return manifest


def _build_chain(tmp_path):
    docs = {}
    d0 = tmp_path / "d0"
    _write(d0 / "source.tar.gz", b"source-bytes")
    _write(d0 / "LICENSE", "MIT")
    docs["d0"] = _manifest("d0", d0)
    d1 = tmp_path / "d1"
    _write(d1 / "operator.py", "def one():\n    return 1\n")
    docs["d1"] = _manifest("d1", d1, parent=docs["d0"])
    d2 = tmp_path / "d2"
    _write(d2 / "claim.json", "{}")
    docs["d2"] = _manifest("d2", d2, parent=docs["d1"])
    d3 = tmp_path / "d3"
    contract = {"schema": "scirel.asset-document", "asset_id": "scirel.pilot.one"}
    _write(d3 / "assets/one.json", json.dumps(contract))
    _write(d3 / "assets/evidence.json", "{}")
    _write(d3 / "src/one.py", "def one():\n    return 1\n")
    _write(d3 / "tests/test_one.py", "def test_one():\n    assert True\n")
    _write(d3 / "LICENSE", "MIT")
    docs["d3"] = _manifest("d3", d3, parent=docs["d2"])
    return tmp_path, docs


def test_valid_chain_passes_with_parent_links(tmp_path):
    root, _ = _build_chain(tmp_path)
    for layer in ("d0", "d1", "d2", "d3"):
        parent = None if layer == "d0" else root / {"d1": "d0", "d2": "d1", "d3": "d2"}[layer]
        result = handoff.validate_package(root / layer, expected_layer=layer,
                                          parent_dir=parent)
        assert result["status"] == "PASS", result["errors"]


def test_artifact_tamper_breaks_payload_digest(tmp_path):
    root, _ = _build_chain(tmp_path)
    (root / "d1" / "operator.py").write_bytes(b"tampered")
    result = handoff.validate_package(root / "d1", expected_layer="d1")
    assert result["status"] == "FAIL"
    assert any("digest mismatch" in e or "payload_digest" in e for e in result["errors"])


def test_parent_identity_must_match(tmp_path):
    root, docs = _build_chain(tmp_path)
    manifest = json.loads((root / "d2" / "handoff.json").read_text())
    manifest["parent_handoff"]["payload_digest"] = "0" * 64
    (root / "d2" / "handoff.json").write_text(json.dumps(manifest))
    result = handoff.validate_package(root / "d2", expected_layer="d2",
                                      parent_dir=root / "d1")
    assert result["status"] == "FAIL"
    assert any("parent_handoff.payload_digest" in e for e in result["errors"])


def test_d3_contract_schema_and_asset_identity(tmp_path):
    root, docs = _build_chain(tmp_path)
    contract = {"schema": "other-schema", "asset_id": "scirel.other.one"}
    (root / "d3" / "assets/one.json").write_text(json.dumps(contract))
    manifest = json.loads((root / "d3" / "handoff.json").read_text())
    artifacts = manifest["declarations"]["artifacts"]
    for item in artifacts:
        if item["path"] in ("assets/one.json",):
            item["sha256"] = hashlib.sha256((root / "d3" / item["path"]).read_bytes()).hexdigest()
    manifest["payload_digest"] = handoff.compute_payload_digest(artifacts)
    (root / "d3" / "handoff.json").write_text(json.dumps(manifest))
    result = handoff.validate_package(root / "d3", expected_layer="d3")
    assert result["status"] == "FAIL"
    assert any("contract schema mismatch" in e for e in result["errors"])


def test_required_declaration_and_example_policy(tmp_path):
    root, _ = _build_chain(tmp_path)
    manifest = json.loads((root / "d3" / "handoff.json").read_text())
    del manifest["declarations"]["claim_ceiling"]
    manifest["delivery"]["example_policy"] = "maybe"
    (root / "d3" / "handoff.json").write_text(json.dumps(manifest))
    result = handoff.validate_package(root / "d3", expected_layer="d3")
    assert result["status"] == "FAIL"
    assert any("claim_ceiling" in e for e in result["errors"])
    assert any("example_policy" in e for e in result["errors"])


def test_schemas_are_parseable_and_keep_common_layer_fields():
    common = {"schema", "schema_version", "layer", "package_id", "package_version",
              "producer_role", "payload_digest", "parent_handoff", "declarations"}
    for layer in ("d0", "d1", "d2", "d3"):
        schema = json.loads((ROOT / "contracts/handoff" / f"{layer}-package.schema.json")
                            .read_text())
        assert schema["properties"]["layer"]["const"] == layer
        assert common <= set(schema["required"])

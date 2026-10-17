from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from requalify_document_selection import requalify_selection  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def _commit(repo: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git", "-C", str(repo),
            "-c", "user.name=SciRel tests",
            "-c", "user.email=tests@scirel.invalid",
            "commit", "-m", message,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return _git(repo, "rev-parse", "HEAD")


def _fixture(tmp_path: Path, *, changed_module: bool = False, changed_contract: bool = False) -> dict[str, Path | str]:
    repo = tmp_path / "fixture"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    document = repo / "catalog/examples/scirel.foo.example.json"
    module = repo / "src/scirel/foo.py"
    selection = repo / "provenance/selections/current.json"
    document.parent.mkdir(parents=True)
    module.parent.mkdir(parents=True)
    selection.parent.mkdir(parents=True)
    old_document = {
        "schema": "scirel.asset-document.v1",
        "asset_id": "scirel.foo.example",
        "kind": "operator",
        "version": {"implementation_version": "0.1.0.dev8"},
        "public_api": {"python": {"module": "scirel.foo", "symbol": "evaluate"}},
        "contract": "old",
    }
    document.write_text(json.dumps(old_document, sort_keys=True) + "\n", encoding="utf-8")
    module.write_text("def evaluate(value):\n    return value\n", encoding="utf-8")
    selection.write_text(
        json.dumps(
            {
                "schema": "scirel.selected-document-set.v1",
                "records": [{
                    "asset_id": "scirel.foo.example",
                    "path": "catalog/examples/scirel.foo.example.json",
                    "sha256": _sha256(document),
                }],
            },
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    baseline = _commit(repo, "baseline")
    successor = dict(old_document)
    successor["version"] = {"implementation_version": "0.1.0.dev9"}
    if changed_contract:
        successor["contract"] = "changed"
    document.write_text(json.dumps(successor, sort_keys=True) + "\n", encoding="utf-8")
    if changed_module:
        module.write_text("def evaluate(value):\n    return value + 1\n", encoding="utf-8")
    source = _commit(repo, "successor")
    return {"repo": repo, "document": document, "module": module, "selection": selection, "baseline": baseline, "source": source}


def test_frozen_dev9_receipt_is_validated_without_rerunning_mutable_catalog() -> None:
    receipt = json.loads((ROOT / "provenance/validation/scirel-dev9-document-requalification-20261017.json").read_text(encoding="utf-8"))
    proof = json.loads((ROOT / "provenance/validation/scirel-dev9-document-requalification-proof-20261017.json").read_text(encoding="utf-8"))
    selection = json.loads((ROOT / "provenance/selections/scientific-core-documents-20261017-dev9.json").read_text(encoding="utf-8"))
    assert receipt["schema"] == "scirel.document-requalification.v1"
    assert receipt["selected_count"] == receipt["eligible_count"] == 260
    assert receipt["blocked_count"] == 0
    assert receipt["output_selection"] == "provenance/selections/scientific-core-documents-20261017-dev9.json"
    assert proof["schema"] == "scirel.document-requalification-proof.v1"
    assert selection["schema"] == "scirel.selected-document-set.v1"
    assert len(selection["records"]) >= receipt["selected_count"]
    assert len({row["asset_id"] for row in selection["records"]}) == len(selection["records"])


def test_complete_requalification_fails_closed_on_changed_contracts(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, changed_module=True)
    with pytest.raises(ValueError, match="complete requalification is blocked"):
        requalify_selection(selection_path=fixture["selection"], root=fixture["repo"], baseline_ref=fixture["baseline"], source_ref=fixture["source"], old_version="0.1.0.dev8", new_version="0.1.0.dev9")


def test_source_ref_rejects_a_candidate_document_drift(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    document = fixture["document"]
    original = document.read_bytes()
    try:
        document.write_bytes(original + b"\n")
        with pytest.raises(ValueError, match="candidate document changed since source_ref"):
            requalify_selection(selection_path=fixture["selection"], root=fixture["repo"], baseline_ref=fixture["baseline"], source_ref=fixture["source"], old_version="0.1.0.dev8", new_version="0.1.0.dev9", require_complete=False)
    finally:
        document.write_bytes(original)


def test_requalification_cli_exposes_source_and_target_ref_options() -> None:
    result = subprocess.run([sys.executable, str(ROOT / "scripts/requalify_document_selection.py"), "--help"], cwd=ROOT, check=True, capture_output=True, text=True)
    assert "--source-ref" in result.stdout
    assert "--target-ref" in result.stdout


def test_apply_never_shrinks_a_blocked_selection(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, changed_module=True)
    with pytest.raises(ValueError, match="--apply requires complete requalification"):
        requalify_selection(selection_path=fixture["selection"], root=fixture["repo"], baseline_ref=fixture["baseline"], source_ref=fixture["source"], old_version="0.1.0.dev8", new_version="0.1.0.dev9", output_selection=tmp_path / "selection.json", apply=True, require_complete=False)
    assert not (tmp_path / "selection.json").exists()


def _proof_manifest(fixture: dict[str, Path | str], path: Path, module_digest: str) -> Path:
    receipt = fixture["repo"] / "receipt.json"
    receipt.write_text(json.dumps({"status": "PASS"}) + "\n", encoding="utf-8")
    manifest = {
        "schema": "scirel.document-requalification-proof.v1",
        "source_revision": fixture["source"],
        "baseline_revision": fixture["baseline"],
        "proofs": [{
            "asset_ids": ["scirel.foo.example"],
            "module": "src/scirel/foo.py",
            "module_sha256": module_digest,
            "test_paths": [{"path": "receipt.json", "sha256": _sha256(receipt)}],
            "receipt_paths": [{"path": "receipt.json", "sha256": _sha256(receipt)}],
        }],
    }
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_explicit_proof_requalifies_a_changed_public_module(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, changed_module=True)
    proof = _proof_manifest(fixture, tmp_path / "proof.json", _sha256(fixture["module"]))
    result = requalify_selection(selection_path=fixture["selection"], root=fixture["repo"], baseline_ref=fixture["baseline"], source_ref=fixture["source"], old_version="0.1.0.dev8", new_version="0.1.0.dev9", proof_manifest=proof, require_complete=False)
    assert result["selected_count"] == result["eligible_count"] == 1
    assert result["blocked_count"] == 0
    assert result["proof_manifest_sha256"] == _sha256(proof)


def test_explicit_proof_rejects_a_stale_module_digest(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, changed_module=True)
    proof = _proof_manifest(fixture, tmp_path / "stale-proof.json", "0" * 64)
    with pytest.raises(ValueError, match="module digest differs"):
        requalify_selection(selection_path=fixture["selection"], root=fixture["repo"], baseline_ref=fixture["baseline"], source_ref=fixture["source"], old_version="0.1.0.dev8", new_version="0.1.0.dev9", proof_manifest=proof)

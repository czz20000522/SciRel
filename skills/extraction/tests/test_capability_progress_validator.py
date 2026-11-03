from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import pytest


ROOT = Path(__file__).resolve().parents[3]
SELF_TEST = (
    ROOT
    / "skills"
    / "extraction"
    / "scientific-computation-asset-extraction"
    / "scripts"
    / "test_validate_capability_progress.py"
)

sys.path.insert(0, str(SELF_TEST.parent))
import validate_capability_progress as validator  # noqa: E402
from validate_capability_progress import (  # noqa: E402
    _file_hash_digest,
    bundle_file_hashes,
    compute_bundle_digest,
    compute_file_sha256,
    validate_external_bindings,
)


def test_capability_progress_validator_self_test() -> None:
    completed = subprocess.run(
        [sys.executable, str(SELF_TEST)],
        cwd=SELF_TEST.parent,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "capability progress validator: PASS" in completed.stdout


@pytest.mark.parametrize("reviewer_role", ["independent_subagent", "independent_agent"])
def test_bounded_delivery_requires_bound_independent_review_receipt(
    tmp_path: Path, reviewer_role: str
) -> None:
    run_root = tmp_path / "run"
    bundle_root = run_root / "candidate_bundle"
    bundle_root.mkdir(parents=True)
    (run_root / "scope.json").write_text("scope", encoding="utf-8")
    (run_root / "matrix.md").write_text("matrix", encoding="utf-8")
    (run_root / "ledger.md").write_text("ledger", encoding="utf-8")

    scope = {
        "scope_manifest_digest": compute_file_sha256(run_root / "scope.json"),
        "capability_evidence_matrix_digest": compute_file_sha256(run_root / "matrix.md"),
        "ledger_digest": compute_file_sha256(run_root / "ledger.md"),
        "bundle_digest": compute_bundle_digest(bundle_root),
    }
    receipt = {
        "review_id": "review-001",
        "reviewer_role": reviewer_role,
        "verdict": "pass",
        "source_scope_digest": scope["scope_manifest_digest"],
        "bundle_digest": scope["bundle_digest"],
        "reviewed_target_ids": ["T-001"],
        "reviewed_evidence_refs": ["evidence:source-first"],
        "claim_ceiling": "bounded delivery only",
        "reopen_condition": "a missing capability is found during assembly",
        "findings": ["No blocking bounded-delivery finding."],
    }
    receipt_path = run_root / "review.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    document = {
        "scope": scope,
        "closure_signal": {
            "kind": "bounded_delivery",
            "delivered_target_ids": ["T-001"],
            "evidence_refs": ["evidence:source-first"],
            "claim_ceiling": "bounded delivery only",
            "reopen_condition": "a missing capability is found during assembly",
            "bounded_delivery_review": {
                "receipt_ref": "review.json",
                "receipt_sha256": compute_file_sha256(receipt_path),
            },
        },
    }

    assert validate_external_bindings(
        document,
        scope_manifest=run_root / "scope.json",
        capability_evidence_matrix=run_root / "matrix.md",
        ledger=run_root / "ledger.md",
        bundle_root=bundle_root,
    ) == []

    malformed = json.loads(json.dumps(document))
    malformed["closure_signal"]["delivered_target_ids"] = None
    malformed_errors = validate_external_bindings(
        malformed,
        scope_manifest=run_root / "scope.json",
        capability_evidence_matrix=run_root / "matrix.md",
        ledger=run_root / "ledger.md",
        bundle_root=bundle_root,
    )
    assert any("delivered_target_ids must be a list" in error for error in malformed_errors)

    receipt["reviewer_role"] = "coordinator"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    document["closure_signal"]["bounded_delivery_review"][
        "receipt_sha256"
    ] = compute_file_sha256(receipt_path)
    errors = validate_external_bindings(
        document,
        scope_manifest=run_root / "scope.json",
        capability_evidence_matrix=run_root / "matrix.md",
        ledger=run_root / "ledger.md",
        bundle_root=bundle_root,
    )
    assert any("reviewer_role must equal independent_subagent" in error for error in errors)


def _report_rebind_batch(run_root: Path, case_count: int = 8) -> tuple[dict, Path]:
    """Synthetic binding cases; no scientific execution or qualification is claimed."""
    bundle = run_root / "candidate_bundle"
    bundle.mkdir(parents=True)
    (bundle / "relation.py").write_text("def calculate(): return 1\n", encoding="utf-8")
    report = bundle / "extraction_report.md"
    report.write_text("initial report\n", encoding="utf-8")
    baseline = bundle_file_hashes(bundle)
    baseline_digest = compute_bundle_digest(bundle)

    def write_json(relative: str, value: dict) -> str:
        path = run_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return compute_file_sha256(path)

    manifest_ref = "evidence/baseline.json"
    manifest_digest = write_json(manifest_ref, {
        "schema_version": "scirel.bundle-file-manifest.v1",
        "bundle_digest": baseline_digest, "files": baseline,
    })
    report.write_text("corrected report\n", encoding="utf-8")
    current_digest = compute_bundle_digest(bundle)
    input_digest = "1" * 64
    target = "T-EXAMPLE"
    execution_ref = "evidence/execution.json"
    execution_digest = write_json(execution_ref, {
        "bundle_digest": baseline_digest,
        "cases": {f"{target}::case-{i}": {"input_digest": input_digest}
                  for i in range(case_count)},
    })
    probe_ref = "evidence/probe.json"
    image = "sha256:" + "e" * 64
    probe_digest = write_json(probe_ref, {"exit_code": 0, "image_id": image})
    oracle_ref = "evidence/source.json"
    oracle_digest = write_json(oracle_ref, {"result": 1})
    tolerance_ref = "evidence/tolerances.json"
    tolerance_digest = write_json(tolerance_ref, {"absolute_error": 0.0})
    scope = {}
    for field, relative in (("scope_manifest_digest", "scope.json"),
                            ("capability_evidence_matrix_digest", "matrix.json"),
                            ("ledger_digest", "ledger.json")):
        scope[field] = write_json(relative, {"fixture": True})
    scope["bundle_digest"] = current_digest
    cases = []
    for i in range(case_count):
        case = {
            "case_id": f"case-{i}", "kind": "canonical", "status": "passed",
            "source_oracle_ref": oracle_ref, "source_oracle_sha256": oracle_digest,
            "bundle_execution_ref": execution_ref, "bundle_execution_sha256": execution_digest,
            "tolerance_contract_ref": tolerance_ref, "tolerance_contract_sha256": tolerance_digest,
            "source_input_digest": input_digest, "bundle_input_digest": input_digest,
            "compared_terminal_output_ids": ["result"],
        }
        rebind_ref = f"evidence/rebind-{i}.json"
        rebind_digest = write_json(rebind_ref, {
            "schema_version": "scirel.execution-rebind.v1",
            "target_id": target, "case_id": case["case_id"],
            "baseline_bundle_digest": baseline_digest, "current_bundle_digest": current_digest,
            "baseline_manifest_ref": manifest_ref, "baseline_manifest_sha256": manifest_digest,
            "changed_report_paths": ["extraction_report.md"],
            "scientific_identity_digest": _file_hash_digest({
                path: digest for path, digest in baseline.items() if path != "extraction_report.md"
            }),
            "source_scope_digest": scope["scope_manifest_digest"],
            "source_input_digest": input_digest, "bundle_input_digest": input_digest,
            "tolerance_contract_digest": tolerance_digest,
            "bundle_execution_ref": execution_ref, "bundle_execution_sha256": execution_digest,
            "bundle_execution_receipt_ref": probe_ref, "bundle_execution_receipt_sha256": probe_digest,
            "runtime_image_id": image,
        })
        comparison_ref = f"evidence/comparison-{i}.json"
        case["comparison_receipt_ref"] = comparison_ref
        case["comparison_receipt_sha256"] = write_json(comparison_ref, {
            "schema_version": "scirel.extraction-reassembly-comparison.v2",
            "status": "passed", "target_id": target, "case_id": case["case_id"],
            "kind": case["kind"], "bundle_digest": current_digest,
            "source_scope_digest": scope["scope_manifest_digest"],
            "source_input_digest": input_digest, "bundle_input_digest": input_digest,
            "tolerance_contract_digest": tolerance_digest,
            "bundle_execution_ref": execution_ref, "bundle_execution_sha256": execution_digest,
            "bundle_execution_receipt_ref": probe_ref, "bundle_execution_receipt_sha256": probe_digest,
            "execution_rebind_ref": rebind_ref, "execution_rebind_sha256": rebind_digest,
            "terminal_output_ids": ["result"],
            "comparisons": [{"output_id": "result", "status": "passed", "metric": "absolute_error",
                             "observed_error": 0.0, "allowed_error": 0.0}],
        })
        cases.append(case)
    return {"scope": scope, "target_paths": [{
        "target_id": target, "status": "passed", "reassembly_evidence": {"cases": cases},
    }]}, bundle


def _validate_batch(document: dict, bundle: Path) -> list[str]:
    root = bundle.parent
    return validate_external_bindings(document, scope_manifest=root / "scope.json",
                                     capability_evidence_matrix=root / "matrix.json",
                                     ledger=root / "ledger.json", bundle_root=bundle)


def test_rebind_batch_reads_bundle_once_and_does_not_reuse_across_calls(tmp_path, monkeypatch):
    document, bundle = _report_rebind_batch(tmp_path)
    original_hash = validator.compute_file_sha256
    bundle_reads = []

    def count_hash(path):
        if path.is_relative_to(bundle):
            bundle_reads.append(path)
        return original_hash(path)

    monkeypatch.setattr(validator, "compute_file_sha256", count_hash)
    assert _validate_batch(document, bundle) == []
    # One ordinary artifact digest and one shared rebind manifest, not one per case.
    file_count = sum(path.is_file() for path in bundle.rglob("*"))
    assert len(bundle_reads) == 2 * file_count, bundle_reads
    # Re-entering the gate must read fresh bytes, including same-length code changes.
    (bundle / "relation.py").write_text("def calculate(): return 2\n", encoding="utf-8")
    assert any("bundle_digest" in error or "only to root project reports" in error
               for error in _validate_batch(document, bundle))


def test_rebind_batch_rejects_bundle_changed_during_last_case(tmp_path, monkeypatch):
    document, bundle = _report_rebind_batch(tmp_path)
    original = validator._validate_comparison_receipt
    calls = 0

    def mutate_after_last_case(*args, **kwargs):
        nonlocal calls
        original(*args, **kwargs)
        calls += 1
        if calls == 8:
            (bundle / "relation.py").write_text("def calculate(): return 9\n", encoding="utf-8")

    monkeypatch.setattr(validator, "_validate_comparison_receipt", mutate_after_last_case)
    assert any("changed during validation" in error for error in _validate_batch(document, bundle))


def test_rebind_batch_rejects_same_size_write_with_restored_mtime(tmp_path, monkeypatch):
    document, bundle = _report_rebind_batch(tmp_path)
    original = validator._validate_comparison_receipt
    code = bundle / "relation.py"
    before = code.stat()
    calls = 0

    def mutate_and_restore_mtime(*args, **kwargs):
        nonlocal calls
        original(*args, **kwargs)
        calls += 1
        if calls == 1:
            code.write_text("def calculate(): return 9\n", encoding="utf-8")
            os.utime(code, ns=(before.st_atime_ns, before.st_mtime_ns))

    monkeypatch.setattr(validator, "_validate_comparison_receipt", mutate_and_restore_mtime)
    assert any("changed during validation" in error for error in _validate_batch(document, bundle))

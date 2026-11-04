from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


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
from validate_capability_progress import (  # noqa: E402
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


def test_bounded_delivery_requires_bound_independent_review_receipt(tmp_path: Path) -> None:
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
        "reviewer_role": "independent_subagent",
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

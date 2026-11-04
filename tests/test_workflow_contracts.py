"""Check that development contract files match the workflow records."""

import json
from pathlib import Path

from scirel_plugin import BODY_OPERATIONS
from scirel_workflow import (
    AutomatedCheckResult,
    CandidatePackage,
    ReleaseManifest,
    ReviewDecision,
    SciRelWorkflow,
    StandardizationSubmission,
    StandardizedDraft,
)
from scirel_workflow.models import digest


ROOT = Path(__file__).resolve().parents[1]


def load_contract(name: str) -> dict:
    return json.loads((ROOT / "contracts" / name).read_text(encoding="utf-8"))


def test_dev_contract_schema_names_are_stable_for_the_first_slice():
    assert load_contract("candidate-package-dev.schema.json")["properties"]["schema"]["const"] == "scirel.candidate-package.dev"
    assert load_contract("automated-check-result-dev.schema.json")["properties"]["schema"]["const"] == "scirel.automated-check-result.dev"
    assert load_contract("l1-bundle-dev.schema.json")["properties"]["schema"]["const"] == "scirel.l1-bundle.dev"
    assert load_contract("l1-inventory-dev.schema.json")["properties"]["schema"]["const"] == "scirel.l1-inventory.dev"
    assert load_contract("standardized-draft-dev.schema.json")["properties"]["schema"]["const"] == "scirel.standardized-draft.dev"
    assert load_contract("standardization-submission-dev.schema.json")["properties"]["schema"]["const"] == "scirel.standardization-submission.dev"
    assert load_contract("release-manifest-dev.schema.json")["properties"]["schema"]["const"] == "scirel.release-manifest.dev"
    assert load_contract("review-decision-dev.schema.json")["properties"]["schema"]["const"] == "scirel.review-decision.dev"
    assert load_contract("review-ui-extension-dev.schema.json")["properties"]["schema"]["const"] == "scirel.review-ui-extension.dev"
    assert load_contract("review-item-dev.schema.json")["properties"]["schema"]["const"] == "scirel.review-item.dev"
    assert load_contract("review-item-decision-dev.schema.json")["properties"]["schema"]["const"] == "scirel.review-item-decision.dev"
    assert load_contract("review-item-detail-dev.schema.json")["properties"]["schema"]["const"] == "scirel.review-item-detail.dev"
    assert load_contract("review-completed-results-dev.schema.json")["properties"]["schema"]["const"] == "scirel.review-completed-results.dev"
    assert load_contract("workflow-state-dev.schema.json")["properties"]["schema"]["const"] == "scirel.workflow-state.dev"


def test_body_wire_request_contract_has_only_artifact_fields_and_opaque_payload():
    contract = load_contract("body-wire-request-dev.schema.json")
    expected = {"operation", "artifact_ref", "artifact_digest", "media_type", "body"}

    assert contract["additionalProperties"] is False
    assert set(contract["required"]) == expected
    assert set(contract["properties"]) == expected | {"operation_payload"}
    assert set(contract["properties"]["operation"]["enum"]) == set(BODY_OPERATIONS)
    open_payload, action_payload = contract["properties"]["operation_payload"][
        "oneOf"
    ]
    assert set(open_payload["properties"]) == {
        "item_ref",
        "revision",
    }
    assert set(action_payload["properties"]) == {
        "item_ref",
        "revision",
        "extension_ref",
        "action_ref",
        "reviewer",
        "payload",
    }
    assert action_payload["properties"]["extension_ref"]["const"] == (
        "scirel.review"
    )
    assert set(action_payload["properties"]["action_ref"]["enum"]) == {
        "plugin://scirel/review/approve",
        "plugin://scirel/review/request-evidence",
        "plugin://scirel/review/request-rework",
        "plugin://scirel/review/reject",
    }
    assert {
        (
            rule["if"]["properties"]["action_ref"]["const"],
            rule["then"]["properties"]["payload"]["properties"]["outcome"][
                "const"
            ],
        )
        for rule in action_payload["allOf"]
    } == {
        ("plugin://scirel/review/approve", "approved"),
        ("plugin://scirel/review/request-evidence", "needs_evidence"),
        ("plugin://scirel/review/request-rework", "rework_requested"),
        ("plugin://scirel/review/reject", "rejected"),
    }
    assert set(action_payload["properties"]["reviewer"]["required"]) == {
        "actor_ref"
    }
    assert not {
        "tenant_id",
        "project_id",
        "actor",
        "correlation_id",
        "idempotency_key",
    }.intersection(contract["properties"])


def test_records_emit_the_matching_dev_schema_names():
    candidate = CandidatePackage.from_l1(
        {"assets": [], "automated_checks": []},
        source_artifact_ref="artifact://l1/example",
        source_digest="sha256:source",
        run_id="run-contract",
    )
    draft = StandardizedDraft("draft-contract", candidate.candidate_id, (), (), ())
    release = ReleaseManifest(
        "release-contract",
        draft.draft_id,
        ("scirel.x",),
        "catalog",
        "sha256:" + "c" * 64,
        "wheel",
        "sha256:" + "d" * 64,
        candidate.candidate_id,
        candidate.package_digest,
        draft.draft_digest,
        "0.1.0.dev5",
    )
    candidate_contract = load_contract("candidate-package-dev.schema.json")

    assert candidate.to_dict()["schema"] == "scirel.candidate-package.dev"
    assert set(candidate_contract["required"]) <= set(candidate.to_dict())
    assert AutomatedCheckResult("result-contract", candidate.candidate_id, candidate.source_digest, ({"name": "x", "status": "passed"},)).to_dict()["schema"] == "scirel.automated-check-result.dev"
    assert draft.to_dict()["schema"] == "scirel.standardized-draft.dev"
    assert ReviewDecision("draft-contract", "approved", "expert").to_dict()["schema"] == "scirel.review-decision.dev"
    assert release.to_dict()["schema"] == "scirel.release-manifest.dev"


def test_standardization_submission_covers_contract_fields_exactly():
    candidate = CandidatePackage.from_l1(
        {
            "assets": [{"candidate_asset_id": "candidate-contract"}],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/standardization-contract",
        source_digest="sha256:" + "1" * 64,
        run_id="run-standardization-contract",
    )
    document = {"content": "Review this proposal."}
    document["digest"] = digest(document)
    code = {"kind": "none", "content": None, "rationale": "Reuse existing code."}
    code["digest"] = digest(code)
    tests = {
        "content": {"files": {"tests/test_example.py": "def test_example(): pass\n"}},
        "commands": [{"command": "pytest tests/test_example.py"}],
        "results": [{"exit_code": 0}],
    }
    tests["digest"] = digest(tests)
    submission = StandardizationSubmission.from_mapping(
        {
            "schema": "scirel.standardization-submission.dev",
            "submission_id": "submission-contract",
            "draft_id": "draft-contract",
            "candidate_id": candidate.candidate_id,
            "candidate_digest": candidate.package_digest,
            "source_digest": candidate.source_digest,
            "scirel_git_base": "a" * 40,
            "candidate_pool_ref": "artifact://candidate-pool/contract",
            "candidate_pool_digest": "sha256:" + "b" * 64,
            "producer": {
                "harness": {"name": "codex", "version": "dev"},
                "model": {"name": "model", "version": "dev"},
                "skill": {
                    "name": "scirel-integration",
                    "version": "dev",
                    "digest": "sha256:" + "c" * 64,
                },
            },
            "review_units": [
                {
                    "review_unit_id": "unit-contract",
                    "source_asset_ids": ["candidate-contract"],
                    "disposition": "reuse",
                    "asset_document": {
                        "asset_id": "scirel.contract.example",
                        "version": {"dependencies": []},
                    },
                    "candidate_document": document,
                    "candidate_code": code,
                    "candidate_tests": tests,
                    "dependency_asset_ids": [],
                    "evidence": [],
                    "gaps": [],
                }
            ],
            "run_evidence": [],
            "gaps": [],
        }
    )
    contract = load_contract("standardization-submission-dev.schema.json")

    assert set(submission.to_dict()) == set(contract["properties"]) - {"input_dispositions"}
    assert "input_dispositions" not in contract["required"]


def test_project_l1_payload_covers_inventory_contract_required_fields(tmp_path):
    project = tmp_path / "sample"
    project.mkdir()
    (project / "extraction_ledger.md").write_text("# ledger\n", encoding="utf-8")
    (project / "program_framework_map.md").write_text("# framework\n", encoding="utf-8")
    (project / "operators").mkdir()
    (project / "task_graphs").mkdir()

    from scirel_workflow import build_inventory

    payload = build_inventory(tmp_path).to_project_l1_payloads()[0]
    contract = load_contract("l1-inventory-dev.schema.json")

    assert set(contract["required"]) <= set(payload)
    assert set(payload) <= set(contract["properties"])
    assert len(payload["projects"]) == 1
    assert payload["projects"][0]["project_id"] == payload["project_id"]


def test_release_and_review_records_cover_contract_required_fields():
    release_contract = load_contract("release-manifest-dev.schema.json")
    review_contract = load_contract("review-decision-dev.schema.json")

    required_release = set(release_contract["required"])
    required_review = set(review_contract["required"])
    release = ReleaseManifest(
        "release-required",
        "draft-required",
        ("scirel.x",),
        "catalog",
        "sha256:" + "c" * 64,
        "wheel",
        "sha256:" + "d" * 64,
        "candidate-required",
        "sha256:" + "a" * 64,
        "sha256:" + "b" * 64,
        "0.1.0.dev5",
    ).to_dict()
    review = ReviewDecision("draft-required", "approved", "expert").to_dict()

    assert required_release <= set(release)
    assert required_review <= set(review)
    assert set(release) <= set(release_contract["properties"])
    assert set(review) <= set(review_contract["properties"])


def test_workflow_snapshot_covers_contract_fields_exactly():
    candidate = CandidatePackage.from_l1(
        {"assets": [], "automated_checks": []},
        source_artifact_ref="artifact://l1/workflow-contract",
        source_digest="sha256:source",
        run_id="run-workflow-contract",
    )
    snapshot = SciRelWorkflow(candidate).to_dict()
    contract = load_contract("workflow-state-dev.schema.json")

    assert set(contract["required"]) <= set(snapshot)
    assert set(snapshot) == set(contract["properties"]) - {"no_change_submission"}
    assert "no_change_submission" not in contract["required"]


def test_review_ui_projection_contract_has_exact_public_actions():
    contract = load_contract("review-ui-extension-dev.schema.json")

    assert set(contract["required"]) == set(contract["properties"])
    assert set(contract["properties"]["available_actions"]["items"]["enum"]) == {
        "standardize",
        "retry_automated_check",
        "provide_evidence",
        "rework_candidate",
        "create_draft",
        "update_draft",
        "submit_for_review",
        "start_review",
        "approve",
        "needs_evidence",
        "rework_requested",
        "reject",
        "release",
    }

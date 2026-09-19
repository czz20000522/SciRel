"""Tests for the host-independent development workflow."""

import json
from pathlib import Path

import pytest

from scirel_workflow import (
    AutomatedCheckResult,
    CandidatePackage,
    ReviewDecision,
    ReviewOutcome,
    SciRelWorkflow,
    WorkflowError,
    WorkflowStatus,
)


ASSET_DOCUMENT = json.loads(
    (
        Path(__file__).parents[2]
        / "catalog/examples/scirel.field.circular-filament-green.json"
    ).read_text(encoding="utf-8")
)


def ready_candidate() -> CandidatePackage:
    return CandidatePackage.from_l1(
        {"assets": [{"candidate_asset_id": "candidate-field"}], "automated_checks": [{"name": "replay", "status": "passed"}]},
        source_artifact_ref="artifact://l1/pleiades",
        source_digest="sha256:l1",
        run_id="run-1",
    )


def test_l1_candidate_moves_through_review_and_release():
    workflow = SciRelWorkflow(ready_candidate())
    assert workflow.status is WorkflowStatus.AUTOMATED_READY

    draft = workflow.create_draft(
        draft_id="draft-1",
        assets=[ASSET_DOCUMENT],
        evidence=[{"kind": "test", "ref": "tests/example.py"}],
    )
    assert draft.to_dict()["schema"] == "scirel.standardized-draft.dev"
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision("draft-1", ReviewOutcome.APPROVED, "expert-1", "checked")
    )
    release = workflow.release(
        release_id="release-1",
        catalog_ref="artifact://catalog/dev",
        catalog_digest="sha256:" + "c" * 64,
        wheel_ref="artifact://wheel/dev",
        wheel_digest="sha256:" + "d" * 64,
    )

    assert workflow.status is WorkflowStatus.RELEASED
    assert draft.status is WorkflowStatus.APPROVED
    assert release.to_dict()["schema"] == "scirel.release-manifest.dev"
    assert release.approved_assets == ("scirel.field.circular-filament-green",)
    assert release.candidate_id == "candidate-run-1"
    assert release.candidate_digest.startswith("sha256:")
    assert release.draft_digest.startswith("sha256:")
    assert release.release_version == "0.1.0.dev5"
    assert release.release_digest.startswith("sha256:")


def test_open_draft_can_be_replaced_without_creating_review_history():
    workflow = SciRelWorkflow(ready_candidate())
    original = workflow.create_draft(
        draft_id="draft-editable",
        assets=[ASSET_DOCUMENT],
        evidence=[{"kind": "test", "ref": "tests/original.py"}],
    )
    replacement_asset = json.loads(json.dumps(ASSET_DOCUMENT))
    replacement_asset["summary"] = "Replacement candidate summary."

    updated = workflow.update_open_draft(
        assets=[replacement_asset],
        dependency_asset_ids=["scirel.field.related"],
        evidence=[{"kind": "test", "ref": "tests/replacement.py"}],
    )

    assert updated.draft_id == original.draft_id
    assert updated.draft_digest != original.draft_digest
    assert workflow.record.drafts == [updated]
    assert workflow.record.draft is updated
    assert workflow.status is WorkflowStatus.DRAFT

    restored = SciRelWorkflow.from_dict(workflow.to_dict())
    assert restored.record.draft is not None
    assert restored.record.draft.draft_digest == updated.draft_digest
    assert len(restored.record.drafts) == 1


def test_queued_draft_can_be_updated_until_expert_observes_it():
    workflow = SciRelWorkflow(ready_candidate())
    original = workflow.create_draft(
        draft_id="draft-frozen", assets=[ASSET_DOCUMENT]
    )
    workflow.submit_for_review()

    updated = workflow.update_open_draft(
        assets=[ASSET_DOCUMENT],
        evidence=[{"kind": "queue-revision", "ref": "artifact://candidate/a-plus"}],
    )

    assert updated.draft_id == original.draft_id
    assert updated.draft_digest != original.draft_digest
    assert workflow.status is WorkflowStatus.REVIEW_PENDING

    workflow = SciRelWorkflow.from_dict(workflow.to_dict())
    assert workflow.status is WorkflowStatus.REVIEW_PENDING
    assert len(workflow.record.drafts) == 1
    assert workflow.record.draft is not None
    assert workflow.record.draft.draft_digest == updated.draft_digest

    workflow.start_review()

    with pytest.raises(WorkflowError, match="only an open draft"):
        workflow.update_open_draft(assets=[ASSET_DOCUMENT])


def test_l1_candidate_preserves_one_project_id():
    candidate = CandidatePackage.from_l1(
        {
            "project": "pleiades",
            "assets": [{"candidate_asset_id": "pleiades.field"}],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/pleiades",
        source_digest="sha256:pleiades",
        run_id="run-project",
    )

    assert candidate.project_id == "pleiades"
    assert candidate.to_dict()["project_id"] == "pleiades"


def test_candidate_package_mapping_is_strict_and_round_trips():
    candidate = ready_candidate()
    assert CandidatePackage.from_mapping(candidate.to_dict()).to_dict() == candidate.to_dict()

    unknown = candidate.to_dict()
    unknown["tenant_id"] = "must-not-enter-domain"
    with pytest.raises(ValueError, match="unknown fields: tenant_id"):
        CandidatePackage.from_mapping(unknown)

    wrong_schema = candidate.to_dict()
    wrong_schema["schema"] = "scirel.candidate-package.other"
    with pytest.raises(ValueError, match="unsupported candidate package schema"):
        CandidatePackage.from_mapping(wrong_schema)

    wrong_status = candidate.to_dict()
    wrong_status["status"] = "automated_ready"
    with pytest.raises(ValueError, match="status must be candidate"):
        CandidatePackage.from_mapping(wrong_status)


def test_l1_candidate_rejects_mixed_projects():
    with pytest.raises(ValueError, match="must contain one project"):
        CandidatePackage.from_l1(
            {
                "projects": [{"project_id": "aorsa3d"}, {"project_id": "gseq"}],
                "assets": [],
                "automated_checks": [],
            },
            source_artifact_ref="artifact://l1/mixed",
            source_digest="sha256:mixed",
            run_id="run-mixed-projects",
        )


def test_l1_candidate_derives_inventory_gaps_when_upstream_omits_them():
    candidate = CandidatePackage.from_l1(
        {
            "project_id": "sample",
            "assets": [
                {
                    "l1_asset_id": "sample:operator:leaf",
                    "asset_path": "operators/leaf",
                    "contract_path": "operators/leaf/operator.md",
                    "implementation_path": "operators/leaf/scientific_operator.py",
                    "direct_test_path": None,
                    "dependency_refs": [],
                },
                {
                    "l1_asset_id": "sample:task_graph:flow",
                    "asset_path": "task_graphs/flow",
                    "asset_kind": "task_graph",
                    "contract_path": "task_graphs/flow/task_graph.md",
                    "implementation_path": "task_graphs/flow/task_graph.py",
                    "direct_test_path": "task_graphs/flow/test_task_graph.py",
                    "dependency_refs": ["operators/missing"],
                },
            ],
            "automated_checks": [{"name": "inventory", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:sample",
        run_id="run-derived-inventory-gaps",
    )

    assert "missing_direct_test_mapping:sample:operator:leaf" in candidate.gaps
    assert (
        "unresolved_task_graph_dependency:sample:task_graph:flow -> operators/missing"
        in candidate.gaps
    )
    assert SciRelWorkflow(candidate).status is WorkflowStatus.AUTOMATED_REJECTED


def test_workflow_snapshot_round_trips_without_host_fields():
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(
        draft_id="draft-snapshot",
        assets=[ASSET_DOCUMENT],
        evidence=[{"kind": "test", "ref": "tests/example.py"}],
    )
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision("draft-snapshot", ReviewOutcome.APPROVED, "expert-1")
    )
    workflow.release(
        release_id="release-snapshot",
        catalog_ref="artifact://catalog/dev",
        catalog_digest="sha256:" + "c" * 64,
        wheel_ref="artifact://wheel/dev",
        wheel_digest="sha256:" + "d" * 64,
    )

    snapshot = workflow.to_dict()
    restored = SciRelWorkflow.from_dict(snapshot)

    assert restored.status is WorkflowStatus.RELEASED
    assert restored.record.candidate.candidate_id == workflow.record.candidate.candidate_id
    assert [item.draft_id for item in restored.record.drafts] == ["draft-snapshot"]
    assert restored.record.reviews[0].reviewer == "expert-1"
    assert restored.record.release.release_id == "release-snapshot"
    assert "tenant_id" not in snapshot
    assert "job_id" not in snapshot


def test_workflow_snapshot_rejects_inconsistent_status():
    workflow = SciRelWorkflow(ready_candidate())
    snapshot = workflow.to_dict()
    snapshot["status"] = WorkflowStatus.RELEASED.value

    with pytest.raises(WorkflowError, match="status does not match"):
        SciRelWorkflow.from_dict(snapshot)


def test_workflow_snapshot_rederives_draft_contract_gaps():
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(
        draft_id="draft-snapshot-gap",
        assets=[{"asset_id": "scirel.field.incomplete"}],
    )
    snapshot = workflow.to_dict()
    snapshot["draft"]["gaps"] = []
    snapshot["drafts"][0]["gaps"] = []

    restored = SciRelWorkflow.from_dict(snapshot)

    assert any(
        gap.startswith("scientific_contract_missing:")
        for gap in restored.record.draft.gaps
    )


def test_workflow_snapshot_rejects_approved_draft_with_hidden_contract_gaps():
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(
        draft_id="draft-approved-snapshot",
        assets=[ASSET_DOCUMENT],
    )
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision(
            "draft-approved-snapshot",
            ReviewOutcome.APPROVED,
            "expert-snapshot",
        )
    )
    snapshot = workflow.to_dict()
    incomplete = {"asset_id": "scirel.field.incomplete"}
    snapshot["draft"]["assets"] = [incomplete]
    snapshot["draft"]["gaps"] = []
    snapshot["drafts"][0]["assets"] = [incomplete]
    snapshot["drafts"][0]["gaps"] = []

    with pytest.raises(WorkflowError, match="unresolved gaps cannot be approved"):
        SciRelWorkflow.from_dict(snapshot)


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("candidate_id", "candidate-other", "candidate_id does not match"),
        ("draft_id", "draft-other", "draft_id does not match"),
        ("candidate_digest", "sha256:" + "a" * 64, "candidate digest does not match"),
        ("draft_digest", "sha256:" + "b" * 64, "draft digest does not match"),
        ("approved_assets", ["scirel.field.other"], "asset set does not match"),
        ("release_version", "9.9.9", "implementation_version does not match"),
    ],
)
def test_workflow_snapshot_rejects_release_binding_mismatch(field, value, message):
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(
        draft_id="draft-release-binding",
        assets=[ASSET_DOCUMENT],
    )
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision(
            "draft-release-binding",
            ReviewOutcome.APPROVED,
            "expert-release-binding",
        )
    )
    workflow.release(
        release_id="release-binding",
        catalog_ref="artifact://catalog/binding",
        catalog_digest="sha256:" + "c" * 64,
        wheel_ref="artifact://wheel/binding",
        wheel_digest="sha256:" + "d" * 64,
    )
    snapshot = workflow.to_dict()
    snapshot["release"][field] = value

    with pytest.raises(WorkflowError, match=message):
        SciRelWorkflow.from_dict(snapshot)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_review", "no approved review"),
        ("rejected_review", "no approved review"),
        ("unapproved_draft", "draft is not approved"),
        ("unready_candidate", "drafts for a candidate that is not"),
    ],
)
def test_workflow_snapshot_cannot_restore_release_without_release_gates(
    mutation, message
):
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(
        draft_id="draft-release-gates",
        assets=[ASSET_DOCUMENT],
    )
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision("draft-release-gates", ReviewOutcome.APPROVED, "expert-1")
    )
    workflow.release(
        release_id="release-gates",
        catalog_ref="artifact://catalog/dev",
        catalog_digest="sha256:" + "c" * 64,
        wheel_ref="artifact://wheel/dev",
        wheel_digest="sha256:" + "d" * 64,
    )
    snapshot = workflow.to_dict()

    if mutation == "missing_review":
        snapshot["review"] = None
        snapshot["reviews"] = []
    elif mutation == "rejected_review":
        snapshot["review"]["outcome"] = "rejected"
        snapshot["reviews"][0]["outcome"] = "rejected"
    elif mutation == "unapproved_draft":
        snapshot["draft"]["status"] = "review_pending"
        snapshot["drafts"][0]["status"] = "review_pending"
    else:
        snapshot["candidate"]["automated_checks"][0]["status"] = "failed"
        snapshot["release"]["candidate_digest"] = CandidatePackage.from_mapping(
            snapshot["candidate"]
        ).package_digest

    with pytest.raises(WorkflowError, match=message):
        SciRelWorkflow.from_dict(snapshot)


@pytest.mark.parametrize("reviewed", [False, True])
def test_workflow_snapshot_cannot_restore_draft_for_unready_candidate(reviewed):
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(
        draft_id="draft-candidate-gate",
        assets=[ASSET_DOCUMENT],
    )
    if reviewed:
        workflow.submit_for_review()
        workflow.start_review()
        workflow.record_review(
            ReviewDecision(
                "draft-candidate-gate",
                ReviewOutcome.NEEDS_EVIDENCE,
                "expert-1",
            )
        )
    snapshot = workflow.to_dict()
    snapshot["candidate"]["automated_checks"][0]["status"] = "failed"

    with pytest.raises(WorkflowError, match="drafts for a candidate that is not"):
        SciRelWorkflow.from_dict(snapshot)


@pytest.mark.parametrize("history", ["drafts", "reviews"])
def test_workflow_snapshot_current_records_must_be_latest_history(history):
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(draft_id="draft-first", assets=[ASSET_DOCUMENT])
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision(
            "draft-first", ReviewOutcome.REWORK_REQUESTED, "expert-1"
        )
    )
    workflow.create_draft(draft_id="draft-second", assets=[ASSET_DOCUMENT])
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision("draft-second", ReviewOutcome.APPROVED, "expert-1")
    )
    snapshot = workflow.to_dict()
    snapshot[history] = list(reversed(snapshot[history]))

    with pytest.raises(WorkflowError, match="not its latest history record"):
        SciRelWorkflow.from_dict(snapshot)


def test_release_rejects_asset_implementation_version_mismatch():
    asset = json.loads(json.dumps(ASSET_DOCUMENT))
    asset["version"]["implementation_version"] = "0.2.0"
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(
        draft_id="draft-version-mismatch",
        assets=[asset],
    )
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision(
            "draft-version-mismatch",
            ReviewOutcome.APPROVED,
            "expert-version",
        )
    )

    with pytest.raises(WorkflowError, match="implementation_version does not match"):
        workflow.release(
            release_id="release-version-mismatch",
            catalog_ref="artifact://catalog/version-mismatch",
            catalog_digest="sha256:" + "c" * 64,
            wheel_ref="artifact://wheel/version-mismatch",
            wheel_digest="sha256:" + "d" * 64,
            release_version="0.1.0.dev5",
        )


def test_failed_automated_check_cannot_create_draft():
    candidate = CandidatePackage.from_l1(
        {"assets": [{"candidate_asset_id": "candidate-field"}], "automated_checks": [{"name": "replay", "status": "failed"}]},
        source_artifact_ref="artifact://l1/pleiades",
        source_digest="sha256:l1",
        run_id="run-failed",
    )
    workflow = SciRelWorkflow(candidate)

    with pytest.raises(WorkflowError, match="automated checks"):
        workflow.create_draft(draft_id="draft-failed", assets=[{"asset_id": "scirel.x"}])


def test_second_stage_result_can_update_deterministic_check_status():
    candidate = CandidatePackage.from_l1(
        {
            "assets": [{"l1_asset_id": "sample:operator:leaf"}],
            "automated_checks": [{"name": "inventory", "status": "failed"}],
        },
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id="run-recover",
    )
    workflow = SciRelWorkflow(candidate)
    assert workflow.status is WorkflowStatus.AUTOMATED_REJECTED

    workflow.apply_automated_result(
        AutomatedCheckResult(
            result_id="check-recover",
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            checks=({"name": "inventory", "status": "passed"},),
        )
    )

    assert workflow.status is WorkflowStatus.AUTOMATED_READY
    workflow.create_draft(draft_id="draft-recovered", assets=[{"asset_id": "scirel.x"}])


def test_automated_result_replay_is_idempotent_even_after_draft_creation():
    candidate = CandidatePackage.from_l1(
        {
            "assets": [{"l1_asset_id": "sample:operator:leaf"}],
            "automated_checks": [{"name": "inventory", "status": "failed"}],
        },
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id="run-idempotent-result",
    )
    workflow = SciRelWorkflow(candidate)
    result = AutomatedCheckResult(
        result_id="check-idempotent",
        candidate_id=candidate.candidate_id,
        source_digest=candidate.source_digest,
        checks=({"name": "inventory", "status": "passed"},),
    )

    first = workflow.apply_automated_result(result)
    workflow.create_draft(draft_id="draft-after-result", assets=[ASSET_DOCUMENT])
    replayed = workflow.apply_automated_result(result)

    assert replayed is first
    assert len(workflow.record.automated_results) == 1
    assert workflow.status is WorkflowStatus.DRAFT


def test_automated_result_id_cannot_be_reused_with_different_content():
    workflow = SciRelWorkflow(ready_candidate())
    original = AutomatedCheckResult(
        result_id="check-conflict",
        candidate_id=workflow.record.candidate.candidate_id,
        source_digest=workflow.record.candidate.source_digest,
        checks=({"name": "replay", "status": "passed"},),
    )
    workflow.apply_automated_result(original)
    candidate_digest = workflow.record.candidate.package_digest

    with pytest.raises(WorkflowError, match="reused with different content"):
        workflow.apply_automated_result(
            AutomatedCheckResult(
                result_id="check-conflict",
                candidate_id=workflow.record.candidate.candidate_id,
                source_digest=workflow.record.candidate.source_digest,
                checks=({"name": "replay", "status": "failed"},),
                gaps=("conflicting replay",),
            )
        )

    assert workflow.record.candidate.package_digest == candidate_digest
    assert len(workflow.record.automated_results) == 1


def test_automated_result_must_match_candidate_source():
    candidate = CandidatePackage.from_l1(
        {"assets": [{"l1_asset_id": "sample:operator:leaf"}], "automated_checks": []},
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id="run-mismatch",
    )
    workflow = SciRelWorkflow(candidate)

    with pytest.raises(WorkflowError, match="source digest"):
        workflow.apply_automated_result(
            AutomatedCheckResult(
                result_id="check-mismatch",
                candidate_id=candidate.candidate_id,
                source_digest="sha256:other",
                checks=({"name": "inventory", "status": "passed"},),
            )
        )


@pytest.mark.parametrize(
    "next_action, expected",
    [
        ("needs_evidence", WorkflowStatus.NEEDS_EVIDENCE),
        ("rework_requested", WorkflowStatus.REWORK_REQUESTED),
        ("rejected", WorkflowStatus.REJECTED),
    ],
)
def test_failed_automated_result_exposes_next_action(next_action, expected):
    candidate = CandidatePackage.from_l1(
        {"assets": [{"l1_asset_id": "sample:operator:leaf"}], "automated_checks": []},
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id=f"run-{next_action}",
    )
    workflow = SciRelWorkflow(candidate)
    workflow.apply_automated_result(
        AutomatedCheckResult(
            result_id=f"check-{next_action}",
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            checks=({"name": "inventory", "status": "failed"},),
            gaps=("unresolved issue",),
            next_action=next_action,
        )
    )

    assert workflow.status is expected


@pytest.mark.parametrize(
    "next_action, expected",
    [
        ("needs_evidence", WorkflowStatus.NEEDS_EVIDENCE),
        ("rework_requested", WorkflowStatus.REWORK_REQUESTED),
    ],
)
def test_explicit_non_ready_action_blocks_a_passing_automated_check(
    next_action, expected
):
    candidate = CandidatePackage.from_l1(
        {"assets": [{"l1_asset_id": "sample:operator:leaf"}], "automated_checks": []},
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id=f"run-passing-{next_action}",
    )
    workflow = SciRelWorkflow(candidate)

    workflow.apply_automated_result(
        AutomatedCheckResult(
            result_id=f"check-passing-{next_action}",
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            checks=({"name": "inventory", "status": "passed"},),
            next_action=next_action,
        )
    )

    assert not workflow.record.candidate.automated_ready
    assert workflow.status is expected


def test_unresolved_draft_gap_blocks_approval():
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(
        draft_id="draft-gap",
        assets=[ASSET_DOCUMENT],
        gaps=["missing scientific evidence"],
    )
    workflow.submit_for_review()
    workflow.start_review()

    with pytest.raises(WorkflowError, match="unresolved gaps cannot be approved"):
        workflow.record_review(
            ReviewDecision("draft-gap", ReviewOutcome.APPROVED, "expert-1")
        )

    assert workflow.status is WorkflowStatus.REVIEW_IN_PROGRESS


def test_incomplete_standardization_becomes_structured_contract_gaps():
    workflow = SciRelWorkflow(ready_candidate())

    draft = workflow.create_draft(
        draft_id="draft-incomplete-contract",
        assets=[{
            "asset_id": "scirel.field.incomplete",
            "tenant_id": "must-not-enter-the-contract",
        }],
    )

    assert "scientific_contract_missing:scirel.field.incomplete:schema" in draft.gaps
    assert (
        "scientific_contract_unknown:scirel.field.incomplete:tenant_id" in draft.gaps
    )
    assert (
        "scientific_contract_private:scirel.field.incomplete:tenant_id" in draft.gaps
    )

    workflow.submit_for_review()
    workflow.start_review()
    with pytest.raises(WorkflowError, match="unresolved gaps cannot be approved"):
        workflow.record_review(
            ReviewDecision(
                draft.draft_id,
                ReviewOutcome.APPROVED,
                "expert-contract",
            )
        )
    assert workflow.status is WorkflowStatus.REVIEW_IN_PROGRESS


@pytest.mark.parametrize(
    "outcome, expected",
    [
        (ReviewOutcome.NEEDS_EVIDENCE, WorkflowStatus.NEEDS_EVIDENCE),
        (ReviewOutcome.REWORK_REQUESTED, WorkflowStatus.REWORK_REQUESTED),
        (ReviewOutcome.REJECTED, WorkflowStatus.REJECTED),
    ],
)
def test_review_branch_is_visible(outcome, expected):
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(draft_id="draft-branch", assets=[{"asset_id": "scirel.x"}])
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(ReviewDecision("draft-branch", outcome, "expert-1"))

    assert workflow.status is expected


def test_rework_creates_a_new_draft_and_keeps_review_history():
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(
        draft_id="draft-first",
        assets=[{"asset_id": "scirel.field.example"}],
    )
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision("draft-first", ReviewOutcome.REWORK_REQUESTED, "expert-1")
    )

    revised = workflow.create_draft(
        draft_id="draft-second",
        assets=[{"asset_id": "scirel.field.example"}],
        evidence=[{"kind": "boundary", "ref": "tests/example.py"}],
    )

    assert revised.draft_id == "draft-second"
    assert [draft.draft_id for draft in workflow.record.drafts] == [
        "draft-first",
        "draft-second",
    ]
    assert workflow.record.reviews[0].outcome is ReviewOutcome.REWORK_REQUESTED
    assert workflow.status is WorkflowStatus.DRAFT


def test_needs_evidence_can_be_reworked_but_approved_cannot():
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(draft_id="draft-evidence", assets=[{"asset_id": "scirel.x"}])
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision("draft-evidence", ReviewOutcome.NEEDS_EVIDENCE, "expert-1")
    )
    workflow.create_draft(draft_id="draft-evidence-fixed", assets=[ASSET_DOCUMENT])
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision("draft-evidence-fixed", ReviewOutcome.APPROVED, "expert-1")
    )

    with pytest.raises(WorkflowError, match="only evidence or rework"):
        workflow.create_draft(draft_id="draft-too-late", assets=[{"asset_id": "scirel.x"}])


def test_review_event_requires_registered_plugin():
    from scirel_plugin import FakeHost

    host = FakeHost()
    with pytest.raises(ValueError, match="not registered"):
        host.emit_event(
            plugin_id="unregistered",
            event_type="scirel.test",
            workflow_run_id="run-1",
            correlation_id="job-1",
        )

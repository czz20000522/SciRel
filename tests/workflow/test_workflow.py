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
    StandardizationSubmission,
    WorkflowError,
    WorkflowStatus,
)
from scirel_workflow.models import digest


ASSET_DOCUMENT = json.loads(
    (
        Path(__file__).parents[2]
        / "tests/fixtures/contracts/fixture-identity.json"
    ).read_text(encoding="utf-8")
)


def ready_candidate() -> CandidatePackage:
    return CandidatePackage.from_l1(
        {"assets": [{"candidate_asset_id": "candidate-field"}], "automated_checks": [{"name": "replay", "status": "passed"}]},
        source_artifact_ref="artifact://l1/synthetic",
        source_digest="sha256:l1",
        run_id="run-1",
    )


def standardization_submission(
    candidate: CandidatePackage,
    *,
    source_asset_ids: tuple[str, ...] = ("candidate-field",),
) -> StandardizationSubmission:
    candidate_document = {"content": "# Candidate\n\nReview the normalized relation."}
    candidate_document["digest"] = digest(candidate_document)
    candidate_code = {
        "kind": "none",
        "content": None,
        "rationale": "The existing public implementation is reused unchanged.",
    }
    candidate_code["digest"] = digest(candidate_code)
    candidate_tests = {
        "content": {"files": {"tests/test_relation.py": "def test_relation(): pass\n"}},
        "commands": [{"command": "pytest tests/test_relation.py"}],
        "results": [{"command": "pytest tests/test_relation.py", "exit_code": 0}],
    }
    candidate_tests["digest"] = digest(candidate_tests)
    return StandardizationSubmission.from_mapping(
        {
            "schema": "scirel.standardization-submission.dev",
            "submission_id": "submission-1",
            "draft_id": "draft-submission-1",
            "candidate_id": candidate.candidate_id,
            "candidate_digest": candidate.package_digest,
            "source_digest": candidate.source_digest,
            "scirel_git_base": "a" * 40,
            "candidate_pool_ref": "artifact://scirel/candidate-pool/empty",
            "candidate_pool_digest": "sha256:" + "b" * 64,
            "producer": {
                "harness": {"name": "claude-code", "version": "1"},
                "model": {"name": "deepseek-v4.1-flash", "version": "proxy"},
                "skill": {
                    "name": "scirel-integration",
                    "version": "dev",
                    "digest": "sha256:" + "c" * 64,
                },
            },
            "review_units": [
                {
                    "review_unit_id": "unit-field",
                    "source_asset_ids": list(source_asset_ids),
                    "disposition": "reuse",
                    "asset_document": ASSET_DOCUMENT,
                    "candidate_document": candidate_document,
                    "candidate_code": candidate_code,
                    "candidate_tests": candidate_tests,
                    "dependency_asset_ids": [
                        item["asset_id"]
                        for item in ASSET_DOCUMENT["version"]["dependencies"]
                    ],
                    "evidence": [{"kind": "comparison", "ref": "run://comparison/1"}],
                    "gaps": [],
                }
            ],
            "run_evidence": [{"kind": "harness_run", "ref": "run://standardize/1"}],
            "gaps": [],
        }
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
        release_version="0.1.0.dev5",
    )

    assert workflow.status is WorkflowStatus.RELEASED
    assert draft.status is WorkflowStatus.APPROVED
    assert release.to_dict()["schema"] == "scirel.release-manifest.dev"
    assert release.approved_assets == ("scirel.fixture.identity",)
    assert release.candidate_id == "candidate-run-1"
    assert release.candidate_digest.startswith("sha256:")
    assert release.draft_digest.startswith("sha256:")
    assert release.release_version == "0.1.0.dev5"
    assert release.release_digest.startswith("sha256:")


def test_model_submission_is_bound_and_queued_for_item_review():
    candidate = CandidatePackage.from_l1(
        {
            "assets": [{"candidate_asset_id": "candidate-field"}],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/standardization",
        source_digest="sha256:" + "1" * 64,
        run_id="run-standardization",
    )
    submission = standardization_submission(candidate)
    workflow = SciRelWorkflow(candidate)

    draft = workflow.submit_standardization(
        submission,
        expected_scirel_git_base="a" * 40,
        expected_candidate_pool_digest="sha256:" + "b" * 64,
        expected_skill_digest="sha256:" + "c" * 64,
    )

    assert workflow.status is WorkflowStatus.REVIEW_PENDING
    assert draft.status is WorkflowStatus.REVIEW_PENDING
    assert draft.assets == (ASSET_DOCUMENT,)
    batch_evidence, unit_evidence = draft.evidence
    assert batch_evidence["submission_digest"] == submission.submission_digest
    assert unit_evidence["asset_id"] == ASSET_DOCUMENT["asset_id"]
    assert unit_evidence["candidate_document"]["content"].startswith("# Candidate")
    assert unit_evidence["candidate_code"]["kind"] == "none"
    assert unit_evidence["candidate_tests"]["results"][0]["exit_code"] == 0


def no_change_submission_payload(*source_asset_ids: str):
    candidate = CandidatePackage.from_l1(
        {
            "assets": [{"candidate_asset_id": item} for item in source_asset_ids],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/reuse",
        source_digest="sha256:" + "1" * 64,
        run_id="run-reuse",
    )
    payload = standardization_submission(candidate).to_dict()
    payload["review_units"] = []
    payload["input_dispositions"] = [{
        "source_asset_ids": list(source_asset_ids),
        "disposition": "exact_duplicate",
        "target_asset_id": ASSET_DOCUMENT["asset_id"],
        "target_ref": "git://" + "a" * 40 + "/catalog/assets/fixture.json",
        "target_digest": digest(ASSET_DOCUMENT),
        "evidence": [{"kind": "comparison", "ref": "run://comparison/1"}],
    }]
    return candidate, payload


def test_no_change_submission_finishes_without_a_review_item_or_release():
    from scirel_plugin.adapter import review_items_from_body, review_ui_projection

    candidate, payload = no_change_submission_payload("candidate-field")
    submission = StandardizationSubmission.from_mapping(payload)
    workflow = SciRelWorkflow(candidate)

    assert workflow.submit_standardization(submission) is None
    assert workflow.status is WorkflowStatus.NO_CHANGES
    snapshot = workflow.to_dict()
    assert snapshot["draft"] is None
    assert snapshot["review"] is None
    assert snapshot["release"] is None
    assert snapshot["no_change_submission"] == submission.to_dict()
    assert SciRelWorkflow.from_dict(snapshot).to_dict() == snapshot
    assert review_items_from_body(json.dumps(snapshot).encode()) == []
    assert review_ui_projection(workflow)["available_actions"] == []
    with pytest.raises(WorkflowError):
        workflow.release(
            release_id="not-a-release",
            catalog_ref="artifact://catalog/dev",
            catalog_digest="sha256:" + "c" * 64,
            wheel_ref="artifact://wheel/dev",
            wheel_digest="sha256:" + "d" * 64,
            release_version="0.1.0.dev5",
        )
    with pytest.raises(WorkflowError, match="no-change"):
        workflow.create_draft(draft_id="unexpected", assets=[ASSET_DOCUMENT])
    with pytest.raises(WorkflowError, match="no-change"):
        workflow.submit_standardization(submission)
    with pytest.raises(WorkflowError, match="no-change"):
        workflow.apply_automated_result(AutomatedCheckResult(
            "new-result", candidate.candidate_id, candidate.source_digest,
            ({"name": "later", "status": "passed"},),
        ))


def test_no_change_completion_owns_nested_input_and_exported_snapshot():
    candidate, payload = no_change_submission_payload("candidate-field")
    payload["input_dispositions"][0]["evidence"][0]["metrics"] = {"error": 0.0}
    payload["run_evidence"][0]["runtime"] = {"version": "fixed"}
    submission = StandardizationSubmission.from_mapping(payload)
    original_submission = json.loads(json.dumps(submission.to_dict()))
    payload["input_dispositions"][0]["evidence"][0]["metrics"]["error"] = 99.0
    assert submission.to_dict() == original_submission

    workflow = SciRelWorkflow(candidate)
    workflow.submit_standardization(submission)
    expected = json.loads(json.dumps(workflow.to_dict()))
    expected_digest = workflow.record.no_change_submission.submission_digest

    # Mutating either the supplied model or its original payload cannot edit a
    # completed comparison, including metadata nested outside dispositions.
    submission.input_dispositions[0]["target_asset_id"] = "changed-after-submit"
    submission.input_dispositions[0]["evidence"][0]["metrics"]["error"] = 1.0
    submission.producer["skill"]["version"] = "changed-after-submit"
    payload["run_evidence"][0]["runtime"]["version"] = "changed-after-submit"
    assert workflow.to_dict() == expected
    assert workflow.record.no_change_submission.submission_digest == expected_digest

    exported = workflow.to_dict()
    exported["no_change_submission"]["input_dispositions"][0]["target_asset_id"] = "changed-export"
    exported["no_change_submission"]["input_dispositions"][0]["evidence"][0]["metrics"]["error"] = 2.0
    exported["no_change_submission"]["producer"]["skill"]["version"] = "changed-export"
    exported["candidate"]["assets"][0]["candidate_asset_id"] = "changed-export"
    assert workflow.to_dict() == expected
    assert workflow.record.no_change_submission.submission_digest == expected_digest


def test_no_change_restoration_owns_its_input_snapshot():
    candidate, payload = no_change_submission_payload("candidate-field")
    payload["run_evidence"][0]["runtime"] = {"version": "fixed"}
    workflow = SciRelWorkflow(candidate)
    workflow.submit_standardization(StandardizationSubmission.from_mapping(payload))
    snapshot = workflow.to_dict()
    restored = SciRelWorkflow.from_dict(snapshot)
    expected = json.loads(json.dumps(restored.to_dict()))
    expected_digest = restored.record.no_change_submission.submission_digest
    snapshot["no_change_submission"]["run_evidence"][0]["runtime"]["version"] = "modified"
    snapshot["no_change_submission"]["producer"]["skill"]["version"] = "modified"
    snapshot["no_change_submission"]["input_dispositions"][0]["target_asset_id"] = "modified"
    assert restored.to_dict() == expected
    assert restored.record.no_change_submission.submission_digest == expected_digest


def test_mixed_submission_queues_only_changed_assets_and_retains_reuse_lineage():
    from scirel_plugin.adapter import review_items_from_body

    candidate, payload = no_change_submission_payload("candidate-field", "duplicate")
    payload["input_dispositions"][0]["source_asset_ids"] = ["duplicate"]
    payload["review_units"] = standardization_submission(candidate).to_dict()["review_units"]
    payload["review_units"][0]["disposition"] = "new_capability"
    workflow = SciRelWorkflow(candidate)

    draft = workflow.submit_standardization(StandardizationSubmission.from_mapping(payload))

    assert workflow.status is WorkflowStatus.REVIEW_PENDING
    assert len(draft.assets) == 1
    disposition_evidence = [
        item for item in draft.evidence if item["kind"] == "standardization_input_disposition"
    ]
    assert disposition_evidence == [
        {"kind": "standardization_input_disposition", **payload["input_dispositions"][0]}
    ]
    snapshot = workflow.to_dict()
    assert "no_change_submission" not in snapshot
    assert len(review_items_from_body(json.dumps(snapshot).encode())) == 1
    assert SciRelWorkflow.from_dict(snapshot).to_dict() == snapshot


def test_mixed_submission_owns_new_disposition_evidence_on_input_and_export():
    candidate, payload = no_change_submission_payload("candidate-field", "duplicate")
    payload["input_dispositions"][0]["source_asset_ids"] = ["duplicate"]
    payload["input_dispositions"][0]["evidence"][0]["metrics"] = {"error": 0.0}
    payload["review_units"] = standardization_submission(candidate).to_dict()["review_units"]
    payload["review_units"][0]["disposition"] = "new_capability"
    submission = StandardizationSubmission.from_mapping(payload)
    workflow = SciRelWorkflow(candidate)
    draft = workflow.submit_standardization(submission)
    expected_digest = draft.draft_digest

    submission.input_dispositions[0]["source_asset_ids"].append("unvalidated-source")
    submission.input_dispositions[0]["evidence"][0]["metrics"]["error"] = 1.0
    assert draft.draft_digest == expected_digest

    snapshot = workflow.to_dict()
    for draft_record in (snapshot["draft"], *snapshot["drafts"]):
        item = next(
            item for item in draft_record["evidence"]
            if item["kind"] == "standardization_input_disposition"
        )
        item["source_asset_ids"].append("unvalidated-export")
        item["evidence"][0]["metrics"]["error"] = 2.0
    assert draft.draft_digest == expected_digest


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unknown"])
def test_input_dispositions_do_not_bypass_complete_unique_source_accounting(mutation):
    candidate, payload = no_change_submission_payload("candidate-field", "second")
    if mutation == "missing":
        payload["input_dispositions"][0]["source_asset_ids"] = ["candidate-field"]
        message = "does not account"
    elif mutation == "duplicate":
        payload["review_units"] = standardization_submission(candidate).to_dict()["review_units"]
        message = "more than once"
    else:
        payload["input_dispositions"][0]["source_asset_ids"].append("another-run")
        message = "unknown source"
    with pytest.raises(WorkflowError, match=message):
        SciRelWorkflow(candidate).submit_standardization(StandardizationSubmission.from_mapping(payload))


@pytest.mark.parametrize("field,value", [
    ("target_ref", ""), ("target_digest", "invalid"), ("evidence", []),
    ("disposition", "unresolved"),
])
def test_reuse_disposition_requires_exact_target_and_comparison_basis(field, value):
    _, payload = no_change_submission_payload("candidate-field")
    payload["input_dispositions"][0][field] = value
    with pytest.raises(ValueError):
        StandardizationSubmission.from_mapping(payload)


def test_no_change_submission_cannot_hide_unresolved_science():
    candidate, payload = no_change_submission_payload("candidate-field")
    payload["gaps"] = ["unresolved units"]
    with pytest.raises(WorkflowError, match="gaps"):
        SciRelWorkflow(candidate).submit_standardization(StandardizationSubmission.from_mapping(payload))


@pytest.mark.parametrize("mutation", ["source", "coverage", "checks", "gaps", "draft"])
def test_no_change_snapshot_revalidates_completion_and_cannot_gain_review_authority(mutation):
    candidate, payload = no_change_submission_payload("candidate-field")
    workflow = SciRelWorkflow(candidate)
    workflow.submit_standardization(StandardizationSubmission.from_mapping(payload))
    snapshot = workflow.to_dict()
    if mutation == "source":
        snapshot["no_change_submission"]["source_digest"] = "sha256:" + "0" * 64
    elif mutation == "coverage":
        snapshot["no_change_submission"]["input_dispositions"][0]["source_asset_ids"] = ["unknown"]
    elif mutation == "checks":
        snapshot["candidate"]["automated_checks"] = [{"name": "replay", "status": "failed"}]
    elif mutation == "gaps":
        snapshot["no_change_submission"]["gaps"] = ["unresolved science"]
    else:
        draft_workflow = SciRelWorkflow(candidate)
        draft = draft_workflow.create_draft(draft_id="injected", assets=[ASSET_DOCUMENT])
        snapshot["draft"] = draft.to_dict()
        snapshot["drafts"] = [draft.to_dict()]
        snapshot["status"] = "draft"
    with pytest.raises(WorkflowError):
        SciRelWorkflow.from_dict(snapshot)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("candidate_digest", "sha256:" + "0" * 64, "candidate digest"),
        ("source_digest", "sha256:" + "0" * 64, "source digest"),
        ("scirel_git_base", "d" * 40, "Git base"),
        ("candidate_pool_digest", "sha256:" + "d" * 64, "candidate-pool digest"),
    ],
)
def test_model_submission_rejects_stale_or_unrelated_bindings(field, value, message):
    candidate = CandidatePackage.from_l1(
        {
            "assets": [{"candidate_asset_id": "candidate-field"}],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/standardization",
        source_digest="sha256:" + "1" * 64,
        run_id="run-standardization-bindings",
    )
    payload = standardization_submission(candidate).to_dict()
    payload[field] = value
    submission = StandardizationSubmission.from_mapping(payload)

    with pytest.raises(WorkflowError, match=message):
        SciRelWorkflow(candidate).submit_standardization(
            submission,
            expected_scirel_git_base="a" * 40,
            expected_candidate_pool_digest="sha256:" + "b" * 64,
            expected_skill_digest="sha256:" + "c" * 64,
        )


def test_model_submission_must_account_for_every_candidate_asset():
    candidate = CandidatePackage.from_l1(
        {
            "assets": [
                {"candidate_asset_id": "candidate-field"},
                {"candidate_asset_id": "candidate-unaccounted"},
            ],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/standardization",
        source_digest="sha256:" + "1" * 64,
        run_id="run-standardization-coverage",
    )

    with pytest.raises(WorkflowError, match="does not account"):
        SciRelWorkflow(candidate).submit_standardization(
            standardization_submission(candidate)
        )


def test_model_submission_rejects_source_claimed_by_multiple_review_units():
    candidate = CandidatePackage.from_l1(
        {
            "assets": [{"candidate_asset_id": "candidate-field"}],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/standardization",
        source_digest="sha256:" + "1" * 64,
        run_id="run-standardization-duplicate-source",
    )
    payload = standardization_submission(candidate).to_dict()
    second = dict(payload["review_units"][0])
    second["review_unit_id"] = "unit-second"
    second["asset_document"] = {**ASSET_DOCUMENT, "asset_id": "scirel.fixture.second"}
    payload["review_units"].append(second)
    submission = StandardizationSubmission.from_mapping(payload)

    with pytest.raises(WorkflowError, match="more than once"):
        SciRelWorkflow(candidate).submit_standardization(submission)


def test_model_submission_rejects_modified_three_piece_content():
    candidate = CandidatePackage.from_l1(
        {
            "assets": [{"candidate_asset_id": "candidate-field"}],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/standardization",
        source_digest="sha256:" + "1" * 64,
        run_id="run-standardization-materials",
    )
    payload = standardization_submission(candidate).to_dict()
    payload["review_units"][0]["candidate_tests"]["content"] = {"files": {}}

    with pytest.raises(ValueError, match="candidate_tests.digest does not match"):
        StandardizationSubmission.from_mapping(payload)


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
        dependency_asset_ids=["scirel.fixture.related"],
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


def test_uploaded_draft_cannot_be_updated_before_expert_opens_it():
    workflow = SciRelWorkflow(ready_candidate())
    workflow.create_draft(
        draft_id="draft-frozen", assets=[ASSET_DOCUMENT]
    )
    workflow.submit_for_review()

    with pytest.raises(WorkflowError, match="only a pre-upload draft"):
        workflow.update_open_draft(
            assets=[ASSET_DOCUMENT],
            evidence=[
                {"kind": "queue-revision", "ref": "artifact://candidate/a-plus"}
            ],
        )

    assert workflow.status is WorkflowStatus.REVIEW_PENDING


def test_l1_candidate_preserves_one_project_id():
    candidate = CandidatePackage.from_l1(
        {
            "project": "synthetic",
            "assets": [{"candidate_asset_id": "synthetic.field"}],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/synthetic",
        source_digest="sha256:synthetic",
        run_id="run-project",
    )

    assert candidate.project_id == "synthetic"
    assert candidate.to_dict()["project_id"] == "synthetic"


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
                "projects": [{"project_id": "samplewave"}, {"project_id": "sampleflow"}],
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
        release_version="0.1.0.dev5",
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
        assets=[{"asset_id": "scirel.fixture.incomplete"}],
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
    incomplete = {"asset_id": "scirel.fixture.incomplete"}
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
        ("approved_assets", ["scirel.fixture.other"], "asset set does not match"),
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
        release_version="0.1.0.dev5",
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
        release_version="0.1.0.dev5",
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
        source_artifact_ref="artifact://l1/synthetic",
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
            "asset_id": "scirel.fixture.incomplete",
            "tenant_id": "must-not-enter-the-contract",
        }],
    )

    assert "scientific_contract_missing:scirel.fixture.incomplete:schema" in draft.gaps
    assert (
        "scientific_contract_unknown:scirel.fixture.incomplete:tenant_id" in draft.gaps
    )
    assert (
        "scientific_contract_private:scirel.fixture.incomplete:tenant_id" in draft.gaps
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
        assets=[{"asset_id": "scirel.fixture.example"}],
    )
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision("draft-first", ReviewOutcome.REWORK_REQUESTED, "expert-1")
    )

    revised = workflow.create_draft(
        draft_id="draft-second",
        assets=[{"asset_id": "scirel.fixture.example"}],
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
            plugin_context_ref="run-1",
            correlation_id="job-1",
        )

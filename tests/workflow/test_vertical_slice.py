"""One local L1 -> release run without CodeFusion or source-project access."""

import json
from pathlib import Path

import pytest

from scirel_plugin import FakeHost, SciRelPlugin
from scirel_workflow import (
    AutomatedCheckResult,
    CandidatePackage,
    ReviewOutcome,
    SciRelWorkflow,
    WorkflowError,
    WorkflowStatus,
)
FIXTURE = Path(__file__).parents[1] / "fixtures" / "l1" / "synthetic-minimal.json"
ASSET_DOCUMENT = json.loads(
    (
        Path(__file__).parents[2]
        / "tests/fixtures/contracts/fixture-identity.json"
    ).read_text(encoding="utf-8")
)


def test_saved_l1_runs_to_release_with_host_adapter():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    run_id = "run-vertical-synthetic"

    host = FakeHost(tenant_id="tenant-test", project_id="project-scirel")
    plugin = SciRelPlugin.for_development(host)
    source_artifact = host.put_artifact("scirel.l1-payload.dev", payload)
    handoff = plugin.import_l1_artifact(
        source_artifact,
        run_id=run_id,
    )
    source_ref = source_artifact.ref
    source_digest = source_artifact.digest

    workflow = SciRelWorkflow(
        CandidatePackage.from_l1(
            payload,
            source_artifact_ref=source_ref,
            source_digest=source_digest,
            run_id=run_id,
        )
    )
    assert workflow.status is WorkflowStatus.AUTOMATED_READY

    draft = workflow.create_draft(
        draft_id="draft-vertical-synthetic",
        assets=[ASSET_DOCUMENT],
        evidence=[{"kind": "direct_test", "ref": "tests/fixtures/runtime/check_identity.py"}],
    )
    draft_artifact = plugin.publish_draft(draft)
    workflow.submit_for_review()
    workflow.start_review()
    review_result = plugin.record_review_action(
        workflow,
        ReviewOutcome.APPROVED.value,
        notes="fixture checked",
        correlation_id="workbench://vertical/review",
    )
    release_result = plugin.complete_release(
        workflow,
        release_id="release-vertical-synthetic",
        catalog_ref="artifact://catalog/dev/vertical",
        catalog_digest="sha256:" + "c" * 64,
        wheel_ref="artifact://wheel/dev/vertical",
        wheel_digest="sha256:" + "d" * 64,
        correlation_id="build://vertical/release",
        release_version="0.1.0.dev5",
    )
    release = release_result.release

    assert workflow.status is WorkflowStatus.RELEASED
    assert handoff.artifact.ref in host.artifacts
    assert draft_artifact.ref in host.artifacts
    assert review_result.decision_artifact.ref in host.artifacts
    assert release_result.release_artifact.ref in host.artifacts
    assert release.candidate_id == "candidate-run-vertical-synthetic"
    assert release.candidate_digest == workflow.record.candidate.package_digest
    assert release.draft_digest == draft.draft_digest
    assert host.jobs[0][1] == (handoff.artifact.ref,)
    assert release_result.event.event_type == "scirel.release.completed"
    assert json.loads(host.read_artifact(release_result.state_artifact.ref))["status"] == "released"


def test_host_result_artifact_cannot_repair_l1_gap():
    payload = {
        "assets": [{"l1_asset_id": "sample:operator:leaf"}],
        "automated_checks": [{
            "name": "direct_test_mapping",
            "status": "failed",
            "issues": [{
                "code": "missing_direct_test_mapping",
                "automation": "discover_or_generate_test",
            }],
        }],
        "gaps": ["missing direct test"],
    }
    host = FakeHost(project_id="project-scirel")
    plugin = SciRelPlugin.for_development(host)
    candidate = CandidatePackage.from_l1(
        payload,
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id="run-gap-repair",
    )
    workflow = SciRelWorkflow(candidate)
    assert workflow.status is WorkflowStatus.AUTOMATED_REJECTED

    result_artifact = plugin.publish_automated_result(
        AutomatedCheckResult(
            result_id="check-gap-repair",
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            checks=({"name": "direct_test_mapping", "status": "passed"},),
            evidence_refs=("artifact://evidence/generated-test",),
        )
    )
    repaired = plugin.import_automated_result_artifact(candidate, result_artifact)
    workflow.apply_automated_result(
        AutomatedCheckResult.from_mapping(json.loads(host.read_artifact(result_artifact.ref)))
    )

    assert not repaired.automated_ready
    assert workflow.status is WorkflowStatus.AUTOMATED_REJECTED
    with pytest.raises(WorkflowError, match="automated checks"):
        workflow.create_draft(
            draft_id="draft-gap-unresolved", assets=[{"asset_id": "scirel.x"}]
        )


def test_automated_result_cannot_clear_inventory_gaps():
    payload = {
        "assets": [
            {
                "l1_asset_id": "cql3d:operator:solver",
                "asset_path": "operators/solver",
                "direct_test_path": None,
            },
            {
                "l1_asset_id": "sampleflow:task_graph:workflow",
                "asset_path": "task_graphs/workflow",
                "dependency_refs": ["operators/solver-missing"],
            },
        ],
        "automated_checks": [],
    }
    candidate = CandidatePackage.from_l1(
        payload,
        source_artifact_ref="artifact://l1/minimal-closed-loop",
        source_digest="sha256:source",
        run_id="run-unrepaired-gaps",
    )
    workflow = SciRelWorkflow(candidate)

    repaired = workflow.apply_automated_result(
        AutomatedCheckResult(
            result_id="check-false-pass",
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            checks=({"name": "all", "status": "passed"},),
        )
    )

    assert not repaired.automated_ready
    assert "missing_direct_test_mapping:cql3d:operator:solver" in repaired.gaps
    assert (
        "unresolved_task_graph_dependency:sampleflow:task_graph:workflow -> operators/solver-missing"
        in repaired.gaps
    )
    assert workflow.status is WorkflowStatus.AUTOMATED_REJECTED


def test_automated_result_cannot_clear_task_graph_cycle():
    candidate = CandidatePackage.from_l1(
        {
            "assets": [
                {
                    "l1_asset_id": "sample:task_graph:a",
                    "asset_path": "task_graphs/a",
                    "asset_kind": "task_graph",
                    "dependency_refs": ["task_graphs/b"],
                },
                {
                    "l1_asset_id": "sample:task_graph:b",
                    "asset_path": "task_graphs/b",
                    "asset_kind": "task_graph",
                    "dependency_refs": ["task_graphs/a"],
                },
            ],
            "automated_checks": [{"name": "dependency_closure", "status": "failed"}],
            "gaps": [
                "dependency_closure: task_graphs/a -> task_graphs/b -> task_graphs/a"
            ],
        },
        source_artifact_ref="artifact://l1/sample-cycle",
        source_digest="sha256:source",
        run_id="run-unrepaired-cycle",
    )
    workflow = SciRelWorkflow(candidate)

    repaired = workflow.apply_automated_result(
        AutomatedCheckResult(
            result_id="check-false-cycle-pass",
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            checks=({"name": "dependency_closure", "status": "passed"},),
        )
    )

    assert not repaired.automated_ready
    assert any(gap.startswith("task_graph_cycle:") for gap in repaired.gaps)
    assert workflow.status is WorkflowStatus.AUTOMATED_REJECTED

def test_automated_result_keeps_unreported_failed_checks_blocking():
    candidate = CandidatePackage.from_l1(
        {
            "assets": [{"l1_asset_id": "sample:operator:leaf"}],
            "automated_checks": [
                {"name": "direct_test_mapping", "status": "failed"},
                {"name": "license", "status": "failed"},
            ],
            "gaps": [],
        },
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id="run-partial-result",
    )
    workflow = SciRelWorkflow(candidate)

    repaired = workflow.apply_automated_result(
        AutomatedCheckResult(
            result_id="check-partial-result",
            candidate_id=candidate.candidate_id,
            source_digest=candidate.source_digest,
            checks=({"name": "direct_test_mapping", "status": "passed"},),
        )
    )

    assert not repaired.automated_ready
    assert repaired.automated_checks[-1]["name"] == "license"
    assert workflow.status is WorkflowStatus.AUTOMATED_REJECTED


def test_automated_result_contract_rejects_asset_updates():
    result = AutomatedCheckResult(
        result_id="check-no-patches",
        candidate_id="candidate-sample",
        source_digest="sha256:source",
        checks=({"name": "inventory", "status": "passed"},),
    ).to_dict()
    result["asset_updates"] = [{"l1_asset_id": "sample:operator:leaf"}]

    with pytest.raises(ValueError, match="unknown fields: asset_updates"):
        AutomatedCheckResult.from_mapping(result)

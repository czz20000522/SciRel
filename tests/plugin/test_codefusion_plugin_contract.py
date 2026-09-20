"""Contract tests for the narrow CodeFusion host adapter."""

import json
from pathlib import Path
import pytest

from scirel_plugin import (
    ArtifactReference,
    ArtifactRef,
    FakeHost,
    PluginCommandEnvelope,
    PluginContractError,
    PluginEventEnvelope,
    PluginReleaseSnapshot,
    PluginScope,
    PluginRunSubmitEnvelope,
    PluginRunResult,
    SciRelPlugin,
    execute_automated_check,
    SERVICE_PRINCIPAL_SCOPES,
    SciRelBodyImportRequest,
    execute_body_import,
    execute_body_import_wire,
    validate_review_item_snapshot_body,
)


ASSET_DOCUMENT = json.loads(
    (
        Path(__file__).parents[2]
        / "catalog/examples/scirel.field.circular-filament-green.json"
    ).read_text(encoding="utf-8")
)
from scirel_workflow import (
    AutomatedCheckResult,
    CandidatePackage,
    ReleaseManifest,
    ReviewDecision,
    ReviewOutcome,
    StandardizedDraft,
    SciRelWorkflow,
    WorkflowStatus,
)


PLUGIN_RELEASE_REF = "plugin-release://scirel/0.1.0.dev5/example-20260920"


def candidate() -> CandidatePackage:
    return CandidatePackage.from_l1(
        {"assets": [{"candidate_asset_id": "candidate-field"}], "automated_checks": [{"name": "replay", "status": "passed"}]},
        source_artifact_ref="artifact://l1/pleiades",
        source_digest="sha256:l1",
        run_id="run-plugin",
    )


def test_plugin_publishes_candidate_as_artifact_and_job():
    host = FakeHost(user="reviewer-1")
    plugin = SciRelPlugin.for_development(host)

    handoff = plugin.publish_candidate(candidate())

    assert plugin.descriptor()["plugin_id"] == "scirel"
    assert handoff.artifact.kind == "scirel.candidate-package.dev"
    assert handoff.job.operation == "scirel.automated_check"
    assert host.read_artifact(handoff.artifact.ref)
    assert host.jobs == [(handoff.job, (handoff.artifact.ref,))]

    command = host.commands[0]
    assert isinstance(command, PluginCommandEnvelope)
    assert command.command == "scirel.automated_check"
    assert command.scope.plugin_id == "scirel"
    assert command.scope.workflow_run_id == "run-plugin"
    assert command.input_artifacts[0].artifact_ref == handoff.artifact.ref
    assert command.input_artifacts[0].media_type == "application/json"
    assert command.payload == {
        "operation": "scirel.automated_check",
        "candidate_id": candidate().candidate_id,
        "candidate_digest": candidate().package_digest,
        "source_digest": candidate().source_digest,
    }
    assert command.idempotency_key.startswith("scirel:command:")


def test_plugin_publishes_sci_rel_owned_workflow_state():
    host = FakeHost(user="reviewer-1")
    plugin = SciRelPlugin.for_development(host)
    workflow = SciRelWorkflow(candidate())

    artifact = plugin.publish_workflow_state(workflow)

    assert artifact.kind == "scirel.workflow-state.dev"
    payload = json.loads(host.read_artifact(artifact.ref))
    assert payload["schema"] == "scirel.workflow-state.dev"
    assert payload["candidate"]["candidate_id"] == candidate().candidate_id
    assert "tenant_id" not in payload
    assert "job_id" not in payload


def test_body_runner_replays_ready_candidate_as_domain_result():
    value = candidate()
    result = AutomatedCheckResult.from_mapping(
        json.loads(
            execute_automated_check(
                json.dumps(value.to_dict(), ensure_ascii=False).encode("utf-8"),
                candidate_id=value.candidate_id,
                source_digest=value.source_digest,
                result_id="result-body-runner",
            )
        )
    )

    assert result.passed
    assert result.next_action == "ready"
    assert result.candidate_id == value.candidate_id


def test_body_runner_rejects_unknown_candidate_fields():
    candidate_payload = candidate().to_dict()
    candidate_payload["job_id"] = "must-not-enter-domain"
    body = json.dumps(candidate_payload).encode("utf-8")

    with pytest.raises(ValueError, match="unknown fields: job_id"):
        execute_automated_check(
            body,
            candidate_id=candidate_payload["candidate_id"],
            source_digest=candidate_payload["source_digest"],
            result_id="result-strict-candidate",
        )
def test_body_runner_classifies_repairable_inventory_gap_for_retry():
    value = CandidatePackage.from_l1(
        {
            "assets": [{
                "l1_asset_id": "sample:operator:leaf",
                "asset_path": "operators/leaf",
                "direct_test_path": None,
            }],
            "automated_checks": [{
                "name": "direct_test_mapping",
                "status": "failed",
                "issues": [{"automation": "discover_or_generate_test"}],
            }],
            "gaps": ["missing_direct_test_mapping:sample:operator:leaf"],
        },
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id="run-body-repair",
    )

    result = AutomatedCheckResult.from_mapping(
        json.loads(
            execute_automated_check(
                json.dumps(value.to_dict()).encode("utf-8"),
                candidate_id=value.candidate_id,
                source_digest=value.source_digest,
                result_id="result-body-repair",
            )
        )
    )

    assert not result.passed
    assert result.next_action == "retry"
    assert result.gaps == (
        "missing_direct_test_mapping:sample:operator:leaf",
    )


def test_body_runner_routes_unautomated_scientific_gap_to_needs_evidence():
    value = CandidatePackage.from_l1(
        {
            "assets": [{"candidate_asset_id": "sample:operator:leaf"}],
            "automated_checks": [{
                "name": "scientific_evidence",
                "status": "failed",
                "issues": [{"code": "missing_validation_evidence"}],
            }],
            "gaps": ["missing_validation_evidence:sample:operator:leaf"],
        },
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id="run-needs-evidence",
    )

    result = AutomatedCheckResult.from_mapping(
        json.loads(
            execute_automated_check(
                json.dumps(value.to_dict()).encode("utf-8"),
                candidate_id=value.candidate_id,
                source_digest=value.source_digest,
                result_id="result-needs-evidence",
            )
        )
    )

    assert result.next_action == "needs_evidence"
    assert not result.passed


def test_body_runner_rejects_mismatched_candidate_identity():
    value = candidate()
    with pytest.raises(ValueError, match="candidate_id does not match"):
        execute_automated_check(
            json.dumps(value.to_dict()).encode("utf-8"),
            candidate_id="candidate-other",
            source_digest=value.source_digest,
            result_id="result-body-mismatch",
        )


def test_body_runner_classifies_task_graph_cycle_as_rework():
    value = CandidatePackage.from_l1(
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
            "automated_checks": [{
                "name": "dependency_closure",
                "status": "failed",
                "issues": [{"automation": "request_rework"}],
            }],
            "gaps": ["task_graph_cycle: task_graphs/a -> task_graphs/b -> task_graphs/a"],
        },
        source_artifact_ref="artifact://l1/sample-cycle",
        source_digest="sha256:source",
        run_id="run-body-cycle",
    )

    result = AutomatedCheckResult.from_mapping(
        json.loads(
            execute_automated_check(
                json.dumps(value.to_dict()).encode("utf-8"),
                candidate_id=value.candidate_id,
                source_digest=value.source_digest,
                result_id="result-body-cycle",
            )
        )
    )

    assert result.next_action == "rework_requested"


def test_neutral_body_import_adapter_creates_candidate_artifact_body():
    import hashlib

    body = json.dumps(
        {"assets": [], "automated_checks": [{"name": "replay", "status": "passed"}]}
    ).encode("utf-8")
    response = execute_body_import(
        SciRelBodyImportRequest(
            operation="scirel.import_l1",
            artifact_ref="cf://l1/source",
            artifact_digest="sha256:" + hashlib.sha256(body).hexdigest(),
            media_type="application/json",
            body=body,
        )
    )

    assert response.artifact_kind == "scirel.candidate-package.dev"
    assert response.body_digest.startswith("sha256:")
    candidate_body = json.loads(response.body)
    expected_run_id = "run-" + hashlib.sha256(body).hexdigest()
    assert candidate_body["run_id"] == expected_run_id
    assert candidate_body["candidate_id"] == "candidate-" + expected_run_id
    assert candidate_body["source_artifact_ref"] == "cf://l1/source"


def test_neutral_body_import_adapter_creates_automated_result_body():
    import hashlib

    value = candidate()
    body = json.dumps(value.to_dict()).encode("utf-8")
    response = execute_body_import(
        SciRelBodyImportRequest(
            operation="scirel.automated_check",
            artifact_ref="cf://candidate/plugin",
            artifact_digest="sha256:" + hashlib.sha256(body).hexdigest(),
            media_type="application/json",
            body=body,
        )
    )

    assert response.artifact_kind == "scirel.automated-check-result.dev"
    result_body = json.loads(response.body)
    assert result_body["next_action"] == "ready"
    assert result_body["candidate_id"] == value.candidate_id
    assert result_body["result_id"] == "result-" + hashlib.sha256(body).hexdigest()


def test_neutral_body_import_adapter_rejects_tampered_body():
    import hashlib

    body = b"{}"
    with pytest.raises(ValueError, match="digest does not match"):
        execute_body_import(
            SciRelBodyImportRequest(
                operation="scirel.import_l1",
                artifact_ref="cf://l1/source",
                artifact_digest="sha256:" + hashlib.sha256(body).hexdigest(),
                media_type="application/json",
                body=body + b" ",
            )
        )


def test_neutral_body_import_adapter_round_trips_utf8_wire_request_and_response():
    import hashlib

    body = "{\"资产\": []}".encode("utf-8")
    request = SciRelBodyImportRequest(
        operation="scirel.import_l1",
        artifact_ref="cf://l1/utf8",
        artifact_digest="sha256:" + hashlib.sha256(body).hexdigest(),
        media_type="application/json",
        body=body,
    )
    restored = SciRelBodyImportRequest.from_wire(request.to_wire())

    assert restored == request
    response = execute_body_import(
        SciRelBodyImportRequest(
            operation="scirel.import_l1",
            artifact_ref="cf://l1/source",
            artifact_digest="sha256:" + hashlib.sha256(b'{"assets":[]}').hexdigest(),
            media_type="application/json",
            body=b'{"assets":[]}',
        )
    )
    wire = response.to_wire()
    assert wire["body"].encode("utf-8") == response.body
    assert wire["body_digest"] == response.body_digest


def test_wire_handler_is_ready_for_a_thin_http_transport():
    import hashlib

    body = b'{"assets": [], "automated_checks": [{"name": "replay", "status": "passed"}]}'
    response = execute_body_import_wire(
        {
            "operation": "scirel.import_l1",
            "artifact_ref": "cf://l1/http",
            "artifact_digest": "sha256:" + hashlib.sha256(body).hexdigest(),
            "media_type": "application/json",
            "body": body.decode("utf-8"),
        }
    )

    assert response["operation"] == "scirel.import_l1"
    assert response["artifact_kind"] == "scirel.candidate-package.dev"
    result_body = response["body"].encode("utf-8")
    assert response["body_digest"] == "sha256:" + hashlib.sha256(result_body).hexdigest()
    assert json.loads(response["body"])["source_artifact_ref"] == "cf://l1/http"


def test_l1_wire_keeps_host_source_identity_in_artifact_fields_only():
    import hashlib

    body = b'{"assets": [], "automated_checks": []}'
    payload = {
        "operation": "scirel.import_l1",
        "artifact_ref": "cf://l1/identity",
        "artifact_digest": "sha256:" + hashlib.sha256(body).hexdigest(),
        "media_type": "application/json",
        "body": body.decode("utf-8"),
        "source_artifact_ref": "cf://l1/identity",
    }

    with pytest.raises(ValueError, match="unknown fields: source_artifact_ref"):
        SciRelBodyImportRequest.from_wire(payload)


def test_wire_handler_runs_automated_check_without_platform_fields():
    import hashlib

    value = candidate()
    body = json.dumps(value.to_dict(), ensure_ascii=False).encode("utf-8")
    response = execute_body_import_wire(
        {
            "operation": "scirel.automated_check",
            "artifact_ref": "cf://candidate/http",
            "artifact_digest": "sha256:" + hashlib.sha256(body).hexdigest(),
            "media_type": "application/json",
            "body": body.decode("utf-8"),
        }
    )

    assert response["operation"] == "scirel.automated_check"
    assert response["artifact_kind"] == "scirel.automated-check-result.dev"
    assert set(response) == {
        "operation", "artifact_kind", "media_type", "body", "body_digest"
    }
    assert "tenant_id" not in response
    assert "job_id" not in response
    result_body = response["body"].encode("utf-8")
    assert response["body_digest"] == "sha256:" + hashlib.sha256(result_body).hexdigest()
    assert json.loads(response["body"])["next_action"] == "ready"


def test_review_list_and_open_use_one_exact_state_body_wire():
    import hashlib

    workflow = SciRelWorkflow(candidate())
    workflow.create_draft(draft_id="draft-wire-open", assets=[ASSET_DOCUMENT])
    workflow.submit_for_review()
    body = json.dumps(
        workflow.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    revision = "sha256:" + hashlib.sha256(body).hexdigest()
    base = {
        "artifact_ref": "cf://state/review-wire-open",
        "artifact_digest": revision,
        "media_type": "application/json",
        "body": body.decode("utf-8"),
    }

    listed = execute_body_import_wire(
        {"operation": "scirel.review.list_items", **base}
    )
    index = json.loads(listed["body"])
    assert listed["artifact_kind"] == "scirel.review-item-index.dev"
    assert len(index["items"]) == 1
    assert "workflow" not in index
    item = index["items"][0]
    assert item["revision"] == revision

    open_request = {
        "operation": "scirel.review.open_item",
        **base,
        "operation_payload": {
            "item_ref": item["item_ref"],
            "revision": item["revision"],
        },
    }
    opened = execute_body_import_wire(open_request)
    replay = execute_body_import_wire(open_request)
    snapshot = json.loads(opened["body"])

    assert opened == replay
    assert opened["artifact_kind"] == "scirel.review-item-snapshot.dev"
    assert snapshot["item_ref"] == item["item_ref"]
    assert snapshot["opened_from"] == {
        "artifact_ref": base["artifact_ref"],
        "revision": revision,
    }
    assert snapshot["view"]["workflow"]["status"] == "review_in_progress"
    restored = validate_review_item_snapshot_body(
        opened["body"].encode("utf-8"),
        item_ref=item["item_ref"],
        revision=item["revision"],
    )
    assert restored.status is WorkflowStatus.REVIEW_IN_PROGRESS


def test_review_open_wire_rejects_missing_payload_and_stale_revision():
    import hashlib

    workflow = SciRelWorkflow(candidate())
    workflow.create_draft(draft_id="draft-wire-stale", assets=[ASSET_DOCUMENT])
    workflow.submit_for_review()
    body = json.dumps(
        workflow.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    revision = "sha256:" + hashlib.sha256(body).hexdigest()
    base = {
        "operation": "scirel.review.open_item",
        "artifact_ref": "cf://state/review-wire-stale",
        "artifact_digest": revision,
        "media_type": "application/json",
        "body": body.decode("utf-8"),
    }

    with pytest.raises(ValueError, match="operation_payload"):
        execute_body_import_wire(base)
    with pytest.raises(ValueError, match="revision does not match"):
        execute_body_import_wire(
            {
                **base,
                "operation_payload": {
                    "item_ref": "scirel-review-item:" + "0" * 64,
                    "revision": "sha256:" + "0" * 64,
                },
            }
        )


@pytest.mark.parametrize(
    "field", ["candidate_id", "source_digest", "run_id", "result_id"]
)
def test_wire_request_rejects_top_level_domain_authority(field):
    import hashlib

    body = b'{"assets": []}'
    payload = {
        "operation": "scirel.import_l1",
        "artifact_ref": "cf://l1/strict-envelope",
        "artifact_digest": "sha256:" + hashlib.sha256(body).hexdigest(),
        "media_type": "application/json",
        "body": body.decode("utf-8"),
        field: "not-allowed",
    }

    with pytest.raises(ValueError, match=f"unknown fields: {field}"):
        SciRelBodyImportRequest.from_wire(payload)


@pytest.mark.parametrize("field", ["operation", "artifact_ref", "artifact_digest", "media_type"])
def test_wire_request_rejects_non_string_contract_fields(field):
    payload = {
        "operation": "scirel.import_l1",
        "artifact_ref": "cf://l1/type-check",
        "artifact_digest": "sha256:" + "0" * 64,
        "media_type": "application/json",
        "body": "{}",
    }
    payload[field] = 7

    with pytest.raises(ValueError, match=f"{field} must be a string"):
        SciRelBodyImportRequest.from_wire(payload)


def test_wire_request_rejects_non_json_media_type():
    import hashlib

    body = "{}"
    with pytest.raises(ValueError, match="media_type must be application/json"):
        SciRelBodyImportRequest.from_wire({
            "operation": "scirel.import_l1",
            "artifact_ref": "cf://l1/wrong-media",
            "artifact_digest": "sha256:" + hashlib.sha256(body.encode()).hexdigest(),
            "media_type": "text/plain",
            "body": body,
        })


def test_plugin_builds_generic_run_submission_for_candidate_artifact():
    host = FakeHost(tenant_id="tenant-a", project_id="project-a")
    plugin = SciRelPlugin.for_development(host)
    candidate_value = candidate()
    artifact = host.put_artifact(
        "scirel.candidate-package.dev", candidate_value.to_dict()
    )

    envelope = plugin.build_candidate_run_submission(
        candidate_value,
        artifact,
        tenant_id="tenant-a",
        project_id="project-a",
    )
    envelope.validate(plugin.registration())

    assert isinstance(envelope, PluginRunSubmitEnvelope)
    assert envelope.scope.workflow_run_id == candidate_value.run_id
    assert envelope.input_artifacts[0].artifact_ref == artifact.ref
    assert envelope.input_artifacts[0].digest == artifact.digest
    assert envelope.payload["operation"] == "scirel.automated_check"
    assert envelope.payload["candidate_id"] == candidate_value.candidate_id


def test_candidate_run_rejects_cross_project_scope_and_wrong_artifact():
    host = FakeHost(tenant_id="tenant-a", project_id="project-a")
    plugin = SciRelPlugin.for_development(host)
    candidate_value = CandidatePackage.from_l1(
        {
            "project_id": "project-a",
            "assets": [{"candidate_asset_id": "candidate-field"}],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/project-a",
        source_digest="sha256:project-a",
        run_id="run-project-a",
    )
    artifact = host.put_artifact(
        "scirel.candidate-package.dev", candidate_value.to_dict()
    )

    with pytest.raises(ValueError, match="does not match host project scope"):
        plugin.build_candidate_run_submission(
            candidate_value,
            artifact,
            tenant_id="tenant-a",
            project_id="project-b",
        )

    wrong_kind = host.put_artifact("scirel.l1-source.dev", candidate_value.to_dict())
    with pytest.raises(ValueError, match="candidate-package artifact"):
        plugin.build_candidate_run_submission(
            candidate_value,
            wrong_kind,
            tenant_id="tenant-a",
            project_id="project-a",
        )

    wrong_digest = host.put_artifact(
        "scirel.candidate-package.dev",
        {**candidate_value.to_dict(), "candidate_id": "candidate-other"},
    )
    with pytest.raises(ValueError, match="digest does not match"):
        plugin.build_candidate_run_submission(
            candidate_value,
            wrong_digest,
            tenant_id="tenant-a",
            project_id="project-a",
        )


def test_plugin_builds_explicit_l1_import_run_submission():
    host = FakeHost(tenant_id="tenant-a", project_id="project-a")
    plugin = SciRelPlugin.for_development(host)
    source = host.put_artifact(
        "scirel.l1-source.dev",
        {"assets": [], "automated_checks": []},
    )

    envelope = plugin.build_l1_run_submission(
        source,
        tenant_id="tenant-a",
        project_id="project-a",
        workflow_run_id="run-l1-import",
    )
    envelope.validate(plugin.registration())

    assert envelope.scope.workflow_run_id == "run-l1-import"
    assert envelope.input_artifacts == (source.as_contract(),)
    assert envelope.payload == {
        "operation": "scirel.import_l1",
    }


def test_plugin_publishes_draft_and_registers_scientific_review_view():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    draft = StandardizedDraft(
        draft_id="draft-plugin",
        candidate_id="candidate-run-plugin",
        assets=({"asset_id": "scirel.field.example"},),
        dependency_asset_ids=(),
        evidence=({"kind": "test", "ref": "tests/example.py"},),
    )

    artifact = plugin.publish_draft(draft)

    assert artifact.kind == "scirel.standardized-draft.dev"
    view = host.review_views["scirel:scirel.review"]
    assert view.operations == (
        "scirel.review.list_items",
        "scirel.review.open_item",
    )


def test_review_list_is_bounded_minimal_and_does_not_observe_candidate():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    workflow = SciRelWorkflow(candidate())
    workflow.create_draft(draft_id="draft-list", assets=[ASSET_DOCUMENT])
    workflow.submit_for_review()
    current = plugin.publish_workflow_state(workflow)

    result = plugin.list_review_items((current,), limit=1)

    assert result["schema"] == "scirel.review-item-index.dev"
    assert result["has_more"] is False
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert set(item) == {
        "item_ref",
        "revision",
        "display_index",
        "detail_action_ref",
    }
    assert item["revision"] == current.digest
    assert item["item_ref"].startswith("scirel-review-item:")
    assert item["detail_action_ref"].startswith("plugin://scirel/review/open/")
    assert "workflow" not in result
    assert workflow.status is WorkflowStatus.REVIEW_PENDING


def test_review_open_returns_idempotent_exact_snapshot_without_host_side_state():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    workflow = SciRelWorkflow(candidate())
    workflow.create_draft(draft_id="draft-open", assets=[ASSET_DOCUMENT])
    workflow.submit_for_review()
    current = plugin.publish_workflow_state(workflow)
    item = plugin.list_review_items((current,))["items"][0]

    opened = plugin.open_review_item(
        current,
        item_ref=item["item_ref"],
        revision=item["revision"],
    )
    replay = plugin.open_review_item(
        current,
        item_ref=item["item_ref"],
        revision=item["revision"],
    )

    assert opened == replay
    assert opened.kind == "scirel.review-item-snapshot.dev"
    restored = plugin.validate_review_item_snapshot(
        opened,
        item_ref=item["item_ref"],
        revision=item["revision"],
    )
    assert restored.status is WorkflowStatus.REVIEW_IN_PROGRESS
    assert workflow.status is WorkflowStatus.REVIEW_PENDING


def test_review_open_rejects_stale_revision_and_wrong_item_ref():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    workflow = SciRelWorkflow(candidate())
    workflow.create_draft(draft_id="draft-stale", assets=[ASSET_DOCUMENT])
    workflow.submit_for_review()
    current = plugin.publish_workflow_state(workflow)
    item = plugin.list_review_items((current,))["items"][0]

    with pytest.raises(ValueError, match="revision"):
        plugin.open_review_item(
            current,
            item_ref=item["item_ref"],
            revision="sha256:" + "0" * 64,
        )
    with pytest.raises(ValueError, match="item ref"):
        plugin.open_review_item(
            current,
            item_ref="scirel-review-item:" + "0" * 64,
            revision=item["revision"],
        )


def test_plugin_imports_l1_and_publishes_review_artifact():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)

    handoff = plugin.import_l1(
        {"assets": [], "automated_checks": [{"name": "replay", "status": "passed"}]},
        source_artifact_ref="artifact://l1/example",
        source_digest="sha256:l1",
        run_id="run-import",
    )
    review = plugin.publish_review(
        ReviewDecision("draft-import", ReviewOutcome.NEEDS_EVIDENCE, "expert-1")
    )

    assert handoff.artifact.kind == "scirel.candidate-package.dev"
    assert review.kind == "scirel.review-decision.dev"


def test_plugin_imports_l1_from_saved_host_artifact():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    source = host.put_artifact(
        "scirel.l1-payload.dev",
        {"assets": [], "automated_checks": [{"name": "replay", "status": "passed"}]},
    )

    handoff = plugin.import_l1_artifact(source, run_id="run-artifact-import")

    assert handoff.artifact.ref in host.artifacts
    assert host.commands[0].scope.workflow_run_id == "run-artifact-import"
    assert host.commands[0].input_artifacts[0].digest == handoff.artifact.digest


def test_plugin_imports_l1_from_host_supplied_body():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    source = host.put_artifact(
        "scirel.l1-payload.dev",
        {"assets": [], "automated_checks": [{"name": "replay", "status": "passed"}]},
    )

    handoff = plugin.import_l1_body(
        host.read_artifact(source.ref),
        source_artifact_ref=source.ref,
        source_digest=source.digest,
        run_id="run-body-import",
    )

    assert handoff.artifact.ref in host.artifacts
    assert host.commands[0].scope.workflow_run_id == "run-body-import"

    with pytest.raises(ValueError, match="digest does not match"):
        plugin.import_l1_body(
            host.read_artifact(source.ref) + b" ",
            source_artifact_ref=source.ref,
            source_digest=source.digest,
            run_id="run-body-import-tampered",
        )


def test_plugin_publishes_and_applies_automated_result_artifact():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    original = CandidatePackage.from_l1(
        {
            "assets": [{"l1_asset_id": "sample:operator:leaf"}],
            "automated_checks": [{"name": "inventory", "status": "failed"}],
        },
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id="run-result",
    )
    result = AutomatedCheckResult(
        result_id="check-result",
        candidate_id=original.candidate_id,
        source_digest=original.source_digest,
        checks=({"name": "inventory", "status": "passed"},),
        evidence_refs=("artifact://evidence/test-generation",),
    )

    artifact = plugin.publish_automated_result(result)
    updated = plugin.import_automated_result_artifact(original, artifact)

    assert artifact.kind == "scirel.automated-check-result.dev"
    assert updated.automated_ready
    assert updated.assets == original.assets


def test_plugin_imports_automated_result_from_host_supplied_body_and_checks_digest():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    original = CandidatePackage.from_l1(
        {
            "assets": [{"l1_asset_id": "sample:operator:leaf"}],
            "automated_checks": [{"name": "inventory", "status": "failed"}],
        },
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id="run-body-result",
    )
    result = AutomatedCheckResult(
        result_id="check-body-result",
        candidate_id=original.candidate_id,
        source_digest=original.source_digest,
        checks=({"name": "inventory", "status": "passed"},),
    )
    artifact = plugin.publish_automated_result(result)
    body = host.read_artifact(artifact.ref)

    updated = plugin.import_automated_result_body(
        original,
        body,
        expected_digest=artifact.digest,
    )
    assert updated.automated_ready

    with pytest.raises(ValueError, match="digest does not match"):
        plugin.import_automated_result_body(
            original,
            body + b" ",
            expected_digest=artifact.digest,
        )


def test_automated_result_artifact_mapping_is_fail_closed():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    original = candidate()
    result = AutomatedCheckResult(
        result_id="check-strict",
        candidate_id=original.candidate_id,
        source_digest=original.source_digest,
        checks=({"name": "replay", "status": "passed"},),
    )
    artifact = plugin.publish_automated_result(result)
    payload = result.to_dict()

    payload["unexpected"] = True
    host.artifacts[artifact.ref] = (
        artifact,
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8"),
    )
    with pytest.raises(ValueError, match="unknown fields"):
        plugin.import_automated_result_body(
            original,
            host.read_artifact(artifact.ref),
        )

    payload.pop("unexpected")
    payload["schema"] = "scirel.automated-check-result.other"
    host.artifacts[artifact.ref] = (
        artifact,
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8"),
    )
    with pytest.raises(ValueError, match="unsupported automated result schema"):
        plugin.import_automated_result_body(
            original,
            host.read_artifact(artifact.ref),
        )


def test_artifact_imports_require_verified_json_references():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    original = candidate()
    result = AutomatedCheckResult(
        result_id="check-artifact-contract",
        candidate_id=original.candidate_id,
        source_digest=original.source_digest,
        checks=({"name": "replay", "status": "passed"},),
    )
    result_artifact = plugin.publish_automated_result(result)

    with pytest.raises(ValueError, match="automated-check-result artifact"):
        plugin.import_automated_result_artifact(
            original,
            ArtifactRef(
                ref=result_artifact.ref,
                kind="scirel.l1-source.dev",
                digest=result_artifact.digest,
            ),
        )
    with pytest.raises(ValueError, match="media_type must be application/json"):
        plugin.import_automated_result_artifact(
            original,
            ArtifactReference(
                result_artifact.ref,
                result_artifact.digest,
                "text/plain",
            ),
        )

    l1_artifact = host.put_artifact(
        "scirel.l1-source.dev",
        {"assets": [], "automated_checks": []},
    )
    with pytest.raises(ValueError, match="L1 artifact media_type must be application/json"):
        plugin.import_l1_artifact(
            ArtifactReference(l1_artifact.ref, l1_artifact.digest, "text/plain")
        )


def test_completed_run_imports_one_result_artifact_and_platform_failure_stays_platform_failure():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    original = CandidatePackage.from_l1(
        {
            "assets": [{"l1_asset_id": "sample:operator:leaf"}],
            "automated_checks": [{"name": "inventory", "status": "failed"}],
        },
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:source",
        run_id="run-platform-result",
    )
    result = AutomatedCheckResult(
        result_id="check-platform-result",
        candidate_id=original.candidate_id,
        source_digest=original.source_digest,
        checks=({"name": "inventory", "status": "passed"},),
    )
    artifact = plugin.publish_automated_result(result)

    imported = plugin.import_automated_result_from_run(
        original,
        PluginRunResult(
            run_id="run-host-1",
            plugin_release_ref=PLUGIN_RELEASE_REF,
            attempt_no=1,
            status="completed",
            failure_class=None,
            result_artifact_refs=(
                ArtifactReference(artifact.ref, artifact.digest, artifact.media_type),
            ),
        ),
    )
    assert imported.automated_ready

    workflow = SciRelWorkflow(original)
    state_artifact = plugin.consume_automated_result_into_workflow(
        workflow,
        PluginRunResult(
            run_id="run-host-workflow",
            plugin_release_ref=PLUGIN_RELEASE_REF,
            attempt_no=1,
            status="completed",
            failure_class=None,
            result_artifact_refs=(
                ArtifactReference(artifact.ref, artifact.digest, artifact.media_type),
            ),
        ),
    )
    assert workflow.status.value == "automated_ready"
    assert state_artifact.kind == "scirel.workflow-state.dev"
    assert json.loads(host.read_artifact(state_artifact.ref))["status"] == "automated_ready"

    replayed_state_artifact = plugin.consume_automated_result_into_workflow(
        workflow,
        PluginRunResult(
            run_id="run-host-workflow-replay",
            plugin_release_ref=PLUGIN_RELEASE_REF,
            attempt_no=2,
            status="completed",
            failure_class=None,
            result_artifact_refs=(
                ArtifactReference(artifact.ref, artifact.digest, artifact.media_type),
            ),
            replayed=True,
        ),
    )
    assert replayed_state_artifact.ref == state_artifact.ref
    assert len(workflow.record.automated_results) == 1

    with pytest.raises(ValueError, match="media_type must be application/json"):
        plugin.consume_automated_result_into_workflow(
            SciRelWorkflow(original),
            PluginRunResult(
                run_id="run-host-wrong-media",
                plugin_release_ref=PLUGIN_RELEASE_REF,
                attempt_no=1,
                status="completed",
                failure_class=None,
                result_artifact_refs=(
                    ArtifactReference(artifact.ref, artifact.digest, "text/plain"),
                ),
            ),
        )

    host.artifacts[artifact.ref] = (artifact, b"{}")
    with pytest.raises(ValueError, match="digest does not match"):
        plugin.import_automated_result_from_run(
            original,
            PluginRunResult(
                run_id="run-host-tampered",
                plugin_release_ref=PLUGIN_RELEASE_REF,
                attempt_no=1,
                status="completed",
                failure_class=None,
                result_artifact_refs=(
                    ArtifactReference(artifact.ref, artifact.digest, artifact.media_type),
                ),
            ),
        )

    with pytest.raises(ValueError, match="runner_unavailable"):
        plugin.import_automated_result_from_run(
            original,
            PluginRunResult(
                run_id="run-host-2",
                plugin_release_ref=PLUGIN_RELEASE_REF,
                attempt_no=1,
                status="failed",
                failure_class="runner_unavailable",
                result_artifact_refs=(),
            ),
        )


def test_codefusion_run_result_wire_mapping_accepts_completed_receipt():
    result = PluginRunResult.from_mapping(
        {
            "run_id": "run_wire-1",
            "plugin_release_ref": PLUGIN_RELEASE_REF,
            "attempt_no": 1,
            "status": "completed",
            "failure_class": None,
            "result_artifact_refs": [
                {
                    "artifact_ref": "cf://artifact/result",
                    "digest": "sha256:" + "a" * 64,
                    "media_type": "application/json",
                }
            ],
            "replayed": False,
        }
    )

    assert result.to_dict()["plugin_release_ref"] == PLUGIN_RELEASE_REF
    assert result.to_dict()["status"] == "completed"
    assert result.result_artifact_refs[0].artifact_ref == "cf://artifact/result"

    unknown = PluginRunResult.from_mapping(
        {
            "run_id": "run_wire-unknown",
            "plugin_release_ref": PLUGIN_RELEASE_REF,
            "attempt_no": 1,
            "status": "result_unknown",
            "failure_class": None,
            "result_artifact_refs": [],
            "replayed": True,
        }
    )
    assert unknown.to_dict()["status"] == "result_unknown"


def test_registration_maps_codefusion_host_fields():
    plugin = SciRelPlugin.for_development(FakeHost())

    registration = plugin.registration()
    registration.validate()
    expected = json.loads(
        (
            Path(__file__).parents[2]
            / "contracts/examples/scirel-plugin-registration.dev.json"
        ).read_text(encoding="utf-8")
    )
    assert registration.to_dict() == expected
    assert plugin.descriptor()["ui_extensions"] == ["scirel.review"]
    assert tuple(plugin.descriptor()["service_principal_scopes"]) == SERVICE_PRINCIPAL_SCOPES


def test_runtime_registration_uses_the_admitted_release_snapshot():
    release = PluginReleaseSnapshot(
        plugin_release_ref="plugin-release://scirel/0.1.0.dev5/admitted",
        artifacts=(),
        skill_entrypoints=(),
        connectors=(),
        runtime_dependency_refs=(),
    )

    plugin = SciRelPlugin(FakeHost(), release)

    assert plugin.registration().release is release
    assert plugin.registration().to_dict()["release"] == release.to_dict()


def test_review_ui_projection_is_domain_owned_and_status_driven():
    plugin = SciRelPlugin.for_development(FakeHost())
    workflow = SciRelWorkflow(candidate())

    ready = plugin.review_ui_projection(workflow)

    assert ready["schema"] == "scirel.review-ui-extension.dev"
    assert ready["extension_id"] == "scientific-asset-review"
    assert ready["workflow"] == workflow.to_dict()
    assert ready["available_actions"] == ["standardize"]
    assert not {
        "tenant_id",
        "job_id",
        "session_id",
        "credential_ref",
        "attempt_id",
    }.intersection(ready)

    workflow.create_draft(
        draft_id="draft-ui",
        assets=[ASSET_DOCUMENT],
    )
    assert plugin.review_ui_projection(workflow)["available_actions"] == [
        "update_draft",
        "submit_for_review"
    ]

    workflow.submit_for_review()
    assert plugin.review_ui_projection(workflow)["available_actions"] == [
        "update_draft",
        "start_review",
    ]

    workflow.start_review()
    assert plugin.review_ui_projection(workflow)["available_actions"] == [
        "approve",
        "needs_evidence",
        "rework_requested",
        "reject",
    ]
    assert "update_draft" not in plugin.review_ui_projection(workflow)[
        "available_actions"
    ]


def test_review_ui_projection_exposes_rework_without_platform_state():
    plugin = SciRelPlugin.for_development(FakeHost())
    workflow = SciRelWorkflow(candidate())
    draft = workflow.create_draft(
        draft_id="draft-ui-rework",
        assets=[{"asset_id": "scirel.field.example"}],
    )
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision(
            draft_id=draft.draft_id,
            outcome=ReviewOutcome.REWORK_REQUESTED,
            reviewer="expert-ui",
        )
    )

    projection = plugin.review_ui_projection(workflow)

    assert projection["workflow"]["status"] == "rework_requested"
    assert projection["available_actions"] == ["create_draft"]


@pytest.mark.parametrize(
    "next_action, expected_action",
    (
        ("needs_evidence", "provide_evidence"),
        ("rework_requested", "rework_candidate"),
    ),
)
def test_review_ui_projection_keeps_pre_draft_queue_actions_distinct(
    next_action, expected_action
):
    plugin = SciRelPlugin.for_development(FakeHost())
    workflow = SciRelWorkflow(candidate())
    workflow.apply_automated_result(
        AutomatedCheckResult(
            result_id="check-ui-" + next_action,
            candidate_id=workflow.record.candidate.candidate_id,
            source_digest=workflow.record.candidate.source_digest,
            checks=({"name": "scientific_gap", "status": "failed"},),
            gaps=("scientific_gap:sample",),
            next_action=next_action,
        )
    )

    projection = plugin.review_ui_projection(workflow)

    assert projection["workflow"]["status"] == next_action
    assert projection["available_actions"] == [expected_action]


def test_review_ui_projection_runtime_actions_match_exact_schema():
    plugin = SciRelPlugin.for_development(FakeHost())
    projected_actions = set(plugin.review_ui_projection(SciRelWorkflow(candidate()))["available_actions"])

    for next_action in ("retry", "needs_evidence", "rework_requested", "rejected"):
        workflow = SciRelWorkflow(candidate())
        workflow.apply_automated_result(
            AutomatedCheckResult(
                result_id="check-schema-" + next_action,
                candidate_id=workflow.record.candidate.candidate_id,
                source_digest=workflow.record.candidate.source_digest,
                checks=({"name": "schema_branch", "status": "failed"},),
                gaps=("schema_branch:sample",),
                next_action=next_action,
            )
        )
        projected_actions.update(
            plugin.review_ui_projection(workflow)["available_actions"]
        )

    review_workflow = SciRelWorkflow(candidate())
    draft = review_workflow.create_draft(
        draft_id="draft-schema-actions",
        assets=[ASSET_DOCUMENT],
    )
    projected_actions.update(
        plugin.review_ui_projection(review_workflow)["available_actions"]
    )
    review_workflow.submit_for_review()
    projected_actions.update(
        plugin.review_ui_projection(review_workflow)["available_actions"]
    )
    review_workflow.start_review()
    projected_actions.update(
        plugin.review_ui_projection(review_workflow)["available_actions"]
    )
    review_workflow.record_review(
        ReviewDecision(
            draft_id=draft.draft_id,
            outcome=ReviewOutcome.APPROVED,
            reviewer="expert-schema",
        )
    )
    projected_actions.update(
        plugin.review_ui_projection(review_workflow)["available_actions"]
    )

    rework_workflow = SciRelWorkflow(candidate())
    rework_draft = rework_workflow.create_draft(
        draft_id="draft-schema-rework",
        assets=[ASSET_DOCUMENT],
    )
    rework_workflow.submit_for_review()
    rework_workflow.start_review()
    rework_workflow.record_review(
        ReviewDecision(
            draft_id=rework_draft.draft_id,
            outcome=ReviewOutcome.REWORK_REQUESTED,
            reviewer="expert-schema",
        )
    )
    projected_actions.update(
        plugin.review_ui_projection(rework_workflow)["available_actions"]
    )

    contract = json.loads(
        (
            Path(__file__).parents[2]
            / "contracts/review-ui-extension-dev.schema.json"
        ).read_text(encoding="utf-8")
    )
    declared_actions = set(
        contract["properties"]["available_actions"]["items"]["enum"]
    )
    assert projected_actions == declared_actions


def test_review_ui_projection_hides_approve_for_unresolved_gaps():
    plugin = SciRelPlugin.for_development(FakeHost())
    workflow = SciRelWorkflow(candidate())
    workflow.create_draft(
        draft_id="draft-ui-gap",
        assets=[{"asset_id": "scirel.field.incomplete"}],
    )
    workflow.submit_for_review()
    workflow.start_review()

    projection = plugin.review_ui_projection(workflow)

    assert projection["available_actions"] == [
        "needs_evidence",
        "rework_requested",
        "reject",
    ]
    assert projection["workflow"]["draft"]["gaps"]


def test_review_action_uses_host_identity_and_publishes_domain_artifacts():
    host = FakeHost(user="expert-reviewer")
    plugin = SciRelPlugin.for_development(host)
    workflow = SciRelWorkflow(candidate())
    workflow.create_draft(
        draft_id="draft-ui-action",
        assets=[{"asset_id": "scirel.field.example"}],
    )
    workflow.submit_for_review()
    workflow.start_review()

    result = plugin.record_review_action(
        workflow,
        "needs_evidence",
        notes="add a conservation check",
        correlation_id="workbench://review/case-1",
    )

    decision = json.loads(host.read_artifact(result.decision_artifact.ref))
    state = json.loads(host.read_artifact(result.state_artifact.ref))
    assert decision == {
        "schema": "scirel.review-decision.dev",
        "draft_id": "draft-ui-action",
        "outcome": "needs_evidence",
        "reviewer": "expert-reviewer",
        "notes": "add a conservation check",
    }
    assert state["status"] == "needs_evidence"
    assert result.event.correlation_id == "workbench://review/case-1"
    assert result.event.payload == {
        "draft_id": "draft-ui-action",
        "outcome": "needs_evidence",
        "workflow_status": "needs_evidence",
    }
    assert [ref.artifact_ref for ref in result.event.artifact_refs] == [
        result.decision_artifact.ref,
        result.state_artifact.ref,
    ]
    assert plugin.review_ui_projection(workflow)["available_actions"] == [
        "create_draft"
    ]


def test_review_action_cannot_bypass_expert_observation_transition():
    host = FakeHost(user="expert-reviewer")
    plugin = SciRelPlugin.for_development(host)
    workflow = SciRelWorkflow(candidate())
    workflow.create_draft(
        draft_id="draft-not-pending",
        assets=[{"asset_id": "scirel.field.example"}],
    )

    with pytest.raises(ValueError, match="review_in_progress"):
        plugin.record_review_action(
            workflow,
            "approved",
            correlation_id="workbench://review/case-invalid",
        )

    assert workflow.status.value == "draft"
    assert host.artifacts == {}


def test_automated_result_event_carries_artifact_and_opaque_summary():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    candidate_value = candidate()
    result = AutomatedCheckResult(
        result_id="check-event",
        candidate_id=candidate_value.candidate_id,
        source_digest=candidate_value.source_digest,
        checks=({"name": "replay", "status": "passed"},),
    )
    artifact = plugin.publish_automated_result(result)

    event = plugin.publish_automated_result_event(
        result,
        artifact,
        workflow_run_id=candidate_value.run_id,
        correlation_id="job://check-event",
    )

    assert event.artifact_refs[0].artifact_ref == artifact.ref
    assert event.payload == {
        "result_id": "check-event",
        "candidate_id": candidate_value.candidate_id,
        "result_digest": result.result_digest,
        "status": "passed",
        "next_action": "ready",
    }

    wrong = host.put_artifact(
        "scirel.automated-check-result.dev",
        {**result.to_dict(), "result_id": "check-event-other"},
    )
    with pytest.raises(ValueError, match="digest does not match result"):
        plugin.publish_automated_result_event(
            result,
            wrong,
            workflow_run_id=candidate_value.run_id,
            correlation_id="job://check-event-wrong",
        )

    with pytest.raises(ValueError, match="automated-check-result artifact"):
        plugin.publish_automated_result_event(
            result,
            ArtifactRef(
                ref=artifact.ref,
                kind="scirel.candidate-package.dev",
                digest=artifact.digest,
            ),
            workflow_run_id=candidate_value.run_id,
            correlation_id="job://check-event-kind",
        )


def test_host_generates_event_system_fields_and_preserves_domain_payload():
    host = FakeHost(tenant_id="tenant-a", project_id="project-a")
    plugin = SciRelPlugin.for_development(host)
    handoff = plugin.publish_candidate(candidate())

    event = host.emit_event(
        plugin_id=plugin.plugin_id,
        event_type="scirel.candidate.automated_check_submitted",
        workflow_run_id=candidate().run_id,
        correlation_id=handoff.job.ref,
        artifact_refs=(handoff.artifact.ref,),
        payload={"candidate_id": candidate().candidate_id},
    )

    assert isinstance(event, PluginEventEnvelope)
    assert event.event_id == "event-1"
    assert event.idempotency_key == "scirel:event:1"
    assert event.scope.tenant_id == "tenant-a"
    assert event.scope.project_id == "project-a"
    assert event.correlation_id == handoff.job.ref
    assert event.artifact_refs[0].artifact_ref == handoff.artifact.ref
    assert event.payload == {"candidate_id": candidate().candidate_id}


def test_command_scope_must_match_registration():
    plugin = SciRelPlugin.for_development(FakeHost())
    registration = plugin.registration()
    command = PluginCommandEnvelope(
        command="scirel.automated_check",
        scope=PluginScope("tenant", "project", "other", "run-1"),
        idempotency_key="host-generated",
        input_artifacts=(),
        payload={},
    )

    with pytest.raises(PluginContractError, match="scope plugin_id"):
        command.validate(registration)


@pytest.mark.parametrize("payload", [None, ["candidate", 1], "candidate"])
def test_envelope_payload_matches_json_value_contract(payload):
    plugin = SciRelPlugin.for_development(FakeHost())
    registration = plugin.registration()
    command = PluginCommandEnvelope(
        command="scirel.inspect",
        scope=PluginScope("tenant", "project", "scirel", "run-1"),
        idempotency_key="host-generated",
        input_artifacts=(),
        payload=payload,
    )

    command.validate(registration)
    assert command.to_dict()["payload"] == payload


def test_plugin_release_is_an_artifact_operation():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)

    artifact = plugin.release(
        {
            "schema": "scirel.release-manifest.dev",
            "release_id": "release-plugin",
            "draft_id": "draft-plugin",
            "approved_assets": ["scirel.field.example"],
            "catalog_ref": "artifact://catalog/dev",
            "catalog_digest": "sha256:" + "2" * 64,
            "wheel_ref": "artifact://wheel/dev",
            "wheel_digest": "sha256:" + "3" * 64,
            "candidate_id": "candidate-run-plugin",
            "candidate_digest": "sha256:" + "0" * 64,
            "draft_digest": "sha256:" + "1" * 64,
            "release_version": "0.1.0.dev5",
        }
    )

    assert artifact.kind == "scirel.release-manifest.dev"
    assert artifact.ref in host.artifacts

    invalid = json.loads(host.read_artifact(artifact.ref))
    invalid.pop("wheel_digest")
    with pytest.raises(ValueError, match="missing fields: wheel_digest"):
        plugin.release(invalid)

    invalid = json.loads(host.read_artifact(artifact.ref))
    invalid["job_id"] = "must-not-enter-domain"
    with pytest.raises(ValueError, match="unknown fields: job_id"):
        plugin.release(invalid)


def test_release_events_bind_manifest_and_use_bounded_failure_codes():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    release = ReleaseManifest(
        release_id="release-event",
        draft_id="draft-event",
        approved_assets=("scirel.field.example",),
        catalog_ref="artifact://catalog/event",
        catalog_digest="sha256:" + "2" * 64,
        wheel_ref="artifact://wheel/event",
        wheel_digest="sha256:" + "3" * 64,
        candidate_id="candidate-event",
        candidate_digest="sha256:" + "0" * 64,
        draft_digest="sha256:" + "1" * 64,
        release_version="0.1.0.dev5",
    )
    artifact = plugin.release(release)

    completed = plugin.publish_release_completed_event(
        release,
        artifact,
        workflow_run_id="run-release-event",
        correlation_id="build://release-event",
    )
    failed = plugin.publish_release_failed_event(
        workflow_run_id="run-release-failed",
        correlation_id="build://release-failed",
        failure_code="validation_failed",
    )

    assert completed.event_type == "scirel.release.completed"
    assert completed.artifact_refs[0].artifact_ref == artifact.ref
    assert completed.payload["release_digest"] == release.release_digest
    assert failed.event_type == "scirel.release.failed"
    assert failed.payload == {"failure_code": "validation_failed"}
    assert failed.artifact_refs == ()

    wrong = host.put_artifact(
        "scirel.release-manifest.dev",
        {**release.to_dict(), "release_id": "release-other"},
    )
    with pytest.raises(ValueError, match="digest does not match"):
        plugin.publish_release_completed_event(
            release,
            wrong,
            workflow_run_id="run-release-event",
            correlation_id="build://release-event",
        )
    with pytest.raises(ValueError, match="unsupported release failure code"):
        plugin.publish_release_failed_event(
            workflow_run_id="run-release-failed",
            correlation_id="build://release-failed",
            failure_code="platform_timeout",
        )

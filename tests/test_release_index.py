"""Development release index and exact review binding gates."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

import pytest

from scirel_plugin.adapter import (
    execute_body_import_wire,
    review_item_from_body,
    review_item_from_workflow,
    review_items_from_body,
)
from scirel_workflow import CandidatePackage, SciRelWorkflow
from scirel_workflow.models import digest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _candidate_entry_id(path):
    return json.loads(path.read_text(encoding="utf-8"))["entries"][0]["entry_id"]


def _pending_item(
    *, release_ready=False,
    document_name="scirel.field.circular-filament-green.json",
    support_file=None,
    omit_dependencies=False,
):
    document = json.loads(
        (ROOT / "catalog/examples" / document_name).read_text(
            encoding="utf-8"
        )
    )
    if omit_dependencies:
        document["version"]["dependencies"] = []
    evidence = []
    if release_ready:
        document["provenance"]["license_status"] = "approved-for-public-release"
        test_names = document["verification"]["tests"]
        test_name = test_names[0]
        code = {
            "kind": "none", "content": None,
            "rationale": "The maintained implementation is reused unchanged.",
        }
        if support_file is not None:
            code = {
                "kind": "files",
                "content": {"files": {
                    support_file: (ROOT / support_file).read_bytes().decode("utf-8"),
                }},
                "rationale": "The selected implementation binds this exact support module.",
            }
        code["digest"] = digest(code)
        tests = {
            "content": {"files": {
                name: (ROOT / name).read_bytes().decode("utf-8")
                for name in test_names
            }},
            "commands": [{"command": f"pytest {test_name}"}],
            "results": [{"command": f"pytest {test_name}", "exit_code": 0}],
        }
        tests["digest"] = digest(tests)
        evidence = [{
            "kind": "standardization_review_unit",
            "asset_id": document["asset_id"],
            "candidate_code": code,
            "candidate_tests": tests,
            "gaps": [],
        }]
    candidate = CandidatePackage.from_l1(
        {
            "assets": [{"candidate_asset_id": "candidate-field"}],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/test",
        source_digest="sha256:l1",
        run_id="run-release-index",
    )
    workflow = SciRelWorkflow(candidate)
    workflow.create_draft(
        draft_id="draft-release-index", assets=[document], evidence=evidence
    )
    workflow.submit_for_review()
    return review_item_from_workflow(workflow, 0)


def _multi_item_workflow_body(*, release_ready=False):
    first = _pending_item(release_ready=release_ready)
    second = json.loads(
        (ROOT / "catalog/examples/scirel.closures.hall-two-fluid-pressure.json").read_text(
            encoding="utf-8"
        )
    )
    candidate = CandidatePackage.from_l1(
        {
            "assets": [
                {"candidate_asset_id": "candidate-field"},
                {"candidate_asset_id": "candidate-closure"},
            ],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/test",
        source_digest="sha256:l1",
        run_id="run-release-index",
    )
    workflow = SciRelWorkflow(candidate)
    workflow.create_draft(
        draft_id="draft-release-index",
        assets=[first["asset"], second],
        evidence=first["evidence"],
    )
    workflow.submit_for_review()
    return json.dumps(workflow.to_dict(), ensure_ascii=False, sort_keys=True).encode("utf-8")


def test_candidate_index_registers_every_item_from_one_workflow_revision(tmp_path):
    from release_index import register_candidate

    body = _multi_item_workflow_body()
    artifact = tmp_path / "workflow.json"
    artifact.write_bytes(body)

    index = register_candidate(
        item_artifacts=[artifact],
        git_revision="a" * 40,
        output_path=tmp_path / "index.json",
    )

    items = index["entries"][0]["items"]
    assert {item["item_ref"] for item in items} == {
        item["item_ref"] for item in review_items_from_body(body)
    }
    assert len(items) == 2
    assert {item["initial_revision"] for item in items} == {
        "sha256:" + hashlib.sha256(body).hexdigest()
    }


def test_candidate_index_rejects_repeated_multi_item_artifact(tmp_path):
    from release_index import register_candidate

    artifact = tmp_path / "workflow.json"
    artifact.write_bytes(_multi_item_workflow_body())

    with pytest.raises(ValueError, match="repeats an asset or review item"):
        register_candidate(
            item_artifacts=[artifact, artifact],
            git_revision="a" * 40,
            output_path=tmp_path / "index.json",
        )


def test_candidate_index_rejects_workflow_without_pending_items(tmp_path):
    from release_index import register_candidate

    workflow = json.loads(_multi_item_workflow_body())
    workflow["status"] = "draft"
    workflow["draft"]["status"] = "draft"
    workflow["drafts"][0]["status"] = "draft"
    artifact = tmp_path / "workflow.json"
    artifact.write_text(json.dumps(workflow), encoding="utf-8")

    with pytest.raises(ValueError, match="no pending review items"):
        register_candidate(
            item_artifacts=[artifact],
            git_revision="a" * 40,
            output_path=tmp_path / "index.json",
        )


def test_candidate_index_preserves_exact_pending_revision_without_approval(tmp_path):
    from release_index import register_candidate

    item = _pending_item()
    item_path = tmp_path / "pending.json"
    item_path.write_text(json.dumps(item), encoding="utf-8")

    index = register_candidate(
        item_artifacts=[item_path],
        git_revision="a" * 40,
        output_path=tmp_path / "index.json",
    )

    assert index["schema"] == "scirel.release-index.dev"
    assert index["entries"][0]["status"] == "candidate"
    assert index["entries"][0]["items"][0]["item_ref"] == item["item_ref"]
    assert "approved" not in index["entries"][0]

    contract = json.loads((ROOT / "contracts/release-index-dev.schema.json").read_text(encoding="utf-8"))
    assert set(index) == set(contract["required"])
    assert set(index["entries"][0]) == set(contract["$defs"]["candidate"]["required"])


def test_candidate_index_can_freeze_an_item_waiting_for_evidence(tmp_path):
    from release_index import register_candidate

    item = _pending_item()
    item["gaps"] = ["needs_source_comparison"]
    artifact = tmp_path / "pending-with-gap.json"
    artifact.write_text(json.dumps(item), encoding="utf-8")

    index = register_candidate(
        item_artifacts=[artifact],
        git_revision="a" * 40,
        output_path=tmp_path / "index.json",
    )

    assert index["entries"][0]["status"] == "candidate"


def test_candidate_index_appends_without_rewriting_previous_entry(tmp_path):
    from release_index import register_candidate

    artifact = tmp_path / "pending.json"
    artifact.write_text(json.dumps(_pending_item()), encoding="utf-8")
    first_path = tmp_path / "first.json"
    first = register_candidate(
        item_artifacts=[artifact], git_revision="a" * 40,
        output_path=first_path,
    )
    second = register_candidate(
        item_artifacts=[artifact], git_revision="b" * 40,
        output_path=tmp_path / "second.json", existing_index=first_path,
    )

    assert second["entries"][0] == first["entries"][0]
    assert second["entries"][1]["entry_id"] != first["entries"][0]["entry_id"]
    assert json.loads(first_path.read_text(encoding="utf-8")) == first


def test_development_snapshot_appends_exact_artifacts_without_approval(tmp_path, monkeypatch):
    import release_index

    monkeypatch.setattr(release_index, "ROOT", tmp_path)
    catalog = tmp_path / "catalog" / "release.json"
    catalog.parent.mkdir()
    catalog_body = {"schema": "scirel.catalog-release.v1", "release_version": "0.1.0.dev5"}
    catalog_body["root_digest"] = release_index.digest(release_index.canonical_json(catalog_body))
    catalog.write_text(json.dumps(catalog_body), encoding="utf-8")
    wheel = tmp_path / "wheel.whl"
    wheel.write_bytes(b"development wheel")
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"result":"bounded"}', encoding="utf-8")
    destination = tmp_path / "delivery.json"
    destination.write_text('{"status":"pending_unapproved"}', encoding="utf-8")

    result = release_index.register_development_snapshot(
        snapshot_id="r43-dev5", catalog_release=catalog, wheel=wheel,
        evidence_paths=[evidence], destination_paths=[destination],
        git_revision="a" * 40, source_qualification="bounded_d1",
        output_path=tmp_path / "index.json",
    )

    entry = result["entries"][0]
    assert entry["status"] == "development"
    assert entry["approval_state"] == "pending_unapproved"
    assert entry["source_qualification"] == "bounded_d1"
    assert entry["catalog"]["root_digest"] == catalog_body["root_digest"]
    assert entry["wheel"] == release_index.artifact_ref(wheel)
    assert entry["destination_refs"] == [release_index.artifact_ref(destination)]
    assert release_index.read_index(tmp_path / "index.json") == result
    assert "approved" not in entry

    pending = tmp_path / "pending.json"
    pending.write_text(json.dumps(_pending_item()), encoding="utf-8")
    with_candidate = release_index.register_candidate(
        item_artifacts=[pending], git_revision="b" * 40,
        output_path=tmp_path / "with-candidate.json",
        existing_index=tmp_path / "index.json", evidence_paths=[evidence],
        source_qualification="bounded_d1",
    )
    assert with_candidate["entries"][0] == entry
    assert with_candidate["entries"][1]["destination"] == "review_host"
    assert with_candidate["entries"][1]["destination_refs"] == []
    assert release_index.read_index(tmp_path / "with-candidate.json") == with_candidate


def test_development_snapshot_rejects_invalid_catalog_binding(tmp_path, monkeypatch):
    import release_index

    monkeypatch.setattr(release_index, "ROOT", tmp_path)
    catalog = tmp_path / "release.json"
    catalog.write_text(json.dumps({
        "schema": "scirel.catalog-release.v1", "root_digest": "sha256:" + "0" * 64,
    }), encoding="utf-8")
    wheel = tmp_path / "wheel.whl"
    wheel.write_bytes(b"wheel")
    with pytest.raises(ValueError, match="catalog root digest differs"):
        release_index.register_development_snapshot(
            snapshot_id="bad", catalog_release=catalog, wheel=wheel,
            evidence_paths=[catalog], destination_paths=[catalog],
            source_manifest_digest="sha256:" + "a" * 64,
            source_qualification="mixed_unverified",
            output_path=tmp_path / "index.json",
        )


def test_lifecycle_replaces_only_a_current_development_entry(tmp_path, monkeypatch):
    import release_index

    monkeypatch.setattr(release_index, "ROOT", tmp_path)
    catalog = tmp_path / "release.json"
    catalog_body = {"schema": "scirel.catalog-release.v1"}
    catalog_body["root_digest"] = release_index.digest(release_index.canonical_json(catalog_body))
    catalog.write_text(json.dumps(catalog_body), encoding="utf-8")
    evidence = tmp_path / "transition.json"
    evidence.write_text('{"predecessor":"old","successor":"new"}', encoding="utf-8")
    old_wheel = tmp_path / "old.whl"
    old_wheel.write_bytes(b"old wheel")
    new_wheel = tmp_path / "new.whl"
    new_wheel.write_bytes(b"new wheel")
    first_path = tmp_path / "first.json"
    first = release_index.register_development_snapshot(
        snapshot_id="old", catalog_release=catalog, wheel=old_wheel,
        evidence_paths=[evidence], destination_paths=[evidence],
        git_revision="a" * 40, source_qualification="mixed_unverified",
        output_path=first_path,
    )
    second_path = tmp_path / "second.json"
    second = release_index.register_development_snapshot(
        snapshot_id="new", catalog_release=catalog, wheel=new_wheel,
        evidence_paths=[evidence], destination_paths=[evidence],
        git_revision="b" * 40, source_qualification="mixed_unverified",
        existing_index=first_path, output_path=second_path,
    )
    old_id, new_id = (entry["entry_id"] for entry in second["entries"])
    third_path = tmp_path / "third.json"
    third = release_index.register_lifecycle(
        transition="superseded", subject_entry_id=old_id,
        successor_entry_id=new_id, evidence_path=evidence,
        existing_index=second_path, output_path=third_path,
    )

    assert third["entries"][:2] == second["entries"]
    assert third["entries"][0] == first["entries"][0]
    assert third["entries"][-1]["evidence_ref"] == release_index.artifact_ref(evidence)
    assert [entry["entry_id"] for entry in release_index.current_unpublished_entries(third)] == [new_id]
    assert release_index.read_index(third_path) == third

    with pytest.raises(ValueError, match="current unpublished subject"):
        release_index.register_lifecycle(
            transition="withdrawn", subject_entry_id=old_id,
            evidence_path=evidence, existing_index=third_path,
            output_path=tmp_path / "duplicate.json",
        )
    with pytest.raises(ValueError, match="cannot name a successor"):
        release_index.register_lifecycle(
            transition="withdrawn", subject_entry_id=new_id,
            successor_entry_id=old_id, evidence_path=evidence,
            existing_index=third_path, output_path=tmp_path / "bad-withdrawal.json",
        )

    pending = tmp_path / "pending.json"
    pending.write_text(json.dumps(_pending_item()), encoding="utf-8")
    with_candidate = release_index.register_candidate(
        item_artifacts=[pending], git_revision="c" * 40,
        existing_index=third_path, output_path=tmp_path / "candidate.json",
    )
    with pytest.raises(ValueError, match="same kind"):
        release_index.register_lifecycle(
            transition="superseded", subject_entry_id=new_id,
            successor_entry_id=with_candidate["entries"][-1]["entry_id"],
            evidence_path=evidence, existing_index=tmp_path / "candidate.json",
            output_path=tmp_path / "wrong-kind.json",
        )


def test_withdrawn_candidate_cannot_enter_release_gates(tmp_path, monkeypatch):
    import release_index
    from finalize_release import finalize_reviewed_release
    from prepare_reviewed_distribution import prepare_reviewed_distribution

    monkeypatch.setattr(release_index, "ROOT", tmp_path)
    pending = tmp_path / "pending.json"
    pending.write_text(json.dumps(_pending_item()), encoding="utf-8")
    first_path = tmp_path / "candidate.json"
    candidate = release_index.register_candidate(
        item_artifacts=[pending], git_revision="a" * 40,
        output_path=first_path,
    )["entries"][0]
    evidence = tmp_path / "withdrawal.json"
    evidence.write_text('{"decision":"withdrawn"}', encoding="utf-8")
    withdrawn_path = tmp_path / "withdrawn.json"
    withdrawn = release_index.register_lifecycle(
        transition="withdrawn", subject_entry_id=candidate["entry_id"],
        evidence_path=evidence, existing_index=first_path,
        output_path=withdrawn_path,
    )
    assert release_index.current_unpublished_entries(withdrawn) == []
    assert release_index.read_index(withdrawn_path) == withdrawn

    with pytest.raises(ValueError, match="no longer current"):
        prepare_reviewed_distribution(
            release_index=withdrawn_path, candidate_entry_id=candidate["entry_id"],
            approved_results=tmp_path / "missing.json", review_artifacts_dir=tmp_path,
            source_root=ROOT, staging_dir=tmp_path / "staging",
        )
    with pytest.raises(ValueError, match="no longer current"):
        finalize_reviewed_release(
            release_index=withdrawn_path, candidate_entry_id=candidate["entry_id"],
            approved_results=tmp_path / "missing.json", review_artifacts_dir=tmp_path,
            documents_dir=tmp_path, catalog_dir=tmp_path, wheel=tmp_path / "missing.whl",
            output_dir=tmp_path / "release", release_id="withdrawn",
            source_root=ROOT,
        )


def test_lifecycle_cannot_select_an_already_released_successor(tmp_path):
    import release_index

    pending = tmp_path / "pending.json"
    pending.write_text(json.dumps(_pending_item()), encoding="utf-8")
    candidate = release_index.register_candidate(
        item_artifacts=[pending], git_revision="a" * 40,
        output_path=tmp_path / "first.json",
    )["entries"][0]
    second_candidate = dict(candidate, entry_id="candidate:" + "b" * 64)
    second_candidate["entry_digest"] = release_index.digest(release_index.canonical_json({
        key: value for key, value in second_candidate.items() if key != "entry_digest"
    }))
    index = release_index.append_entry(release_index.read_index(tmp_path / "first.json"), {
        key: value for key, value in second_candidate.items() if key != "entry_digest"
    })
    index = release_index.append_entry(index, {
        "entry_id": "release:test", "status": "released",
        "predecessor_entry_id": second_candidate["entry_id"],
        "baseline_entry_id": None, "included_assets": [],
        "manifest_digest": "sha256:" + "c" * 64,
    })
    index = release_index.append_entry(index, {
        "entry_id": "lifecycle:" + "d" * 64, "status": "lifecycle",
        "subject_entry_id": candidate["entry_id"], "transition": "superseded",
        "successor_entry_id": second_candidate["entry_id"],
        "evidence_ref": {"ref": "transition.json", "digest": "sha256:" + "e" * 64},
    })
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(index), encoding="utf-8")
    with pytest.raises(ValueError, match="current entry of the same kind"):
        release_index.read_index(path)


def test_consumer_evidence_binds_existing_development_without_approval(tmp_path, monkeypatch):
    import release_index

    monkeypatch.setattr(release_index, "ROOT", tmp_path)
    catalog = tmp_path / "release.json"
    catalog_body = {"schema": "scirel.catalog-release.v1"}
    catalog_body["root_digest"] = release_index.digest(release_index.canonical_json(catalog_body))
    catalog.write_text(json.dumps(catalog_body), encoding="utf-8")
    wheel = tmp_path / "wheel.whl"
    wheel.write_bytes(b"development wheel")
    first_path = tmp_path / "development.json"
    first = release_index.register_development_snapshot(
        snapshot_id="r43-dev5", catalog_release=catalog, wheel=wheel,
        evidence_paths=[catalog], destination_paths=[catalog],
        git_revision="a" * 40, source_qualification="mixed_unverified",
        output_path=first_path,
    )
    development = first["entries"][0]
    record = tmp_path / "consumer.json"
    record_body = {
        "schema": "scirel.outbound-evaluation-manifest.v1",
        "status": "development_product_ordinary_same_request_acceptance",
        "development_entry_id": development["entry_id"],
        "scirel_source_revision": "a" * 40,
        "runtime": {
            "wheel_sha256": development["wheel"]["digest"].removeprefix("sha256:"),
            "catalog_release_sha256": development["catalog"]["digest"].removeprefix("sha256:"),
            "catalog_root_digest": development["catalog"]["root_digest"],
        },
        "codefusion_observation": {
            "request_ref": "appreq-exact", "request_status": "completed",
            "owner_resolved_skill_revision_digest": "sha256:" + "b" * 64,
            "environment_version": "envver-exact",
            "shell_tool_plan_revision": "tool-plan@sha256:" + "c" * 64,
            "shell_calls_bound_to_plan": 2,
            "input_mount": "read_only",
        },
        "review_boundary": {"approved_items": 0},
    }
    record.write_text(json.dumps(record_body), encoding="utf-8")
    second_path = tmp_path / "with-consumer.json"
    second = release_index.register_development_consumer_evidence(
        development_entry_id=development["entry_id"], evidence_path=record,
        existing_index=first_path, output_path=second_path,
    )

    assert second["entries"][0] == development
    evidence = second["entries"][1]
    assert evidence["evidence_type"] == "development_consumer_acceptance"
    assert evidence["subject_entry_id"] == development["entry_id"]
    assert evidence["approval_state"] == "pending_unapproved"
    assert evidence["evidence_ref"] == release_index.artifact_ref(record)
    assert release_index.read_index(second_path) == second
    contract = json.loads((ROOT / "contracts/release-index-dev.schema.json").read_text(encoding="utf-8"))
    assert set(evidence) == set(contract["$defs"]["evidence"]["required"])

    outside = tmp_path.parent / f"{tmp_path.name}-outside-consumer.json"
    outside.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="within SciRel"):
        release_index.register_development_consumer_evidence(
            development_entry_id=development["entry_id"],
            evidence_path=tmp_path / ".." / outside.name,
            existing_index=first_path, output_path=tmp_path / "outside-consumer.json",
        )

    with pytest.raises(ValueError, match="already exists"):
        release_index.register_development_consumer_evidence(
            development_entry_id=development["entry_id"], evidence_path=record,
            existing_index=second_path, output_path=tmp_path / "duplicate.json",
        )
    record_body["runtime"]["wheel_sha256"] = "0" * 64
    record.write_text(json.dumps(record_body), encoding="utf-8")
    with pytest.raises(ValueError, match="does not bind"):
        release_index.register_development_consumer_evidence(
            development_entry_id=development["entry_id"], evidence_path=record,
            existing_index=first_path, output_path=tmp_path / "wrong-wheel.json",
        )
    record_body["runtime"]["wheel_sha256"] = development["wheel"]["digest"].removeprefix("sha256:")
    del record_body["codefusion_observation"]["shell_tool_plan_revision"]
    record.write_text(json.dumps(record_body), encoding="utf-8")
    with pytest.raises(ValueError, match="does not bind"):
        release_index.register_development_consumer_evidence(
            development_entry_id=development["entry_id"], evidence_path=record,
            existing_index=first_path, output_path=tmp_path / "missing-plan.json",
        )


def test_review_host_evidence_appends_without_rewriting_candidate(tmp_path, monkeypatch):
    import release_index

    monkeypatch.setattr(release_index, "ROOT", tmp_path)
    artifact = tmp_path / "pending.json"
    artifact.write_bytes(_multi_item_workflow_body())
    first_path = tmp_path / "candidate.json"
    first = release_index.register_candidate(
        item_artifacts=[artifact], git_revision="a" * 40,
        output_path=first_path,
    )
    candidate = first["entries"][0]
    record = tmp_path / "host-evidence.json"
    record.write_text(json.dumps({
        "schema": "scirel.review-host-export-acceptance.dev",
        "candidate_entry_id": candidate["entry_id"],
        "workflow_revision": candidate["items"][0]["initial_revision"],
        "item_count": len(candidate["items"]),
        "review_pending_items": len(candidate["items"]),
        "needs_evidence_items": 0,
        "approved_items": 0,
        "applied_transitions": 0,
        "approval_state": "pending_unapproved",
        "host_source_revision": "a" * 40,
        "host_export_artifact_ref": "artifact://host/snapshot",
        "host_export_artifact_digest": "sha256:" + "b" * 64,
        "host_receipt_digest": "sha256:" + "e" * 64,
    }), encoding="utf-8")
    second_path = tmp_path / "with-evidence.json"
    second = release_index.register_review_host_evidence(
        candidate_entry_id=candidate["entry_id"], evidence_path=record,
        existing_index=first_path, output_path=second_path,
    )

    assert second["entries"][0] == candidate
    evidence = second["entries"][1]
    assert evidence["status"] == "evidence"
    assert evidence["subject_entry_id"] == candidate["entry_id"]
    assert evidence["approval_state"] == "pending_unapproved"
    assert evidence["evidence_ref"] == release_index.artifact_ref(record)
    assert release_index.read_index(second_path) == second
    contract = json.loads((ROOT / "contracts/release-index-dev.schema.json").read_text(encoding="utf-8"))
    assert set(evidence) == set(contract["$defs"]["evidence"]["required"])

    outside = tmp_path.parent / f"{tmp_path.name}-outside-review.json"
    outside.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="within SciRel"):
        release_index.register_review_host_evidence(
            candidate_entry_id=candidate["entry_id"], evidence_path=outside,
            existing_index=first_path, output_path=tmp_path / "outside-review.json",
        )

    with pytest.raises(ValueError, match="already exists"):
        release_index.register_review_host_evidence(
            candidate_entry_id=candidate["entry_id"], evidence_path=record,
            existing_index=second_path, output_path=tmp_path / "duplicate.json",
        )
    orphan = dict(evidence, subject_entry_id="candidate:" + "0" * 64)
    orphan["entry_digest"] = release_index.digest(release_index.canonical_json({
        key: value for key, value in orphan.items() if key != "entry_digest"
    }))
    orphan_path = tmp_path / "orphan.json"
    orphan_path.write_text(json.dumps({
        "schema": release_index.SCHEMA,
        "entries": [candidate, orphan],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="earlier candidate"):
        release_index.read_index(orphan_path)

    action_record = tmp_path / "action-evidence.json"
    action_body = json.loads(record.read_text(encoding="utf-8"))
    action_body.update({
        "review_pending_items": len(candidate["items"]) - 1,
        "needs_evidence_items": 1,
        "applied_transitions": 1,
        "review_action": {
            "item_ref": candidate["items"][0]["item_ref"],
            "action": "request-evidence",
            "run_id": "run-test",
            "successor_digest": "sha256:" + "d" * 64,
        },
    })
    action_record.write_text(json.dumps(action_body), encoding="utf-8")
    third = release_index.register_review_host_evidence(
        candidate_entry_id=candidate["entry_id"], evidence_path=action_record,
        existing_index=second_path, output_path=tmp_path / "with-action.json",
    )
    assert third["entries"][:2] == second["entries"]
    assert third["entries"][2]["status"] == "evidence"
    action_body["approved_items"] = 1
    action_record.write_text(json.dumps(action_body), encoding="utf-8")
    with pytest.raises(ValueError, match="does not bind the pending candidate"):
        release_index.register_review_host_evidence(
            candidate_entry_id=candidate["entry_id"], evidence_path=action_record,
            existing_index=second_path, output_path=tmp_path / "approved.json",
        )
    action_body["approved_items"] = 0
    action_body["review_pending_items"] = -1
    action_body["needs_evidence_items"] = len(candidate["items"]) + 1
    action_record.write_text(json.dumps(action_body), encoding="utf-8")
    with pytest.raises(ValueError, match="does not bind the pending candidate"):
        release_index.register_review_host_evidence(
            candidate_entry_id=candidate["entry_id"], evidence_path=action_record,
            existing_index=second_path, output_path=tmp_path / "negative.json",
        )

    record_body = json.loads(record.read_text(encoding="utf-8"))
    record_body["workflow_revision"] = "sha256:" + "c" * 64
    record.write_text(json.dumps(record_body), encoding="utf-8")
    with pytest.raises(ValueError, match="does not bind the pending candidate"):
        release_index.register_review_host_evidence(
            candidate_entry_id=candidate["entry_id"], evidence_path=record,
            existing_index=first_path, output_path=tmp_path / "mismatch.json",
        )


def test_review_host_registration_evidence_binds_development_materials(tmp_path, monkeypatch):
    import release_index

    monkeypatch.setattr(release_index, "ROOT", tmp_path)
    catalog = tmp_path / "release.json"
    catalog_body = {"schema": "scirel.catalog-release.v1"}
    catalog_body["root_digest"] = release_index.digest(release_index.canonical_json(catalog_body))
    catalog.write_text(json.dumps(catalog_body), encoding="utf-8")
    wheel = tmp_path / "wheel.whl"
    wheel.write_bytes(b"development wheel")
    development_path = tmp_path / "development.json"
    development = release_index.register_development_snapshot(
        snapshot_id="r43-dev5", catalog_release=catalog, wheel=wheel,
        evidence_paths=[catalog], destination_paths=[catalog],
        git_revision="a" * 40, source_qualification="mixed_unverified",
        output_path=development_path,
    )["entries"][0]
    pending = tmp_path / "pending.json"
    pending.write_bytes(_multi_item_workflow_body())
    candidate_path = tmp_path / "candidate.json"
    candidate = release_index.register_candidate(
        item_artifacts=[pending], git_revision="a" * 40,
        existing_index=development_path, output_path=candidate_path,
    )["entries"][-1]
    workflow_revision = candidate["items"][0]["initial_revision"]
    record = tmp_path / "registration.json"
    body = {
        "schema": "scirel.review-host-registration-acceptance.dev",
        "candidate_entry_id": candidate["entry_id"],
        "development_entry_id": development["entry_id"],
        "workflow_revision": workflow_revision,
        "scirel_source_revision": "a" * 40,
        "catalog_root_digest": development["catalog"]["root_digest"],
        "registration_digest": "sha256:" + "b" * 64,
        "owner_evidence_digest": "sha256:" + "d" * 64,
        "host_plugin_release_ref": "plugin-release://scirel/development",
        "host_artifacts": [
            {"role": "wheel", "artifact_ref": "cf://artifact/wheel",
             "digest": development["wheel"]["digest"], "media_type": "application/octet-stream"},
            {"role": "catalog_snapshot_zip", "artifact_ref": "cf://artifact/catalog",
             "digest": "sha256:" + "c" * 64,
             "media_type": "application/vnd.scirel.catalog-snapshot+zip"},
        ],
        "runtime_dependency_refs": [],
        "approval_state": "pending_unapproved",
        "approved_items": 0,
    }
    record.write_text(json.dumps(body), encoding="utf-8")
    result = release_index.register_review_host_evidence(
        candidate_entry_id=candidate["entry_id"], evidence_path=record,
        existing_index=candidate_path, output_path=tmp_path / "accepted.json",
    )
    assert result["entries"][:-1] == release_index.read_index(candidate_path)["entries"]
    assert result["entries"][-1]["evidence_type"] == "review_host_registration_acceptance"
    assert release_index.read_index(tmp_path / "accepted.json") == result

    body["host_artifacts"][0]["digest"] = "sha256:" + "0" * 64
    record.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(ValueError, match="does not bind"):
        release_index.register_review_host_evidence(
            candidate_entry_id=candidate["entry_id"], evidence_path=record,
            existing_index=candidate_path, output_path=tmp_path / "wrong-wheel.json",
        )
    body["host_artifacts"][0]["digest"] = development["wheel"]["digest"]
    body["workflow_revision"] = "sha256:" + "0" * 64
    record.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(ValueError, match="does not bind"):
        release_index.register_review_host_evidence(
            candidate_entry_id=candidate["entry_id"], evidence_path=record,
            existing_index=candidate_path, output_path=tmp_path / "wrong-workflow.json",
        )
    body["workflow_revision"] = workflow_revision
    body["approved_items"] = False
    record.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(ValueError, match="does not bind"):
        release_index.register_review_host_evidence(
            candidate_entry_id=candidate["entry_id"], evidence_path=record,
            existing_index=candidate_path, output_path=tmp_path / "boolean-approval.json",
        )


def test_repository_release_index_keeps_exact_evidence_bindings():
    from release_index import digest, read_index

    index = read_index(ROOT / "provenance/release-index.dev.json")
    assert index["entries"]
    for entry in index["entries"]:
        if entry["status"] in {"evidence", "lifecycle"}:
            bindings = [entry["evidence_ref"]]
        elif entry["status"] in {"candidate", "development"}:
            assert entry["approval_state"] == "pending_unapproved"
            bindings = [*entry["evidence_refs"], *entry["destination_refs"]]
        else:
            continue
        for binding in bindings:
            path = ROOT / binding["ref"]
            if path.is_file():
                assert digest(path.read_bytes()) == binding["digest"]
            else:
                assert binding["ref"].startswith("build/")


def test_strict_finalizer_rejects_a_candidate_without_item_approval(tmp_path):
    from finalize_release import finalize_reviewed_release
    from release_index import register_candidate

    item_path = tmp_path / "pending.json"
    item_path.write_text(json.dumps(_pending_item()), encoding="utf-8")
    register_candidate(
        item_artifacts=[item_path],
        git_revision="a" * 40,
        output_path=tmp_path / "index.json",
    )
    results = tmp_path / "completed.json"
    results.write_text(
        json.dumps(
            {
                "schema": "scirel.review-completed-results.dev",
                "completed_items": [],
                "approved_items": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="approved item"):
        finalize_reviewed_release(
            release_index=tmp_path / "index.json",
            candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
            approved_results=results,
            review_artifacts_dir=tmp_path,
            documents_dir=tmp_path,
            catalog_dir=tmp_path,
            wheel=tmp_path / "missing.whl",
            output_dir=tmp_path / "release",
            release_id="release-test",
            source_root=ROOT,
        )


def _reviewed_release_inputs(
    tmp_path, *, multi_item=False,
    document_name="scirel.field.circular-filament-green.json",
    git_revision="a" * 40,
    support_file=None,
    build_release_catalog=True,
    omit_dependencies=False,
):
    from build_catalog import build_catalog
    from release_index import register_candidate

    if multi_item:
        pending_body = _multi_item_workflow_body(release_ready=True)
        item = review_items_from_body(pending_body)[0]
    else:
        item = _pending_item(
            release_ready=True, document_name=document_name,
            support_file=support_file,
            omit_dependencies=omit_dependencies,
        )
        pending_body = json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")
    pending_revision = "sha256:" + hashlib.sha256(pending_body).hexdigest()
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / f"{pending_revision[7:]}.json").write_bytes(pending_body)
    register_candidate(
        item_artifacts=[artifacts / f"{pending_revision[7:]}.json"],
        git_revision=git_revision,
        output_path=tmp_path / "index.json",
    )
    successor_body = execute_body_import_wire({
        "operation": "plugin.review.action",
        "artifact_ref": "artifact://review/pending",
        "artifact_digest": pending_revision,
        "media_type": "application/json",
        "body": pending_body.decode("utf-8"),
        "operation_payload": {
            "item_ref": item["item_ref"],
            "revision": pending_revision,
            "extension_ref": "scirel.review",
            "action_ref": "plugin://scirel/review/approve",
            "reviewer": {"actor_ref": "actor://reviewer/test-expert"},
            "payload": {"outcome": "approved", "notes": "test fixture"},
        },
    })["body"].encode("utf-8")
    revision = "sha256:" + hashlib.sha256(successor_body).hexdigest()
    (artifacts / f"{revision[7:]}.json").write_bytes(successor_body)
    approved_item = review_item_from_body(successor_body)
    projection = {
        "item_ref": item["item_ref"],
        "revision": revision,
        "asset": approved_item["asset"],
        "dependency_asset_ids": approved_item["dependency_asset_ids"],
        "evidence": approved_item["evidence"],
        "decision": approved_item["decision"],
    }
    (tmp_path / "results.json").write_text(json.dumps({
        "schema": "scirel.review-completed-results.dev",
        "completed_items": [projection],
        "approved_items": [projection],
    }), encoding="utf-8")
    documents = tmp_path / "documents"
    documents.mkdir()
    (documents / "asset.json").write_text(json.dumps(item["asset"]), encoding="utf-8")
    catalog = tmp_path / "catalog"
    if build_release_catalog:
        build_catalog(
            documents, catalog, catalog_id="test-reviewed-release",
            release_version="0.1.0.dev5", coverage_status="complete",
            declared_total=1,
        )
    wheel = tmp_path / "scirel-0.1.0.dev5-py3-none-any.whl"
    module_name = item["asset"]["public_api"]["python"]["module"].replace(".", "/") + ".py"
    with ZipFile(wheel, "w") as archive:
        archive.writestr(
            "scirel-0.1.0.dev5.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: scirel\nVersion: 0.1.0.dev5\n",
        )
        archive.writestr(module_name, (ROOT / "src" / module_name).read_bytes())
    return artifacts, documents, catalog, wheel, projection


def test_first_reviewed_distribution_rejects_incomplete_composition_dependencies(tmp_path):
    from prepare_reviewed_distribution import prepare_reviewed_distribution

    artifacts, _, _, _, projection = _reviewed_release_inputs(
        tmp_path,
        document_name="scirel.kinetic.kinetic-dispersion-relation.json",
        build_release_catalog=False,
    )
    assert "scirel.kinetic.species-equilibrium-scales" in projection["dependency_asset_ids"]
    staging = tmp_path / "reviewed-source"
    with pytest.raises(
        ValueError,
        match=r"release dependency closure is incomplete: scirel\.kinetic\.kinetic-dispersion-relation",
    ):
        prepare_reviewed_distribution(
            release_index=tmp_path / "index.json",
            candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
            approved_results=tmp_path / "results.json",
            review_artifacts_dir=artifacts,
            source_root=ROOT,
            staging_dir=staging,
        )
    assert not staging.exists()


@pytest.mark.parametrize(
    ("document_name", "missing_module"),
    [
        (
            "scirel.kinetic.kinetic-dispersion-ronnmark.json",
            "scirel.kinetic.ronnmark_r_function",
        ),
        (
            "scirel.kinetic.kinetic-wavevector-roots.json",
            "scirel.kinetic.kinetic_dispersion_ronnmark",
        ),
    ],
)
def test_first_reviewed_distribution_rejects_undeclared_internal_import(
    tmp_path, document_name, missing_module
):
    from prepare_reviewed_distribution import prepare_reviewed_distribution

    artifacts, _, _, _, _ = _reviewed_release_inputs(
        tmp_path, document_name=document_name, omit_dependencies=True
    )
    staging = tmp_path / "reviewed-source"
    with pytest.raises(ValueError, match="missing internal import") as error:
        prepare_reviewed_distribution(
            release_index=tmp_path / "index.json",
            candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
            approved_results=tmp_path / "results.json",
            review_artifacts_dir=artifacts,
            source_root=ROOT,
            staging_dir=staging,
        )
    assert missing_module in str(error.value)
    assert not staging.exists()


@pytest.mark.parametrize("multi_item", [False, True])
def test_reviewed_finalization_binds_item_document_test_and_wheel(tmp_path, monkeypatch, multi_item):
    import finalize_release

    artifacts, documents, catalog, wheel, projection = _reviewed_release_inputs(
        tmp_path, multi_item=multi_item
    )
    monkeypatch.setattr(finalize_release, "_git_revision", lambda root: "a" * 40)
    monkeypatch.setattr(finalize_release, "_git_changed_files", lambda root, revision: set())
    monkeypatch.setattr(finalize_release, "_require_clean_release_sources", lambda root: None)
    result = finalize_release.finalize_reviewed_release(
        release_index=tmp_path / "index.json",
        candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
        approved_results=tmp_path / "results.json",
        review_artifacts_dir=artifacts,
        documents_dir=documents,
        catalog_dir=catalog,
        wheel=wheel,
        output_dir=tmp_path / "release",
        release_id="release-test",
        source_root=ROOT,
    )
    manifest = json.loads(Path(result["release_manifest"]).read_text(encoding="utf-8"))
    index = json.loads(Path(result["release_index"]).read_text(encoding="utf-8"))
    assert manifest["approved_items"][0]["revision"] == projection["revision"]
    assert len(manifest["approved_items"]) == 1
    assert manifest["verified_tests"] == [
        "tests/operator_contracts/test_circular_filament_green.py"
    ]
    assert manifest["verified_test_run"]["exit_code"] == 0
    assert index["entries"][-1]["status"] == "released"
    contract = json.loads((ROOT / "contracts/reviewed-release-manifest-dev.schema.json").read_text(encoding="utf-8"))
    assert set(manifest) == set(contract["required"])


def test_first_reviewed_distribution_builds_only_the_selected_asset(tmp_path, monkeypatch):
    import finalize_release
    from build_catalog import build_catalog
    from prepare_reviewed_distribution import prepare_reviewed_distribution

    artifacts, _, _, _, _ = _reviewed_release_inputs(tmp_path)
    staging = tmp_path / "reviewed-source"
    result = prepare_reviewed_distribution(
        release_index=tmp_path / "index.json",
        candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
        approved_results=tmp_path / "results.json",
        review_artifacts_dir=artifacts,
        source_root=ROOT,
        staging_dir=staging,
    )
    assert result["asset_count"] == 1
    assert result["test_paths"] == [
        "tests/operator_contracts/test_circular_filament_green.py"
    ]
    wheel_dir = tmp_path / "built-wheel"
    wheel_dir.mkdir()
    built = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--disable-pip-version-check",
         "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheel_dir), str(staging)],
        capture_output=True, text=True, check=True,
    )
    assert built.returncode == 0
    wheel = next(wheel_dir.glob("*.whl"))
    with ZipFile(wheel) as archive:
        source_members = {name for name in archive.namelist() if name.startswith("scirel/")}
    assert source_members == {
        "scirel/__init__.py",
        "scirel/field/__init__.py",
        "scirel/field/circular_filament_green.py",
    }
    catalog = tmp_path / "built-catalog"
    build_catalog(
        staging / "documents", catalog, catalog_id="test-reviewed-subset",
        release_version="0.1.0.dev5", coverage_status="complete", declared_total=1,
    )
    monkeypatch.setattr(finalize_release, "_git_revision", lambda root: "a" * 40)
    monkeypatch.setattr(finalize_release, "_git_changed_files", lambda root, revision: set())
    monkeypatch.setattr(finalize_release, "_require_clean_release_sources", lambda root: None)
    finalized = finalize_release.finalize_reviewed_release(
        release_index=tmp_path / "index.json",
        candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
        approved_results=tmp_path / "results.json",
        review_artifacts_dir=artifacts,
        documents_dir=staging / "documents",
        catalog_dir=catalog,
        wheel=wheel,
        output_dir=tmp_path / "reviewed-release",
        release_id="release-test",
        source_root=ROOT,
    )
    assert Path(finalized["release_manifest"]).is_file()


def test_first_reviewed_distribution_requires_bound_private_support(tmp_path):
    from prepare_reviewed_distribution import prepare_reviewed_distribution

    artifacts, _, _, _, _ = _reviewed_release_inputs(
        tmp_path,
        document_name="scirel.closures.mirror-ambipolar-potential.json",
    )
    staging = tmp_path / "reviewed-source"
    with pytest.raises(ValueError, match="missing internal import.*scirel._validation"):
        prepare_reviewed_distribution(
            release_index=tmp_path / "index.json",
            candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
            approved_results=tmp_path / "results.json",
            review_artifacts_dir=artifacts,
            source_root=ROOT,
            staging_dir=staging,
        )
    assert not staging.exists()


def test_first_reviewed_distribution_includes_bound_private_support(tmp_path, monkeypatch):
    import finalize_release
    from build_catalog import build_catalog
    from prepare_reviewed_distribution import prepare_reviewed_distribution

    support = "src/scirel/_validation.py"
    artifacts, _, _, _, _ = _reviewed_release_inputs(
        tmp_path,
        document_name="scirel.closures.mirror-ambipolar-potential.json",
        support_file=support,
    )
    staging = tmp_path / "reviewed-source"
    result = prepare_reviewed_distribution(
        release_index=tmp_path / "index.json",
        candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
        approved_results=tmp_path / "results.json",
        review_artifacts_dir=artifacts,
        source_root=ROOT,
        staging_dir=staging,
    )
    assert result["asset_count"] == 1
    assert (staging / support).read_bytes() == (ROOT / support).read_bytes()
    assert not (staging / "src/scirel/field").exists()
    wheel_dir = tmp_path / "built-wheel"
    wheel_dir.mkdir()
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--disable-pip-version-check",
         "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheel_dir), str(staging)],
        capture_output=True, text=True, check=True,
    )
    catalog = tmp_path / "built-catalog"
    build_catalog(
        staging / "documents", catalog, catalog_id="test-reviewed-support",
        release_version="0.1.0.dev5", coverage_status="complete", declared_total=1,
    )
    monkeypatch.setattr(finalize_release, "_git_revision", lambda root: "a" * 40)
    monkeypatch.setattr(finalize_release, "_git_changed_files", lambda root, revision: set())
    monkeypatch.setattr(finalize_release, "_require_clean_release_sources", lambda root: None)
    finalized = finalize_release.finalize_reviewed_release(
        release_index=tmp_path / "index.json",
        candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
        approved_results=tmp_path / "results.json",
        review_artifacts_dir=artifacts,
        documents_dir=staging / "documents",
        catalog_dir=catalog,
        wheel=next(wheel_dir.glob("*.whl")),
        output_dir=tmp_path / "reviewed-release",
        release_id="release-test",
        source_root=ROOT,
    )
    assert Path(finalized["release_manifest"]).is_file()


def test_reviewed_finalization_rejects_changed_wheel_code(tmp_path, monkeypatch):
    import finalize_release

    artifacts, documents, catalog, wheel, _ = _reviewed_release_inputs(tmp_path)
    with ZipFile(wheel, "w") as archive:
        archive.writestr(
            "scirel-0.1.0.dev5.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: scirel\nVersion: 0.1.0.dev5\n",
        )
        archive.writestr("scirel/field/circular_filament_green.py", b"changed")
    monkeypatch.setattr(finalize_release, "_git_revision", lambda root: "a" * 40)
    monkeypatch.setattr(finalize_release, "_git_changed_files", lambda root, revision: set())
    monkeypatch.setattr(finalize_release, "_require_clean_release_sources", lambda root: None)
    with pytest.raises(ValueError, match="wheel differs from source"):
        finalize_release.finalize_reviewed_release(
            release_index=tmp_path / "index.json",
            candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
            approved_results=tmp_path / "results.json",
            review_artifacts_dir=artifacts,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=wheel,
            output_dir=tmp_path / "release",
            release_id="release-test",
            source_root=ROOT,
        )


def test_reviewed_finalization_rejects_unapproved_science_module(tmp_path, monkeypatch):
    import finalize_release

    artifacts, documents, catalog, wheel, _ = _reviewed_release_inputs(tmp_path)
    approved_module = "scirel/field/circular_filament_green.py"
    unapproved_module = "scirel/field/poloidal_field_magnitude.py"
    with ZipFile(wheel, "w") as archive:
        archive.writestr(
            "scirel-0.1.0.dev5.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: scirel\nVersion: 0.1.0.dev5\n",
        )
        for name in (approved_module, unapproved_module):
            archive.writestr(name, (ROOT / "src" / name).read_bytes())
    monkeypatch.setattr(finalize_release, "_git_revision", lambda root: "a" * 40)
    monkeypatch.setattr(finalize_release, "_git_changed_files", lambda root, revision: set())
    monkeypatch.setattr(finalize_release, "_require_clean_release_sources", lambda root: None)

    with pytest.raises(ValueError, match="unapproved scientific module"):
        finalize_release.finalize_reviewed_release(
            release_index=tmp_path / "index.json",
            candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
            approved_results=tmp_path / "results.json",
            review_artifacts_dir=artifacts,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=wheel,
            output_dir=tmp_path / "release",
            release_id="release-test",
            source_root=ROOT,
        )


@pytest.mark.parametrize(
    ("extra_name", "message"),
    [
        ("scirel_plugin/adapter.py", "outside the reviewed SciRel package"),
        ("scirel/_validation.py", "unreviewed support module"),
    ],
)
def test_reviewed_finalization_rejects_unreviewed_wheel_content(
    tmp_path, monkeypatch, extra_name, message
):
    import finalize_release

    artifacts, documents, catalog, wheel, _ = _reviewed_release_inputs(tmp_path)
    with ZipFile(wheel) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    members[extra_name] = (ROOT / "src" / extra_name).read_bytes()
    with ZipFile(wheel, "w") as archive:
        for name, body in members.items():
            archive.writestr(name, body)
    monkeypatch.setattr(finalize_release, "_git_revision", lambda root: "a" * 40)
    monkeypatch.setattr(finalize_release, "_git_changed_files", lambda root, revision: set())
    monkeypatch.setattr(finalize_release, "_require_clean_release_sources", lambda root: None)

    with pytest.raises(ValueError, match=message):
        finalize_release.finalize_reviewed_release(
            release_index=tmp_path / "index.json",
            candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
            approved_results=tmp_path / "results.json",
            review_artifacts_dir=artifacts,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=wheel,
            output_dir=tmp_path / "release",
            release_id="release-test",
            source_root=ROOT,
        )


def test_reviewed_finalization_requires_private_import_closure(tmp_path, monkeypatch):
    import finalize_release

    artifacts, documents, catalog, wheel, _ = _reviewed_release_inputs(
        tmp_path,
        document_name="scirel.closures.mirror-ambipolar-potential.json",
    )
    monkeypatch.setattr(finalize_release, "_git_revision", lambda root: "a" * 40)
    monkeypatch.setattr(finalize_release, "_git_changed_files", lambda root, revision: set())
    monkeypatch.setattr(finalize_release, "_require_clean_release_sources", lambda root: None)

    with pytest.raises(ValueError, match="missing internal import.*scirel._validation"):
        finalize_release.finalize_reviewed_release(
            release_index=tmp_path / "index.json",
            candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
            approved_results=tmp_path / "results.json",
            review_artifacts_dir=artifacts,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=wheel,
            output_dir=tmp_path / "release",
            release_id="release-test",
            source_root=ROOT,
        )


def test_reviewed_wheel_import_closure_accepts_bound_private_support():
    from finalize_release import _validate_wheel_import_closure

    module = "scirel/closures/mirror_ambipolar_potential.py"
    support = "scirel/_validation.py"
    members = {
        name: (ROOT / "src" / name).read_bytes()
        for name in (module, support)
    }

    _validate_wheel_import_closure(members, ROOT)


def test_reviewed_wheel_import_closure_rejects_unfiltered_package_initializer():
    from finalize_release import _validate_wheel_import_closure

    members = {
        name: (ROOT / "src" / name).read_bytes()
        for name in (
            "scirel/field/__init__.py",
            "scirel/field/circular_filament_green.py",
        )
    }

    with pytest.raises(ValueError, match="missing internal import.*poloidal_field_magnitude"):
        _validate_wheel_import_closure(members, ROOT)


def test_reviewed_finalization_rejects_partial_approval_of_shared_module(tmp_path, monkeypatch):
    import finalize_release

    artifacts, documents, catalog, wheel, _ = _reviewed_release_inputs(
        tmp_path, document_name="scirel.collisions.normalized-momentum.json"
    )
    monkeypatch.setattr(finalize_release, "_git_revision", lambda root: "a" * 40)
    monkeypatch.setattr(finalize_release, "_git_changed_files", lambda root, revision: set())
    monkeypatch.setattr(finalize_release, "_require_clean_release_sources", lambda root: None)

    with pytest.raises(ValueError, match="unapproved asset in a shared module"):
        finalize_release.finalize_reviewed_release(
            release_index=tmp_path / "index.json",
            candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
            approved_results=tmp_path / "results.json",
            review_artifacts_dir=artifacts,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=wheel,
            output_dir=tmp_path / "release",
            release_id="release-test",
            source_root=ROOT,
        )


def test_reviewed_finalization_rejects_a_forged_approval_projection(tmp_path):
    import finalize_release

    artifacts, documents, catalog, wheel, _ = _reviewed_release_inputs(tmp_path)
    results_path = tmp_path / "results.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    results["approved_items"][0]["asset"]["summary"] = "unreviewed change"
    results["completed_items"][0]["asset"]["summary"] = "unreviewed change"
    results_path.write_text(json.dumps(results), encoding="utf-8")

    with pytest.raises(ValueError, match="projection differs"):
        finalize_release.finalize_reviewed_release(
            release_index=tmp_path / "index.json",
            candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
            approved_results=results_path,
            review_artifacts_dir=artifacts,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=wheel,
            output_dir=tmp_path / "release",
            release_id="release-test",
            source_root=ROOT,
        )

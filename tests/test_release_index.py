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
    document_name="fixture-identity.json",
    support_file=None,
    omit_dependencies=False,
):
    document = json.loads(
        (ROOT / "tests/fixtures/contracts" / document_name).read_text(
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


def _multi_item_workflow_body(*, release_ready=False, asset_count=2):
    assert asset_count >= 2
    first = _pending_item(release_ready=release_ready)
    second = json.loads(
        (ROOT / "tests/fixtures/contracts/fixture-secondary.json").read_text(
            encoding="utf-8"
        )
    )
    additional = []
    for index in range(asset_count - 2):
        document = json.loads(json.dumps(second))
        document["asset_id"] = f"scirel.fixture.extra-{index}"
        document["public_api"]["python"]["module"] = f"scirel.fixture.extra_{index}"
        additional.append(document)
    candidate = CandidatePackage.from_l1(
        {
            "assets": [
                {"candidate_asset_id": "candidate-field"},
                {"candidate_asset_id": "candidate-closure"},
                *({"candidate_asset_id": f"candidate-extra-{index}"}
                  for index in range(len(additional))),
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
        assets=[first["asset"], second, *additional],
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
    second["coverage"] = {
        "scope": "registered_entries_only",
        "current_unpublished_entry_ids": [old_id, new_id],
        "unindexed_scopes": {
            "external_source_checkouts": "not_independently_inventoried",
            "host_artifacts_outside_index": "not_independently_inventoried",
            "d1_inputs_not_handed_to_d2": "not_independently_inventoried",
        },
    }
    second_path.write_text(json.dumps(second), encoding="utf-8")
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
    assert third["coverage"]["current_unpublished_entry_ids"] == [new_id]
    assert third["coverage"]["unindexed_scopes"] == second["coverage"]["unindexed_scopes"]
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
    assert with_candidate["coverage"]["current_unpublished_entry_ids"] == [
        new_id, with_candidate["entries"][-1]["entry_id"]
    ]
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


def test_host_evidence_binds_current_candidate_and_development(tmp_path, monkeypatch):
    import release_index

    monkeypatch.setattr(release_index, "ROOT", tmp_path)
    artifact = tmp_path / "pending.json"
    artifact.write_bytes(_multi_item_workflow_body())
    candidate_path = tmp_path / "candidate.json"
    candidate_index = release_index.register_candidate(
        item_artifacts=[artifact], git_revision="a" * 40,
        output_path=candidate_path,
    )
    candidate = candidate_index["entries"][0]
    catalog = tmp_path / "release.json"
    catalog_body = {"schema": "scirel.catalog-release.v1"}
    catalog_body["root_digest"] = release_index.digest(release_index.canonical_json(catalog_body))
    catalog.write_text(json.dumps(catalog_body), encoding="utf-8")
    wheel = tmp_path / "scirel-0.1.0.dev5-py3-none-any.whl"
    wheel.write_bytes(b"development wheel")
    development_path = tmp_path / "development.json"
    development_index = release_index.register_development_snapshot(
        snapshot_id="r43-dev5", catalog_release=catalog, wheel=wheel,
        evidence_paths=[catalog], destination_paths=[catalog],
        git_revision="a" * 40, source_qualification="mixed_unverified",
        existing_index=candidate_path, output_path=development_path,
    )
    development = development_index["entries"][-1]
    snapshot_digest = "sha256:" + "b" * 64
    record_body = {
        "schema": "scirel.development-host-acceptance.dev",
        "status": "development_host_same_tuple_acceptance",
        "development_entry_id": development["entry_id"],
        "candidate_entry_id": candidate["entry_id"],
        "scirel_source_revision": "a" * 40,
        "source_qualification": "mixed_unverified",
        "approval_state": "pending_unapproved",
        "runtime": {
            "wheel_digest": development["wheel"]["digest"],
            "catalog_release_digest": development["catalog"]["digest"],
            "catalog_root_digest": development["catalog"]["root_digest"],
            "catalog_snapshot_digest": snapshot_digest,
        },
        "codefusion_host": {
            "source_revision": "c" * 40,
            "acceptance_digest": "sha256:" + "d" * 64,
            "backend_version": "0.1.0.dev5",
            "release_ref": (
                "plugin-release://scirel/0.1.0.dev5/source-" + "a" * 40
                + "/wheel-" + development["wheel"]["digest"][7:]
                + "/catalog-" + snapshot_digest[7:]
            ),
        },
        "reviewer": {
            "project_ref": "reviewer-project", "wheel_artifact_ref": "cf://wheel/reviewer",
            "catalog_artifact_ref": "cf://catalog/reviewer",
            "initial_l1_run_id": "run-failed", "completed_l1_run_id": "run-completed",
            "completed_l1_result_digest": "sha256:" + "1" * 64,
            "review_run_id": "run-review",
            "workflow_revision": candidate["items"][0]["initial_revision"],
            "item_count": len(candidate["items"]), "applied_transitions": 0,
            "approved_items": 0, "run_status": "completed",
            "snapshot_artifact_ref": "cf://snapshot/reviewer",
            "snapshot_digest": "sha256:" + "e" * 64,
        },
        "ordinary_user": {
            "project_ref": "ordinary-project", "wheel_artifact_ref": "cf://wheel/ordinary",
            "catalog_artifact_ref": "cf://catalog/ordinary",
            "request_ref": "appreq-current", "request_status": "completed",
            "evidence_digest": "sha256:" + "f" * 64,
        },
    }
    record = tmp_path / "host.json"
    record.write_text(json.dumps(record_body), encoding="utf-8")
    output = tmp_path / "host-index.json"
    result = release_index.register_development_host_evidence(
        development_entry_id=development["entry_id"], evidence_path=record,
        existing_index=development_path, output_path=output,
    )
    assert result["entries"][:-1] == development_index["entries"]
    assert result["entries"][-1]["evidence_type"] == "development_host_acceptance"
    assert result["entries"][-1]["approval_state"] == "pending_unapproved"
    assert release_index.read_index(output) == result
    contract = json.loads((ROOT / "contracts/release-index-dev.schema.json").read_text(encoding="utf-8"))
    assert "development_host_acceptance" in contract["$defs"]["evidence"]["oneOf"][1]["properties"]["evidence_type"]["enum"]

    for label, modify in (
        ("wrong-wheel", lambda body: body["runtime"].update(wheel_digest="sha256:" + "0" * 64)),
        ("wrong-release", lambda body: body["codefusion_host"].update(release_ref="plugin-release://scirel/old")),
        ("same-l1-run", lambda body: body["reviewer"].update(completed_l1_run_id="run-failed")),
        ("approved", lambda body: body["reviewer"].update(approved_items=1)),
        ("shared-project", lambda body: body["ordinary_user"].update(project_ref="reviewer-project")),
        ("wrong-candidate", lambda body: body.update(candidate_entry_id="candidate:" + "0" * 64)),
    ):
        invalid = json.loads(json.dumps(record_body))
        modify(invalid)
        record.write_text(json.dumps(invalid), encoding="utf-8")
        with pytest.raises(ValueError, match="host evidence does not bind"):
            release_index.register_development_host_evidence(
                development_entry_id=development["entry_id"], evidence_path=record,
                existing_index=development_path, output_path=tmp_path / f"{label}.json",
            )


def test_project_case_evidence_binds_exact_development_artifacts(tmp_path, monkeypatch):
    import release_index

    monkeypatch.setattr(release_index, "ROOT", tmp_path)
    catalog = tmp_path / "release.json"
    catalog_body = {"schema": "scirel.catalog-release.v1"}
    catalog_body["root_digest"] = release_index.digest(release_index.canonical_json(catalog_body))
    catalog.write_text(json.dumps(catalog_body), encoding="utf-8")
    wheel = tmp_path / "scirel-0.1.0.dev5-py3-none-any.whl"
    wheel.write_bytes(b"c69 development wheel")
    development_path = tmp_path / "development.json"
    development_index = release_index.register_development_snapshot(
        snapshot_id="r43-c69", catalog_release=catalog, wheel=wheel,
        evidence_paths=[catalog], destination_paths=[catalog],
        git_revision="a" * 40, source_qualification="mixed_unverified",
        output_path=development_path,
    )
    development = development_index["entries"][0]
    document = tmp_path / "selected.json"
    document.write_text(json.dumps({"asset_id": "scirel.kinetic.test"}), encoding="utf-8")
    acceptance = tmp_path / "d2.json"
    acceptance.write_bytes(b"D2 acceptance")
    archive = tmp_path / "project.tgz"
    archive.write_bytes(b"frozen project")
    receipt = tmp_path / "freeze.json"
    receipt.write_bytes(b"freeze receipt")

    def file_ref(path):
        return str(path), hashlib.sha256(path.read_bytes()).hexdigest()

    wheel_path, wheel_hash = file_ref(wheel)
    catalog_path, catalog_hash = file_ref(catalog)
    document_path, document_hash = file_ref(document)
    acceptance_path, acceptance_hash = file_ref(acceptance)
    archive_path, archive_hash = file_ref(archive)
    receipt_path, receipt_hash = file_ref(receipt)
    record_body = {
        "schema": "scirel.outbound-evaluation-manifest.v1",
        "case_id": "bounded-project-case",
        "status": "development_user_project_bounded_candidate",
        "not_claims": ["expert_approval", "trusted_release", "public_v1"],
        "d2_handoff": {
            "git_commit": "a" * 40,
            "independent_acceptance": acceptance_path,
            "independent_acceptance_sha256": acceptance_hash,
        },
        "runtime": {
            "wheel": wheel_path, "wheel_sha256": wheel_hash,
            "catalog_release": catalog_path,
            "catalog_release_sha256": catalog_hash,
            "catalog_root_digest": development["catalog"]["root_digest"],
            "selected_asset_id": "scirel.kinetic.test",
            "selected_document": document_path,
            "selected_document_sha256": document_hash,
        },
        "evidence": {
            "archive": archive_path, "archive_sha256": archive_hash,
            "receipt": receipt_path, "receipt_sha256": receipt_hash,
        },
    }
    record = tmp_path / "project-case.json"
    record.write_text(json.dumps(record_body), encoding="utf-8")
    output = tmp_path / "with-project-case.json"
    result = release_index.register_development_project_evidence(
        development_entry_id=development["entry_id"], evidence_path=record,
        existing_index=development_path, output_path=output,
    )
    assert result["entries"][0] == development
    assert result["entries"][1]["evidence_type"] == "development_project_case_acceptance"
    assert result["entries"][1]["approval_state"] == "pending_unapproved"
    assert release_index.read_index(output) == result

    for label, modify in (
        ("wrong-source", lambda body: body["d2_handoff"].update(git_commit="b" * 40)),
        ("wrong-wheel", lambda body: body["runtime"].update(wheel_sha256="0" * 64)),
        ("wrong-archive", lambda body: body["evidence"].update(archive_sha256="0" * 64)),
        ("approval-claim", lambda body: body.update(not_claims=["public_v1"])),
    ):
        invalid = json.loads(json.dumps(record_body))
        modify(invalid)
        record.write_text(json.dumps(invalid), encoding="utf-8")
        with pytest.raises(ValueError, match="project evidence"):
            release_index.register_development_project_evidence(
                development_entry_id=development["entry_id"], evidence_path=record,
                existing_index=development_path, output_path=tmp_path / f"{label}.json",
            )


def test_recovery_evidence_binds_existing_development_without_approval(tmp_path, monkeypatch):
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
    record = tmp_path / "recovery.json"
    record_body = {
        "schema": "scirel.development-consumer-recovery-acceptance.dev",
        "status": "development_product_ordinary_recovery_acceptance",
        "development_entry_id": development["entry_id"],
        "scirel_source_revision": "a" * 40,
        "source_qualification": "mixed_unverified",
        "runtime": {
            "wheel_sha256": development["wheel"]["digest"][7:],
            "catalog_release_sha256": development["catalog"]["digest"][7:],
            "catalog_root_digest": development["catalog"]["root_digest"],
            "input_zip_digest": "sha256:" + "b" * 64,
            "qualified_l1_zip_digest": "sha256:" + "c" * 64,
        },
        "codefusion_observation": {
            "source_revision": "d" * 40,
            "project_ref": "project-1", "session_ref": "session-1",
            "environment_version": "env-1",
            "skill_content_digest": "sha256:" + "e" * 64,
            "request_refs": ["request-failed", "request-corrected"],
            "final_request_status": "completed",
        },
        "saved_evidence": {
            "owner_receipt_digest": "sha256:" + "1" * 64,
            "initial_failure_digest": "sha256:" + "2" * 64,
            "pre_correction_result_digest": "sha256:" + "3" * 64,
            "final_result_digest": "sha256:" + "4" * 64,
            "final_script_digest": "sha256:" + "5" * 64,
        },
        "review_boundary": {"approved_items": 0},
        "approval_state": "pending_unapproved",
    }
    record.write_text(json.dumps(record_body), encoding="utf-8")
    second_path = tmp_path / "with-recovery.json"
    second = release_index.register_development_consumer_evidence(
        development_entry_id=development["entry_id"], evidence_path=record,
        existing_index=first_path, output_path=second_path,
    )
    assert second["entries"][0] == development
    assert second["entries"][1]["evidence_type"] == "development_consumer_recovery_acceptance"
    assert second["entries"][1]["approval_state"] == "pending_unapproved"
    assert release_index.read_index(second_path) == second

    for label, modify in (
        ("wrong-wheel", lambda body: body["runtime"].update(wheel_sha256="0" * 64)),
        ("duplicate-request", lambda body: body["codefusion_observation"].update(
            request_refs=["request-failed", "request-failed"])),
        ("missing-failure", lambda body: body["saved_evidence"].pop("initial_failure_digest")),
        ("approved", lambda body: body["review_boundary"].update(approved_items=1)),
    ):
        invalid = json.loads(json.dumps(record_body))
        modify(invalid)
        record.write_text(json.dumps(invalid), encoding="utf-8")
        with pytest.raises(ValueError, match="recovery evidence does not bind"):
            release_index.register_development_consumer_evidence(
                development_entry_id=development["entry_id"], evidence_path=record,
                existing_index=first_path, output_path=tmp_path / f"{label}.json",
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


def test_repository_release_index_has_no_inherited_candidates_or_approval():
    from release_index import current_unpublished_entries, read_index

    index = read_index(ROOT / "provenance/mainline-release-index.dev.json")
    assert index["entries"] == []
    assert current_unpublished_entries(index) == []
    assert index["coverage"]["scope"] == "registered_entries_only"
    assert index["coverage"]["current_unpublished_entry_ids"] == []
    assert set(index["coverage"]["unindexed_scopes"].values()) == {
        "not_independently_inventoried"
    }


@pytest.mark.parametrize("overstatement", ["stale_candidate", "inventory_complete"])
def test_release_index_rejects_stale_or_overstated_coverage(tmp_path, overstatement):
    from release_index import read_index

    index = json.loads((ROOT / "provenance/mainline-release-index.dev.json").read_text())
    if overstatement == "stale_candidate":
        index["coverage"]["current_unpublished_entry_ids"] = ["nonexistent-candidate"]
    else:
        index["coverage"]["unindexed_scopes"]["external_source_checkouts"] = "complete"
    path = tmp_path / "overstated-index.json"
    path.write_text(json.dumps(index))
    with pytest.raises(ValueError, match="coverage differs"):
        read_index(path)


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
    tmp_path, *, multi_item=False, multi_item_count=2,
    document_name="fixture-identity.json",
    git_revision="a" * 40,
    support_file=None,
    build_release_catalog=True,
    omit_dependencies=False,
):
    from build_catalog import build_catalog
    from release_index import register_candidate

    if multi_item:
        pending_body = _multi_item_workflow_body(
            release_ready=True, asset_count=multi_item_count
        )
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
        archive.writestr(module_name, (ROOT / "tests/fixtures/runtime/identity.py").read_bytes())
    return artifacts, documents, catalog, wheel, projection


@pytest.mark.parametrize("alter_tests", [False, True])
def test_first_release_preparation_uses_only_selected_synthetic_material(tmp_path, alter_tests):
    from prepare_reviewed_distribution import prepare_reviewed_distribution

    artifacts, _, _, _, _ = _reviewed_release_inputs(tmp_path)
    source = tmp_path / "maintained"
    module = source / "src/scirel/fixture/identity.py"
    module.parent.mkdir(parents=True)
    module.write_bytes((ROOT / "tests/fixtures/runtime/identity.py").read_bytes())
    (module.parent / "unselected.py").write_text("raise RuntimeError('must not enter selected wheel')\n")
    root_init = source / "src/scirel/__init__.py"
    root_init.write_text("__all__ = []\n")
    (source / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
    tests = source / "tests/fixtures/runtime/check_identity.py"
    tests.parent.mkdir(parents=True)
    tests.write_bytes((ROOT / "tests/fixtures/runtime/check_identity.py").read_bytes())
    if alter_tests:
        tests.write_text("# unreviewed replacement\n")
    stage = tmp_path / "stage"
    arguments = dict(
        release_index=tmp_path / "index.json",
        candidate_entry_id=_candidate_entry_id(tmp_path / "index.json"),
        approved_results=tmp_path / "results.json",
        review_artifacts_dir=artifacts,
        source_root=source,
        staging_dir=stage,
    )
    if alter_tests:
        with pytest.raises(ValueError, match="approved test differs"):
            prepare_reviewed_distribution(**arguments)
        assert not stage.exists()
    else:
        result = prepare_reviewed_distribution(**arguments)
        assert result["asset_count"] == 1
        assert result["test_paths"] == ["tests/fixtures/runtime/check_identity.py"]
        assert (stage / "src/scirel/fixture/identity.py").read_bytes() == module.read_bytes()
        assert not (stage / "src/scirel/fixture/unselected.py").exists()
        assert "from .fixture.identity import identity" in (stage / "src/scirel/__init__.py").read_text()
    assert root_init.read_text() == "__all__ = []\n"

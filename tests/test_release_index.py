"""Development release index and exact review binding gates."""

import hashlib
import json
from pathlib import Path
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
):
    document = json.loads(
        (ROOT / "catalog/examples" / document_name).read_text(
            encoding="utf-8"
        )
    )
    evidence = []
    if release_ready:
        document["provenance"]["license_status"] = "approved-for-public-release"
        test_name = document["verification"]["tests"][0]
        test_body = (ROOT / test_name).read_bytes().decode("utf-8")
        code = {
            "kind": "none", "content": None,
            "rationale": "The maintained implementation is reused unchanged.",
        }
        code["digest"] = digest(code)
        tests = {
            "content": {"files": {test_name: test_body}},
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
):
    from build_catalog import build_catalog
    from release_index import register_candidate

    if multi_item:
        pending_body = _multi_item_workflow_body(release_ready=True)
        item = review_items_from_body(pending_body)[0]
    else:
        item = _pending_item(release_ready=True, document_name=document_name)
        pending_body = json.dumps(item, ensure_ascii=False, sort_keys=True).encode("utf-8")
    pending_revision = "sha256:" + hashlib.sha256(pending_body).hexdigest()
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / f"{pending_revision[7:]}.json").write_bytes(pending_body)
    register_candidate(
        item_artifacts=[artifacts / f"{pending_revision[7:]}.json"],
        git_revision="a" * 40,
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

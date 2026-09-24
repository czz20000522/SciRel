import json
import hashlib
from pathlib import Path
import sys

import pytest

from scirel_workflow import (
    CandidatePackage,
    ReviewDecision,
    ReviewOutcome,
    SciRelWorkflow,
    WorkflowStatus,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_catalog import build_catalog  # noqa: E402
from finalize_release import finalize_release  # noqa: E402


def _approved_snapshot(tmp_path: Path, *, alter_asset: bool = False) -> Path:
    document = json.loads(
        (
            ROOT / "catalog/examples/scirel.field.circular-filament-green.json"
        ).read_text(encoding="utf-8")
    )
    if alter_asset:
        document["summary"] = "Unreviewed replacement text."
    candidate = CandidatePackage.from_l1(
        {
            "assets": [{"candidate_asset_id": "candidate-field"}],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/pleiades",
        source_digest="sha256:l1",
        run_id="run-release-gate",
    )
    workflow = SciRelWorkflow(candidate)
    workflow.create_draft(draft_id="draft-release-gate", assets=[document])
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision(
            "draft-release-gate", ReviewOutcome.APPROVED, "expert-release-gate"
        )
    )
    snapshot = tmp_path / "approved-workflow.json"
    snapshot.write_text(json.dumps(workflow.to_dict()), encoding="utf-8")
    return snapshot


def _release_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    documents = tmp_path / "documents"
    documents.mkdir()
    source = ROOT / "catalog/examples/scirel.field.circular-filament-green.json"
    (documents / source.name).write_bytes(source.read_bytes())
    catalog = tmp_path / "catalog"
    build_catalog(
        documents,
        catalog,
        catalog_id="scirel-release-test",
        release_version="0.1.0.dev6",
        coverage_status="complete",
        declared_total=1,
    )
    wheel = tmp_path / "scirel-0.1.0.dev6-py3-none-any.whl"
    wheel.write_bytes(b"wheel fixture")
    return documents, catalog, wheel


def test_finalization_binds_approved_snapshot_to_exact_artifacts(tmp_path):
    snapshot = _approved_snapshot(tmp_path)
    documents, catalog, wheel = _release_inputs(tmp_path)
    output = tmp_path / "release"

    result = finalize_release(
        workflow_snapshot=snapshot,
        documents_dir=documents,
        catalog_dir=catalog,
        wheel=wheel,
        output_dir=output,
        release_id="release-test",
        expected_coverage_status="complete",
        expected_included_asset_count=1,
        expected_declared_total_asset_count=1,
    )

    manifest = json.loads((output / "release-manifest.json").read_text(encoding="utf-8"))
    released = SciRelWorkflow.from_dict(
        json.loads((output / "workflow-state.json").read_text(encoding="utf-8"))
    )
    catalog_release = json.loads((catalog / "release.json").read_text(encoding="utf-8"))
    assert released.status is WorkflowStatus.RELEASED
    assert manifest["approved_assets"] == [
        "scirel.field.circular-filament-green"
    ]
    assert manifest["catalog_digest"] == catalog_release["root_digest"]
    assert manifest["wheel_digest"] == result["wheel_digest"]
    assert manifest["catalog_ref"] == "catalog/release.json"
    assert manifest["wheel_ref"] == f"{wheel.name}"
    assert manifest["candidate_digest"] == released.record.candidate.package_digest
    assert manifest["draft_digest"] == released.record.draft.draft_digest


def test_finalization_rejects_a_snapshot_without_expert_approval(tmp_path):
    snapshot = _approved_snapshot(tmp_path)
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    payload["review"] = None
    payload["reviews"] = []
    payload["draft"]["status"] = "review_pending"
    payload["drafts"][0]["status"] = "review_pending"
    payload["status"] = "review_pending"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")
    documents, catalog, wheel = _release_inputs(tmp_path)

    with pytest.raises(ValueError, match="requires an approved"):
        finalize_release(
            workflow_snapshot=snapshot,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=wheel,
            output_dir=tmp_path / "release",
            release_id="release-test",
            expected_coverage_status="complete",
            expected_included_asset_count=1,
            expected_declared_total_asset_count=1,
        )


def test_finalization_rejects_draft_content_not_in_the_baseline(tmp_path):
    snapshot = _approved_snapshot(tmp_path, alter_asset=True)
    documents, catalog, wheel = _release_inputs(tmp_path)

    with pytest.raises(ValueError, match="differs from the release document"):
        finalize_release(
            workflow_snapshot=snapshot,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=wheel,
            output_dir=tmp_path / "release",
            release_id="release-test",
            expected_coverage_status="complete",
            expected_included_asset_count=1,
            expected_declared_total_asset_count=1,
        )


def test_finalization_rejects_a_catalog_record_that_differs_from_the_document(tmp_path):
    snapshot = _approved_snapshot(tmp_path)
    documents, catalog, wheel = _release_inputs(tmp_path)
    release_path = catalog / "release.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    record_path = next((catalog / "records").rglob("*.json"))
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["summary"] = "Catalog-only replacement text."
    payload = (
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    record_path.write_bytes(payload)
    relative = record_path.relative_to(catalog).as_posix()
    partition = next(item for item in release["partitions"] if item["path"] == relative)
    partition["bytes"] = len(payload)
    partition["sha256"] = "sha256:" + hashlib.sha256(payload).hexdigest()
    unsigned = dict(release)
    unsigned.pop("root_digest")
    canonical = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    release["root_digest"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
    release_path.write_text(json.dumps(release), encoding="utf-8")

    with pytest.raises(ValueError, match="record differs from the release document"):
        finalize_release(
            workflow_snapshot=snapshot,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=wheel,
            output_dir=tmp_path / "release",
            release_id="release-test",
            expected_coverage_status="complete",
            expected_included_asset_count=1,
            expected_declared_total_asset_count=1,
        )


def test_finalization_never_overwrites_existing_metadata(tmp_path):
    snapshot = _approved_snapshot(tmp_path)
    documents, catalog, wheel = _release_inputs(tmp_path)
    output = tmp_path / "release"
    output.mkdir()

    with pytest.raises(FileExistsError, match="already exists"):
        finalize_release(
            workflow_snapshot=snapshot,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=wheel,
            output_dir=output,
            release_id="release-test",
            expected_coverage_status="complete",
            expected_included_asset_count=1,
            expected_declared_total_asset_count=1,
        )


@pytest.mark.parametrize(
    ("status", "included", "declared", "message"),
    [
        ("partial", 1, 1, "coverage status differs"),
        ("complete", 2, 1, "included asset count differs"),
        ("complete", 1, 62, "declared asset count differs"),
    ],
)
def test_finalization_rejects_catalog_coverage_outside_release_policy(
    tmp_path, status, included, declared, message
):
    snapshot = _approved_snapshot(tmp_path)
    documents, catalog, wheel = _release_inputs(tmp_path)

    with pytest.raises(ValueError, match=message):
        finalize_release(
            workflow_snapshot=snapshot,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=wheel,
            output_dir=tmp_path / "release",
            release_id="release-test",
            expected_coverage_status=status,
            expected_included_asset_count=included,
            expected_declared_total_asset_count=declared,
        )


def test_finalization_rejects_catalog_outside_release_root(tmp_path):
    snapshot = _approved_snapshot(tmp_path)
    documents, catalog, wheel = _release_inputs(tmp_path)
    release_root = tmp_path / "release-root"
    release_root.mkdir()
    inside_wheel = release_root / wheel.name
    inside_wheel.write_bytes(wheel.read_bytes())

    with pytest.raises(ValueError, match="catalog release must be inside"):
        finalize_release(
            workflow_snapshot=snapshot,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=inside_wheel,
            output_dir=release_root / "release",
            release_id="release-test",
            expected_coverage_status="complete",
            expected_included_asset_count=1,
            expected_declared_total_asset_count=1,
        )


def test_finalization_rejects_wheel_outside_release_root(tmp_path):
    release_root = tmp_path / "release-root"
    release_root.mkdir()
    snapshot = _approved_snapshot(tmp_path)
    documents, catalog, _ = _release_inputs(release_root)
    outside_wheel = tmp_path / "outside.whl"
    outside_wheel.write_bytes(b"wheel fixture")

    with pytest.raises(ValueError, match="wheel must be inside"):
        finalize_release(
            workflow_snapshot=snapshot,
            documents_dir=documents,
            catalog_dir=catalog,
            wheel=outside_wheel,
            output_dir=release_root / "release",
            release_id="release-test",
            expected_coverage_status="complete",
            expected_included_asset_count=1,
            expected_declared_total_asset_count=1,
        )

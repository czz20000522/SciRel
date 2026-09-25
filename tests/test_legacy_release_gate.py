"""A per-item review cannot authorize a whole development version."""

import json
from pathlib import Path
import sys

import pytest

from scirel_plugin import FakeHost, SciRelPlugin
from scirel_workflow import (
    CandidatePackage,
    ReleaseManifest,
    ReviewDecision,
    ReviewOutcome,
    SciRelWorkflow,
    WorkflowError,
    WorkflowStatus,
)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from finalize_release import finalize_release  # noqa: E402


def _approved_workflow() -> SciRelWorkflow:
    document = json.loads(
        (ROOT / "catalog/examples/scirel.field.circular-filament-green.json").read_text(
            encoding="utf-8"
        )
    )
    candidate = CandidatePackage.from_l1(
        {
            "assets": [{"candidate_asset_id": "candidate-field"}],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/sample",
        source_digest="sha256:sample",
        run_id="run-legacy-gate",
    )
    workflow = SciRelWorkflow(candidate)
    workflow.create_draft(draft_id="draft-legacy-gate", assets=[document])
    workflow.submit_for_review()
    workflow.start_review()
    workflow.record_review(
        ReviewDecision("draft-legacy-gate", ReviewOutcome.APPROVED, "reviewer")
    )
    return workflow


def _release_args(workflow: SciRelWorkflow) -> dict:
    assert workflow.record.draft is not None
    return {
        "release_id": "release-legacy-gate",
        "catalog_ref": "artifact://catalog/sample",
        "catalog_digest": "sha256:" + "c" * 64,
        "wheel_ref": "artifact://wheel/sample",
        "wheel_digest": "sha256:" + "d" * 64,
        "release_version": workflow.record.draft.assets[0]["version"]["implementation_version"],
    }


def test_approved_item_cannot_release_or_change_workflow_state():
    workflow = _approved_workflow()
    with pytest.raises(WorkflowError, match="trusted version"):
        workflow.release(**_release_args(workflow))
    assert workflow.status is WorkflowStatus.APPROVED
    assert workflow.record.release is None


def test_plugin_does_not_advertise_or_publish_legacy_release():
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    workflow = _approved_workflow()
    assert "scirel.release" not in plugin.descriptor()["operations"]
    assert "release" not in plugin.review_ui_projection(workflow)["available_actions"]

    release = ReleaseManifest(
        draft_id=workflow.record.draft.draft_id,
        approved_assets=(workflow.record.draft.assets[0]["asset_id"],),
        candidate_id=workflow.record.candidate.candidate_id,
        candidate_digest=workflow.record.candidate.package_digest,
        draft_digest=workflow.record.draft.draft_digest,
        **_release_args(workflow),
    )
    with pytest.raises(ValueError, match="trusted version"):
        plugin.release(release)
    artifact = host.put_artifact("scirel.release-manifest.dev", release.to_dict())
    with pytest.raises(ValueError, match="trusted version"):
        plugin.publish_release_completed_event(
            release,
            artifact,
            workflow_run_id="run-legacy-gate",
            correlation_id="build://legacy-gate",
        )
    with pytest.raises(ValueError, match="trusted version"):
        plugin.complete_release(
            workflow,
            correlation_id="build://legacy-gate",
            **_release_args(workflow),
        )
    assert not host.events


def test_direct_finalizer_rejects_approved_item_before_writing(tmp_path):
    workflow = _approved_workflow()
    snapshot = tmp_path / "approved.json"
    snapshot.write_text(json.dumps(workflow.to_dict()), encoding="utf-8")
    output = tmp_path / "release"
    with pytest.raises(ValueError, match="trusted version"):
        finalize_release(
            workflow_snapshot=snapshot,
            documents_dir=tmp_path / "documents",
            catalog_dir=tmp_path / "catalog",
            wheel=tmp_path / "wheel.whl",
            output_dir=output,
            release_id="release-legacy-gate",
            expected_coverage_status="complete",
            expected_included_asset_count=1,
            expected_declared_total_asset_count=1,
        )
    assert not output.exists()

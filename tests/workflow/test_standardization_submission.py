"""The model submission gate produces an exact reviewer-visible snapshot."""

import hashlib
import json
from pathlib import Path
import subprocess

from scirel_plugin import FakeHost, SciRelPlugin
from scirel_workflow import CandidatePackage, StandardizationSubmission
from scirel_workflow.models import digest
from scripts.submit_standardization import build_review_workflow


ROOT = Path(__file__).parents[2]
ASSET_DOCUMENT = json.loads(
    (ROOT / "catalog/examples/scirel.field.circular-filament-green.json").read_text(
        encoding="utf-8"
    )
)
SKILL = ROOT / "skills/integration/scirel-integration/SKILL.md"


def _material(value: dict) -> dict:
    result = dict(value)
    result["digest"] = digest(result)
    return result


def _submission_payload(candidate: CandidatePackage, git_base: str) -> dict:
    return {
        "schema": "scirel.standardization-submission.dev",
        "submission_id": "submission-review-visible",
        "draft_id": "draft-review-visible",
        "candidate_id": candidate.candidate_id,
        "candidate_digest": candidate.package_digest,
        "source_digest": candidate.source_digest,
        "scirel_git_base": git_base,
        "candidate_pool_ref": "artifact://candidate-pool/empty",
        "candidate_pool_digest": digest([]),
        "producer": {
            "harness": {"name": "codefusion", "version": "development"},
            "model": {"name": "configured-model", "version": "development"},
            "skill": {
                "name": "scirel-integration",
                "version": "development",
                "digest": "sha256:" + hashlib.sha256(SKILL.read_bytes()).hexdigest(),
            },
        },
        "review_units": [
            {
                "review_unit_id": "unit-circular-filament-green",
                "source_asset_ids": ["pleiades:operator:circular-filament-green"],
                "disposition": "reuse",
                "asset_document": ASSET_DOCUMENT,
                "candidate_document": _material(
                    {"content": "# Reuse proposal\n\nThe incoming relation matches the maintained asset."}
                ),
                "candidate_code": _material(
                    {
                        "kind": "none",
                        "content": None,
                        "rationale": "Reuse requires no runtime patch.",
                    }
                ),
                "candidate_tests": _material(
                    {
                        "content": {
                            "files": {
                                "tests/test_reuse.py": "def test_reuse(): pass\n"
                            }
                        },
                        "commands": [{"command": "pytest tests/test_reuse.py"}],
                        "results": [
                            {"command": "pytest tests/test_reuse.py", "exit_code": 0}
                        ],
                    }
                ),
                "dependency_asset_ids": [
                    dependency["asset_id"]
                    for dependency in ASSET_DOCUMENT["version"]["dependencies"]
                ],
                "evidence": [{"kind": "mapped_comparison", "ref": "run://comparison"}],
                "gaps": [],
            }
        ],
        "run_evidence": [{"kind": "harness_run", "ref": "run://standardization"}],
        "gaps": [],
    }


def test_official_gate_preserves_three_piece_in_review_detail():
    candidate = CandidatePackage.from_l1(
        {
            "assets": [
                {
                    "candidate_asset_id": "pleiades:operator:circular-filament-green"
                }
            ],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/pleiades",
        source_digest="sha256:" + "1" * 64,
        run_id="run-review-visible",
    )
    git_base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    payload = _submission_payload(candidate, git_base)

    snapshot = build_review_workflow(
        candidate.to_dict(),
        payload,
        [],
        scirel_git_base=git_base,
        skill_digest=payload["producer"]["skill"]["digest"],
    )
    host = FakeHost()
    plugin = SciRelPlugin.for_development(host)
    artifact = host.put_artifact("scirel.workflow-state.dev", snapshot)
    listed = plugin.list_review_items((artifact,))
    item = listed["items"][0]
    opened = plugin.open_review_item(
        artifact,
        item_ref=item["item_ref"],
        revision=item["revision"],
    )
    detail = plugin.validate_review_item_detail(
        opened,
        item_ref=item["item_ref"],
        revision=item["revision"],
    )

    materials = next(
        evidence
        for evidence in detail["evidence"]
        if evidence["kind"] == "standardization_review_unit"
    )
    assert snapshot["status"] == "review_pending"
    assert materials["candidate_document"]["content"].startswith("# Reuse proposal")
    assert materials["candidate_code"]["kind"] == "none"
    assert materials["candidate_tests"]["results"][0]["exit_code"] == 0


def test_standardization_submission_has_no_automated_check_override():
    candidate = CandidatePackage.from_l1(
        {
            "assets": [
                {
                    "candidate_asset_id": "pleiades:operator:circular-filament-green"
                }
            ],
            "automated_checks": [{"name": "replay", "status": "passed"}],
        },
        source_artifact_ref="artifact://l1/pleiades",
        source_digest="sha256:" + "1" * 64,
        run_id="run-no-check-override",
    )
    payload = _submission_payload(candidate, "a" * 40)
    payload["automated_checks"] = [{"name": "forged", "status": "passed"}]

    try:
        StandardizationSubmission.from_mapping(payload)
    except ValueError as error:
        assert "unknown fields: automated_checks" in str(error)
    else:
        raise AssertionError("submission accepted a forged automated-check field")

"""Capture the exact locally available unpublished review units for this comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _digest(value: object) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("workflow", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--additional-workflow", action="append", type=Path, default=[])
    args = parser.parse_args()
    submission_bytes = args.submission.read_bytes()
    workflow_bytes = args.workflow.read_bytes()
    submission = json.loads(submission_bytes)
    workflow = json.loads(workflow_bytes)
    if workflow["status"] != "review_pending" or workflow["draft"]["status"] != "review_pending":
        raise ValueError("the local workflow is not a pending review snapshot")
    if workflow["candidate"]["candidate_id"] != submission["candidate_id"]:
        raise ValueError("submission and workflow refer to different candidates")
    units = [
        {
            "review_unit_id": unit["review_unit_id"],
            "asset_id": unit["asset_document"]["asset_id"],
            "source_asset_ids": unit["source_asset_ids"],
            "status": "review_pending",
            "disposition": unit["disposition"],
            "document_digest": unit["candidate_document"]["digest"],
            "code_digest": unit["candidate_code"]["digest"],
            "tests_digest": unit["candidate_tests"]["digest"],
        }
        for unit in submission["review_units"]
    ]
    review_materials = {
        row["review_unit_id"]: row
        for row in workflow["draft"]["evidence"]
        if row["kind"] == "standardization_review_unit"
    }
    if len(review_materials) != len(units):
        raise ValueError("workflow evidence does not cover every review unit")
    for unit in units:
        material = review_materials[unit["review_unit_id"]]
        if (
            material["asset_id"] != unit["asset_id"]
            or material["candidate_document"]["digest"] != unit["document_digest"]
            or material["candidate_code"]["digest"] != unit["code_digest"]
            or material["candidate_tests"]["digest"] != unit["tests_digest"]
        ):
            raise ValueError("workflow review material differs from the submission")
    if {row["asset_id"] for row in units} != {
        asset["asset_id"] for asset in workflow["draft"]["assets"]
    }:
        raise ValueError("submission units do not match workflow draft assets")
    additional_snapshots = []
    for path in args.additional_workflow:
        body = path.read_bytes()
        other = json.loads(body)
        if other["status"] != "review_pending" or other["draft"]["status"] != "review_pending":
            raise ValueError(f"additional workflow is not review_pending: {path}")
        additional_snapshots.append(
            {
                "local_path": path.as_posix(),
                "revision_sha256": "sha256:" + hashlib.sha256(body).hexdigest(),
                "workflow_status": other["status"],
                "draft_id": other["draft"]["draft_id"],
                "draft_status": other["draft"]["status"],
                "candidate_id": other["candidate"]["candidate_id"],
                "source_digest": other["candidate"]["source_digest"],
                "units": [
                    {
                        "asset_id": asset["asset_id"],
                        "status": other["draft"]["status"],
                        "asset_document_digest": _digest(asset),
                        "trio_status": "not recorded as separate exact materials in this workflow",
                    }
                    for asset in other["draft"]["assets"]
                ],
            }
        )
    snapshot = {
        "scope": "local SciRel build/standardization and build/verification snapshots; host queue was not queried",
        "submission_id": submission["submission_id"],
        "submission_sha256": "sha256:" + hashlib.sha256(submission_bytes).hexdigest(),
        "workflow_sha256": "sha256:" + hashlib.sha256(workflow_bytes).hexdigest(),
        "workflow_status": workflow["status"],
        "draft_id": workflow["draft"]["draft_id"],
        "draft_status": workflow["draft"]["status"],
        "candidate_id": submission["candidate_id"],
        "candidate_digest": submission["candidate_digest"],
        "source_digest": submission["source_digest"],
        "scirel_git_base": submission["scirel_git_base"],
        "units": sorted(units, key=lambda row: row["review_unit_id"]),
        "additional_snapshots": sorted(
            additional_snapshots, key=lambda row: row["local_path"]
        ),
    }
    snapshot["snapshot_digest"] = _digest(snapshot)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "exact_trio_units": len(units),
        "additional_local_units": sum(len(row["units"]) for row in additional_snapshots),
        "snapshot_digest": snapshot["snapshot_digest"],
    }))


if __name__ == "__main__":
    main()

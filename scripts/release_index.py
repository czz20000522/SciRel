"""Register immutable unpublished candidates and their lifecycle in one index."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scirel_plugin.adapter import review_items_from_body  # noqa: E402


SCHEMA = "scirel.release-index.dev"
_GIT_REVISION = re.compile(r"^[0-9a-f]{40}$")
_SHA256_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def artifact_ref(path: Path) -> dict[str, str]:
    resolved = path.resolve(strict=True)
    if not resolved.is_file() or not resolved.is_relative_to(ROOT):
        raise ValueError(f"index artifact must be a file within SciRel: {path}")
    return {
        "ref": resolved.relative_to(ROOT).as_posix(),
        "digest": digest(resolved.read_bytes()),
    }


def read_index(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {"schema", "entries"}:
        raise ValueError("release index fields are invalid")
    if value["schema"] != SCHEMA or not isinstance(value["entries"], list):
        raise ValueError("release index schema or entries are invalid")
    ids = set()
    candidates = set()
    developments = set()
    unpublished = {}
    retired = set()
    released_candidates = set()
    latest_release = None
    for entry in value["entries"]:
        if not isinstance(entry, dict) or entry.get("status") not in {
            "candidate", "development", "evidence", "lifecycle", "released"
        }:
            raise ValueError("release index contains an invalid entry")
        unsigned = {key: part for key, part in entry.items() if key != "entry_digest"}
        if entry.get("entry_digest") != digest(canonical_json(unsigned)):
            raise ValueError("release index entry digest differs from its contents")
        if entry.get("entry_id") in ids:
            raise ValueError("release index repeats an entry ID")
        ids.add(entry["entry_id"])
        if entry["status"] == "candidate":
            if not isinstance(entry.get("items"), list) or not entry["items"]:
                raise ValueError("candidate index entry has no review items")
            candidates.add(entry["entry_id"])
            unpublished[entry["entry_id"]] = entry
        elif entry["status"] == "development":
            if (
                entry.get("approval_state") != "pending_unapproved"
                or not isinstance(entry.get("catalog"), dict)
                or not isinstance(entry.get("wheel"), dict)
            ):
                raise ValueError("development entry lacks an unapproved artifact binding")
            developments.add(entry["entry_id"])
            unpublished[entry["entry_id"]] = entry
        elif entry["status"] == "evidence":
            binding = entry.get("evidence_ref")
            evidence_type = entry.get("evidence_type")
            subject = entry.get("subject_entry_id")
            if (
                not (
                    (evidence_type in {
                        "review_host_export_acceptance",
                        "review_host_registration_acceptance",
                    } and subject in candidates)
                    or (evidence_type in {
                        "development_consumer_acceptance",
                        "development_consumer_recovery_acceptance",
                    } and subject in developments)
                )
                or entry.get("approval_state") != "pending_unapproved"
                or not isinstance(binding, dict)
                or not isinstance(binding.get("ref"), str)
                or not binding["ref"]
                or not isinstance(binding.get("digest"), str)
                or not _SHA256_DIGEST.fullmatch(binding["digest"])
            ):
                subject_kind = (
                    "candidate" if evidence_type in {
                        "review_host_export_acceptance",
                        "review_host_registration_acceptance",
                    }
                    else "development snapshot"
                )
                raise ValueError(f"evidence entry lacks an earlier {subject_kind} or exact binding")
        elif entry["status"] == "lifecycle":
            subject = entry.get("subject_entry_id")
            successor = entry.get("successor_entry_id")
            transition = entry.get("transition")
            binding = entry.get("evidence_ref")
            if (
                not isinstance(entry.get("entry_id"), str)
                or not re.fullmatch(r"lifecycle:[0-9a-f]{64}", entry["entry_id"])
                or subject not in unpublished or subject in retired
                or subject in released_candidates
                or transition not in {"superseded", "withdrawn"}
                or not isinstance(binding, dict)
                or not isinstance(binding.get("ref"), str) or not binding["ref"]
                or not isinstance(binding.get("digest"), str)
                or not _SHA256_DIGEST.fullmatch(binding["digest"])
            ):
                raise ValueError("lifecycle entry lacks a current unpublished subject or exact evidence")
            if transition == "superseded":
                if (
                    successor not in unpublished or successor == subject
                    or successor in retired or successor in released_candidates
                    or unpublished[successor]["status"] != unpublished[subject]["status"]
                ):
                    raise ValueError("lifecycle successor must be a current entry of the same kind")
            elif "successor_entry_id" in entry:
                raise ValueError("withdrawn lifecycle entry cannot name a successor")
            retired.add(subject)
        else:
            if (
                entry.get("predecessor_entry_id") not in candidates
                or entry.get("predecessor_entry_id") in retired
                or entry.get("baseline_entry_id") != latest_release
            ):
                raise ValueError("released index entry has an invalid predecessor")
            latest_release = entry["entry_id"]
            released_candidates.add(entry["predecessor_entry_id"])
    return value


def current_unpublished_entries(index: dict[str, Any]) -> list[dict[str, Any]]:
    retired = {
        entry["subject_entry_id"] for entry in index["entries"]
        if entry["status"] == "lifecycle"
    }
    retired.update(
        entry["predecessor_entry_id"] for entry in index["entries"]
        if entry["status"] == "released"
    )
    return [
        entry for entry in index["entries"]
        if entry["status"] in {"candidate", "development"}
        and entry["entry_id"] not in retired
    ]


def append_entry(index: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    unsigned = dict(entry)
    unsigned["entry_digest"] = digest(canonical_json(entry))
    result = {"schema": SCHEMA, "entries": [*index["entries"], unsigned]}
    if any(old["entry_id"] == entry["entry_id"] for old in index["entries"]):
        raise ValueError("release index entry ID already exists")
    return result


def register_lifecycle(
    *,
    transition: str,
    subject_entry_id: str,
    evidence_path: Path,
    existing_index: Path,
    output_path: Path,
    successor_entry_id: str | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"release index output already exists: {output_path}")
    index = read_index(existing_index)
    current = {entry["entry_id"]: entry for entry in current_unpublished_entries(index)}
    subject = current.get(subject_entry_id)
    if subject is None or transition not in {"superseded", "withdrawn"}:
        raise ValueError("lifecycle requires a current unpublished subject")
    if transition == "superseded":
        successor = current.get(successor_entry_id)
        if successor is None or successor_entry_id == subject_entry_id or successor["status"] != subject["status"]:
            raise ValueError("lifecycle successor must be a current entry of the same kind")
    elif successor_entry_id is not None:
        raise ValueError("withdrawn lifecycle entry cannot name a successor")
    binding = artifact_ref(evidence_path)
    entry = {
        "status": "lifecycle",
        "subject_entry_id": subject_entry_id,
        "transition": transition,
        "evidence_ref": binding,
    }
    if successor_entry_id is not None:
        entry["successor_entry_id"] = successor_entry_id
    entry["entry_id"] = "lifecycle:" + digest(canonical_json(entry))[7:]
    result = append_entry(index, entry)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return result


def register_candidate(
    *,
    item_artifacts: list[Path],
    git_revision: str,
    output_path: Path,
    existing_index: Path | None = None,
    evidence_paths: list[Path] | None = None,
    source_qualification: str | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"release index output already exists: {output_path}")
    if not _GIT_REVISION.fullmatch(git_revision):
        raise ValueError("candidate Git revision must be an exact 40-character SHA")
    if not item_artifacts:
        raise ValueError("candidate requires review item artifacts")
    if source_qualification not in (None, "bounded_d1", "mixed_unverified"):
        raise ValueError("candidate source qualification is invalid")
    index = (
        read_index(existing_index)
        if existing_index is not None
        else {"schema": SCHEMA, "entries": []}
    )
    items = []
    candidate_ids = set()
    draft_ids = set()
    asset_ids = set()
    item_refs = set()
    for path in item_artifacts:
        body = path.read_bytes()
        revision = digest(body)
        artifact_items = review_items_from_body(body)
        if not artifact_items:
            raise ValueError("candidate artifact has no pending review items")
        for item in artifact_items:
            if item["status"] != "review_pending":
                raise ValueError("candidate item must be pending")
            asset = item["asset"]
            asset_id = asset.get("asset_id")
            if not isinstance(asset_id, str) or not asset_id:
                raise ValueError("candidate asset requires a stable asset_id")
            if asset_id in asset_ids or item["item_ref"] in item_refs:
                raise ValueError("candidate repeats an asset or review item")
            asset_ids.add(asset_id)
            item_refs.add(item["item_ref"])
            candidate_ids.add(item["candidate_id"])
            draft_ids.add(item["draft_id"])
            items.append(
                {
                    "item_ref": item["item_ref"],
                    "initial_revision": revision,
                    "asset_id": asset_id,
                    "document_digest": digest(canonical_json(asset)),
                    "dependency_asset_ids": item["dependency_asset_ids"],
                }
            )
    if len(candidate_ids) != 1 or len(draft_ids) != 1:
        raise ValueError("candidate items must belong to one candidate and draft")
    items.sort(key=lambda item: item["item_ref"])
    entry = {
        "entry_id": "candidate:" + digest(canonical_json([git_revision, items]))[7:],
        "status": "candidate",
        "candidate_id": candidate_ids.pop(),
        "draft_id": draft_ids.pop(),
        "git_revision": git_revision,
        "items": items,
    }
    if evidence_paths:
        entry["approval_state"] = "pending_unapproved"
        entry["evidence_refs"] = [artifact_ref(path) for path in evidence_paths]
        entry["destination"] = "review_host"
        entry["destination_refs"] = []
    if source_qualification is not None:
        entry["source_qualification"] = source_qualification
    result = append_entry(index, entry)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return result


def register_development_snapshot(
    *,
    snapshot_id: str,
    catalog_release: Path,
    wheel: Path,
    evidence_paths: list[Path],
    destination_paths: list[Path],
    output_path: Path,
    existing_index: Path | None = None,
    git_revision: str | None = None,
    source_manifest_digest: str | None = None,
    source_qualification: str,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"release index output already exists: {output_path}")
    if not snapshot_id or not evidence_paths or not destination_paths:
        raise ValueError("development snapshot needs identity, evidence and destination")
    if source_qualification not in ("bounded_d1", "mixed_unverified"):
        raise ValueError("development snapshot source qualification is invalid")
    if (git_revision is None) == (source_manifest_digest is None):
        raise ValueError("development snapshot needs exactly one source binding")
    if git_revision is not None and not _GIT_REVISION.fullmatch(git_revision):
        raise ValueError("development snapshot Git revision is invalid")
    if source_manifest_digest is not None and not re.fullmatch(
        r"sha256:[0-9a-f]{64}", source_manifest_digest
    ):
        raise ValueError("development snapshot source manifest digest is invalid")
    catalog = artifact_ref(catalog_release)
    catalog_body = json.loads(catalog_release.read_text(encoding="utf-8"))
    if catalog_body.get("schema") != "scirel.catalog-release.v1":
        raise ValueError("development snapshot catalog schema is invalid")
    unsigned_catalog = {
        key: value for key, value in catalog_body.items() if key != "root_digest"
    }
    if catalog_body.get("root_digest") != digest(canonical_json(unsigned_catalog)):
        raise ValueError("development snapshot catalog root digest differs")
    catalog["root_digest"] = catalog_body["root_digest"]
    index = read_index(existing_index) if existing_index else {"schema": SCHEMA, "entries": []}
    wheel_ref = artifact_ref(wheel)
    entry = {
        "entry_id": "development:" + digest(canonical_json([snapshot_id, catalog, wheel_ref]))[7:],
        "status": "development",
        "snapshot_id": snapshot_id,
        "approval_state": "pending_unapproved",
        "source_qualification": source_qualification,
        "source_binding": (
            {"git_revision": git_revision}
            if git_revision else {"manifest_digest": source_manifest_digest}
        ),
        "catalog": catalog,
        "wheel": wheel_ref,
        "evidence_refs": [artifact_ref(path) for path in evidence_paths],
        "destination_refs": [artifact_ref(path) for path in destination_paths],
    }
    result = append_entry(index, entry)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return result


def register_review_host_evidence(
    *,
    candidate_entry_id: str,
    evidence_path: Path,
    existing_index: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"release index output already exists: {output_path}")
    index = read_index(existing_index)
    candidates = [
        entry for entry in index["entries"]
        if entry["status"] == "candidate" and entry["entry_id"] == candidate_entry_id
    ]
    if len(candidates) != 1:
        raise ValueError("review host evidence needs an indexed candidate")
    candidate = candidates[0]
    binding = artifact_ref(evidence_path)
    record = json.loads(evidence_path.read_text(encoding="utf-8"))
    revisions = {item["initial_revision"] for item in candidate["items"]}
    if isinstance(record, dict) and record.get("schema") == "scirel.review-host-registration-acceptance.dev":
        developments = {
            entry["entry_id"]: entry for entry in index["entries"]
            if entry["status"] == "development"
        }
        development = developments.get(record.get("development_entry_id"))
        artifacts = record.get("host_artifacts")
        by_role = (
            {artifact.get("role"): artifact for artifact in artifacts}
            if isinstance(artifacts, list) and all(
                isinstance(artifact, dict) and isinstance(artifact.get("role"), str)
                for artifact in artifacts
            )
            else {}
        )
        wheel = by_role.get("wheel", {})
        catalog = by_role.get("catalog_snapshot_zip", {})
        dependencies = record.get("runtime_dependency_refs")
        if (
            record.get("candidate_entry_id") != candidate_entry_id
            or development is None
            or revisions != {record.get("workflow_revision")}
            or record.get("scirel_source_revision") != candidate["git_revision"]
            or development["source_binding"] != {"git_revision": candidate["git_revision"]}
            or record.get("catalog_root_digest") != development["catalog"]["root_digest"]
            or not isinstance(record.get("registration_digest"), str)
            or not _SHA256_DIGEST.fullmatch(record["registration_digest"])
            or not isinstance(record.get("owner_evidence_digest"), str)
            or not _SHA256_DIGEST.fullmatch(record["owner_evidence_digest"])
            or not isinstance(record.get("host_plugin_release_ref"), str)
            or not record["host_plugin_release_ref"]
            or not isinstance(artifacts, list) or len(artifacts) != 2
            or set(by_role) != {"wheel", "catalog_snapshot_zip"}
            or wheel.get("digest") != development["wheel"]["digest"]
            or wheel.get("media_type") != "application/octet-stream"
            or not isinstance(catalog.get("digest"), str)
            or not _SHA256_DIGEST.fullmatch(catalog["digest"])
            or catalog.get("media_type") != "application/vnd.scirel.catalog-snapshot+zip"
            or any(not isinstance(artifact.get("artifact_ref"), str)
                   or not artifact["artifact_ref"] for artifact in artifacts)
            or not isinstance(dependencies, list)
            or any(not isinstance(value, str) or not value for value in dependencies)
            or len(set(dependencies)) != len(dependencies)
            or record.get("approval_state") != "pending_unapproved"
            or type(record.get("approved_items")) is not int
            or record["approved_items"] != 0
        ):
            raise ValueError("review host registration evidence does not bind the pending candidate")
        evidence_type = "review_host_registration_acceptance"
    else:
        evidence_type = "review_host_export_acceptance"
        _validate_review_host_export(record, candidate, candidate_entry_id, revisions)
    entry = {
        "entry_id": "evidence:" + digest(canonical_json([candidate_entry_id, binding]))[7:],
        "status": "evidence",
        "subject_entry_id": candidate_entry_id,
        "evidence_type": evidence_type,
        "approval_state": "pending_unapproved",
        "evidence_ref": binding,
    }
    result = append_entry(index, entry)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return result


def _validate_review_host_export(
    record: Any, candidate: dict[str, Any], candidate_entry_id: str, revisions: set[str],
) -> None:
    action = record.get("review_action") if isinstance(record, dict) else None
    transition_count = record.get("applied_transitions") if isinstance(record, dict) else None
    action_valid = (
        type(transition_count) is int and transition_count == 0 and action is None
    ) or (
        type(transition_count) is int and transition_count == 1
        and isinstance(action, dict)
        and action.get("action") == "request-evidence"
        and action.get("item_ref") in {item["item_ref"] for item in candidate["items"]}
        and isinstance(action.get("run_id"), str)
        and bool(action["run_id"])
        and isinstance(action.get("successor_digest"), str)
        and bool(_SHA256_DIGEST.fullmatch(action["successor_digest"]))
    )
    if not isinstance(record, dict) or (
        record.get("schema") != "scirel.review-host-export-acceptance.dev"
        or record.get("candidate_entry_id") != candidate_entry_id
        or revisions != {record.get("workflow_revision")}
        or record.get("item_count") != len(candidate["items"])
        or type(record.get("review_pending_items")) is not int
        or record["review_pending_items"] < 0
        or type(record.get("needs_evidence_items")) is not int
        or record["needs_evidence_items"] < 0
        or type(record.get("approved_items")) is not int
        or record["approved_items"] != 0
        or record["review_pending_items"] + record["needs_evidence_items"] != len(candidate["items"])
        or not action_valid
        or record.get("approval_state") != "pending_unapproved"
        or not isinstance(record.get("host_source_revision"), str)
        or not _GIT_REVISION.fullmatch(record["host_source_revision"])
        or not isinstance(record.get("host_export_artifact_ref"), str)
        or not record["host_export_artifact_ref"]
        or not isinstance(record.get("host_export_artifact_digest"), str)
        or not _SHA256_DIGEST.fullmatch(record["host_export_artifact_digest"])
        or not isinstance(record.get("host_receipt_digest"), str)
        or not _SHA256_DIGEST.fullmatch(record["host_receipt_digest"])
    ):
        raise ValueError("review host evidence does not bind the pending candidate")


def register_development_consumer_evidence(
    *,
    development_entry_id: str,
    evidence_path: Path,
    existing_index: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"release index output already exists: {output_path}")
    index = read_index(existing_index)
    developments = [
        entry for entry in index["entries"]
        if entry["status"] == "development" and entry["entry_id"] == development_entry_id
    ]
    if len(developments) != 1:
        raise ValueError("consumer evidence needs an indexed development snapshot")
    development = developments[0]
    binding = artifact_ref(evidence_path)
    record = json.loads(evidence_path.read_text(encoding="utf-8"))
    if isinstance(record, dict) and record.get("schema") == "scirel.development-consumer-recovery-acceptance.dev":
        _validate_development_consumer_recovery(record, development, development_entry_id)
        evidence_type = "development_consumer_recovery_acceptance"
    else:
        _validate_development_consumer_same_request(record, development, development_entry_id)
        evidence_type = "development_consumer_acceptance"
    entry = {
        "entry_id": "evidence:" + digest(canonical_json([development_entry_id, binding]))[7:],
        "status": "evidence",
        "subject_entry_id": development_entry_id,
        "evidence_type": evidence_type,
        "approval_state": "pending_unapproved",
        "evidence_ref": binding,
    }
    result = append_entry(index, entry)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return result


def _validate_development_consumer_recovery(
    record: dict[str, Any], development: dict[str, Any], development_entry_id: str,
) -> None:
    runtime = record.get("runtime")
    host = record.get("codefusion_observation")
    saved = record.get("saved_evidence")
    review = record.get("review_boundary")
    requests = host.get("request_refs") if isinstance(host, dict) else None
    required_digests = (
        "owner_receipt_digest", "initial_failure_digest",
        "pre_correction_result_digest", "final_result_digest", "final_script_digest",
    )
    if (
        record.get("status") != "development_product_ordinary_recovery_acceptance"
        or record.get("development_entry_id") != development_entry_id
        or not isinstance(record.get("scirel_source_revision"), str)
        or not _GIT_REVISION.fullmatch(record["scirel_source_revision"])
        or record.get("scirel_source_revision") != development["source_binding"].get("git_revision")
        or record.get("source_qualification") != development["source_qualification"]
        or not isinstance(runtime, dict)
        or "sha256:" + str(runtime.get("wheel_sha256")) != development["wheel"]["digest"]
        or "sha256:" + str(runtime.get("catalog_release_sha256")) != development["catalog"]["digest"]
        or runtime.get("catalog_root_digest") != development["catalog"]["root_digest"]
        or any(not isinstance(runtime.get(key), str) or not _SHA256_DIGEST.fullmatch(runtime[key])
               for key in ("input_zip_digest", "qualified_l1_zip_digest"))
        or not isinstance(host, dict)
        or not isinstance(host.get("source_revision"), str)
        or not _GIT_REVISION.fullmatch(host["source_revision"])
        or any(not isinstance(host.get(key), str) or not host[key]
               for key in ("project_ref", "session_ref", "environment_version"))
        or not isinstance(host.get("skill_content_digest"), str)
        or not _SHA256_DIGEST.fullmatch(host["skill_content_digest"])
        or host.get("final_request_status") != "completed"
        or not isinstance(requests, list) or len(requests) < 2
        or any(not isinstance(ref, str) or not ref for ref in requests)
        or len(set(requests)) != len(requests)
        or not isinstance(saved, dict)
        or any(not isinstance(saved.get(key), str) or not _SHA256_DIGEST.fullmatch(saved[key])
               for key in required_digests)
        or saved["pre_correction_result_digest"] == saved["final_result_digest"]
        or not isinstance(review, dict)
        or type(review.get("approved_items")) is not int
        or review["approved_items"] != 0
        or record.get("approval_state") != "pending_unapproved"
    ):
        raise ValueError("consumer recovery evidence does not bind the development snapshot")


def _validate_development_consumer_same_request(
    record: Any, development: dict[str, Any], development_entry_id: str,
) -> None:
    runtime = record.get("runtime") if isinstance(record, dict) else None
    observation = record.get("codefusion_observation") if isinstance(record, dict) else None
    review = record.get("review_boundary") if isinstance(record, dict) else None
    if not isinstance(record, dict) or (
        record.get("schema") != "scirel.outbound-evaluation-manifest.v1"
        or record.get("status") != "development_product_ordinary_same_request_acceptance"
        or record.get("development_entry_id") != development_entry_id
        or not isinstance(runtime, dict)
        or "sha256:" + str(runtime.get("wheel_sha256")) != development["wheel"]["digest"]
        or "sha256:" + str(runtime.get("catalog_release_sha256")) != development["catalog"]["digest"]
        or runtime.get("catalog_root_digest") != development["catalog"]["root_digest"]
        or development["source_binding"] != {"git_revision": record.get("scirel_source_revision")}
        or not isinstance(observation, dict)
        or observation.get("request_status") != "completed"
        or not isinstance(observation.get("request_ref"), str)
        or not observation["request_ref"]
        or not isinstance(observation.get("owner_resolved_skill_revision_digest"), str)
        or not _SHA256_DIGEST.fullmatch(observation["owner_resolved_skill_revision_digest"])
        or not isinstance(observation.get("environment_version"), str)
        or not observation["environment_version"]
        or not isinstance(observation.get("shell_tool_plan_revision"), str)
        or not re.fullmatch(r"tool-plan@sha256:[0-9a-f]{64}", observation["shell_tool_plan_revision"])
        or type(observation.get("shell_calls_bound_to_plan")) is not int
        or observation["shell_calls_bound_to_plan"] < 1
        or observation.get("input_mount") != "read_only"
        or not isinstance(review, dict)
        or type(review.get("approved_items")) is not int
        or review["approved_items"] != 0
    ):
        raise ValueError("consumer evidence does not bind the development snapshot")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item-artifact", type=Path, action="append")
    parser.add_argument("--snapshot-id")
    parser.add_argument("--catalog-release", type=Path)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--git-revision")
    parser.add_argument("--source-manifest-digest")
    parser.add_argument("--source-qualification", choices=["bounded_d1", "mixed_unverified"])
    parser.add_argument("--evidence", type=Path, action="append", default=[])
    parser.add_argument("--destination", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--existing-index", type=Path)
    parser.add_argument("--review-host-evidence", type=Path)
    parser.add_argument("--candidate-entry-id")
    parser.add_argument("--development-consumer-evidence", type=Path)
    parser.add_argument("--development-entry-id")
    parser.add_argument("--lifecycle", choices=["superseded", "withdrawn"])
    parser.add_argument("--subject-entry-id")
    parser.add_argument("--successor-entry-id")
    args = parser.parse_args()
    try:
        if args.lifecycle:
            if (
                not args.subject_entry_id or not args.existing_index
                or len(args.evidence) != 1 or args.review_host_evidence
                or args.development_consumer_evidence or args.candidate_entry_id
                or args.development_entry_id or args.snapshot_id or args.item_artifact
                or args.catalog_release or args.wheel or args.git_revision
                or args.source_manifest_digest or args.source_qualification
                or args.destination
            ):
                raise ValueError("lifecycle needs one evidence file and an existing index")
            index = register_lifecycle(
                transition=args.lifecycle, subject_entry_id=args.subject_entry_id,
                successor_entry_id=args.successor_entry_id,
                evidence_path=args.evidence[0], existing_index=args.existing_index,
                output_path=args.output,
            )
        elif args.review_host_evidence:
            if (
                not args.candidate_entry_id or not args.existing_index
                or args.development_consumer_evidence or args.development_entry_id
                or args.snapshot_id or args.item_artifact or args.catalog_release
                or args.wheel or args.git_revision or args.source_manifest_digest
                or args.source_qualification or args.evidence or args.destination
                or args.subject_entry_id or args.successor_entry_id
            ):
                raise ValueError("review host evidence needs a candidate and existing index")
            index = register_review_host_evidence(
                candidate_entry_id=args.candidate_entry_id,
                evidence_path=args.review_host_evidence,
                existing_index=args.existing_index,
                output_path=args.output,
            )
        elif args.development_consumer_evidence:
            if (
                not args.development_entry_id or not args.existing_index
                or args.candidate_entry_id or args.item_artifact or args.snapshot_id
                or args.catalog_release or args.wheel or args.git_revision
                or args.source_manifest_digest or args.source_qualification
                or args.evidence or args.destination or args.subject_entry_id
                or args.successor_entry_id
            ):
                raise ValueError("consumer evidence needs a development entry and existing index")
            index = register_development_consumer_evidence(
                development_entry_id=args.development_entry_id,
                evidence_path=args.development_consumer_evidence,
                existing_index=args.existing_index,
                output_path=args.output,
            )
        elif args.snapshot_id:
            if (
                args.item_artifact or args.candidate_entry_id or args.development_entry_id
                or not args.catalog_release or not args.wheel
                or args.subject_entry_id or args.successor_entry_id
            ):
                raise ValueError("development snapshot needs catalog and wheel, not review items")
            index = register_development_snapshot(
                snapshot_id=args.snapshot_id, catalog_release=args.catalog_release,
                wheel=args.wheel, evidence_paths=args.evidence,
                destination_paths=args.destination, output_path=args.output,
                existing_index=args.existing_index, git_revision=args.git_revision,
                source_manifest_digest=args.source_manifest_digest,
                source_qualification=args.source_qualification,
            )
        else:
            if (
                not args.item_artifact or not args.git_revision
                or args.candidate_entry_id or args.development_entry_id
                or args.source_manifest_digest or args.catalog_release
                or args.wheel or args.destination
                or args.subject_entry_id or args.successor_entry_id
            ):
                raise ValueError("review candidate needs item artifacts and Git revision")
            index = register_candidate(
                item_artifacts=args.item_artifact, git_revision=args.git_revision,
                output_path=args.output, existing_index=args.existing_index,
                evidence_paths=args.evidence,
                source_qualification=args.source_qualification,
            )
    except (OSError, TypeError, ValueError) as error:
        print(f"candidate registration failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"entry": index["entries"][-1]["entry_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

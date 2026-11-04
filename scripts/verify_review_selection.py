"""Bind two CodeFusion selection exports to one SciRel development candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scirel_plugin.adapter import review_item_from_body, review_items_from_body  # noqa: E402
from release_index import current_unpublished_entries, read_index  # noqa: E402


SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
NONCE = re.compile(r"[0-9a-f]{64}\Z")
APPROVE = "plugin://scirel/review/approve"


def digest(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


def canonical_digest(value: Any) -> str:
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8"))


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def artifact(value: Any, label: str) -> dict[str, str]:
    if (
        not isinstance(value, dict)
        or set(value) != {"artifact_ref", "digest", "media_type"}
        or not isinstance(value["artifact_ref"], str)
        or not value["artifact_ref"].strip()
        or not isinstance(value["digest"], str)
        or not SHA256.fullmatch(value["digest"])
        or value["media_type"] != "application/json"
    ):
        raise ValueError(f"{label} must be an exact JSON Artifact reference")
    return value


def review_body(directory: Path, reference: dict[str, str], item_ref: str) -> dict[str, Any]:
    body = (directory / f"{reference['digest'][7:]}.json").read_bytes()
    if digest(body) != reference["digest"]:
        raise ValueError(f"review Artifact bytes differ for {item_ref}")
    return review_item_from_body(body, item_ref=item_ref)


def snapshot(path: Path, receipt_path: Path) -> tuple[dict[str, Any], dict[str, str]]:
    body = path.read_bytes()
    value = json.loads(body)
    receipt = read_object(receipt_path)
    if not isinstance(value, dict) or value.get("schema") != "codefusion.plugin-review-snapshot-export.v1":
        raise ValueError("unsupported host snapshot export")
    selection = value.get("selection")
    if not isinstance(selection, dict):
        raise ValueError("host snapshot lacks a selection proof")
    reference = artifact({key: receipt.get(key) for key in ("artifact_ref", "digest", "media_type")}, "snapshot receipt")
    if (
        reference["digest"] != digest(body)
        or receipt.get("byte_size") != len(body)
        or receipt.get("source_kind") != "review_snapshot_export"
        or not isinstance(receipt.get("replayed"), bool)
        or receipt.get("item_count") != value.get("item_count")
        or receipt.get("captured_at_epoch_ms") != value.get("captured_at_epoch_ms")
        or receipt.get("selection_nonce") != selection.get("nonce")
        or receipt.get("release_attempt_ref") != selection.get("release_attempt_ref")
    ):
        raise ValueError("host receipt differs from downloaded snapshot bytes")
    return value, reference


def verify_review_selection(
    *, release_index: Path, candidate_entry_id: str, approved_results: Path,
    review_artifacts_dir: Path, candidate_artifact: Path, candidate_artifact_ref: str,
    initial_snapshot: Path, initial_receipt: Path,
    revalidation_snapshot: Path, revalidation_receipt: Path,
    tenant_id: str, project_id: str, plugin_id: str, view_ref: str,
    plugin_release_ref: str, release_attempt_ref: str,
) -> dict[str, Any]:
    index = read_index(release_index)
    candidates = [entry for entry in current_unpublished_entries(index)
                  if entry["status"] == "candidate" and entry["entry_id"] == candidate_entry_id]
    if len(candidates) != 1:
        raise ValueError("selected candidate is absent or no longer current")
    candidate = candidates[0]
    original = candidate_artifact.read_bytes()
    original_ref = artifact({"artifact_ref": candidate_artifact_ref, "digest": digest(original),
                             "media_type": "application/json"}, "candidate Artifact")
    candidate_items = {item["item_ref"]: item for item in candidate["items"]}
    original_items = review_items_from_body(original)
    if (
        len(candidate_items) != len(candidate["items"])
        or {item["initial_revision"] for item in candidate_items.values()} != {original_ref["digest"]}
        or {item["item_ref"] for item in original_items} != set(candidate_items)
        or any(item["asset"]["asset_id"] != candidate_items[item["item_ref"]]["asset_id"]
               or canonical_digest(item["asset"]) != candidate_items[item["item_ref"]]["document_digest"]
               or item["dependency_asset_ids"] != candidate_items[item["item_ref"]]["dependency_asset_ids"]
               for item in original_items)
    ):
        raise ValueError("candidate Artifact does not match the indexed item census")

    results_body = approved_results.read_bytes()
    results = json.loads(results_body)
    if not isinstance(results, dict) or results.get("schema") != "scirel.review-completed-results.dev":
        raise ValueError("approved results schema is invalid")
    approved = results.get("approved_items")
    completed = results.get("completed_items")
    if not isinstance(approved, list) or not approved or not isinstance(completed, list):
        raise ValueError("approved results need completed and approved items")
    selected = {item.get("item_ref"): item for item in approved if isinstance(item, dict)}
    if len(selected) != len(approved) or not set(selected) <= set(candidate_items):
        raise ValueError("approved item selection is repeated or outside the candidate")
    if any(item not in completed for item in approved):
        raise ValueError("approved item is absent from completed results")

    first, first_ref = snapshot(initial_snapshot, initial_receipt)
    second, second_ref = snapshot(revalidation_snapshot, revalidation_receipt)
    if (
        not isinstance(first.get("exported_by_actor_id"), str)
        or not first["exported_by_actor_id"]
        or second.get("exported_by_actor_id") != first["exported_by_actor_id"]
    ):
        raise ValueError("revalidation exporter differs from initial host reviewer")
    expected_scope = {"tenant_id": tenant_id, "project_id": project_id, "plugin_id": plugin_id,
                      "view_ref": view_ref, "plugin_release_ref": plugin_release_ref}
    for export in (first, second):
        for key, expected in expected_scope.items():
            if not expected or export.get(key) != expected:
                raise ValueError(f"host snapshot {key} differs from the expected scope")
        items = export.get("items")
        if not isinstance(items, list) or export.get("item_count") != len(items):
            raise ValueError("host snapshot item census is invalid")
        by_ref = {item.get("item_ref"): item for item in items if isinstance(item, dict)}
        if len(by_ref) != len(items) or not set(candidate_items) <= set(by_ref):
            raise ValueError("host snapshot item census differs from the candidate")
        candidate_states = {item_ref: by_ref[item_ref] for item_ref in candidate_items}
        selection = export.get("selection")
        if not isinstance(selection, dict) or (
            selection.get("release_attempt_ref") != release_attempt_ref
            or artifact(selection.get("candidate_artifact"), "selected candidate") != original_ref
            or selection.get("expected_plugin_release_ref") != plugin_release_ref
            or not isinstance(selection.get("nonce"), str)
            or not NONCE.fullmatch(selection["nonce"])
        ):
            raise ValueError("host selection identity differs from the requested release attempt")
        declared = selection.get("selected_items")
        if not isinstance(declared, list) or len(declared) != len(selected):
            raise ValueError("host selected item set differs from approved results")
        for position, item_ref in enumerate(sorted(selected)):
            record = declared[position]
            if not isinstance(record, dict) or set(record) != {"item_ref", "current_artifact"} or record["item_ref"] != item_ref:
                raise ValueError("host selected items are not the exact ordered approved subset")
            current = artifact(record["current_artifact"], f"selected {item_ref}")
            if current["digest"] != selected[item_ref].get("revision"):
                raise ValueError("host selected current revision differs from approved results")
            if current != artifact(candidate_states[item_ref].get("current_artifact"), f"current {item_ref}"):
                raise ValueError("host selection differs from the view's current Artifact")
        for item_ref, state in candidate_states.items():
            source = artifact(state.get("source_artifact"), f"source {item_ref}")
            current = artifact(state.get("current_artifact"), f"current {item_ref}")
            if source != original_ref or source["digest"] != candidate_items[item_ref]["initial_revision"]:
                raise ValueError("host item source differs from indexed candidate")
            chain = state.get("transitions")
            if not isinstance(chain, list):
                raise ValueError("host item transition chain is missing")
            predecessor = source
            prior_time = -1
            for transition in chain:
                if (
                    not isinstance(transition, dict)
                    or not all(isinstance(transition.get(key), str) and transition[key]
                               for key in ("reviewer_actor_id", "run_id", "action_ref"))
                    or not isinstance(transition.get("applied_at_epoch_ms"), int)
                    or transition["applied_at_epoch_ms"] < prior_time
                    or artifact(transition.get("predecessor_artifact"), "transition predecessor") != predecessor
                ):
                    raise ValueError("host item transition chain is discontinuous")
                predecessor = artifact(transition.get("successor_artifact"), "transition successor")
                prior_time = transition["applied_at_epoch_ms"]
            if predecessor != current or state.get("applied_transition") != (chain[-1] if chain else None):
                raise ValueError("host item transition does not reach its current Artifact")
            if item_ref in selected:
                if not chain or chain[-1]["action_ref"] != APPROVE:
                    raise ValueError("selected item has no final authenticated approval action")
                final = chain[-1]
                successor = review_body(review_artifacts_dir, current, item_ref)
                decision = successor.get("decision")
                submitted = review_body(review_artifacts_dir, final["predecessor_artifact"], item_ref)
                projection = {key: successor[key] for key in
                              ("item_ref", "asset", "dependency_asset_ids", "evidence", "decision")}
                projection["revision"] = current["digest"]
                successor_body = (review_artifacts_dir / f"{current['digest'][7:]}.json").read_bytes()
                successor_envelope = json.loads(successor_body)
                if (
                    successor["status"] != "approved" or successor["gaps"]
                    or successor["candidate_id"] != candidate["candidate_id"]
                    or successor["draft_id"] != candidate["draft_id"]
                    or successor["asset"].get("asset_id") != candidate_items[item_ref]["asset_id"]
                    or not isinstance(decision, dict) or decision.get("outcome") != "approved"
                    or successor_envelope.get("predecessor") != final["predecessor_artifact"]
                    or decision.get("reviewer_actor_ref") != final["reviewer_actor_id"]
                    or decision.get("submitted_artifact") != final["predecessor_artifact"]
                    or decision.get("submitted_revision") != final["predecessor_artifact"]["digest"]
                    or submitted["status"] != "review_pending"
                    or selected[item_ref] != projection
                ):
                    raise ValueError("approved successor, actor, predecessor, or projection differs")

    first_selection = first["selection"]
    second_selection = second["selection"]
    if (
        first_selection.get("previous_snapshot") is not None
        or second_selection.get("previous_snapshot") != first_ref
        or first_selection["nonce"] == second_selection["nonce"]
        or first_ref == second_ref
        or second["captured_at_epoch_ms"] < first["captured_at_epoch_ms"]
        or first_selection["selected_items"] != second_selection["selected_items"]
    ):
        raise ValueError("revalidation does not bind the same current selection to the first snapshot")
    return {
        "schema": "scirel.review-host-selection-binding.dev",
        "candidate_entry_id": candidate_entry_id,
        "candidate_entry_digest": candidate["entry_digest"],
        "candidate_artifact": original_ref,
        "release_attempt_ref": release_attempt_ref,
        "host_scope": expected_scope,
        "approved_results_digest": digest(results_body),
        "selected_items": second_selection["selected_items"],
        "initial_snapshot": first_ref,
        "initial_nonce": first_selection["nonce"],
        "revalidation_snapshot": second_ref,
        "revalidation_nonce": second_selection["nonce"],
        "revalidated_at_epoch_ms": second["captured_at_epoch_ms"],
        "approval_state": "host_selection_consistency_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("release_index", "approved_results", "review_artifacts_dir", "candidate_artifact",
                 "initial_snapshot", "initial_receipt", "revalidation_snapshot", "revalidation_receipt"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    for name in ("candidate_entry_id", "candidate_artifact_ref", "tenant_id", "project_id",
                 "plugin_id", "view_ref", "plugin_release_ref", "release_attempt_ref"):
        parser.add_argument("--" + name.replace("_", "-"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise FileExistsError(f"binding output already exists: {args.output}")
        fields = vars(args).copy()
        output = fields.pop("output")
        result = verify_review_selection(**fields)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8", newline="\n")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"review selection verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"binding": str(output), "revalidation_snapshot": result["revalidation_snapshot"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

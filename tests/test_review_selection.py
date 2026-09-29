"""Selected host snapshots bind exact SciRel review artifacts without releasing them."""

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

from test_release_index import _candidate_entry_id, _reviewed_release_inputs


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_review_selection import verify_review_selection  # noqa: E402


def _digest(body):
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _write_snapshot(path, receipt_path, value, ref):
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(body)
    receipt_path.write_text(json.dumps({
        "artifact_ref": ref,
        "digest": _digest(body),
        "media_type": "application/json",
        "byte_size": len(body),
        "item_count": value["item_count"],
        "captured_at_epoch_ms": value["captured_at_epoch_ms"],
        "source_kind": "review_snapshot_export",
        "selection_nonce": value["selection"]["nonce"],
        "release_attempt_ref": value["selection"]["release_attempt_ref"],
        "replayed": False,
    }), encoding="utf-8")
    return {"artifact_ref": ref, "digest": _digest(body), "media_type": "application/json"}


def _inputs(tmp_path, *, multi_item=False):
    artifacts, _, _, _, projection = _reviewed_release_inputs(tmp_path, multi_item=multi_item)
    candidate = json.loads((tmp_path / "index.json").read_text())["entries"][0]
    initial = next(item for item in candidate["items"] if item["item_ref"] == projection["item_ref"])
    source = {"artifact_ref": "artifact://review/pending",
              "digest": initial["initial_revision"], "media_type": "application/json"}
    current = {"artifact_ref": "cf://artifact/approved",
               "digest": projection["revision"], "media_type": "application/json"}
    transition = {
        "reviewer_actor_id": projection["decision"]["reviewer_actor_ref"],
        "run_id": "run-approved",
        "action_ref": "plugin://scirel/review/approve",
        "predecessor_artifact": source,
        "successor_artifact": current,
        "applied_at_epoch_ms": 100,
    }
    selection = {
        "release_attempt_ref": "attempt-1",
        "candidate_artifact": source,
        "expected_plugin_release_ref": "plugin-release:scirel:1",
        "selected_items": [{"item_ref": initial["item_ref"], "current_artifact": current}],
        "previous_snapshot": None,
        "nonce": "a" * 64,
    }
    first = {
        "schema": "codefusion.plugin-review-snapshot-export.v1",
        "tenant_id": "tenant-1", "project_id": "project-1", "plugin_id": "scirel",
        "view_ref": "review", "plugin_release_ref": "plugin-release:scirel:1",
        "exported_by_actor_id": "reviewer-1", "captured_at_epoch_ms": 200,
        "item_count": len(candidate["items"]),
        "items": [{"item_ref": initial["item_ref"], "plugin_context_ref": "ctx-1",
                   "source_artifact": source, "current_artifact": current,
                   "current_updated_at_epoch_ms": 100,
                   "applied_transition": transition, "transitions": [transition]}],
        "selection": selection,
    }
    for pending in candidate["items"]:
        if pending["item_ref"] != initial["item_ref"]:
            first["items"].append({
                "item_ref": pending["item_ref"], "plugin_context_ref": "ctx-1",
                "source_artifact": source, "current_artifact": source,
                "current_updated_at_epoch_ms": 100,
                "applied_transition": None, "transitions": [],
            })
    second = copy.deepcopy(first)
    second["captured_at_epoch_ms"] = 300
    second["selection"]["nonce"] = "b" * 64
    first_path = tmp_path / "initial.json"
    first_receipt = tmp_path / "initial-receipt.json"
    first_ref = _write_snapshot(first_path, first_receipt, first, "cf://artifact/snapshot-initial")
    second["selection"]["previous_snapshot"] = first_ref
    second_path = tmp_path / "revalidation.json"
    second_receipt = tmp_path / "revalidation-receipt.json"
    _write_snapshot(second_path, second_receipt, second, "cf://artifact/snapshot-revalidated")
    arguments = {
        "release_index": tmp_path / "index.json",
        "candidate_entry_id": _candidate_entry_id(tmp_path / "index.json"),
        "approved_results": tmp_path / "results.json",
        "review_artifacts_dir": artifacts,
        "candidate_artifact": artifacts / f"{source['digest'][7:]}.json",
        "candidate_artifact_ref": source["artifact_ref"],
        "initial_snapshot": first_path, "initial_receipt": first_receipt,
        "revalidation_snapshot": second_path, "revalidation_receipt": second_receipt,
        "tenant_id": "tenant-1", "project_id": "project-1", "plugin_id": "scirel",
        "view_ref": "review", "plugin_release_ref": "plugin-release:scirel:1",
        "release_attempt_ref": "attempt-1",
    }
    return arguments, first, second


def test_selection_binds_two_host_snapshots_to_exact_successor(tmp_path):
    arguments, _, _ = _inputs(tmp_path)
    receipt = json.loads(arguments["revalidation_receipt"].read_text())
    receipt["replayed"] = True
    arguments["revalidation_receipt"].write_text(json.dumps(receipt))
    result = verify_review_selection(**arguments)
    assert result["schema"] == "scirel.review-host-selection-binding.dev"
    assert result["approval_state"] == "host_selection_consistency_only"
    assert len(result["selected_items"]) == 1
    assert result["initial_nonce"] != result["revalidation_nonce"]


def test_selection_requires_full_census_but_allows_unselected_item_to_advance(tmp_path):
    arguments, _, second = _inputs(tmp_path, multi_item=True)
    pending = next(item for item in second["items"]
                   if item["item_ref"] != second["selection"]["selected_items"][0]["item_ref"])
    advanced = {"artifact_ref": "cf://artifact/unselected-successor",
                "digest": "sha256:" + "c" * 64, "media_type": "application/json"}
    transition = {"reviewer_actor_id": "reviewer-2", "run_id": "run-other",
                  "action_ref": "plugin://scirel/review/request-evidence",
                  "predecessor_artifact": pending["source_artifact"],
                  "successor_artifact": advanced, "applied_at_epoch_ms": 250}
    pending["current_artifact"] = advanced
    pending["applied_transition"] = transition
    pending["transitions"] = [transition]
    _write_snapshot(arguments["revalidation_snapshot"], arguments["revalidation_receipt"],
                    second, "cf://artifact/snapshot-revalidated")
    assert len(verify_review_selection(**arguments)["selected_items"]) == 1

    second["items"].remove(pending)
    second["item_count"] = 1
    _write_snapshot(arguments["revalidation_snapshot"], arguments["revalidation_receipt"],
                    second, "cf://artifact/snapshot-revalidated")
    with pytest.raises(ValueError, match="item census"):
        verify_review_selection(**arguments)


@pytest.mark.parametrize(("change", "message"), [
    ("candidate", "selection identity"),
    ("stale_successor", "selected current revision"),
    ("selected_set", "selected item set"),
    ("action", "approval action"),
    ("actor", "actor"),
    ("previous", "revalidation"),
    ("nonce", "revalidation"),
    ("receipt", "receipt"),
])
def test_selection_rejects_unbound_or_replayed_evidence(tmp_path, change, message):
    arguments, first, second = _inputs(tmp_path)
    if change == "candidate":
        second["selection"]["candidate_artifact"]["digest"] = "sha256:" + "f" * 64
    elif change == "stale_successor":
        second["selection"]["selected_items"][0]["current_artifact"]["digest"] = "sha256:" + "f" * 64
    elif change == "selected_set":
        second["selection"]["selected_items"] = []
    elif change == "action":
        second["items"][0]["transitions"][0]["action_ref"] = "plugin://scirel/review/request-evidence"
        second["items"][0]["applied_transition"]["action_ref"] = "plugin://scirel/review/request-evidence"
    elif change == "actor":
        second["items"][0]["transitions"][0]["reviewer_actor_id"] = "other-reviewer"
        second["items"][0]["applied_transition"]["reviewer_actor_id"] = "other-reviewer"
    elif change == "previous":
        second["selection"]["previous_snapshot"] = None
    elif change == "nonce":
        second["selection"]["nonce"] = first["selection"]["nonce"]
    elif change == "receipt":
        receipt = json.loads(arguments["revalidation_receipt"].read_text())
        receipt["digest"] = "sha256:" + "f" * 64
        arguments["revalidation_receipt"].write_text(json.dumps(receipt))
    if change != "receipt":
        _write_snapshot(arguments["revalidation_snapshot"], arguments["revalidation_receipt"],
                        second, "cf://artifact/snapshot-revalidated")
    with pytest.raises(ValueError, match=message):
        verify_review_selection(**arguments)

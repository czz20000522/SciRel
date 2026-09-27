"""Neutral body import boundary for a CodeFusion host adapter."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Mapping

from scirel_workflow import CandidatePackage, SciRelWorkflow, WorkflowStatus
from scirel_workflow.l1_bundle import L1_BUNDLE_SCHEMA, l1_bundle_to_payload
from scirel_workflow.models import canonical_json, scientific_contract_gaps

from .body_runner import execute_automated_check


BODY_OPERATIONS = (
    "scirel.import_l1",
    "scirel.automated_check",
    "scirel.review.list_items",
    "scirel.review.open_item",
    "scirel.review.list_completed",
    "plugin.review.action",
)
SERVICE_PRINCIPAL_SCOPES = ("artifact.read", "artifact.write", "job.submit")
_SHA256 = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
_PLUGIN_VIEW_INDEX_SCHEMA = "codefusion.plugin-view-index.v1"
_PLUGIN_REVIEWER_SUCCESSOR_SCHEMA = (
    "codefusion.plugin-reviewer-successor-snapshot.v1"
)
_SCIREL_REVIEW_ITEM_SCHEMA = "scirel.review-item.dev"
_SCIREL_REVIEW_ITEM_DECISION_SCHEMA = "scirel.review-item-decision.dev"
_SCIREL_REVIEW_DETAIL_SCHEMA = "scirel.review-item-detail.dev"
_SCIREL_COMPLETED_RESULTS_SCHEMA = "scirel.review-completed-results.dev"
_SCIREL_REVIEW_EXTENSION = "scirel.review"
_REVIEW_ACTION_SPECS = (
    ("approved", "plugin://scirel/review/approve", "Approve"),
    (
        "needs_evidence",
        "plugin://scirel/review/request-evidence",
        "Request evidence",
    ),
    (
        "rework_requested",
        "plugin://scirel/review/request-rework",
        "Request rework",
    ),
    ("rejected", "plugin://scirel/review/reject", "Reject"),
)
_REVIEW_ACTION_OUTCOMES = {
    action_ref: outcome for outcome, action_ref, _ in _REVIEW_ACTION_SPECS
}
_REVIEW_OUTCOMES = {
    "approved",
    "needs_evidence",
    "rework_requested",
    "rejected",
}


@dataclass(frozen=True)
class SciRelBodyImportRequest:
    """Host-to-SciRel request with no platform-owned fields."""

    operation: str
    artifact_ref: str
    artifact_digest: str
    media_type: str
    body: bytes
    operation_payload: Mapping[str, Any] | None = None

    def validate(self) -> None:
        if self.operation not in BODY_OPERATIONS:
            raise ValueError(f"unsupported SciRel body operation: {self.operation}")
        if not self.artifact_ref.strip():
            raise ValueError("artifact_ref is required")
        if not _SHA256.fullmatch(self.artifact_digest):
            raise ValueError("artifact_digest must be sha256:<64 hex>")
        if self.media_type != "application/json":
            raise ValueError("media_type must be application/json")
        if not isinstance(self.body, bytes):
            raise ValueError("body must be bytes")
        actual_digest = "sha256:" + hashlib.sha256(self.body).hexdigest()
        if actual_digest != self.artifact_digest:
            raise ValueError("artifact body digest does not match artifact_digest")
        if self.operation == "scirel.review.open_item":
            if not isinstance(self.operation_payload, Mapping):
                raise ValueError("review open operation_payload must be an object")
            required = {"item_ref", "revision"}
            missing = required.difference(self.operation_payload)
            unknown = set(self.operation_payload).difference(required)
            if missing:
                raise ValueError(
                    "review open operation_payload is missing fields: "
                    + ", ".join(sorted(missing))
                )
            if unknown:
                raise ValueError(
                    "review open operation_payload has unknown fields: "
                    + ", ".join(sorted(unknown))
                )
            item_ref = self.operation_payload["item_ref"]
            revision = self.operation_payload["revision"]
            if not isinstance(item_ref, str) or not item_ref.strip():
                raise ValueError("review open item_ref must be a non-empty string")
            if not isinstance(revision, str) or not _SHA256.fullmatch(revision):
                raise ValueError("review open revision must be sha256:<64 hex>")
            if revision != self.artifact_digest:
                raise ValueError("review item revision does not match current artifact")
        elif self.operation == "plugin.review.action":
            _validate_review_action_envelope(
                self.operation_payload,
                artifact_digest=self.artifact_digest,
            )
        elif self.operation_payload is not None:
            raise ValueError(
                f"{self.operation} does not accept operation_payload"
            )

    def to_wire(self) -> dict[str, Any]:
        """Encode the JSON artifact body as a UTF-8 JSON string for HTTP wire."""

        self.validate()
        try:
            wire_body = self.body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("SciRel body wire format requires UTF-8 JSON") from exc
        wire = {
            "operation": self.operation,
            "artifact_ref": self.artifact_ref,
            "artifact_digest": self.artifact_digest,
            "media_type": self.media_type,
            "body": wire_body,
        }
        if self.operation_payload is not None:
            wire["operation_payload"] = dict(self.operation_payload)
        return wire

    @classmethod
    def from_wire(cls, payload: Mapping[str, Any]) -> "SciRelBodyImportRequest":
        if not isinstance(payload, Mapping):
            raise ValueError("SciRel body request must be an object")
        required = {"operation", "artifact_ref", "artifact_digest", "media_type", "body"}
        missing = required.difference(payload)
        if missing:
            raise ValueError(
                "SciRel body request is missing fields: " + ", ".join(sorted(missing))
            )
        unknown = set(payload).difference(required | {"operation_payload"})
        if unknown:
            raise ValueError(
                "SciRel body request has unknown fields: " + ", ".join(sorted(unknown))
            )
        if not isinstance(payload["body"], str):
            raise ValueError("SciRel body request body must be a UTF-8 string")

        text_fields = ("operation", "artifact_ref", "artifact_digest", "media_type")
        for field in text_fields:
            if not isinstance(payload[field], str):
                raise ValueError(f"SciRel body request {field} must be a string")
        request = cls(
            operation=payload["operation"],
            artifact_ref=payload["artifact_ref"],
            artifact_digest=payload["artifact_digest"],
            media_type=payload["media_type"],
            body=payload["body"].encode("utf-8"),
            operation_payload=payload.get("operation_payload"),
        )
        request.validate()
        return request


@dataclass(frozen=True)
class SciRelBodyImportResponse:
    """Domain artifact body returned for host-side artifact persistence."""

    operation: str
    artifact_kind: str
    media_type: str
    body: bytes

    @property
    def body_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.body).hexdigest()

    def to_metadata(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "artifact_kind": self.artifact_kind,
            "media_type": self.media_type,
            "body_digest": self.body_digest,
        }

    def to_wire(self) -> dict[str, Any]:
        try:
            wire_body = self.body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("SciRel body wire format requires UTF-8 JSON") from exc
        return {
            **self.to_metadata(),
            "body": wire_body,
        }


def execute_body_import(request: SciRelBodyImportRequest) -> SciRelBodyImportResponse:
    """Validate one host body and produce a canonical SciRel artifact body."""

    request.validate()
    if request.operation == "scirel.import_l1":
        candidate = _candidate_from_l1(request)
        return SciRelBodyImportResponse(
            operation=request.operation,
            artifact_kind="scirel.candidate-package.dev",
            media_type="application/json",
            body=canonical_json(candidate.to_dict()),
        )

    if request.operation == "scirel.review.list_items":
        items = review_items_from_body(request.body)
        if len(items) > 100:
            raise ValueError(
                "one review source artifact cannot expose more than 100 items"
            )
        return SciRelBodyImportResponse(
            operation=request.operation,
            artifact_kind=_PLUGIN_VIEW_INDEX_SCHEMA,
            media_type="application/json",
            body=canonical_json(
                {
                    "schema": _PLUGIN_VIEW_INDEX_SCHEMA,
                    "items": [
                        review_item_index_entry(item, request.artifact_digest)
                        for item in items
                    ],
                    "has_more": False,
                }
            ),
        )

    if request.operation == "scirel.review.open_item":
        assert request.operation_payload is not None
        item_ref = request.operation_payload["item_ref"]
        item = review_item_from_body(request.body, item_ref=item_ref)
        snapshot = review_item_detail(
            item,
            item_ref=item_ref,
            artifact_ref=request.artifact_ref,
            revision=request.artifact_digest,
        )
        return SciRelBodyImportResponse(
            operation=request.operation,
            artifact_kind=_SCIREL_REVIEW_DETAIL_SCHEMA,
            media_type="application/json",
            body=canonical_json(snapshot),
        )

    if request.operation == "plugin.review.action":
        assert request.operation_payload is not None
        successor = apply_review_action(request)
        return SciRelBodyImportResponse(
            operation=request.operation,
            artifact_kind=_PLUGIN_REVIEWER_SUCCESSOR_SCHEMA,
            media_type="application/json",
            body=canonical_json(successor),
        )

    if request.operation == "scirel.review.list_completed":
        completed_items = [
            {
                "item_ref": item["item_ref"],
                "revision": request.artifact_digest,
                "asset": item["asset"],
                "dependency_asset_ids": item["dependency_asset_ids"],
                "evidence": item["evidence"],
                "decision": item["decision"],
            }
            for item in review_items_from_body(request.body)
            if item["status"] != "review_pending"
        ]
        approved_items = [
            item
            for item in completed_items
            if item["decision"]["outcome"] == "approved"
        ]
        return SciRelBodyImportResponse(
            operation=request.operation,
            artifact_kind=_SCIREL_COMPLETED_RESULTS_SCHEMA,
            media_type="application/json",
            body=canonical_json(
                {
                    "schema": _SCIREL_COMPLETED_RESULTS_SCHEMA,
                    "completed_items": completed_items,
                    "approved_items": approved_items,
                }
            ),
        )

    result_body = execute_automated_check(request.body)
    return SciRelBodyImportResponse(
        operation=request.operation,
        artifact_kind="scirel.automated-check-result.dev",
        media_type="application/json",
        body=result_body,
    )


def execute_body_import_wire(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Handle one decoded HTTP JSON request without owning the transport.

    A thin HTTP server can pass its parsed JSON object here and serialize the
    returned object as JSON. Transport, authentication and request limits stay
    with the host; this function only applies the SciRel wire contract.
    """

    return execute_body_import(
        SciRelBodyImportRequest.from_wire(payload)
    ).to_wire()


def _candidate_from_l1(request: SciRelBodyImportRequest) -> CandidatePackage:
    import json

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("L1 artifact must contain a JSON object") from exc
    if not isinstance(payload, dict):
        raise ValueError("L1 artifact must contain a JSON object")
    if payload.get("schema") == L1_BUNDLE_SCHEMA:
        payload = l1_bundle_to_payload(payload)
    return CandidatePackage.from_l1(
        payload,
        source_artifact_ref=request.artifact_ref,
        source_digest=request.artifact_digest,
        run_id="run-" + hashlib.sha256(request.body).hexdigest(),
    )


def _validate_review_action_envelope(
    payload: Mapping[str, Any] | None,
    *,
    artifact_digest: str,
) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("review action operation_payload must be an object")
    required = {
        "item_ref",
        "revision",
        "extension_ref",
        "action_ref",
        "reviewer",
        "payload",
    }
    missing = required.difference(payload)
    unknown = set(payload).difference(required)
    if missing:
        raise ValueError(
            "review action operation_payload is missing fields: "
            + ", ".join(sorted(missing))
        )
    if unknown:
        raise ValueError(
            "review action operation_payload has unknown fields: "
            + ", ".join(sorted(unknown))
        )
    item_ref = payload["item_ref"]
    if not isinstance(item_ref, str) or not item_ref.strip():
        raise ValueError("review action item_ref must be a non-empty string")
    revision = payload["revision"]
    if not isinstance(revision, str) or not _SHA256.fullmatch(revision):
        raise ValueError("review action revision must be sha256:<64 hex>")
    if revision != artifact_digest:
        raise ValueError("review action revision does not match current artifact")
    if payload["extension_ref"] != _SCIREL_REVIEW_EXTENSION:
        raise ValueError("review action extension_ref does not identify SciRel review")
    action_ref = payload["action_ref"]
    if action_ref not in _REVIEW_ACTION_OUTCOMES:
        raise ValueError("unsupported SciRel review action_ref")

    reviewer = payload["reviewer"]
    if not isinstance(reviewer, Mapping) or set(reviewer) != {"actor_ref"}:
        raise ValueError("review action reviewer must contain only actor_ref")
    actor_ref = reviewer["actor_ref"]
    if not isinstance(actor_ref, str) or not actor_ref.strip():
        raise ValueError("review action reviewer.actor_ref must be non-empty")

    domain_payload = payload["payload"]
    if not isinstance(domain_payload, Mapping):
        raise ValueError("SciRel review action payload must be an object")
    required_action = {"outcome", "notes"}
    missing_action = required_action.difference(domain_payload)
    unknown_action = set(domain_payload).difference(required_action)
    if missing_action:
        raise ValueError(
            "SciRel review action payload is missing fields: "
            + ", ".join(sorted(missing_action))
        )
    if unknown_action:
        raise ValueError(
            "SciRel review action payload has unknown fields: "
            + ", ".join(sorted(unknown_action))
        )
    if domain_payload["outcome"] not in _REVIEW_OUTCOMES:
        raise ValueError("unsupported SciRel review outcome")
    expected_outcome = _REVIEW_ACTION_OUTCOMES[action_ref]
    if domain_payload["outcome"] != expected_outcome:
        raise ValueError("SciRel review action_ref does not match its outcome")
    if not isinstance(domain_payload["notes"], str):
        raise ValueError("SciRel review notes must be a string")


def _decode_json_object(body: bytes, label: str) -> Mapping[str, Any]:
    import json

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} must contain a JSON object") from exc
    if not isinstance(payload, Mapping):
        raise ValueError(f"{label} must contain a JSON object")
    return payload


def review_items_from_body(body: bytes) -> list[dict[str, Any]]:
    payload = _decode_json_object(body, "review state artifact")
    schema = payload.get("schema")
    if schema == "scirel.workflow-state.dev":
        workflow = SciRelWorkflow.from_dict(payload)
        if workflow.status is not WorkflowStatus.REVIEW_PENDING:
            return []
        draft = workflow.record.draft
        if draft is None:
            raise ValueError("workflow has no standardized draft")
        return [
            review_item_from_workflow(workflow, index)
            for index in range(len(draft.assets))
        ]
    if schema == _PLUGIN_REVIEWER_SUCCESSOR_SCHEMA:
        required = {
            "schema",
            "item_ref",
            "predecessor",
            "payload",
            "display_index",
            "detail_action_ref",
            "actions",
            "lease_disposition",
        }
        missing = required.difference(payload)
        unknown = set(payload).difference(required)
        if missing or unknown:
            raise ValueError("review successor fields are invalid")
        _validate_artifact_reference(payload["predecessor"], "predecessor")
        display_index = payload["display_index"]
        if not isinstance(display_index, Mapping) or set(display_index) != {
            "title",
            "subtitle",
        }:
            raise ValueError("review successor display_index fields are invalid")
        if not all(
            isinstance(display_index[field], str) and display_index[field].strip()
            for field in ("title", "subtitle")
        ):
            raise ValueError("review successor display_index values must be non-empty")
        if not isinstance(payload["detail_action_ref"], str) or not payload[
            "detail_action_ref"
        ].strip():
            raise ValueError("review successor detail_action_ref must be non-empty")
        if payload["lease_disposition"] not in {"retain", "release"}:
            raise ValueError("review successor lease_disposition is invalid")
        item = validate_review_item(payload["payload"])
        if item["item_ref"] != payload["item_ref"]:
            raise ValueError("review successor item ref does not match its payload")
        if dict(display_index) != review_item_display_index(item):
            raise ValueError("review successor display_index does not match its payload")
        expected_detail_action_ref = (
            "plugin://scirel/review/open/"
            + item["item_ref"].removeprefix("scirel-review-item:")
        )
        if payload["detail_action_ref"] != expected_detail_action_ref:
            raise ValueError("review successor detail_action_ref does not match its item")
        if payload["actions"] != review_item_action_descriptors(item):
            raise ValueError("review successor actions do not match its item")
        expected_disposition = (
            "retain" if item["status"] == "review_pending" else "release"
        )
        if payload["lease_disposition"] != expected_disposition:
            raise ValueError("review successor lease disposition does not match item status")
        return [item]
    if schema == _SCIREL_REVIEW_ITEM_SCHEMA:
        return [validate_review_item(payload)]
    raise ValueError("artifact is not a SciRel review source")


def review_item_from_body(
    body: bytes,
    *,
    item_ref: str | None = None,
) -> dict[str, Any]:
    items = review_items_from_body(body)
    if item_ref is None:
        if len(items) != 1:
            raise ValueError("review source does not identify exactly one item")
        return items[0]
    for item in items:
        if item["item_ref"] == item_ref:
            return item
    raise ValueError("review item ref does not match current artifact")


def review_item_from_workflow(
    workflow: SciRelWorkflow,
    asset_index: int,
) -> dict[str, Any]:
    if workflow.status is not WorkflowStatus.REVIEW_PENDING:
        raise ValueError("only queued review items can be projected")
    draft = workflow.record.draft
    if draft is None:
        raise ValueError("workflow has no standardized draft")
    if isinstance(asset_index, bool) or not isinstance(asset_index, int):
        raise ValueError("asset_index must be an integer")
    if not 0 <= asset_index < len(draft.assets):
        raise ValueError("asset_index is outside the standardized draft")
    asset = dict(draft.assets[asset_index])
    raw_asset_id = asset.get("asset_id")
    asset_id = (
        raw_asset_id
        if isinstance(raw_asset_id, str) and raw_asset_id.strip()
        else f"asset[{asset_index}]"
    )
    item_ref = _review_item_ref(
        candidate_id=draft.candidate_id,
        draft_id=draft.draft_id,
        asset_index=asset_index,
        asset_id=asset_id,
    )
    known_asset_ids = {
        value
        for candidate_asset in draft.assets
        if isinstance((value := candidate_asset.get("asset_id")), str) and value
    }
    item_gaps = list(scientific_contract_gaps([asset]))
    for gap in draft.gaps:
        parts = gap.split(":", 2)
        gap_asset_id = (
            parts[1]
            if parts[0].startswith("scientific_contract_") and len(parts) > 1
            else parts[0]
        )
        if gap_asset_id not in known_asset_ids or gap_asset_id == asset_id:
            item_gaps.append(gap)
    dependencies = list(
        dict.fromkeys((*_asset_dependency_ids(asset), *draft.dependency_asset_ids))
    )
    evidence = [
        dict(record)
        for record in draft.evidence
        if not record.get("asset_id") or record.get("asset_id") == asset_id
    ]
    return validate_review_item(
        {
            "schema": _SCIREL_REVIEW_ITEM_SCHEMA,
            "item_ref": item_ref,
            "candidate_id": draft.candidate_id,
            "draft_id": draft.draft_id,
            "asset_index": asset_index,
            "asset": asset,
            "dependency_asset_ids": dependencies,
            "evidence": evidence,
            "gaps": list(dict.fromkeys(item_gaps)),
            "status": "review_pending",
            "decision": None,
        }
    )


def _asset_dependency_ids(asset: Mapping[str, Any]) -> list[str]:
    version = asset.get("version")
    if not isinstance(version, Mapping):
        return []
    dependencies = version.get("dependencies")
    if not isinstance(dependencies, (list, tuple)):
        return []
    result = []
    for dependency in dependencies:
        if not isinstance(dependency, Mapping):
            continue
        asset_id = dependency.get("asset_id")
        if isinstance(asset_id, str) and asset_id.strip() and asset_id not in result:
            result.append(asset_id)
    return result


def validate_review_item(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("SciRel review item must be an object")
    required = {
        "schema",
        "item_ref",
        "candidate_id",
        "draft_id",
        "asset_index",
        "asset",
        "dependency_asset_ids",
        "evidence",
        "gaps",
        "status",
        "decision",
    }
    missing = required.difference(payload)
    unknown = set(payload).difference(required)
    if missing or unknown:
        raise ValueError("SciRel review item fields are invalid")
    if payload["schema"] != _SCIREL_REVIEW_ITEM_SCHEMA:
        raise ValueError("unsupported SciRel review item schema")
    for field in ("item_ref", "candidate_id", "draft_id"):
        value = payload[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"review item {field} must be a non-empty string")
    asset_index = payload["asset_index"]
    if isinstance(asset_index, bool) or not isinstance(asset_index, int) or asset_index < 0:
        raise ValueError("review item asset_index must be a nonnegative integer")
    asset = payload["asset"]
    if not isinstance(asset, Mapping):
        raise ValueError("review item asset must be an object")
    asset = dict(asset)
    raw_asset_id = asset.get("asset_id")
    asset_id = (
        raw_asset_id
        if isinstance(raw_asset_id, str) and raw_asset_id.strip()
        else f"asset[{asset_index}]"
    )
    expected_ref = _review_item_ref(
        candidate_id=payload["candidate_id"],
        draft_id=payload["draft_id"],
        asset_index=asset_index,
        asset_id=asset_id,
    )
    if payload["item_ref"] != expected_ref:
        raise ValueError("review item identity does not match its scientific content")

    dependencies = _validated_string_list(
        payload["dependency_asset_ids"], "dependency_asset_ids"
    )
    gaps = _validated_string_list(payload["gaps"], "gaps")
    evidence_value = payload["evidence"]
    if not isinstance(evidence_value, (list, tuple)) or not all(
        isinstance(record, Mapping) for record in evidence_value
    ):
        raise ValueError("review item evidence must be an array of objects")
    evidence = [dict(record) for record in evidence_value]
    status = payload["status"]
    if status not in {"review_pending", *_REVIEW_OUTCOMES}:
        raise ValueError("unsupported SciRel review item status")
    decision = payload["decision"]
    if status == "review_pending":
        if decision is not None:
            raise ValueError("pending review item must not contain a decision")
    else:
        decision = _validate_item_decision(
            decision,
            item_ref=payload["item_ref"],
            draft_id=payload["draft_id"],
            asset_id=asset_id,
            outcome=status,
        )
    return {
        "schema": _SCIREL_REVIEW_ITEM_SCHEMA,
        "item_ref": payload["item_ref"],
        "candidate_id": payload["candidate_id"],
        "draft_id": payload["draft_id"],
        "asset_index": asset_index,
        "asset": asset,
        "dependency_asset_ids": dependencies,
        "evidence": evidence,
        "gaps": gaps,
        "status": status,
        "decision": decision,
    }


def _validated_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"review item {field} must be an array")
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"review item {field} values must be non-empty strings")
        if item in result:
            raise ValueError(f"review item {field} must not contain duplicates")
        result.append(item)
    return result


def _validate_artifact_reference(value: Any, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {
        "artifact_ref",
        "digest",
        "media_type",
    }:
        raise ValueError(f"{field} must be an exact Artifact reference")
    if not isinstance(value["artifact_ref"], str) or not value["artifact_ref"].strip():
        raise ValueError(f"{field}.artifact_ref must be non-empty")
    if not isinstance(value["digest"], str) or not _SHA256.fullmatch(value["digest"]):
        raise ValueError(f"{field}.digest must be sha256:<64 hex>")
    if value["media_type"] != "application/json":
        raise ValueError(f"{field}.media_type must be application/json")
    return dict(value)


def _validate_item_decision(
    value: Any,
    *,
    item_ref: str,
    draft_id: str,
    asset_id: str,
    outcome: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("completed review item must contain a decision")
    required = {
        "schema",
        "item_ref",
        "draft_id",
        "asset_id",
        "outcome",
        "reviewer_actor_ref",
        "notes",
        "submitted_revision",
        "submitted_artifact",
    }
    if set(value) != required:
        raise ValueError("review item decision fields are invalid")
    if value["schema"] != _SCIREL_REVIEW_ITEM_DECISION_SCHEMA:
        raise ValueError("unsupported review item decision schema")
    if (
        value["item_ref"] != item_ref
        or value["draft_id"] != draft_id
        or value["asset_id"] != asset_id
        or value["outcome"] != outcome
    ):
        raise ValueError("review item decision identity does not match its item")
    if not isinstance(value["reviewer_actor_ref"], str) or not value[
        "reviewer_actor_ref"
    ].strip():
        raise ValueError("review decision reviewer_actor_ref must be non-empty")
    if not isinstance(value["notes"], str):
        raise ValueError("review decision notes must be a string")
    revision = value["submitted_revision"]
    if not isinstance(revision, str) or not _SHA256.fullmatch(revision):
        raise ValueError("review decision submitted_revision is invalid")
    submitted_artifact = _validate_artifact_reference(
        value["submitted_artifact"], "submitted_artifact"
    )
    if submitted_artifact["digest"] != revision:
        raise ValueError("review decision revision does not match submitted artifact")
    return {
        **dict(value),
        "submitted_artifact": submitted_artifact,
    }


def review_item_display_index(item: Mapping[str, Any]) -> dict[str, str]:
    asset = item["asset"]
    title = asset.get("title")
    if isinstance(title, Mapping):
        title = title.get("zh") or title.get("en") or next(
            (value for value in title.values() if isinstance(value, str) and value),
            None,
        )
    if not isinstance(title, str) or not title.strip():
        title = asset.get("asset_id") or item["item_ref"]
    asset_id = asset.get("asset_id") or f"asset[{item['asset_index']}]"
    kind = asset.get("kind") or "asset"
    return {
        "title": title[:512],
        "subtitle": f"{kind} | {asset_id} | {item['status']}"[:512],
    }


def review_item_action_descriptors(
    item: Mapping[str, Any],
) -> list[dict[str, Any]]:
    validated = validate_review_item(item)
    if validated["status"] != "review_pending":
        return []
    return [
        {
            "action_ref": action_ref,
            "label": label,
            "payload": {"outcome": outcome, "notes": ""},
        }
        for outcome, action_ref, label in _REVIEW_ACTION_SPECS
        if outcome != "approved" or not validated["gaps"]
    ]


def apply_review_action(request: SciRelBodyImportRequest) -> dict[str, Any]:
    assert request.operation_payload is not None
    envelope = request.operation_payload
    item = review_item_from_body(request.body, item_ref=envelope["item_ref"])
    if item["status"] != "review_pending":
        raise ValueError("only a pending review item can receive a decision")
    action = envelope["payload"]
    outcome = action["outcome"]
    if outcome == "approved" and item["gaps"]:
        raise ValueError("a review item with unresolved gaps cannot be approved")
    predecessor = {
        "artifact_ref": request.artifact_ref,
        "digest": request.artifact_digest,
        "media_type": request.media_type,
    }
    asset_id = item["asset"].get("asset_id") or f"asset[{item['asset_index']}]"
    decision = {
        "schema": _SCIREL_REVIEW_ITEM_DECISION_SCHEMA,
        "item_ref": item["item_ref"],
        "draft_id": item["draft_id"],
        "asset_id": asset_id,
        "outcome": outcome,
        "reviewer_actor_ref": envelope["reviewer"]["actor_ref"],
        "notes": action["notes"],
        "submitted_revision": request.artifact_digest,
        "submitted_artifact": predecessor,
    }
    successor_item = validate_review_item(
        {
            **item,
            "status": outcome,
            "decision": decision,
        }
    )
    if len(canonical_json(successor_item)) > 64 * 1024:
        raise ValueError("SciRel review item exceeds the successor payload limit")
    return {
        "schema": _PLUGIN_REVIEWER_SUCCESSOR_SCHEMA,
        "item_ref": item["item_ref"],
        "predecessor": predecessor,
        "payload": successor_item,
        "display_index": review_item_display_index(successor_item),
        "detail_action_ref": (
            "plugin://scirel/review/open/"
            + item["item_ref"].removeprefix("scirel-review-item:")
        ),
        "actions": review_item_action_descriptors(successor_item),
        "lease_disposition": "release",
    }


def _review_item_ref(
    *, candidate_id: str, draft_id: str, asset_index: int, asset_id: str
) -> str:
    identity = canonical_json(
        {
            "candidate_id": candidate_id,
            "draft_id": draft_id,
            "asset_index": asset_index,
            "asset_id": asset_id,
        }
    )
    return "scirel-review-item:" + hashlib.sha256(identity).hexdigest()


def review_item_index_entry(
    item: Mapping[str, Any],
    revision: str,
) -> dict[str, Any]:
    validated = validate_review_item(item)
    item_ref = validated["item_ref"]
    return {
        "item_ref": item_ref,
        "revision": revision,
        "display_index": review_item_display_index(validated),
        "detail_action_ref": (
            "plugin://scirel/review/open/"
            + item_ref.removeprefix("scirel-review-item:")
        ),
        "actions": review_item_action_descriptors(validated),
    }


def review_ui_projection(workflow: SciRelWorkflow) -> dict[str, Any]:
    status = workflow.status.value
    actions = {
        "automated_ready": ("standardize",),
        "automated_rejected": ("retry_automated_check",),
        "needs_evidence": (
            "create_draft" if workflow.record.draft is not None else "provide_evidence",
        ),
        "rework_requested": (
            "create_draft" if workflow.record.draft is not None else "rework_candidate",
        ),
        "draft": ("update_draft", "submit_for_review"),
        "review_pending": ("start_review",),
        "review_in_progress": (
            ("approve", "needs_evidence", "rework_requested", "reject")
            if workflow.record.draft is not None and not workflow.record.draft.gaps
            else ("needs_evidence", "rework_requested", "reject")
        ),
        "approved": ("release",),
    }.get(status, ())
    return {
        "schema": "scirel.review-ui-extension.dev",
        "extension_id": "scientific-asset-review",
        "workflow": workflow.to_dict(),
        "available_actions": list(actions),
    }


def review_item_detail(
    item: Mapping[str, Any],
    *,
    item_ref: str,
    artifact_ref: str,
    revision: str,
) -> dict[str, Any]:
    validated = validate_review_item(item)
    if validated["item_ref"] != item_ref:
        raise ValueError("review item ref does not match current artifact")
    return {
        "schema": _SCIREL_REVIEW_DETAIL_SCHEMA,
        "item_ref": item_ref,
        "current_artifact": {
            "artifact_ref": artifact_ref,
            "digest": revision,
            "media_type": "application/json",
        },
        "item": validated,
        "available_actions": [
            action["action_ref"]
            for action in review_item_action_descriptors(validated)
        ],
    }


def validate_review_item_detail_body(
    body: bytes,
    *,
    item_ref: str,
    revision: str,
) -> dict[str, Any]:
    import json

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("review item detail must contain a JSON object") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("review item detail must contain a JSON object")
    return validate_review_item_detail_payload(
        payload,
        item_ref=item_ref,
        revision=revision,
    )


def validate_review_item_detail_payload(
    payload: Mapping[str, Any],
    *,
    item_ref: str,
    revision: str,
) -> dict[str, Any]:
    required = {
        "schema",
        "item_ref",
        "current_artifact",
        "item",
        "available_actions",
    }
    missing = required.difference(payload)
    unknown = set(payload).difference(required)
    if missing:
        raise ValueError(
            "review item detail is missing fields: " + ", ".join(sorted(missing))
        )
    if unknown:
        raise ValueError(
            "review item detail has unknown fields: " + ", ".join(sorted(unknown))
        )
    if payload["schema"] != _SCIREL_REVIEW_DETAIL_SCHEMA:
        raise ValueError("artifact is not a review item detail")
    if payload["item_ref"] != item_ref:
        raise ValueError("review detail item ref does not match request")
    current = payload["current_artifact"]
    if not isinstance(current, Mapping):
        raise ValueError("review detail current_artifact must be an object")
    if set(current) != {"artifact_ref", "digest", "media_type"}:
        raise ValueError("review detail current_artifact fields are invalid")
    if current["digest"] != revision:
        raise ValueError("review detail revision does not match request")
    item = validate_review_item(payload["item"])
    if item["item_ref"] != item_ref:
        raise ValueError("review detail content does not match item ref")
    expected_actions = [
        action["action_ref"] for action in review_item_action_descriptors(item)
    ]
    if payload["available_actions"] != expected_actions:
        raise ValueError("review detail actions do not match item status")
    return item

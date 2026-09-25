"""Neutral body import boundary for a CodeFusion host adapter."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any, Mapping

from scirel_workflow import CandidatePackage, SciRelWorkflow, WorkflowStatus
from scirel_workflow.l1_bundle import L1_BUNDLE_SCHEMA, l1_bundle_to_payload
from scirel_workflow.models import canonical_json

from .body_runner import execute_automated_check


BODY_OPERATIONS = (
    "scirel.import_l1",
    "scirel.automated_check",
    "scirel.review.list_items",
    "scirel.review.open_item",
)
SERVICE_PRINCIPAL_SCOPES = ("artifact.read", "artifact.write", "job.submit")
_SHA256 = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


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
        workflow = workflow_from_review_body(request.body)
        items = []
        if workflow.status is WorkflowStatus.REVIEW_PENDING:
            items.append(review_item_index_entry(workflow, request.artifact_digest))
        return SciRelBodyImportResponse(
            operation=request.operation,
            artifact_kind="scirel.review-item-index.dev",
            media_type="application/json",
            body=canonical_json(
                {
                    "schema": "scirel.review-item-index.dev",
                    "items": items,
                    "has_more": False,
                }
            ),
        )

    if request.operation == "scirel.review.open_item":
        assert request.operation_payload is not None
        workflow = workflow_from_review_body(request.body)
        if workflow.status is not WorkflowStatus.REVIEW_PENDING:
            raise ValueError("only a queued review item can be opened")
        item_ref = request.operation_payload["item_ref"]
        if item_ref != review_item_ref(workflow):
            raise ValueError("review item ref does not match current artifact")
        workflow.start_review()
        snapshot = review_item_snapshot(
            workflow,
            item_ref=item_ref,
            artifact_ref=request.artifact_ref,
            revision=request.artifact_digest,
        )
        return SciRelBodyImportResponse(
            operation=request.operation,
            artifact_kind="scirel.review-item-snapshot.dev",
            media_type="application/json",
            body=canonical_json(snapshot),
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


def workflow_from_review_body(body: bytes) -> SciRelWorkflow:
    import json

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("review state artifact must contain a JSON object") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("review state artifact must contain a JSON object")
    return workflow_from_review_payload(payload)


def workflow_from_review_payload(payload: Mapping[str, Any]) -> SciRelWorkflow:
    if payload.get("schema") == "scirel.workflow-state.dev":
        workflow_payload = payload
    elif payload.get("schema") == "scirel.review-item-snapshot.dev":
        view = payload.get("view")
        if not isinstance(view, Mapping):
            raise ValueError("review item snapshot view must be an object")
        workflow_payload = view.get("workflow")
        if not isinstance(workflow_payload, Mapping):
            raise ValueError("review item snapshot workflow must be an object")
    else:
        raise ValueError("artifact is not a SciRel workflow or review snapshot")
    return SciRelWorkflow.from_dict(workflow_payload)


def review_item_ref(workflow: SciRelWorkflow) -> str:
    draft = workflow.record.draft
    if draft is None:
        raise ValueError("workflow has no standardized draft")
    identity = canonical_json(
        {
            "candidate_id": workflow.record.candidate.candidate_id,
            "draft_id": draft.draft_id,
        }
    )
    return "scirel-review-item:" + hashlib.sha256(identity).hexdigest()


def review_item_index_entry(
    workflow: SciRelWorkflow, revision: str
) -> dict[str, Any]:
    draft = workflow.record.draft
    if draft is None:
        raise ValueError("workflow has no standardized draft")
    item_ref = review_item_ref(workflow)
    return {
        "item_ref": item_ref,
        "revision": revision,
        "display_index": {
            "title": (
                workflow.record.candidate.project_id
                or workflow.record.candidate.candidate_id
            ),
            "subtitle": draft.draft_id,
        },
        "detail_action_ref": (
            "plugin://scirel/review/open/"
            + item_ref.removeprefix("scirel-review-item:")
        ),
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
        "review_pending": ("update_draft", "start_review"),
        "review_in_progress": (
            ("approve", "needs_evidence", "rework_requested", "reject")
            if workflow.record.draft is not None and not workflow.record.draft.gaps
            else ("needs_evidence", "rework_requested", "reject")
        ),
    }.get(status, ())
    return {
        "schema": "scirel.review-ui-extension.dev",
        "extension_id": "scientific-asset-review",
        "workflow": workflow.to_dict(),
        "available_actions": list(actions),
    }


def review_item_snapshot(
    workflow: SciRelWorkflow,
    *,
    item_ref: str,
    artifact_ref: str,
    revision: str,
) -> dict[str, Any]:
    return {
        "schema": "scirel.review-item-snapshot.dev",
        "item_ref": item_ref,
        "opened_from": {
            "artifact_ref": artifact_ref,
            "revision": revision,
        },
        "view": review_ui_projection(workflow),
    }


def validate_review_item_snapshot_body(
    body: bytes,
    *,
    item_ref: str,
    revision: str,
) -> SciRelWorkflow:
    import json

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("review item snapshot must contain a JSON object") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("review item snapshot must contain a JSON object")
    return validate_review_item_snapshot_payload(
        payload,
        item_ref=item_ref,
        revision=revision,
    )


def validate_review_item_snapshot_payload(
    payload: Mapping[str, Any],
    *,
    item_ref: str,
    revision: str,
) -> SciRelWorkflow:
    required = {"schema", "item_ref", "opened_from", "view"}
    missing = required.difference(payload)
    unknown = set(payload).difference(required)
    if missing:
        raise ValueError(
            "review item snapshot is missing fields: " + ", ".join(sorted(missing))
        )
    if unknown:
        raise ValueError(
            "review item snapshot has unknown fields: " + ", ".join(sorted(unknown))
        )
    if payload["schema"] != "scirel.review-item-snapshot.dev":
        raise ValueError("artifact is not a review item snapshot")
    if payload["item_ref"] != item_ref:
        raise ValueError("review snapshot item ref does not match request")
    opened_from = payload["opened_from"]
    if not isinstance(opened_from, Mapping):
        raise ValueError("review snapshot opened_from must be an object")
    if set(opened_from) != {"artifact_ref", "revision"}:
        raise ValueError("review snapshot opened_from fields are invalid")
    if opened_from["revision"] != revision:
        raise ValueError("review snapshot revision does not match request")
    workflow = workflow_from_review_payload(payload)
    if workflow.status is not WorkflowStatus.REVIEW_IN_PROGRESS:
        raise ValueError("opened review snapshot must be review_in_progress")
    if review_item_ref(workflow) != item_ref:
        raise ValueError("review snapshot workflow does not match item ref")
    if payload["view"] != review_ui_projection(workflow):
        raise ValueError("review snapshot view does not match workflow state")
    return workflow

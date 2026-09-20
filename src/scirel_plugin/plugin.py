"""SciRel plugin operations over the narrow CodeFusion host contract."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from scirel_workflow.models import (
    AutomatedCheckResult,
    CandidatePackage,
    ReleaseManifest,
    ReviewDecision,
    StandardizedDraft,
    WorkflowStatus,
)
from scirel_workflow.workflow import SciRelWorkflow

from .contract import (
    ArtifactReference,
    PluginConnectorDescriptor,
    PluginEventEnvelope,
    PluginRegistration,
    PluginReleaseSnapshot,
    PluginRunResult,
    PluginRunSubmitEnvelope,
    PluginSkillEntrypoint,
    PluginScope,
    PluginViewDescriptor,
)
from .host import ArtifactRef, HostServices, JobRef, ReviewView
from .adapter import (
    SERVICE_PRINCIPAL_SCOPES,
    review_item_index_entry,
    review_item_ref,
    review_item_snapshot,
    review_ui_projection as build_review_ui_projection,
    validate_review_item_snapshot_payload,
    workflow_from_review_payload,
)


@dataclass(frozen=True)
class PluginHandoff:
    artifact: ArtifactRef
    job: JobRef


@dataclass(frozen=True)
class PluginReviewResult:
    decision_artifact: ArtifactRef
    state_artifact: ArtifactRef
    event: PluginEventEnvelope


@dataclass(frozen=True)
class PluginReleaseResult:
    release: ReleaseManifest
    release_artifact: ArtifactRef
    state_artifact: ArtifactRef
    event: PluginEventEnvelope


class SciRelPlugin:
    plugin_id = "scirel"
    contract = "scirel-plugin.dev"
    release_failure_codes = frozenset({
        "validation_failed",
        "build_failed",
        "binding_mismatch",
    })

    @staticmethod
    def service_principal_scopes() -> tuple[str, ...]:
        """Minimal host scopes needed by the plugin adapter."""

        return SERVICE_PRINCIPAL_SCOPES

    def __init__(self, host: HostServices):
        self.host = host
        self.host.register_plugin(self.registration())

    def registration(self) -> PluginRegistration:
        skill_bundle_ref = "cf://artifact/scirel-skill-bundle-example-20260920"
        return PluginRegistration(
            plugin_id=self.plugin_id,
            release=PluginReleaseSnapshot(
                plugin_release_ref=(
                    "plugin-release://scirel/0.1.0.dev5/example-20260920"
                ),
                artifacts=(
                    ArtifactReference(
                        artifact_ref=skill_bundle_ref,
                        digest="sha256:" + "1" * 64,
                        media_type="application/vnd.agent-skills.bundle+zip",
                    ),
                    ArtifactReference(
                        artifact_ref=(
                            "cf://artifact/scirel-catalog-example-20260920"
                        ),
                        digest="sha256:" + "2" * 64,
                        media_type="application/vnd.scirel.catalog-snapshot+zip",
                    ),
                ),
                skill_entrypoints=(
                    PluginSkillEntrypoint(
                        name="scientific-computation-asset-extraction",
                        artifact_ref=skill_bundle_ref,
                        path=(
                            "skills/extraction/"
                            "scientific-computation-asset-extraction/SKILL.md"
                        ),
                    ),
                    PluginSkillEntrypoint(
                        name="scirel-integration",
                        artifact_ref=skill_bundle_ref,
                        path="skills/integration/scirel-integration/SKILL.md",
                    ),
                    PluginSkillEntrypoint(
                        name="scirel-solving",
                        artifact_ref=skill_bundle_ref,
                        path="skills/usage/scirel-solving/SKILL.md",
                    ),
                ),
                connectors=(
                    PluginConnectorDescriptor(
                        connector_id="scirel.thin-mcp",
                        protocol_family="mcp",
                        capability_refs=(
                            "catalog.discover",
                            "asset.read",
                            "callable.resolve",
                            "callable.invoke",
                        ),
                        endpoint_ref="connector-endpoint://scirel/default",
                    ),
                ),
                runtime_dependency_refs=(
                    "runtime-dependency://python-distribution/scirel/"
                    "0.1.0.dev5/example-20260920",
                ),
            ),
            capabilities=(
                "plugin.dispatch",
                "artifact.read",
                "artifact.write",
            ),
            required_scopes=(
                "plugin.dispatch",
                "artifact.read",
                "artifact.write",
            ),
            ui_extensions=("scirel.review",),
            view_descriptors=(
                PluginViewDescriptor(
                    view_ref="scirel.review",
                    open_operation="scirel.review.open_item",
                ),
            ),
        )

    def descriptor(self) -> dict[str, Any]:
        registration = self.registration()
        return {
            "plugin_id": self.plugin_id,
            "contract": self.contract,
            "release": registration.release.to_dict(),
            "capabilities": list(registration.capabilities),
            "required_scopes": list(registration.required_scopes),
            "service_principal_scopes": list(self.service_principal_scopes()),
            "ui_extensions": list(registration.ui_extensions),
            "view_descriptors": [
                descriptor.to_dict()
                for descriptor in registration.view_descriptors
            ],
            "operations": [
                "scirel.import_l1",
                "scirel.automated_check",
                "scirel.automated_check_result",
                "scirel.standardize",
                "scirel.review.list_items",
                "scirel.review.open_item",
                "scirel.review",
                "scirel.release",
            ],
            "required_host_capabilities": [
                "artifact_store",
                "job_runner",
                "identity",
                "review_ui_extension",
            ],
        }

    def review_ui_projection(self, workflow: SciRelWorkflow) -> dict[str, Any]:
        """Return the SciRel-owned domain projection for the review extension.

        CodeFusion may render and route actions for this document, but it does
        not derive scientific state or action availability from platform run
        status. The embedded workflow snapshot remains the single source for
        candidate, check, draft, review and release data. A host must apply
        ``start_review`` before rendering full ``review_pending`` detail to an
        expert; projecting queued state for backend routing is not observation.
        """

        return build_review_ui_projection(workflow)

    @staticmethod
    def _review_item_ref(workflow: SciRelWorkflow) -> str:
        return review_item_ref(workflow)

    def _read_json_artifact(
        self, source: ArtifactRef | ArtifactReference
    ) -> tuple[ArtifactReference, Mapping[str, Any]]:
        reference = source.as_contract() if isinstance(source, ArtifactRef) else source
        reference.validate()
        if reference.media_type != "application/json":
            raise ValueError("review state artifact media_type must be application/json")
        body = self.host.read_artifact(reference.artifact_ref)
        actual_digest = "sha256:" + hashlib.sha256(body).hexdigest()
        if actual_digest != reference.digest:
            raise ValueError("review state artifact digest does not match reference")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("review state artifact must contain a JSON object") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("review state artifact must contain a JSON object")
        return reference, payload

    @staticmethod
    def _workflow_from_review_payload(payload: Mapping[str, Any]) -> SciRelWorkflow:
        return workflow_from_review_payload(payload)

    def list_review_items(
        self,
        current_states: tuple[ArtifactRef | ArtifactReference, ...],
        *,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Return a bounded opaque index without observing queued drafts."""

        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("review item limit must be between 1 and 100")
        indexed: list[dict[str, Any]] = []
        for source in current_states:
            reference, payload = self._read_json_artifact(source)
            workflow = self._workflow_from_review_payload(payload)
            if workflow.status is not WorkflowStatus.REVIEW_PENDING:
                continue
            indexed.append(review_item_index_entry(workflow, reference.digest))
        indexed.sort(key=lambda item: item["item_ref"])
        return {
            "schema": "scirel.review-item-index.dev",
            "items": indexed[:limit],
            "has_more": len(indexed) > limit,
        }

    def open_review_item(
        self,
        current_state: ArtifactRef | ArtifactReference,
        *,
        item_ref: str,
        revision: str,
    ) -> ArtifactRef:
        """Observe one queued item and return its exact immutable view/state.

        The generic host owns current-state CAS and idempotency. Replaying this
        method with the same immutable input creates the same content-addressed
        snapshot; this method never advances a host pointer itself.
        """

        reference, payload = self._read_json_artifact(current_state)
        if revision != reference.digest:
            raise ValueError("review item revision does not match current artifact")
        workflow = self._workflow_from_review_payload(payload)
        if workflow.status is not WorkflowStatus.REVIEW_PENDING:
            raise ValueError("only a queued review item can be opened")
        if item_ref != self._review_item_ref(workflow):
            raise ValueError("review item ref does not match current artifact")

        workflow.start_review()
        snapshot = review_item_snapshot(
            workflow,
            item_ref=item_ref,
            artifact_ref=reference.artifact_ref,
            revision=reference.digest,
        )
        return self.host.put_artifact("scirel.review-item-snapshot.dev", snapshot)

    def validate_review_item_snapshot(
        self,
        source: ArtifactRef | ArtifactReference,
        *,
        item_ref: str,
        revision: str,
    ) -> SciRelWorkflow:
        """Validate that an open result is bound to the requested item/revision."""

        _, payload = self._read_json_artifact(source)
        return validate_review_item_snapshot_payload(
            payload,
            item_ref=item_ref,
            revision=revision,
        )

    def publish_candidate(self, candidate: CandidatePackage) -> PluginHandoff:
        artifact = self.host.put_artifact(
            "scirel.candidate-package.dev", candidate.to_dict()
        )
        job = self.host.submit_job(
            "scirel.automated_check",
            (artifact.ref,),
            plugin_id=self.plugin_id,
            workflow_run_id=candidate.run_id,
            payload={
                "operation": "scirel.automated_check",
                "candidate_id": candidate.candidate_id,
                "candidate_digest": candidate.package_digest,
                "source_digest": candidate.source_digest,
            },
        )
        return PluginHandoff(artifact=artifact, job=job)

    def build_l1_run_submission(
        self,
        source_artifact: ArtifactRef | ArtifactReference,
        *,
        tenant_id: str,
        project_id: str,
        workflow_run_id: str,
    ) -> PluginRunSubmitEnvelope:
        """Build the host run envelope that imports one saved L1 artifact.

        The operation is part of the plugin payload so a generic host runner
        never has to infer SciRel behavior from the input artifact kind.
        """

        artifact = (
            source_artifact.as_contract()
            if isinstance(source_artifact, ArtifactRef)
            else source_artifact
        )
        artifact.validate()
        return PluginRunSubmitEnvelope(
            scope=PluginScope(
                tenant_id=tenant_id,
                project_id=project_id,
                plugin_id=self.plugin_id,
                workflow_run_id=workflow_run_id,
            ),
            idempotency_key=(
                f"{self.plugin_id}:l1:{workflow_run_id}:{artifact.digest}"
            ),
            input_artifacts=(artifact,),
            payload={
                "operation": "scirel.import_l1",
            },
        )

    def build_candidate_run_submission(
        self,
        candidate: CandidatePackage,
        artifact: ArtifactRef,
        *,
        tenant_id: str,
        project_id: str,
    ) -> PluginRunSubmitEnvelope:
        """Build the generic CodeFusion run envelope for a candidate artifact.

        The HTTP/platform adapter owns delivery. Keeping construction here makes
        the SciRel payload and the host contract testable without a database.
        """

        if candidate.project_id and candidate.project_id != project_id:
            raise ValueError("candidate project_id does not match host project scope")
        if artifact.kind != "scirel.candidate-package.dev":
            raise ValueError("candidate run requires a candidate-package artifact")
        if artifact.digest != candidate.package_digest:
            raise ValueError("candidate artifact digest does not match candidate package")
        return PluginRunSubmitEnvelope(
            scope=PluginScope(
                tenant_id=tenant_id,
                project_id=project_id,
                plugin_id=self.plugin_id,
                workflow_run_id=candidate.run_id,
            ),
            idempotency_key=(
                f"{self.plugin_id}:run:{candidate.run_id}:{candidate.package_digest}"
            ),
            input_artifacts=(artifact.as_contract(),),
            payload={
                "operation": "scirel.automated_check",
                "candidate_id": candidate.candidate_id,
                "candidate_digest": candidate.package_digest,
                "source_digest": candidate.source_digest,
            },
        )

    def import_automated_result_from_run(
        self,
        candidate: CandidatePackage,
        run_result: PluginRunResult | Mapping[str, Any],
    ) -> CandidatePackage:
        """Import a completed platform run's result artifact.

        Platform failures remain platform failures and must be retried or
        surfaced by the caller; they are never converted into a SciRel result.
        """

        result = self._read_automated_result_from_run(run_result)
        return candidate.apply_automated_result(result)

    def consume_automated_result_into_workflow(
        self,
        workflow: SciRelWorkflow,
        run_result: PluginRunResult | Mapping[str, Any],
    ) -> ArtifactRef:
        """Apply one completed host result and persist the SciRel snapshot.

        Platform failures, invalid result references and invalid result bodies
        raise before the workflow is changed.  The returned artifact is the
        SciRel-owned workflow state, not a platform run receipt.
        """

        result = self._read_automated_result_from_run(run_result)
        workflow.apply_automated_result(result)
        return self.publish_workflow_state(workflow)

    def _read_automated_result_from_run(
        self, run_result: PluginRunResult | Mapping[str, Any]
    ) -> AutomatedCheckResult:
        result = (
            run_result
            if isinstance(run_result, PluginRunResult)
            else PluginRunResult.from_mapping(run_result)
        )
        result.validate()
        if result.status != "completed":
            raise ValueError(
                "platform run did not complete: "
                + (result.failure_class or result.status)
            )
        if len(result.result_artifact_refs) != 1:
            raise ValueError("completed automated run must return exactly one result artifact")
        reference = result.result_artifact_refs[0]
        if reference.media_type != "application/json":
            raise ValueError("automated result artifact media_type must be application/json")
        body = self.host.read_artifact(reference.artifact_ref)
        if "sha256:" + hashlib.sha256(body).hexdigest() != reference.digest:
            raise ValueError("automated result artifact digest does not match reference")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("automated result artifact must contain a JSON object") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("automated result payload must be a JSON object")
        return AutomatedCheckResult.from_mapping(payload)

    def import_l1(
        self,
        payload: Mapping[str, Any],
        *,
        source_artifact_ref: str,
        source_digest: str | None = None,
        run_id: str | None = None,
    ) -> PluginHandoff:
        """Turn one stored L1 payload into a candidate handoff."""
        candidate = CandidatePackage.from_l1(
            payload,
            source_artifact_ref=source_artifact_ref,
            source_digest=source_digest,
            run_id=run_id,
        )
        return self.publish_candidate(candidate)

    def publish_automated_result(self, result: AutomatedCheckResult) -> ArtifactRef:
        """Store a host-produced deterministic check result."""

        return self.host.put_artifact(
            "scirel.automated-check-result.dev", result.to_dict()
        )

    def publish_automated_result_event(
        self,
        result: AutomatedCheckResult,
        artifact: ArtifactRef,
        *,
        workflow_run_id: str,
        correlation_id: str,
    ) -> PluginEventEnvelope:
        """Publish the minimal opaque host event for a result artifact."""

        if artifact.kind != "scirel.automated-check-result.dev":
            raise ValueError(
                "automated result event requires an automated-check-result artifact"
            )
        if artifact.media_type != "application/json":
            raise ValueError(
                "automated result artifact media_type must be application/json"
            )
        if artifact.digest != result.result_digest:
            raise ValueError(
                "automated result artifact digest does not match result"
            )
        return self.host.emit_event(
            plugin_id=self.plugin_id,
            event_type="scirel.automated_check.result",
            workflow_run_id=workflow_run_id,
            correlation_id=correlation_id,
            artifact_refs=(artifact.ref,),
            payload={
                "result_id": result.result_id,
                "candidate_id": result.candidate_id,
                "result_digest": result.result_digest,
                "status": "passed" if result.passed else "failed",
                "next_action": result.next_action,
            },
        )

    def import_automated_result_artifact(
        self,
        candidate: CandidatePackage,
        source: ArtifactRef | ArtifactReference,
    ) -> CandidatePackage:
        """Apply a saved deterministic check result to its candidate."""

        if isinstance(source, ArtifactRef):
            if source.kind != "scirel.automated-check-result.dev":
                raise ValueError(
                    "automated result import requires an automated-check-result artifact"
                )
            if source.media_type != "application/json":
                raise ValueError(
                    "automated result artifact media_type must be application/json"
                )
            source_ref = source.ref
            expected_digest = source.digest
        else:
            source.validate()
            if source.media_type != "application/json":
                raise ValueError(
                    "automated result artifact media_type must be application/json"
                )
            source_ref = source.artifact_ref
            expected_digest = source.digest
        return self.import_automated_result_body(
            candidate,
            self.host.read_artifact(source_ref),
            expected_digest=expected_digest,
        )

    def import_automated_result_body(
        self,
        candidate: CandidatePackage,
        body: bytes,
        *,
        expected_digest: str | None = None,
    ) -> CandidatePackage:
        """Import a result body supplied by a host-controlled artifact adapter."""

        if expected_digest:
            actual_digest = "sha256:" + hashlib.sha256(body).hexdigest()
            if actual_digest != expected_digest:
                raise ValueError("automated result artifact digest does not match reference")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("automated result artifact must contain a JSON object") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("automated result payload must be a JSON object")
        return candidate.apply_automated_result(AutomatedCheckResult.from_mapping(payload))

    def import_l1_artifact(
        self,
        source: ArtifactRef | ArtifactReference,
        *,
        run_id: str | None = None,
    ) -> PluginHandoff:
        """Read a saved JSON L1 artifact through the host and create a candidate."""
        if isinstance(source, ArtifactRef):
            source_ref = source.ref
            source_digest = source.digest
            media_type = source.media_type
        else:
            source.validate()
            source_ref = source.artifact_ref
            source_digest = source.digest
            media_type = source.media_type
        if media_type != "application/json":
            raise ValueError("L1 artifact media_type must be application/json")
        return self.import_l1_body(
            self.host.read_artifact(source_ref),
            source_artifact_ref=source_ref,
            source_digest=source_digest,
            run_id=run_id,
        )

    def import_l1_body(
        self,
        body: bytes,
        *,
        source_artifact_ref: str,
        source_digest: str | None = None,
        run_id: str | None = None,
    ) -> PluginHandoff:
        """Import L1 JSON supplied by a host-controlled artifact adapter."""

        if source_digest:
            actual_digest = "sha256:" + hashlib.sha256(body).hexdigest()
            if actual_digest != source_digest:
                raise ValueError("L1 artifact digest does not match source digest")
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("L1 artifact must contain a JSON object") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("L1 artifact payload must be a JSON object")
        return self.import_l1(
            payload,
            source_artifact_ref=source_artifact_ref,
            source_digest=source_digest,
            run_id=run_id,
        )

    def publish_draft(self, draft: StandardizedDraft) -> ArtifactRef:
        artifact = self.host.put_artifact(
            "scirel.standardized-draft.dev", draft.to_dict()
        )
        self.host.register_review_view(
            self.plugin_id,
            ReviewView(
                view_id="scirel.review",
                title="SciRel scientific asset review",
                operations=(
                    "scirel.review.list_items",
                    "scirel.review.open_item",
                ),
            ),
        )
        return artifact

    def publish_review(self, decision: ReviewDecision) -> ArtifactRef:
        return self.host.put_artifact(
            "scirel.review-decision.dev", decision.to_dict()
        )

    def record_review_action(
        self,
        workflow: SciRelWorkflow,
        outcome: str,
        *,
        notes: str = "",
        correlation_id: str,
    ) -> PluginReviewResult:
        """Apply one expert action and publish its SciRel domain artifacts."""

        draft = workflow.record.draft
        if draft is None:
            raise ValueError("workflow has no standardized draft")
        decision = ReviewDecision(
            draft_id=draft.draft_id,
            outcome=outcome,
            reviewer=self.host.current_user(),
            notes=notes,
        )
        workflow.record_review(decision)
        decision_artifact = self.publish_review(decision)
        state_artifact = self.publish_workflow_state(workflow)
        event = self.host.emit_event(
            plugin_id=self.plugin_id,
            event_type="scirel.review_action.recorded",
            workflow_run_id=workflow.record.candidate.run_id,
            correlation_id=correlation_id,
            artifact_refs=(decision_artifact.ref, state_artifact.ref),
            payload={
                "draft_id": decision.draft_id,
                "outcome": decision.outcome.value,
                "workflow_status": workflow.status.value,
            },
        )
        return PluginReviewResult(
            decision_artifact=decision_artifact,
            state_artifact=state_artifact,
            event=event,
        )

    def publish_workflow_state(self, workflow: SciRelWorkflow) -> ArtifactRef:
        """Persist the resumable SciRel-owned workflow snapshot.

        The host supplies storage only; platform scope, jobs, sessions and
        credentials stay outside the domain snapshot.
        """

        return self.host.put_artifact(
            "scirel.workflow-state.dev", workflow.to_dict()
        )

    def release(self, release_payload: ReleaseManifest | Mapping[str, Any]) -> ArtifactRef:
        release = (
            release_payload
            if isinstance(release_payload, ReleaseManifest)
            else ReleaseManifest.from_mapping(release_payload)
        )
        return self.host.put_artifact(
            "scirel.release-manifest.dev", release.to_dict()
        )

    def publish_release_completed_event(
        self,
        release: ReleaseManifest,
        artifact: ArtifactRef,
        *,
        workflow_run_id: str,
        correlation_id: str,
    ) -> PluginEventEnvelope:
        """Publish a release completion bound to its exact manifest artifact."""

        if artifact.kind != "scirel.release-manifest.dev":
            raise ValueError("release event requires a release-manifest artifact")
        if artifact.digest != release.release_digest:
            raise ValueError("release artifact digest does not match release manifest")
        return self.host.emit_event(
            plugin_id=self.plugin_id,
            event_type="scirel.release.completed",
            workflow_run_id=workflow_run_id,
            correlation_id=correlation_id,
            artifact_refs=(artifact.ref,),
            payload={
                "release_id": release.release_id,
                "candidate_id": release.candidate_id,
                "draft_id": release.draft_id,
                "release_version": release.release_version,
                "release_digest": release.release_digest,
            },
        )

    def publish_release_failed_event(
        self,
        *,
        workflow_run_id: str,
        correlation_id: str,
        failure_code: str,
    ) -> PluginEventEnvelope:
        """Publish one bounded SciRel release failure without platform details."""

        if failure_code not in self.release_failure_codes:
            raise ValueError("unsupported release failure code")
        return self.host.emit_event(
            plugin_id=self.plugin_id,
            event_type="scirel.release.failed",
            workflow_run_id=workflow_run_id,
            correlation_id=correlation_id,
            payload={"failure_code": failure_code},
        )

    def complete_release(
        self,
        workflow: SciRelWorkflow,
        *,
        release_id: str,
        catalog_ref: str,
        catalog_digest: str,
        wheel_ref: str,
        wheel_digest: str,
        correlation_id: str,
        release_version: str,
    ) -> PluginReleaseResult:
        """Complete the SciRel release and persist its resumable state."""

        release = workflow.release(
            release_id=release_id,
            catalog_ref=catalog_ref,
            catalog_digest=catalog_digest,
            wheel_ref=wheel_ref,
            wheel_digest=wheel_digest,
            release_version=release_version,
        )
        release_artifact = self.release(release)
        state_artifact = self.publish_workflow_state(workflow)
        event = self.publish_release_completed_event(
            release,
            release_artifact,
            workflow_run_id=workflow.record.candidate.run_id,
            correlation_id=correlation_id,
        )
        return PluginReleaseResult(
            release=release,
            release_artifact=release_artifact,
            state_artifact=state_artifact,
            event=event,
        )

"""Small host contract and an in-memory fake used by adapter tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from scirel_workflow.models import canonical_json, digest

from .contract import (
    ArtifactReference,
    PluginCommandEnvelope,
    PluginEventEnvelope,
    PluginRegistration,
    PluginScope,
)


@dataclass(frozen=True)
class ArtifactRef:
    ref: str
    kind: str
    digest: str
    media_type: str = "application/json"

    @property
    def artifact_ref(self) -> str:
        return self.ref

    def as_contract(self) -> ArtifactReference:
        return ArtifactReference(
            artifact_ref=self.ref,
            digest=self.digest,
            media_type=self.media_type,
        )


@dataclass(frozen=True)
class JobRef:
    ref: str
    operation: str


@dataclass(frozen=True)
class ReviewView:
    view_id: str
    title: str
    operations: tuple[str, ...]


class HostServices(Protocol):
    def put_artifact(self, kind: str, payload: Mapping[str, Any]) -> ArtifactRef: ...

    def read_artifact(self, ref: str) -> bytes: ...

    def submit_job(
        self,
        operation: str,
        input_refs: tuple[str, ...],
        *,
        plugin_id: str,
        plugin_context_ref: str,
        payload: Mapping[str, Any],
    ) -> JobRef: ...

    def register_plugin(self, registration: PluginRegistration) -> None: ...

    def current_user(self) -> str: ...

    def register_review_view(self, plugin_id: str, view: ReviewView) -> None: ...

    def emit_event(
        self,
        *,
        plugin_id: str,
        event_type: str,
        plugin_context_ref: str,
        correlation_id: str,
        artifact_refs: tuple[str, ...] = (),
        payload: Mapping[str, Any] | None = None,
    ) -> PluginEventEnvelope: ...


class FakeHost:
    """In-memory host with only the services required by the first slice."""

    def __init__(
        self,
        *,
        user: str = "developer",
        tenant_id: str = "tenant-dev",
        project_id: str = "project-dev",
    ) -> None:
        self.user = user
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.artifacts: dict[str, tuple[ArtifactRef, bytes]] = {}
        self.jobs: list[tuple[JobRef, tuple[str, ...]]] = []
        self.review_views: dict[str, ReviewView] = {}
        self.registrations: dict[str, PluginRegistration] = {}
        self.commands: list[PluginCommandEnvelope] = []
        self.events: list[PluginEventEnvelope] = []

    def put_artifact(self, kind: str, payload: Mapping[str, Any]) -> ArtifactRef:
        payload_bytes = canonical_json(payload)
        artifact_digest = digest(payload)
        ref = f"artifact://{kind}/{artifact_digest.removeprefix('sha256:')[:16]}"
        artifact = ArtifactRef(
            ref=ref,
            kind=kind,
            digest=artifact_digest,
            media_type="application/json",
        )
        self.artifacts[ref] = (artifact, payload_bytes)
        return artifact

    def register_plugin(self, registration: PluginRegistration) -> None:
        registration.validate()
        self.registrations[registration.plugin_id] = registration

    def submit_job(
        self,
        operation: str,
        input_refs: tuple[str, ...],
        *,
        plugin_id: str,
        plugin_context_ref: str,
        payload: Mapping[str, Any],
    ) -> JobRef:
        registration = self.registrations[plugin_id]
        input_artifacts = tuple(
            self.artifacts[ref][0].as_contract() for ref in input_refs
        )
        envelope = PluginCommandEnvelope(
            command=operation,
            scope=PluginScope(
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                plugin_id=plugin_id,
                plugin_context_ref=plugin_context_ref,
            ),
            idempotency_key=f"{plugin_id}:command:{len(self.commands) + 1}",
            input_artifacts=input_artifacts,
            payload=dict(payload),
        )
        envelope.validate(registration)
        self.commands.append(envelope)
        ref = f"job://{len(self.jobs) + 1}"
        job = JobRef(ref=ref, operation=operation)
        self.jobs.append((job, tuple(input_refs)))
        return job

    def emit_event(
        self,
        *,
        plugin_id: str,
        event_type: str,
        plugin_context_ref: str,
        correlation_id: str,
        artifact_refs: tuple[str, ...] = (),
        payload: Mapping[str, Any] | None = None,
    ) -> PluginEventEnvelope:
        if plugin_id not in self.registrations:
            raise ValueError(f"plugin is not registered: {plugin_id}")
        event = PluginEventEnvelope(
            event_id=f"event-{len(self.events) + 1}",
            event_type=event_type,
            scope=PluginScope(
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                plugin_id=plugin_id,
                plugin_context_ref=plugin_context_ref,
            ),
            correlation_id=correlation_id,
            idempotency_key=f"{plugin_id}:event:{len(self.events) + 1}",
            artifact_refs=tuple(self.artifacts[ref][0].as_contract() for ref in artifact_refs),
            payload=dict(payload or {}),
        )
        event.validate()
        self.events.append(event)
        return event

    def current_user(self) -> str:
        return self.user

    def register_review_view(self, plugin_id: str, view: ReviewView) -> None:
        self.review_views[f"{plugin_id}:{view.view_id}"] = view

    def read_artifact(self, ref: str) -> bytes:
        return self.artifacts[ref][1]

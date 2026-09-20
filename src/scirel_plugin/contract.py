"""Python representation of the narrow CodeFusion plugin host contract."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


class PluginContractError(ValueError):
    """Raised when a host envelope does not satisfy the public contract."""


_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def _required(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PluginContractError(f"{field} is required")
    return value


def _names(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    for value in values:
        _required(value, field)
    return values


@dataclass(frozen=True)
class PluginSkillEntrypoint:
    name: str
    artifact_ref: str
    path: str

    def validate(self) -> None:
        _required(self.name, "skill_entrypoint.name")
        _required(self.artifact_ref, "skill_entrypoint.artifact_ref")
        _required(self.path, "skill_entrypoint.path")
        if (
            self.path.startswith(("/", "\\"))
            or "\\" in self.path
            or any(ord(character) < 32 for character in self.path)
            or any(segment in {"", ".", ".."} for segment in self.path.split("/"))
        ):
            raise PluginContractError(
                "skill_entrypoint.path must be a portable relative path without traversal"
            )

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {
            "name": self.name,
            "artifact_ref": self.artifact_ref,
            "path": self.path,
        }


@dataclass(frozen=True)
class PluginConnectorDescriptor:
    connector_id: str
    protocol_family: str
    capability_refs: tuple[str, ...]
    endpoint_ref: str

    def validate(self) -> None:
        _required(self.connector_id, "connector_id")
        _required(self.protocol_family, "protocol_family")
        _names(self.capability_refs, "connector.capability_refs")
        _required(self.endpoint_ref, "connector.endpoint_ref")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "connector_id": self.connector_id,
            "protocol_family": self.protocol_family,
            "capability_refs": list(self.capability_refs),
            "endpoint_ref": self.endpoint_ref,
        }


@dataclass(frozen=True)
class PluginReleaseSnapshot:
    plugin_release_ref: str
    artifacts: tuple[ArtifactReference, ...]
    skill_entrypoints: tuple[PluginSkillEntrypoint, ...]
    connectors: tuple[PluginConnectorDescriptor, ...]
    runtime_dependency_refs: tuple[str, ...]

    def validate(self) -> None:
        _required(self.plugin_release_ref, "plugin_release_ref")
        if self.plugin_release_ref != self.plugin_release_ref.strip():
            raise PluginContractError(
                "plugin_release_ref must not contain surrounding whitespace"
            )
        for artifact in self.artifacts:
            artifact.validate()
        artifact_refs = [artifact.artifact_ref for artifact in self.artifacts]
        if len(artifact_refs) != len(set(artifact_refs)):
            raise PluginContractError(
                "release artifact refs must be unique within a plugin release"
            )
        skill_names = []
        for entrypoint in self.skill_entrypoints:
            entrypoint.validate()
            if entrypoint.artifact_ref not in artifact_refs:
                raise PluginContractError(
                    "skill entrypoint must reference a declared release artifact"
                )
            skill_names.append(entrypoint.name)
        if len(skill_names) != len(set(skill_names)):
            raise PluginContractError(
                "skill entrypoint names must be unique within a plugin release"
            )
        connector_ids = []
        for connector in self.connectors:
            connector.validate()
            connector_ids.append(connector.connector_id)
        if len(connector_ids) != len(set(connector_ids)):
            raise PluginContractError(
                "connector ids must be unique within a plugin release"
            )
        _names(self.runtime_dependency_refs, "release.runtime_dependency_refs")
        if len(self.runtime_dependency_refs) != len(set(self.runtime_dependency_refs)):
            raise PluginContractError(
                "runtime dependency refs must be unique within a plugin release"
            )
        if any(ref != ref.strip() for ref in self.runtime_dependency_refs):
            raise PluginContractError(
                "runtime dependency refs must not contain surrounding whitespace"
            )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "plugin_release_ref": self.plugin_release_ref,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "skill_entrypoints": [
                entrypoint.to_dict() for entrypoint in self.skill_entrypoints
            ],
            "connectors": [connector.to_dict() for connector in self.connectors],
            "runtime_dependency_refs": list(self.runtime_dependency_refs),
        }


@dataclass(frozen=True)
class PluginViewDescriptor:
    view_ref: str
    open_operation: str

    def validate(self) -> None:
        _required(self.view_ref, "view_ref")
        _required(self.open_operation, "open_operation")

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {
            "view_ref": self.view_ref,
            "open_operation": self.open_operation,
        }


@dataclass(frozen=True)
class PluginRegistration:
    plugin_id: str
    release: PluginReleaseSnapshot
    capabilities: tuple[str, ...]
    required_scopes: tuple[str, ...]
    ui_extensions: tuple[str, ...]
    view_descriptors: tuple[PluginViewDescriptor, ...] = ()

    def validate(self) -> None:
        _required(self.plugin_id, "plugin_id")
        self.release.validate()
        _names(self.capabilities, "capabilities")
        _names(self.required_scopes, "required_scopes")
        _names(self.ui_extensions, "ui_extensions")
        view_refs = []
        for descriptor in self.view_descriptors:
            descriptor.validate()
            if descriptor.view_ref not in self.ui_extensions:
                raise PluginContractError(
                    "view descriptor must reference a declared UI extension"
                )
            view_refs.append(descriptor.view_ref)
        if len(view_refs) != len(set(view_refs)):
            raise PluginContractError("view descriptor refs must be unique")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload = {
            "plugin_id": self.plugin_id,
            "release": self.release.to_dict(),
            "capabilities": list(self.capabilities),
            "required_scopes": list(self.required_scopes),
            "ui_extensions": list(self.ui_extensions),
        }
        if self.view_descriptors:
            payload["view_descriptors"] = [
                descriptor.to_dict() for descriptor in self.view_descriptors
            ]
        return payload


@dataclass(frozen=True)
class PluginScope:
    tenant_id: str
    project_id: str
    plugin_id: str
    workflow_run_id: str

    def validate(self) -> None:
        _required(self.tenant_id, "tenant_id")
        _required(self.project_id, "project_id")
        _required(self.plugin_id, "plugin_id")
        _required(self.workflow_run_id, "workflow_run_id")

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "plugin_id": self.plugin_id,
            "workflow_run_id": self.workflow_run_id,
        }


@dataclass(frozen=True)
class ArtifactReference:
    artifact_ref: str
    digest: str
    media_type: str

    def validate(self) -> None:
        _required(self.artifact_ref, "artifact_ref")
        _required(self.media_type, "media_type")
        if not _SHA256.fullmatch(self.digest):
            raise PluginContractError("digest must be sha256:<64 hex>")

    def to_dict(self) -> dict[str, str]:
        self.validate()
        return {
            "artifact_ref": self.artifact_ref,
            "digest": self.digest,
            "media_type": self.media_type,
        }


@dataclass(frozen=True)
class PluginCommandEnvelope:
    command: str
    scope: PluginScope
    idempotency_key: str
    input_artifacts: tuple[ArtifactReference, ...]
    payload: Any

    def validate(self, registration: PluginRegistration) -> None:
        _required(self.command, "command")
        _required(self.idempotency_key, "idempotency_key")
        self.scope.validate()
        registration.validate()
        if self.scope.plugin_id != registration.plugin_id:
            raise PluginContractError("scope plugin_id does not match registration")
        for artifact in self.input_artifacts:
            artifact.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "scope": self.scope.to_dict(),
            "idempotency_key": self.idempotency_key,
            "input_artifacts": [item.to_dict() for item in self.input_artifacts],
            "payload": self.payload,
        }


@dataclass(frozen=True)
class PluginRunSubmitEnvelope:
    """Generic CodeFusion run submission envelope.

    The host owns execution state; ``payload`` remains SciRel-defined JSON.
    """

    scope: PluginScope
    idempotency_key: str
    input_artifacts: tuple[ArtifactReference, ...]
    payload: Any

    def validate(self, registration: PluginRegistration) -> None:
        _required(self.idempotency_key, "idempotency_key")
        self.scope.validate()
        registration.validate()
        if self.scope.plugin_id != registration.plugin_id:
            raise PluginContractError("scope plugin_id does not match registration")
        for artifact in self.input_artifacts:
            artifact.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope.to_dict(),
            "idempotency_key": self.idempotency_key,
            "input_artifacts": [item.to_dict() for item in self.input_artifacts],
            "payload": self.payload,
        }


@dataclass(frozen=True)
class PluginRunResult:
    """Platform run receipt returned by CodeFusion."""

    run_id: str
    plugin_release_ref: str
    attempt_no: int
    status: str
    failure_class: str | None
    result_artifact_refs: tuple[ArtifactReference, ...]
    replayed: bool = False

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "PluginRunResult":
        if not isinstance(payload, Mapping):
            raise PluginContractError("run result must be an object")
        required = {
            "run_id",
            "plugin_release_ref",
            "attempt_no",
            "status",
            "failure_class",
            "result_artifact_refs",
            "replayed",
        }
        missing = required.difference(payload)
        if missing:
            raise PluginContractError(
                "run result is missing fields: " + ", ".join(sorted(missing))
            )
        unknown = set(payload).difference(required)
        if unknown:
            raise PluginContractError(
                "run result has unknown fields: " + ", ".join(sorted(unknown))
            )
        refs = payload["result_artifact_refs"]
        if not isinstance(refs, (list, tuple)):
            raise PluginContractError("result_artifact_refs must be an array")
        parsed_refs = []
        for item in refs:
            if not isinstance(item, Mapping):
                raise PluginContractError("result artifact reference must be an object")
            parsed_refs.append(
                ArtifactReference(
                    artifact_ref=item.get("artifact_ref", ""),
                    digest=item.get("digest", ""),
                    media_type=item.get("media_type", ""),
                )
            )
        result = cls(
            run_id=_required(payload["run_id"], "run_id"),
            plugin_release_ref=_required(
                payload["plugin_release_ref"], "plugin_release_ref"
            ),
            attempt_no=payload["attempt_no"],
            status=_required(payload["status"], "status"),
            failure_class=payload["failure_class"],
            result_artifact_refs=tuple(parsed_refs),
            replayed=payload["replayed"],
        )
        result.validate()
        return result

    def validate(self) -> None:
        _required(self.run_id, "run_id")
        _required(self.plugin_release_ref, "plugin_release_ref")
        if not isinstance(self.attempt_no, int) or self.attempt_no < 1:
            raise PluginContractError("attempt_no must be a positive integer")
        if self.status not in {"running", "completed", "failed", "result_unknown"}:
            raise PluginContractError("unsupported run status")
        if self.status == "result_unknown" and (
            self.failure_class is not None or self.result_artifact_refs
        ):
            raise PluginContractError(
                "result_unknown cannot claim a failure or result artifact"
            )
        if self.status == "failed" and not self.failure_class:
            raise PluginContractError("failed run must include failure_class")
        if self.status != "failed" and self.failure_class is not None:
            raise PluginContractError("only failed run may include failure_class")
        if not isinstance(self.replayed, bool):
            raise PluginContractError("replayed must be boolean")
        for ref in self.result_artifact_refs:
            ref.validate()

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "run_id": self.run_id,
            "plugin_release_ref": self.plugin_release_ref,
            "attempt_no": self.attempt_no,
            "status": self.status,
            "failure_class": self.failure_class,
            "result_artifact_refs": [ref.to_dict() for ref in self.result_artifact_refs],
            "replayed": self.replayed,
        }


@dataclass(frozen=True)
class PluginEventEnvelope:
    event_id: str
    event_type: str
    scope: PluginScope
    correlation_id: str
    idempotency_key: str
    artifact_refs: tuple[ArtifactReference, ...]
    payload: Any

    def validate(self) -> None:
        _required(self.event_id, "event_id")
        _required(self.event_type, "event_type")
        _required(self.correlation_id, "correlation_id")
        _required(self.idempotency_key, "idempotency_key")
        self.scope.validate()
        for artifact in self.artifact_refs:
            artifact.validate()

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "scope": self.scope.to_dict(),
            "correlation_id": self.correlation_id,
            "idempotency_key": self.idempotency_key,
            "artifact_refs": [item.to_dict() for item in self.artifact_refs],
            "payload": self.payload,
        }

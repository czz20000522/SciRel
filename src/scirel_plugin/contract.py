"""Python representation of the narrow CodeFusion plugin host contract."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


class PluginContractError(ValueError):
    """Raised when a host envelope does not satisfy the public contract."""


_SHA256 = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


def _required(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PluginContractError(f"{field} is required")
    return value


def _names(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    for value in values:
        _required(value, field)
    return values


@dataclass(frozen=True)
class PluginRegistration:
    plugin_id: str
    capabilities: tuple[str, ...]
    required_scopes: tuple[str, ...]
    ui_extensions: tuple[str, ...]
    command_endpoint: str = ""
    event_endpoint: str = ""

    def validate(self) -> None:
        _required(self.plugin_id, "plugin_id")
        _names(self.capabilities, "capabilities")
        _names(self.required_scopes, "required_scopes")
        _names(self.ui_extensions, "ui_extensions")
        if self.command_endpoint:
            _required(self.command_endpoint, "command_endpoint")
        if self.event_endpoint:
            _required(self.event_endpoint, "event_endpoint")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload = {
            "plugin_id": self.plugin_id,
            "capabilities": list(self.capabilities),
            "required_scopes": list(self.required_scopes),
            "ui_extensions": list(self.ui_extensions),
        }
        if self.command_endpoint:
            payload["command_endpoint"] = self.command_endpoint
        if self.event_endpoint:
            payload["event_endpoint"] = self.event_endpoint
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
        if not isinstance(self.attempt_no, int) or self.attempt_no < 1:
            raise PluginContractError("attempt_no must be a positive integer")
        if self.status not in {"running", "completed", "failed"}:
            raise PluginContractError("unsupported run status")
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

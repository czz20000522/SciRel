"""Minimal CodeFusion host adapter for the SciRel development workflow."""

from .contract import (
    ArtifactReference,
    PluginConnectorDescriptor,
    PluginCommandEnvelope,
    PluginContractError,
    PluginEventEnvelope,
    PluginRegistration,
    PluginReviewerEntryDescriptor,
    PluginReviewerIntakeDescriptor,
    PluginReleaseSnapshot,
    PluginRunResult,
    PluginRunSubmitEnvelope,
    PluginSkillEntrypoint,
    PluginScope,
    PluginViewDescriptor,
)
from .host import ArtifactRef, FakeHost, HostServices, JobRef, ReviewView
from .plugin import PluginReleaseResult, PluginReviewResult, SciRelPlugin
from .body_runner import execute_automated_check
from .adapter import (
    BODY_OPERATIONS,
    SERVICE_PRINCIPAL_SCOPES,
    SciRelBodyImportRequest,
    SciRelBodyImportResponse,
    execute_body_import,
    execute_body_import_wire,
    validate_review_item_detail_body,
)
from .http_listener import (
    DEFAULT_MAX_BODY_BYTES,
    DEFAULT_PATH,
    create_server,
    create_server_ssl_context,
    make_handler,
)
from scirel_workflow import AutomatedCheckResult

__all__ = [
    "ArtifactReference",
    "ArtifactRef",
    "PluginConnectorDescriptor",
    "FakeHost",
    "HostServices",
    "JobRef",
    "PluginCommandEnvelope",
    "PluginContractError",
    "PluginEventEnvelope",
    "PluginRegistration",
    "PluginReviewerEntryDescriptor",
    "PluginReviewerIntakeDescriptor",
    "PluginReleaseSnapshot",
    "PluginRunResult",
    "PluginRunSubmitEnvelope",
    "PluginSkillEntrypoint",
    "PluginScope",
    "PluginViewDescriptor",
    "ReviewView",
    "PluginReviewResult",
    "PluginReleaseResult",
    "SciRelPlugin",
    "AutomatedCheckResult",
    "execute_automated_check",
    "BODY_OPERATIONS",
    "SERVICE_PRINCIPAL_SCOPES",
    "SciRelBodyImportRequest",
    "SciRelBodyImportResponse",
    "execute_body_import",
    "execute_body_import_wire",
    "validate_review_item_detail_body",
    "DEFAULT_MAX_BODY_BYTES",
    "DEFAULT_PATH",
    "create_server",
    "create_server_ssl_context",
    "make_handler",
]

"""Development workflow records for the SciRel asset lifecycle.

The records are deliberately small and JSON-compatible.  They are development
contracts, not a second scientific asset schema and not a database model.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping
from uuid import uuid4


class WorkflowStatus(str, Enum):
    CANDIDATE = "candidate"
    AUTOMATED_CHECKING = "automated_checking"
    AUTOMATED_READY = "automated_ready"
    AUTOMATED_REJECTED = "automated_rejected"
    DRAFT = "draft"
    REVIEW_PENDING = "review_pending"
    REVIEW_IN_PROGRESS = "review_in_progress"
    APPROVED = "approved"
    RELEASED = "released"
    NEEDS_EVIDENCE = "needs_evidence"
    REWORK_REQUESTED = "rework_requested"
    REJECTED = "rejected"


class ReviewOutcome(str, Enum):
    APPROVED = "approved"
    NEEDS_EVIDENCE = "needs_evidence"
    REWORK_REQUESTED = "rework_requested"
    REJECTED = "rejected"


class AutomatedNextAction(str, Enum):
    READY = "ready"
    RETRY = "retry"
    REWORK_REQUESTED = "rework_requested"
    NEEDS_EVIDENCE = "needs_evidence"
    REJECTED = "rejected"


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def new_run_id() -> str:
    return "run-" + uuid4().hex


_ASSET_DOCUMENT_REQUIRED_FIELDS = frozenset({
    "schema",
    "asset_id",
    "kind",
    "title",
    "summary",
    "taxonomy",
    "aliases",
    "identity",
    "inputs",
    "outputs",
    "applicability",
    "failure_semantics",
    "provenance",
    "public_api",
    "version",
    "example",
    "verification",
})
_ASSET_DOCUMENT_ALLOWED_FIELDS = _ASSET_DOCUMENT_REQUIRED_FIELDS | {"graph"}
_ASSET_DOCUMENT_PRIVATE_FIELDS = frozenset({
    "admission_ref",
    "case_ref",
    "decision_ref",
    "tenant_id",
    "candidate_ref",
    "version_commit_ref",
    "source_project_path",
    "job_id",
    "attempt_id",
    "session_id",
    "credential_ref",
})


def scientific_contract_gaps(
    assets: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> tuple[str, ...]:
    """Describe top-level v1 contract defects without guessing their values.

    Full nested scientific validation remains the release validator's job.
    These gaps keep incomplete standardization visible and non-releasable.
    """

    gaps: list[str] = []

    def private_paths(value: Any, path: str = "") -> list[str]:
        found: list[str] = []
        if isinstance(value, Mapping):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                if key in _ASSET_DOCUMENT_PRIVATE_FIELDS:
                    found.append(child_path)
                found.extend(private_paths(child, child_path))
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                found.extend(private_paths(child, f"{path}[{index}]"))
        return found

    for index, asset in enumerate(assets):
        asset_id = asset.get("asset_id")
        label = asset_id if isinstance(asset_id, str) and asset_id else f"asset[{index}]"
        for field in sorted(_ASSET_DOCUMENT_REQUIRED_FIELDS.difference(asset)):
            gaps.append(f"scientific_contract_missing:{label}:{field}")
        for field in sorted(set(asset).difference(_ASSET_DOCUMENT_ALLOWED_FIELDS)):
            gaps.append(f"scientific_contract_unknown:{label}:{field}")
        if "schema" in asset and asset.get("schema") != "scirel.asset-document.v1":
            gaps.append(f"scientific_contract_schema:{label}")
        for path in private_paths(asset):
            gaps.append(f"scientific_contract_private:{label}:{path}")
    return tuple(dict.fromkeys(gaps))


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _digest_text(value: Any, field: str) -> str:
    value = _text(value, field)
    hex_part = value.removeprefix("sha256:")
    if len(hex_part) != 64 or not value.startswith("sha256:") or not all(
        char in "0123456789abcdefABCDEF" for char in hex_part
    ):
        raise ValueError(f"{field} must be sha256:<64 hex>")
    return value


def _records(value: Any, field: str) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be an array")
    records = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"{field}[{index}] must be an object")
        records.append(dict(item))
    return tuple(records)


def _strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be an array")
    values = tuple(_text(item, f"{field}[{index}]") for index, item in enumerate(value))
    if len(values) != len(set(values)):
        raise ValueError(f"{field} must not contain duplicates")
    return values


def _single_project_id(payload: Mapping[str, Any], assets: Any) -> str:
    """Return the one project represented by an L1 payload.

    Inventory batches must be split with ``to_project_l1_payloads`` before
    candidate creation.  Payloads without project metadata remain valid for
    generic development fixtures and carry an empty project id.
    """

    project_ids: list[str] = []

    for field in ("project_id", "project"):
        value = payload.get(field)
        if value is not None and value != "":
            project_ids.append(_text(value, field))

    projects = payload.get("projects")
    if projects is not None:
        if not isinstance(projects, (list, tuple)):
            raise ValueError("L1 payload projects must be an array")
        for index, project in enumerate(projects):
            if not isinstance(project, Mapping):
                raise ValueError(f"L1 payload projects[{index}] must be an object")
            value = project.get("project_id", project.get("project"))
            if value is not None and value != "":
                project_ids.append(_text(value, f"projects[{index}].project_id"))

    if isinstance(assets, (list, tuple)):
        for index, asset in enumerate(assets):
            if not isinstance(asset, Mapping):
                continue
            value = asset.get("project_id")
            if value is not None and value != "":
                project_ids.append(_text(value, f"assets[{index}].project_id"))

    unique = tuple(dict.fromkeys(project_ids))
    if len(unique) > 1:
        raise ValueError(
            "L1 payload must contain one project; split the inventory with "
            "to_project_l1_payloads"
        )
    return unique[0] if unique else ""


def _dependency_cycles_from_assets(assets: list[dict[str, Any]]) -> tuple[str, ...]:
    """Find cycles in the task-graph portion of an L1 asset projection."""

    known = {
        str(asset.get("asset_path")).rstrip("/")
        for asset in assets
        if asset.get("asset_path")
    }
    graph = {
        str(asset["asset_path"]).rstrip("/"): tuple(
            str(reference).rstrip("/")
            for reference in asset.get("dependency_refs", ())
            if isinstance(reference, str)
            and reference.startswith("task_graphs/")
            and reference.rstrip("/") in known
        )
        for asset in assets
        if asset.get("asset_path")
        and asset.get("asset_kind") == "task_graph"
    }
    cycles: set[str] = set()
    visiting: list[str] = []
    active: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in active:
            start = visiting.index(node)
            cycle = (*visiting[start:], node)
            rotations = [
                cycle[index:-1] + cycle[:index] + (cycle[index],)
                for index in range(len(cycle) - 1)
            ]
            cycles.add(" -> ".join(min(rotations)))
            return
        if node in visited:
            return
        active.add(node)
        visiting.append(node)
        for dependency in graph.get(node, ()):
            visit(dependency)
        visiting.pop()
        active.remove(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node)
    return tuple(sorted(cycles))


@dataclass
class CandidatePackage:
    """A candidate produced from one L1 run."""

    run_id: str
    source_artifact_ref: str
    source_digest: str
    assets: tuple[dict[str, Any], ...]
    automated_checks: tuple[dict[str, Any], ...]
    project_id: str = ""
    gaps: tuple[str, ...] = ()
    status: WorkflowStatus = WorkflowStatus.CANDIDATE
    candidate_id: str = ""
    automated_next_action: str = ""

    def __post_init__(self) -> None:
        self.run_id = _text(self.run_id, "run_id")
        self.source_artifact_ref = _text(self.source_artifact_ref, "source_artifact_ref")
        self.source_digest = _text(self.source_digest, "source_digest")
        self.assets = _records(self.assets, "assets")
        self.automated_checks = _records(self.automated_checks, "automated_checks")
        if self.project_id is None:
            self.project_id = ""
        elif not isinstance(self.project_id, str):
            raise ValueError("project_id must be a string")
        elif self.project_id:
            self.project_id = _text(self.project_id, "project_id")
        self.gaps = _strings(self.gaps, "gaps")
        self.gaps = tuple(dict.fromkeys((
            *self.gaps,
            *self._inventory_gaps(list(self.assets)),
        )))
        if not self.candidate_id:
            self.candidate_id = f"candidate-{self.run_id}"
        self.candidate_id = _text(self.candidate_id, "candidate_id")
        if not isinstance(self.status, WorkflowStatus):
            self.status = WorkflowStatus(self.status)
        if self.automated_next_action:
            self.automated_next_action = AutomatedNextAction(
                self.automated_next_action
            ).value

    @classmethod
    def from_l1(
        cls,
        payload: Mapping[str, Any],
        *,
        source_artifact_ref: str,
        source_digest: str | None = None,
        run_id: str | None = None,
    ) -> "CandidatePackage":
        if not isinstance(payload, Mapping):
            raise ValueError("L1 payload must be an object")
        assets = payload.get("assets", [])
        checks = payload.get("automated_checks", [])
        gaps = payload.get("gaps", [])
        project_id = _single_project_id(payload, assets)
        payload_digest = source_digest or digest(payload)
        return cls(
            run_id=run_id or new_run_id(),
            source_artifact_ref=source_artifact_ref,
            source_digest=payload_digest,
            assets=tuple(assets),
            automated_checks=tuple(checks),
            project_id=project_id,
            gaps=tuple(gaps),
            automated_next_action=str(payload.get("automated_next_action") or ""),
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CandidatePackage":
        if not isinstance(payload, Mapping):
            raise ValueError("candidate package must be an object")
        required = {
            "schema",
            "candidate_id",
            "run_id",
            "source_artifact_ref",
            "source_digest",
            "project_id",
            "assets",
            "automated_checks",
            "gaps",
            "status",
            "automated_next_action",
        }
        missing = required.difference(payload)
        if missing:
            raise ValueError(
                "candidate package is missing fields: " + ", ".join(sorted(missing))
            )
        unknown = set(payload).difference(required)
        if unknown:
            raise ValueError(
                "candidate package has unknown fields: " + ", ".join(sorted(unknown))
            )
        if payload["schema"] != "scirel.candidate-package.dev":
            raise ValueError(f"unsupported candidate package schema: {payload['schema']}")
        if payload["status"] != WorkflowStatus.CANDIDATE.value:
            raise ValueError("candidate package status must be candidate")
        project_id = payload["project_id"]
        if not isinstance(project_id, str):
            raise ValueError("project_id must be a string")
        next_action = payload["automated_next_action"]
        if not isinstance(next_action, str):
            raise ValueError("automated_next_action must be a string")
        return cls(
            candidate_id=_text(payload["candidate_id"], "candidate_id"),
            run_id=_text(payload["run_id"], "run_id"),
            source_artifact_ref=_text(
                payload["source_artifact_ref"], "source_artifact_ref"
            ),
            source_digest=_text(payload["source_digest"], "source_digest"),
            project_id=project_id,
            assets=payload["assets"],
            automated_checks=payload["automated_checks"],
            gaps=payload["gaps"],
            status=WorkflowStatus.CANDIDATE,
            automated_next_action=next_action,
        )

    @property
    def automated_ready(self) -> bool:
        return (
            bool(self.automated_checks)
            and not self.gaps
            and self.automated_next_action in ("", AutomatedNextAction.READY.value)
            and all(check.get("status") == "passed" for check in self.automated_checks)
        )

    @property
    def automated_failed(self) -> bool:
        return bool(self.gaps) or any(
            check.get("status") == "failed" for check in self.automated_checks
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "scirel.candidate-package.dev",
            "candidate_id": self.candidate_id,
            "run_id": self.run_id,
            "source_artifact_ref": self.source_artifact_ref,
            "source_digest": self.source_digest,
            "project_id": self.project_id,
            "assets": list(self.assets),
            "automated_checks": list(self.automated_checks),
            "gaps": list(self.gaps),
            "status": self.status.value,
            "automated_next_action": self.automated_next_action,
        }

    @property
    def package_digest(self) -> str:
        return digest(self.to_dict())

    def apply_automated_result(
        self, result: "AutomatedCheckResult"
    ) -> "CandidatePackage":
        """Return a candidate annotated by a matching deterministic check run."""

        if result.candidate_id != self.candidate_id:
            raise ValueError("automated result refers to a different candidate")
        if result.source_digest != self.source_digest:
            raise ValueError("automated result source digest does not match candidate")
        assets = [dict(asset) for asset in self.assets]
        derived_gaps = self._inventory_gaps(assets)
        gaps = tuple(dict.fromkeys((*self.gaps, *result.gaps, *derived_gaps)))
        checks = [dict(check) for check in self.automated_checks]
        checks_by_name = {
            check.get("name"): index
            for index, check in enumerate(checks)
            if check.get("name")
        }
        for check in result.checks:
            name = check.get("name")
            if name and name in checks_by_name:
                checks[checks_by_name[name]] = dict(check)
            else:
                checks.append(dict(check))
        checks_passed = bool(checks) and all(
            check.get("status") == "passed" for check in checks
        )
        return CandidatePackage(
            run_id=self.run_id,
            source_artifact_ref=self.source_artifact_ref,
            source_digest=self.source_digest,
            assets=tuple(assets),
            automated_checks=tuple(checks),
            project_id=self.project_id,
            gaps=gaps,
            status=WorkflowStatus.CANDIDATE,
            candidate_id=self.candidate_id,
            automated_next_action=(
                result.next_action
                if result.next_action != AutomatedNextAction.READY.value
                else (
                    AutomatedNextAction.READY.value
                    if checks_passed and not gaps
                    else AutomatedNextAction.RETRY.value
                )
            ),
        )

    @staticmethod
    def _inventory_gaps(assets: list[dict[str, Any]]) -> tuple[str, ...]:
        """Recheck L1 inventory gaps that must not be self-reported away.

        The check is deliberately limited to the inventory fields. Generic
        candidates may omit these fields and are left to their declared checks.
        """

        gaps: list[str] = []
        known_paths = {
            str(asset.get("asset_path")).rstrip("/")
            for asset in assets
            if asset.get("asset_path")
        }
        for asset in assets:
            asset_id = asset.get("l1_asset_id") or asset.get("candidate_asset_id")
            if not asset_id:
                continue
            for field in ("contract_path", "implementation_path", "direct_test_path"):
                if field in asset and not asset.get(field):
                    if field == "direct_test_path":
                        gaps.append(f"missing_direct_test_mapping:{asset_id}")
                    else:
                        gaps.append(f"missing_l1_asset_file:{asset_id}:{field}")
            for reference in asset.get("dependency_refs", ()):
                if (
                    isinstance(reference, str)
                    and (reference.startswith("operators/") or reference.startswith("task_graphs/"))
                    and reference.rstrip("/") not in known_paths
                ):
                    gaps.append(
                        f"unresolved_task_graph_dependency:{asset_id} -> {reference}"
                    )
                elif (
                    isinstance(reference, str)
                    and asset.get("asset_path")
                    and reference not in {"null", "Null", "NULL", "~"}
                    and not (
                        reference.startswith("operators/")
                        or reference.startswith("task_graphs/")
                    )
                ):
                    gaps.append(
                        f"invalid_task_graph_dependency_ref:{asset_id} -> {reference}"
                    )
        for cycle in _dependency_cycles_from_assets(assets):
            gaps.append(f"task_graph_cycle:{cycle}")
        return tuple(dict.fromkeys(gaps))


@dataclass
class AutomatedCheckResult:
    """Result returned by a host-executed deterministic check run."""

    result_id: str
    candidate_id: str
    source_digest: str
    checks: tuple[dict[str, Any], ...]
    gaps: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    next_action: str = ""

    def __post_init__(self) -> None:
        self.result_id = _text(self.result_id, "result_id")
        self.candidate_id = _text(self.candidate_id, "candidate_id")
        self.source_digest = _text(self.source_digest, "source_digest")
        self.checks = _records(self.checks, "checks")
        self.gaps = _strings(self.gaps, "gaps")
        self.evidence_refs = _strings(self.evidence_refs, "evidence_refs")
        if not self.next_action:
            self.next_action = (
                AutomatedNextAction.READY.value
                if self.passed
                else AutomatedNextAction.RETRY.value
            )
        else:
            self.next_action = AutomatedNextAction(self.next_action).value

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "AutomatedCheckResult":
        if not isinstance(payload, Mapping):
            raise ValueError("automated check result must be an object")
        expected_schema = "scirel.automated-check-result.dev"
        required = {
            "schema",
            "result_id",
            "candidate_id",
            "source_digest",
            "checks",
            "gaps",
            "evidence_refs",
            "status",
            "next_action",
        }
        missing = required.difference(payload)
        if missing:
            raise ValueError(
                "automated check result is missing fields: "
                + ", ".join(sorted(missing))
            )
        unknown = set(payload).difference(required)
        if unknown:
            raise ValueError(
                "automated check result has unknown fields: "
                + ", ".join(sorted(unknown))
            )
        if payload["schema"] != expected_schema:
            raise ValueError(f"unsupported automated result schema: {payload['schema']}")
        checks = _records(payload["checks"], "checks")
        gaps = _strings(payload["gaps"], "gaps")
        expected_status = "passed" if all(
            check.get("status") == "passed" for check in checks
        ) and bool(checks) and not gaps else "failed"
        if payload["status"] != expected_status:
            raise ValueError("automated check result status does not match checks and gaps")
        return cls(
            result_id=_text(payload.get("result_id"), "result_id"),
            candidate_id=_text(payload.get("candidate_id"), "candidate_id"),
            source_digest=_text(payload.get("source_digest"), "source_digest"),
            checks=tuple(checks),
            gaps=tuple(gaps),
            evidence_refs=tuple(payload.get("evidence_refs", ())),
            next_action=str(payload.get("next_action", "")),
        )

    @property
    def passed(self) -> bool:
        return bool(self.checks) and not self.gaps and all(
            check.get("status") == "passed" for check in self.checks
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "scirel.automated-check-result.dev",
            "result_id": self.result_id,
            "candidate_id": self.candidate_id,
            "source_digest": self.source_digest,
            "checks": list(self.checks),
            "gaps": list(self.gaps),
            "evidence_refs": list(self.evidence_refs),
            "next_action": self.next_action,
            "status": "passed" if self.passed else "failed",
        }

    @property
    def result_digest(self) -> str:
        return digest(self.to_dict())


_STANDARDIZATION_DISPOSITIONS = frozenset({
    "reuse",
    "exact_duplicate",
    "semantic_equivalence",
    "subsumes",
    "overlaps",
    "parameterized_variant",
    "lossless_adapter",
    "composition",
    "new_capability",
    "conflict",
    "unresolved",
})


def _exact_record(
    value: Any,
    field: str,
    *,
    required: set[str],
    optional: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    record = dict(value)
    missing = required.difference(record)
    unknown = set(record).difference(required | (optional or set()))
    if missing:
        raise ValueError(f"{field} is missing fields: " + ", ".join(sorted(missing)))
    if unknown:
        raise ValueError(f"{field} has unknown fields: " + ", ".join(sorted(unknown)))
    return record


def _verify_embedded_digest(record: Mapping[str, Any], field: str) -> None:
    supplied = _digest_text(record.get("digest"), f"{field}.digest")
    try:
        expected = digest({key: value for key, value in record.items() if key != "digest"})
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must contain JSON-compatible content") from error
    if supplied != expected:
        raise ValueError(f"{field}.digest does not match its content")


def _producer_record(value: Any) -> dict[str, Any]:
    producer = _exact_record(
        value,
        "producer",
        required={"harness", "model", "skill"},
    )
    for field in ("harness", "model"):
        entry = _exact_record(
            producer[field],
            f"producer.{field}",
            required={"name", "version"},
        )
        entry["name"] = _text(entry["name"], f"producer.{field}.name")
        entry["version"] = _text(entry["version"], f"producer.{field}.version")
        producer[field] = entry
    skill = _exact_record(
        producer["skill"],
        "producer.skill",
        required={"name", "version", "digest"},
    )
    skill["name"] = _text(skill["name"], "producer.skill.name")
    skill["version"] = _text(skill["version"], "producer.skill.version")
    skill["digest"] = _digest_text(skill["digest"], "producer.skill.digest")
    producer["skill"] = skill
    return producer


@dataclass
class StandardizationReviewUnit:
    """One exact document/code/test proposal prepared by a model run."""

    review_unit_id: str
    source_asset_ids: tuple[str, ...]
    disposition: str
    asset_document: dict[str, Any]
    candidate_document: dict[str, Any]
    candidate_code: dict[str, Any]
    candidate_tests: dict[str, Any]
    dependency_asset_ids: tuple[str, ...]
    evidence: tuple[dict[str, Any], ...] = ()
    gaps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.review_unit_id = _text(self.review_unit_id, "review_unit_id")
        self.source_asset_ids = _strings(self.source_asset_ids, "source_asset_ids")
        if not self.source_asset_ids:
            raise ValueError("source_asset_ids must not be empty")
        self.disposition = _text(self.disposition, "disposition")
        if self.disposition not in _STANDARDIZATION_DISPOSITIONS:
            raise ValueError(f"unsupported standardization disposition: {self.disposition}")
        if not isinstance(self.asset_document, Mapping):
            raise ValueError("asset_document must be an object")
        self.asset_document = dict(self.asset_document)
        _text(self.asset_document.get("asset_id"), "asset_document.asset_id")

        self.candidate_document = _exact_record(
            self.candidate_document,
            "candidate_document",
            required={"content", "digest"},
        )
        _text(self.candidate_document["content"], "candidate_document.content")
        _verify_embedded_digest(self.candidate_document, "candidate_document")

        self.candidate_code = _exact_record(
            self.candidate_code,
            "candidate_code",
            required={"kind", "content", "rationale", "digest"},
        )
        code_kind = _text(self.candidate_code["kind"], "candidate_code.kind")
        if code_kind not in {"patch", "files", "none"}:
            raise ValueError("candidate_code.kind must be patch, files, or none")
        if not isinstance(self.candidate_code["rationale"], str):
            raise ValueError("candidate_code.rationale must be a string")
        if code_kind == "none":
            if self.candidate_code["content"] is not None:
                raise ValueError("candidate_code.content must be null when kind is none")
            _text(self.candidate_code["rationale"], "candidate_code.rationale")
        elif self.candidate_code["content"] in (None, "", [], {}):
            raise ValueError("candidate_code.content must not be empty")
        _verify_embedded_digest(self.candidate_code, "candidate_code")

        self.candidate_tests = _exact_record(
            self.candidate_tests,
            "candidate_tests",
            required={"content", "commands", "results", "digest"},
        )
        if self.candidate_tests["content"] in (None, "", [], {}):
            raise ValueError("candidate_tests.content must not be empty")
        commands = _records(self.candidate_tests["commands"], "candidate_tests.commands")
        results = _records(self.candidate_tests["results"], "candidate_tests.results")
        if not commands or not results:
            raise ValueError("candidate_tests must include commands and observed results")
        self.candidate_tests["commands"] = list(commands)
        self.candidate_tests["results"] = list(results)
        _verify_embedded_digest(self.candidate_tests, "candidate_tests")

        self.dependency_asset_ids = _strings(
            self.dependency_asset_ids, "dependency_asset_ids"
        )
        version = self.asset_document.get("version")
        document_dependencies = ()
        if isinstance(version, Mapping) and isinstance(
            version.get("dependencies"), (list, tuple)
        ):
            document_dependencies = tuple(
                dependency.get("asset_id")
                for dependency in version["dependencies"]
                if isinstance(dependency, Mapping)
                and isinstance(dependency.get("asset_id"), str)
                and dependency.get("asset_id")
            )
        if set(document_dependencies) != set(self.dependency_asset_ids):
            raise ValueError(
                "dependency_asset_ids must match asset_document version dependencies"
            )
        self.evidence = _records(self.evidence, "evidence")
        self.gaps = _strings(self.gaps, "gaps")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "StandardizationReviewUnit":
        record = _exact_record(
            payload,
            "review_unit",
            required={
                "review_unit_id",
                "source_asset_ids",
                "disposition",
                "asset_document",
                "candidate_document",
                "candidate_code",
                "candidate_tests",
                "dependency_asset_ids",
                "evidence",
                "gaps",
            },
        )
        return cls(
            review_unit_id=record["review_unit_id"],
            source_asset_ids=tuple(record["source_asset_ids"]),
            disposition=record["disposition"],
            asset_document=dict(record["asset_document"]),
            candidate_document=dict(record["candidate_document"]),
            candidate_code=dict(record["candidate_code"]),
            candidate_tests=dict(record["candidate_tests"]),
            dependency_asset_ids=tuple(record["dependency_asset_ids"]),
            evidence=tuple(record["evidence"]),
            gaps=tuple(record["gaps"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_unit_id": self.review_unit_id,
            "source_asset_ids": list(self.source_asset_ids),
            "disposition": self.disposition,
            "asset_document": dict(self.asset_document),
            "candidate_document": dict(self.candidate_document),
            "candidate_code": dict(self.candidate_code),
            "candidate_tests": dict(self.candidate_tests),
            "dependency_asset_ids": list(self.dependency_asset_ids),
            "evidence": list(self.evidence),
            "gaps": list(self.gaps),
        }


@dataclass
class StandardizationSubmission:
    """Digest-bound model output accepted by the deterministic review gate."""

    submission_id: str
    draft_id: str
    candidate_id: str
    candidate_digest: str
    source_digest: str
    scirel_git_base: str
    candidate_pool_ref: str
    candidate_pool_digest: str
    producer: dict[str, Any]
    review_units: tuple[StandardizationReviewUnit, ...]
    run_evidence: tuple[dict[str, Any], ...] = ()
    gaps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.submission_id = _text(self.submission_id, "submission_id")
        self.draft_id = _text(self.draft_id, "draft_id")
        self.candidate_id = _text(self.candidate_id, "candidate_id")
        self.candidate_digest = _digest_text(self.candidate_digest, "candidate_digest")
        self.source_digest = _digest_text(self.source_digest, "source_digest")
        self.scirel_git_base = _text(self.scirel_git_base, "scirel_git_base")
        if len(self.scirel_git_base) not in {40, 64} or not all(
            char in "0123456789abcdefABCDEF" for char in self.scirel_git_base
        ):
            raise ValueError("scirel_git_base must be a full Git commit id")
        self.candidate_pool_ref = _text(self.candidate_pool_ref, "candidate_pool_ref")
        self.candidate_pool_digest = _digest_text(
            self.candidate_pool_digest, "candidate_pool_digest"
        )
        self.producer = _producer_record(self.producer)
        units: list[StandardizationReviewUnit] = []
        for index, unit in enumerate(self.review_units):
            try:
                units.append(
                    unit
                    if isinstance(unit, StandardizationReviewUnit)
                    else StandardizationReviewUnit.from_mapping(unit)
                )
            except (TypeError, ValueError) as error:
                raise ValueError(f"review_units[{index}] is invalid: {error}") from error
        if not units:
            raise ValueError("review_units must not be empty")
        self.review_units = tuple(units)
        unit_ids = [unit.review_unit_id for unit in units]
        asset_ids = [str(unit.asset_document["asset_id"]) for unit in units]
        if len(unit_ids) != len(set(unit_ids)):
            raise ValueError("review_unit_id values must be unique")
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("review unit asset_id values must be unique")
        self.run_evidence = _records(self.run_evidence, "run_evidence")
        self.gaps = _strings(self.gaps, "gaps")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "StandardizationSubmission":
        record = _exact_record(
            payload,
            "standardization submission",
            required={
                "schema",
                "submission_id",
                "draft_id",
                "candidate_id",
                "candidate_digest",
                "source_digest",
                "scirel_git_base",
                "candidate_pool_ref",
                "candidate_pool_digest",
                "producer",
                "review_units",
                "run_evidence",
                "gaps",
            },
        )
        if record["schema"] != "scirel.standardization-submission.dev":
            raise ValueError(
                "unsupported standardization submission schema: "
                + str(record["schema"])
            )
        if not isinstance(record["review_units"], (list, tuple)):
            raise ValueError("review_units must be an array")
        return cls(
            submission_id=record["submission_id"],
            draft_id=record["draft_id"],
            candidate_id=record["candidate_id"],
            candidate_digest=record["candidate_digest"],
            source_digest=record["source_digest"],
            scirel_git_base=record["scirel_git_base"],
            candidate_pool_ref=record["candidate_pool_ref"],
            candidate_pool_digest=record["candidate_pool_digest"],
            producer=dict(record["producer"]),
            review_units=tuple(record["review_units"]),
            run_evidence=tuple(record["run_evidence"]),
            gaps=tuple(record["gaps"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "scirel.standardization-submission.dev",
            "submission_id": self.submission_id,
            "draft_id": self.draft_id,
            "candidate_id": self.candidate_id,
            "candidate_digest": self.candidate_digest,
            "source_digest": self.source_digest,
            "scirel_git_base": self.scirel_git_base,
            "candidate_pool_ref": self.candidate_pool_ref,
            "candidate_pool_digest": self.candidate_pool_digest,
            "producer": dict(self.producer),
            "review_units": [unit.to_dict() for unit in self.review_units],
            "run_evidence": list(self.run_evidence),
            "gaps": list(self.gaps),
        }

    @property
    def submission_digest(self) -> str:
        return digest(self.to_dict())


@dataclass
class StandardizedDraft:
    """A SciRel standardization result awaiting expert review."""

    draft_id: str
    candidate_id: str
    assets: tuple[dict[str, Any], ...]
    dependency_asset_ids: tuple[str, ...]
    evidence: tuple[dict[str, Any], ...]
    gaps: tuple[str, ...] = ()
    status: WorkflowStatus = WorkflowStatus.DRAFT

    def __post_init__(self) -> None:
        self.draft_id = _text(self.draft_id, "draft_id")
        self.candidate_id = _text(self.candidate_id, "candidate_id")
        self.assets = _records(self.assets, "assets")
        self.dependency_asset_ids = _strings(
            self.dependency_asset_ids, "dependency_asset_ids"
        )
        self.evidence = _records(self.evidence, "evidence")
        self.gaps = _strings(self.gaps, "gaps")
        self.gaps = tuple(dict.fromkeys((
            *self.gaps,
            *scientific_contract_gaps(list(self.assets)),
        )))
        if not isinstance(self.status, WorkflowStatus):
            self.status = WorkflowStatus(self.status)
        if self.gaps and self.status in (
            WorkflowStatus.APPROVED,
            WorkflowStatus.RELEASED,
        ):
            raise ValueError("a draft with unresolved gaps cannot be approved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "scirel.standardized-draft.dev",
            "draft_id": self.draft_id,
            "candidate_id": self.candidate_id,
            "assets": list(self.assets),
            "dependency_asset_ids": list(self.dependency_asset_ids),
            "evidence": list(self.evidence),
            "gaps": list(self.gaps),
            "status": self.status.value,
        }

    @property
    def draft_digest(self) -> str:
        return digest(self.to_dict())


@dataclass
class ReviewDecision:
    draft_id: str
    outcome: ReviewOutcome
    reviewer: str
    notes: str = ""

    def __post_init__(self) -> None:
        self.draft_id = _text(self.draft_id, "draft_id")
        if not isinstance(self.outcome, ReviewOutcome):
            self.outcome = ReviewOutcome(self.outcome)
        self.reviewer = _text(self.reviewer, "reviewer")
        if not isinstance(self.notes, str):
            raise ValueError("notes must be a string")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "scirel.review-decision.dev",
            "draft_id": self.draft_id,
            "outcome": self.outcome.value,
            "reviewer": self.reviewer,
            "notes": self.notes,
        }


@dataclass
class ReleaseManifest:
    """A development release produced after an approved draft."""

    release_id: str
    draft_id: str
    approved_assets: tuple[str, ...]
    catalog_ref: str
    catalog_digest: str
    wheel_ref: str
    wheel_digest: str
    candidate_id: str
    candidate_digest: str
    draft_digest: str
    release_version: str

    def __post_init__(self) -> None:
        self.release_id = _text(self.release_id, "release_id")
        self.draft_id = _text(self.draft_id, "draft_id")
        self.approved_assets = _strings(self.approved_assets, "approved_assets")
        self.catalog_ref = _text(self.catalog_ref, "catalog_ref")
        self.catalog_digest = _digest_text(self.catalog_digest, "catalog_digest")
        self.wheel_ref = _text(self.wheel_ref, "wheel_ref")
        self.wheel_digest = _digest_text(self.wheel_digest, "wheel_digest")
        self.candidate_id = _text(self.candidate_id, "candidate_id")
        self.candidate_digest = _digest_text(self.candidate_digest, "candidate_digest")
        self.draft_digest = _digest_text(self.draft_digest, "draft_digest")
        self.release_version = _text(self.release_version, "release_version")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ReleaseManifest":
        if not isinstance(payload, Mapping):
            raise ValueError("release manifest must be an object")
        required = {
            "schema",
            "release_id",
            "draft_id",
            "approved_assets",
            "catalog_ref",
            "catalog_digest",
            "wheel_ref",
            "wheel_digest",
            "candidate_id",
            "candidate_digest",
            "draft_digest",
            "release_version",
        }
        missing = required.difference(payload)
        if missing:
            raise ValueError(
                "release manifest is missing fields: " + ", ".join(sorted(missing))
            )
        unknown = set(payload).difference(required)
        if unknown:
            raise ValueError(
                "release manifest has unknown fields: " + ", ".join(sorted(unknown))
            )
        if payload["schema"] != "scirel.release-manifest.dev":
            raise ValueError(f"unsupported release manifest schema: {payload['schema']}")
        return cls(
            release_id=payload["release_id"],
            draft_id=payload["draft_id"],
            approved_assets=payload["approved_assets"],
            catalog_ref=payload["catalog_ref"],
            catalog_digest=payload["catalog_digest"],
            wheel_ref=payload["wheel_ref"],
            wheel_digest=payload["wheel_digest"],
            candidate_id=payload["candidate_id"],
            candidate_digest=payload["candidate_digest"],
            draft_digest=payload["draft_digest"],
            release_version=payload["release_version"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "scirel.release-manifest.dev",
            "release_id": self.release_id,
            "draft_id": self.draft_id,
            "approved_assets": list(self.approved_assets),
            "catalog_ref": self.catalog_ref,
            "catalog_digest": self.catalog_digest,
            "wheel_ref": self.wheel_ref,
            "wheel_digest": self.wheel_digest,
            "candidate_id": self.candidate_id,
            "candidate_digest": self.candidate_digest,
            "draft_digest": self.draft_digest,
            "release_version": self.release_version,
        }

    @property
    def release_digest(self) -> str:
        return digest(self.to_dict())

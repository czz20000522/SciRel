from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import string
from pathlib import Path
from typing import Any

MAX_PROGRESS_JSON_BYTES = 10 * 1024 * 1024
CACHE_DIRECTORY_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
REPORT_ONLY_ROOT_FILES = {
    "extraction_report.md",
    "extraction_ledger.md",
    "program_framework_map.md",
}


def _is_package_document(relative: str) -> bool:
    parts = relative.split("/")
    return len(parts) == 3 and (
        (parts[0] == "operators" and parts[2] == "operator.md")
        or (parts[0] == "task_graphs" and parts[2] == "task_graph.md")
    )

ANCHOR_KINDS = {
    "governing_equation",
    "constitutive_closure",
    "boundary_or_initial_condition",
    "geometry_or_coordinate_relation",
    "stochastic_law",
    "optimization_objective_or_constraint",
    "table_or_empirical_relation",
    "numerical_state_transition",
    "cross_relation_coupling",
    "diagnostic_definition",
}
EQUATION_ROLES = {
    "governing_equation",
    "coupled_equation_system",
    "evolution_equation",
    "constraint_equation",
}
NODE_ROLES = {"operator_node", "task_graph_subweb"}
EDGE_ROLES = {"port_binding", "controlled_glue"}
EDGE_CLOSURE_STATES = {"proved", "pending", "blocked", "terminally_classified"}
SOURCE_PARTITION_ROLES = {
    "scientific_source",
    "support_runtime",
    "tests_examples",
    "external_producer",
    "excluded_material",
}
SOURCE_PARTITION_STATES = {"mapped", "unmapped"}
PRIORITIES = {
    "P0_primary_solution",
    "P1_required_closure",
    "P2_material_branch_or_lifecycle",
    "P3_principal_diagnostic",
}
DISPOSITIONS = {"pending", "in_progress", "emitted", "terminally_classified"}
GATE_NAMES = (
    "mapped",
    "contract",
    "implemented",
    "source_free",
    "independent_validation",
)
GATE_STATES = {"passed", "pending", "blocked", "not_applicable"}
PATH_STATES = {"passed", "partial", "blocked", "terminally_classified"}
REASSEMBLY_CASE_KINDS = {"canonical", "sealed_holdout"}
REASSEMBLY_ENTRY_KINDS = {"task_graph", "terminal_operator"}
SOURCE_ORACLE_KINDS = {"source_runtime", "source_fixture", "source_derived_reference"}
PARTITION_STATES = {"proved", "pending", "blocked", "terminally_classified"}
GAP_CLASSES = {
    "extraction_gap",
    "configuration_or_schema_need",
    "ai_completable_glue",
    "validation_oracle_gap",
    "cannot_complete",
}
PROGRESS_FIELDS = (
    "census_maturity",
    "extraction_resolution",
    "usable_core_closure",
    "composition_edge_closure",
    "branch_domain_coverage",
    "target_path_reassembly",
)
MILESTONE_IDS = (
    "M0_equation_census",
    "M1_minimal_golden_path",
    "M2_replaceable_scientific_slices",
    "M3_branch_lifecycle_expansion",
    "M4_extraction_freeze",
)
MILESTONE_STATES = {"pending", "in_progress", "completed", "blocked"}
CLOSURE_SIGNAL_KINDS = {
    "active",
    "bounded_delivery",
    "blocked_external",
    "full_freeze",
}
BOUNDARY_EVENT_KINDS = {
    "in_stage_replan",
    "external_dependency",
    "later_stage_handoff",
    "tooling_defect",
    "unknown",
}
STATE_KINDS = CLOSURE_SIGNAL_KINDS | {"reopened"}


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_nonempty_string(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty string")


def _require_sha256(value: Any, field: str, errors: list[str]) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in string.hexdigits for character in value)
    ):
        errors.append(f"{field} must be a 64-character SHA-256 hex digest")


def _validate_blocker(blocker: Any, field: str, errors: list[str]) -> None:
    if not isinstance(blocker, dict):
        errors.append(f"{field} must be an object")
        return
    classification = blocker.get("classification")
    if classification not in GAP_CLASSES:
        errors.append(f"{field}.classification must be one of {sorted(GAP_CLASSES)}")
    for name in ("reason", "next_action", "owner"):
        _require_nonempty_string(blocker.get(name), f"{field}.{name}", errors)


def _validate_reassembly_evidence(
    evidence: Any,
    field: str,
    *,
    scope_manifest_digest: Any,
    bundle_digest: Any,
    errors: list[str],
) -> None:
    if not isinstance(evidence, dict):
        errors.append(f"{field} must be an object for a passed target")
        return

    _require_sha256(evidence.get("source_scope_digest"), f"{field}.source_scope_digest", errors)
    if evidence.get("source_scope_digest") != scope_manifest_digest:
        errors.append(f"{field}.source_scope_digest must match scope.scope_manifest_digest")
    _require_sha256(evidence.get("bundle_digest"), f"{field}.bundle_digest", errors)
    if evidence.get("bundle_digest") != bundle_digest:
        errors.append(f"{field}.bundle_digest must match scope.bundle_digest")

    if evidence.get("entry_kind") not in REASSEMBLY_ENTRY_KINDS:
        errors.append(f"{field}.entry_kind must be one of {sorted(REASSEMBLY_ENTRY_KINDS)}")
    for name in ("entry_asset_refs", "terminal_output_ids"):
        values = evidence.get(name)
        if not isinstance(values, list) or not values or any(
            not isinstance(value, str) or not value for value in values
        ):
            errors.append(f"{field}.{name} must be a non-empty list of strings")
        elif len(values) != len(set(values)):
            errors.append(f"{field}.{name} must not contain duplicate ids")

    expected_outputs = evidence.get("terminal_output_ids")
    expected_output_set = set(expected_outputs) if isinstance(expected_outputs, list) else set()
    cases = evidence.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append(f"{field}.cases must be a non-empty list")
        return

    seen_case_ids: set[str] = set()
    seen_kinds: set[str] = set()
    for index, case in enumerate(cases):
        case_field = f"{field}.cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{case_field} must be an object")
            continue
        case_id = case.get("case_id")
        _require_nonempty_string(case_id, f"{case_field}.case_id", errors)
        if isinstance(case_id, str):
            if case_id in seen_case_ids:
                errors.append(f"{field}.cases contains duplicate case_id: {case_id}")
            seen_case_ids.add(case_id)
        kind = case.get("kind")
        if kind not in REASSEMBLY_CASE_KINDS:
            errors.append(f"{case_field}.kind must be one of {sorted(REASSEMBLY_CASE_KINDS)}")
        elif isinstance(kind, str):
            seen_kinds.add(kind)
        if case.get("source_oracle_kind") not in SOURCE_ORACLE_KINDS:
            errors.append(
                f"{case_field}.source_oracle_kind must be one of {sorted(SOURCE_ORACLE_KINDS)}"
            )
        for name in (
            "source_oracle_ref",
            "bundle_execution_ref",
            "comparison_receipt_ref",
            "tolerance_contract_ref",
        ):
            _require_nonempty_string(case.get(name), f"{case_field}.{name}", errors)
            digest_name = name.removesuffix("_ref") + "_sha256"
            _require_sha256(case.get(digest_name), f"{case_field}.{digest_name}", errors)
        _require_sha256(case.get("source_input_digest"), f"{case_field}.source_input_digest", errors)
        _require_sha256(case.get("bundle_input_digest"), f"{case_field}.bundle_input_digest", errors)
        if case.get("source_input_digest") != case.get("bundle_input_digest"):
            errors.append(
                f"{case_field} source_input_digest and bundle_input_digest must be identical"
            )
        compared_outputs = case.get("compared_terminal_output_ids")
        if not isinstance(compared_outputs, list) or not compared_outputs or any(
            not isinstance(value, str) or not value for value in compared_outputs
        ):
            errors.append(
                f"{case_field}.compared_terminal_output_ids must be a non-empty list of strings"
            )
        elif set(compared_outputs) != expected_output_set:
            errors.append(
                f"{case_field}.compared_terminal_output_ids must equal {field}.terminal_output_ids"
            )
        if case.get("status") != "passed":
            errors.append(f"{case_field}.status must equal passed")

    missing_kinds = sorted(REASSEMBLY_CASE_KINDS - seen_kinds)
    if missing_kinds:
        errors.append(f"{field}.cases is missing required kinds: {missing_kinds}")


def _validate_closure_signal(
    document: dict[str, Any], errors: list[str], *, required: bool
) -> None:
    """Validate the optional machine-readable stop signal for a progress snapshot."""
    signal = document.get("closure_signal")
    if signal is None:
        if required:
            errors.append("closure_signal is required for a current progress snapshot")
        return
    if not isinstance(signal, dict):
        errors.append("closure_signal must be an object")
        return

    kind = signal.get("kind")
    if kind not in CLOSURE_SIGNAL_KINDS:
        errors.append(
            "closure_signal.kind must be one of "
            f"{sorted(CLOSURE_SIGNAL_KINDS)}"
        )
    for name in ("claim_ceiling", "next_action", "reopen_condition", "owner"):
        _require_nonempty_string(signal.get(name), f"closure_signal.{name}", errors)

    evidence_refs = signal.get("evidence_refs")
    if (
        not isinstance(evidence_refs, list)
        or not evidence_refs
        or any(not isinstance(value, str) or not value for value in evidence_refs)
    ):
        errors.append("closure_signal.evidence_refs must be a non-empty list of strings")

    for name in ("delivered_target_ids", "unresolved_ids"):
        values = signal.get(name, [])
        if not isinstance(values, list) or any(
            not isinstance(value, str) or not value for value in values
        ):
            errors.append(f"closure_signal.{name} must be a list of non-empty strings")
        elif len(values) != len(set(values)):
            errors.append(f"closure_signal.{name} must not contain duplicate ids")

    delivered_target_ids = signal.get("delivered_target_ids", [])
    if not isinstance(delivered_target_ids, list):
        delivered_target_ids = []
    target_paths = document.get("target_paths", [])
    if not isinstance(target_paths, list):
        target_paths = []
    known_target_ids = {
        path.get("target_id")
        for path in target_paths
        if isinstance(path, dict) and isinstance(path.get("target_id"), str)
    }
    unknown_delivered_targets = sorted(
        set(delivered_target_ids) - known_target_ids
    )
    if unknown_delivered_targets:
        errors.append(
            "closure_signal.delivered_target_ids contains unknown target ids: "
            f"{unknown_delivered_targets}"
        )

    if kind == "active" and not document.get("active_frontier"):
        errors.append("closure_signal.kind=active requires a non-empty active_frontier")
    if kind == "blocked_external" and not document.get("active_frontier"):
        errors.append(
            "closure_signal.kind=blocked_external requires a non-empty active_frontier"
        )
    if kind == "blocked_external" and not signal.get("unresolved_ids"):
        errors.append(
            "closure_signal.kind=blocked_external requires unresolved_ids"
        )
    if kind == "bounded_delivery" and not signal.get("delivered_target_ids"):
        errors.append(
            "closure_signal.kind=bounded_delivery requires delivered_target_ids"
        )
    if kind == "bounded_delivery":
        review = signal.get("bounded_delivery_review")
        if not isinstance(review, dict):
            errors.append(
                "closure_signal.kind=bounded_delivery requires bounded_delivery_review"
            )
        else:
            _require_nonempty_string(
                review.get("receipt_ref"),
                "closure_signal.bounded_delivery_review.receipt_ref",
                errors,
            )
            _require_sha256(
                review.get("receipt_sha256"),
                "closure_signal.bounded_delivery_review.receipt_sha256",
                errors,
            )
        target_by_id = {
            target.get("target_id"): target
            for target in document.get("target_paths", [])
            if isinstance(target, dict) and isinstance(target.get("target_id"), str)
        }
        for target_id in signal.get("delivered_target_ids", []):
            target = target_by_id.get(target_id)
            if target is None:
                continue
            if target.get("status") != "passed":
                errors.append(
                    "closure_signal.kind=bounded_delivery requires every delivered "
                    f"target to have status=passed: {target_id}"
                )
            if target.get("trace_status") != "traced":
                errors.append(
                    "closure_signal.kind=bounded_delivery requires every delivered "
                    f"target to be traced: {target_id}"
                )
    if kind == "full_freeze":
        scope = document.get("scope")
        progress = document.get("progress")
        milestones = document.get("milestones")
        if not isinstance(scope, dict) or scope.get("census_status") != "frozen":
            errors.append("closure_signal.kind=full_freeze requires a frozen census")
        if not isinstance(progress, dict) or progress.get("overall") != 1.0:
            errors.append("closure_signal.kind=full_freeze requires progress.overall=1.0")
        if not isinstance(milestones, dict) or not isinstance(
            milestones.get("M4_extraction_freeze"), dict
        ) or milestones["M4_extraction_freeze"].get("status") != "completed":
            errors.append(
                "closure_signal.kind=full_freeze requires completed M4_extraction_freeze"
            )
        if document.get("active_frontier"):
            errors.append("closure_signal.kind=full_freeze requires an empty active_frontier")


def _validate_state_and_boundary_events(
    document: dict[str, Any], errors: list[str]
) -> None:
    """Keep optional lifecycle metadata consistent with the closure signal.

    Older snapshots remain valid without these fields. Current snapshots that include
    them cannot advertise a state different from the deterministic closure signal.
    """
    signal = document.get("closure_signal")
    state = document.get("state")
    if state is not None:
        if state not in STATE_KINDS:
            errors.append(f"state must be one of {sorted(STATE_KINDS)}")
        elif isinstance(signal, dict):
            kind = signal.get("kind")
            if state == "reopened":
                if kind != "active":
                    errors.append("state=reopened requires closure_signal.kind=active")
                _require_sha256(
                    document.get("reopened_from_digest"),
                    "reopened_from_digest",
                    errors,
                )
            elif state != kind:
                errors.append("state must equal closure_signal.kind")
        _require_sha256(document.get("state_digest"), "state_digest", errors)

    events = document.get("boundary_events", [])
    if not isinstance(events, list):
        errors.append("boundary_events must be a list")
        return
    seen: set[str] = set()
    for index, event in enumerate(events):
        field = f"boundary_events[{index}]"
        if not isinstance(event, dict):
            errors.append(f"{field} must be an object")
            continue
        event_id = event.get("event_id")
        _require_nonempty_string(event_id, f"{field}.event_id", errors)
        if isinstance(event_id, str):
            if event_id in seen:
                errors.append(f"duplicate boundary event_id: {event_id}")
            seen.add(event_id)
        if event.get("kind") not in BOUNDARY_EVENT_KINDS:
            errors.append(
                f"{field}.kind must be one of {sorted(BOUNDARY_EVENT_KINDS)}"
            )
        for name in (
            "observed_claim",
            "current_action",
            "forbidden_action",
            "owner",
            "reopen_condition",
        ):
            _require_nonempty_string(event.get(name), f"{field}.{name}", errors)
        refs = event.get("evidence_refs")
        if not isinstance(refs, list) or not refs or any(
            not isinstance(value, str) or not value for value in refs
        ):
            errors.append(f"{field}.evidence_refs must be a non-empty list of strings")
        if "predecessor_digest" in event and event.get("predecessor_digest") is not None:
            _require_sha256(event.get("predecessor_digest"), f"{field}.predecessor_digest", errors)


def _milestone_id_list(
    milestone: dict[str, Any],
    name: str,
    field: str,
    known_ids: set[str],
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> list[str]:
    values = milestone.get(field)
    field_path = f"milestones.{name}.{field}"
    if (
        not isinstance(values, list)
        or (not values and not allow_empty)
        or any(not isinstance(value, str) or not value for value in values)
    ):
        qualifier = "a list" if allow_empty else "a non-empty list"
        errors.append(f"{field_path} must be {qualifier} of non-empty strings")
        return []
    if len(values) != len(set(values)):
        errors.append(f"{field_path} must not contain duplicate ids")
    unknown = sorted(set(values) - known_ids)
    if unknown:
        errors.append(f"{field_path} contains unknown ids: {unknown}")
    return [value for value in values if value in known_ids]


def load_progress_document(
    progress_path: Path, max_bytes: int = MAX_PROGRESS_JSON_BYTES
) -> tuple[Any | None, str | None]:
    try:
        size = progress_path.stat().st_size
        if size > max_bytes:
            return None, f"progress_json exceeds {max_bytes} byte limit"
        return json.loads(progress_path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, str(exc)


def compute_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def compute_bundle_digest(bundle_root: Path) -> str:
    if not bundle_root.is_dir():
        raise OSError(f"bundle root is not a directory: {bundle_root}")
    digest = hashlib.sha256()
    files = sorted(
        (
            path
            for path in bundle_root.rglob("*")
            if path.is_file()
            and not any(part in CACHE_DIRECTORY_NAMES for part in path.relative_to(bundle_root).parts)
        ),
        key=lambda path: path.relative_to(bundle_root).as_posix(),
    )
    for path in files:
        relative = path.relative_to(bundle_root).as_posix()
        file_digest = compute_file_sha256(path)
        digest.update(f"{relative}\t{file_digest}\n".encode("utf-8"))
    return digest.hexdigest()


def bundle_file_hashes(bundle_root: Path) -> dict[str, str]:
    """Capture the exact bundle files used to justify an execution rebind."""
    if not bundle_root.is_dir():
        raise OSError(f"bundle root is not a directory: {bundle_root}")
    files = {}
    for path in bundle_root.rglob("*"):
        relative = path.relative_to(bundle_root)
        if any(part in CACHE_DIRECTORY_NAMES for part in relative.parts):
            continue
        if path.is_symlink():
            raise OSError(f"bundle rebind cannot include a symlink: {path}")
        if path.is_file():
            files[relative.as_posix()] = compute_file_sha256(path)
    return files


def _file_hash_digest(files: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative, file_digest in sorted(files.items()):
        digest.update(f"{relative}\t{file_digest}\n".encode("utf-8"))
    return digest.hexdigest()


def _resolve_bound_evidence_file(
    run_root: Path,
    reference: Any,
    expected_digest: Any,
    field: str,
    errors: list[str],
) -> Path | None:
    if not isinstance(reference, str) or not reference:
        return None
    relative = Path(reference)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"{field} must be a run-relative path without parent traversal")
        return None
    try:
        root = run_root.resolve(strict=True)
        path = (root / relative).resolve(strict=True)
    except OSError as exc:
        errors.append(f"{field} could not be read: {exc}")
        return None
    if not path.is_relative_to(root) or not path.is_file():
        errors.append(f"{field} must resolve to a regular file inside the run root")
        return None
    if (root / relative).is_symlink():
        errors.append(f"{field} must not be a symlink")
        return None
    actual_digest = compute_file_sha256(path)
    if not isinstance(expected_digest, str) or actual_digest != expected_digest.lower():
        errors.append(f"{field} digest does not match {path}")
        return None
    return path


def _validate_execution_rebind(
    receipt: dict[str, Any],
    case: dict[str, Any],
    execution: dict[str, Any],
    probe_receipt: dict[str, Any],
    *,
    run_root: Path,
    bundle_root: Path,
    errors: list[str],
) -> None:
    field = "execution rebind"
    path = _resolve_bound_evidence_file(
        run_root,
        receipt.get("execution_rebind_ref"),
        receipt.get("execution_rebind_sha256"),
        f"{field}.receipt_ref",
        errors,
    )
    if path is None:
        errors.append(f"{field} is required when execution and current bundle digests differ")
        return
    try:
        rebind = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{field} is not readable JSON: {exc}")
        return
    if not isinstance(rebind, dict):
        errors.append(f"{field} must be an object")
        return
    expected = {
        "target_id": receipt.get("target_id"),
        "case_id": case.get("case_id"),
        "baseline_bundle_digest": execution.get("bundle_digest"),
        "current_bundle_digest": receipt.get("bundle_digest"),
        "source_scope_digest": receipt.get("source_scope_digest"),
        "source_input_digest": case.get("source_input_digest"),
        "bundle_input_digest": case.get("bundle_input_digest"),
        "tolerance_contract_digest": case.get("tolerance_contract_sha256"),
        "bundle_execution_ref": case.get("bundle_execution_ref"),
        "bundle_execution_sha256": case.get("bundle_execution_sha256"),
        "bundle_execution_receipt_ref": receipt.get("bundle_execution_receipt_ref"),
        "bundle_execution_receipt_sha256": receipt.get("bundle_execution_receipt_sha256"),
        "runtime_image_id": probe_receipt.get("image_id"),
    }
    for name, value in expected.items():
        if rebind.get(name) != value:
            errors.append(f"{field}.{name} does not match the retained execution or current case")
    image_id = rebind.get("runtime_image_id")
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        errors.append(f"{field}.runtime_image_id must bind a content-addressed image")
    cases = execution.get("cases")
    case_key = f"{receipt.get('target_id')}::{case.get('case_id')}"
    if isinstance(cases, dict):
        executed_case = cases.get(case_key)
        if executed_case is None:
            case_id = case.get("case_id")
            kind = case.get("kind")
            match = (
                re.fullmatch(r"jcase([1-9][0-9]*)-(canonical|sealed_holdout)", case_id)
                if isinstance(case_id, str) else None
            )
            keyed_case = cases.get(case_id)
            controls = keyed_case.get("controls") if isinstance(keyed_case, dict) else None
            if (
                match is not None
                and match.group(2) == kind
                and isinstance(keyed_case, dict)
                and keyed_case.get("target_id") == receipt.get("target_id")
                and keyed_case.get("case_id") == kind
                and type(keyed_case.get("jcase")) is int
                and keyed_case["jcase"] == int(match.group(1))
                and isinstance(controls, dict)
                and controls.get("case_tag") == case_id
                and controls.get("case_kind") == kind
                and type(controls.get("jcase")) is int
                and controls["jcase"] == keyed_case["jcase"]
            ):
                executed_case = keyed_case
    elif isinstance(cases, list):
        executed_case = next(
            (row for row in cases if isinstance(row, dict)
             and row.get("target_id") == receipt.get("target_id")
             and row.get("case_id") == case.get("case_id")),
            None,
        )
    else:
        executed_case = execution if execution.get("target_id") == receipt.get("target_id") else None
    if not isinstance(executed_case, dict) or executed_case.get("input_digest") != case.get("bundle_input_digest"):
        errors.append(f"{field}.bundle_input_digest does not match the original execution case")

    manifest_path = _resolve_bound_evidence_file(
        run_root,
        rebind.get("baseline_manifest_ref"),
        rebind.get("baseline_manifest_sha256"),
        f"{field}.baseline_manifest_ref",
        errors,
    )
    if manifest_path is None:
        errors.append(f"{field}.baseline_manifest_ref is required to reuse an execution")
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{field}.baseline_manifest is not readable JSON: {exc}")
        return
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "scirel.bundle-file-manifest.v1":
        errors.append(f"{field}.baseline_manifest has an unsupported schema")
        return
    baseline = manifest.get("files")
    if not isinstance(baseline, dict) or not baseline:
        errors.append(f"{field}.baseline_manifest.files must be a non-empty object")
        return
    for relative, digest in baseline.items():
        path_value = Path(relative) if isinstance(relative, str) else Path("")
        if (
            not isinstance(relative, str)
            or not relative
            or path_value.is_absolute()
            or ".." in path_value.parts
            or path_value.as_posix() != relative
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in string.hexdigits for character in digest)
        ):
            errors.append(f"{field}.baseline_manifest.files has an invalid path or digest")
            return
    baseline_digest = _file_hash_digest(baseline)
    if manifest.get("bundle_digest") != baseline_digest or baseline_digest != execution.get("bundle_digest"):
        errors.append(f"{field}.baseline_manifest does not reconstruct the execution bundle digest")
    try:
        current = bundle_file_hashes(bundle_root)
    except OSError as exc:
        errors.append(f"{field}.current_bundle cannot be read: {exc}")
        return
    if _file_hash_digest(current) != receipt.get("bundle_digest"):
        errors.append(f"{field}.current_bundle does not reconstruct the current bundle digest")
    changed = sorted(
        path for path in baseline.keys() | current.keys()
        if baseline.get(path) != current.get(path)
    )
    version = rebind.get("schema_version")
    if version == "scirel.execution-rebind.v1":
        if not changed or set(changed) - REPORT_ONLY_ROOT_FILES:
            errors.append(f"{field} permits changes only to root project reports")
        if rebind.get("changed_report_paths") != changed:
            errors.append(f"{field}.changed_report_paths does not match the bundle files")
    elif version == "scirel.execution-rebind.v2":
        if not changed or any(
            path not in REPORT_ONLY_ROOT_FILES and not _is_package_document(path)
            for path in changed
        ):
            errors.append(f"{field} permits changes only to documentation files")
        if not any(_is_package_document(path) for path in changed):
            errors.append(f"{field}.v2 requires a changed package document")
        if rebind.get("changed_document_paths") != changed:
            errors.append(f"{field}.changed_document_paths does not match the bundle files")
    else:
        errors.append(f"{field}.schema_version is unsupported")
    scientific = {path: digest for path, digest in current.items() if path not in changed}
    if rebind.get("scientific_identity_digest") != _file_hash_digest(scientific):
        errors.append(f"{field}.scientific_identity_digest does not match unchanged executable files")
    if version == "scirel.execution-rebind.v2":
        review_path = _resolve_bound_evidence_file(
            run_root,
            rebind.get("documentation_review_ref"),
            rebind.get("documentation_review_sha256"),
            f"{field}.documentation_review_ref",
            errors,
        )
        if review_path is None:
            errors.append(f"{field} requires a documentation review")
            return
        try:
            review = json.loads(review_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{field}.documentation_review is not readable JSON: {exc}")
            return
        if not isinstance(review, dict):
            errors.append(f"{field}.documentation_review must be an object")
            return
        _require_nonempty_string(
            review.get("review_id"), f"{field}.documentation_review.review_id", errors
        )
        findings = review.get("findings")
        if not isinstance(findings, list) or any(
            not isinstance(item, str) or not item for item in findings
        ):
            errors.append(f"{field}.documentation_review.findings must be a list of strings")
        review_expected = {
            "schema_version": "scirel.documentation-rebind-review.v1",
            "reviewer_role": "independent_subagent",
            "verdict": "pass",
            "source_scope_digest": receipt.get("source_scope_digest"),
            "baseline_bundle_digest": execution.get("bundle_digest"),
            "current_bundle_digest": receipt.get("bundle_digest"),
            "scientific_identity_digest": rebind.get("scientific_identity_digest"),
            "reviewed_document_paths": changed,
            "code_and_science_consistent": True,
        }
        for name, value in review_expected.items():
            if review.get(name) != value:
                errors.append(f"{field}.documentation_review.{name} does not match the rebind")


def _validate_comparison_receipt(
    path: Path,
    *,
    run_root: Path,
    bundle_root: Path,
    bundle_execution_path: Path | None,
    target_id: Any,
    case: dict[str, Any],
    scope_manifest_digest: Any,
    bundle_digest: Any,
    require_detailed: bool,
    errors: list[str],
) -> None:
    field = f"comparison receipt {path}"
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{field} is not readable JSON: {exc}")
        return
    expected = {
        "status": "passed",
        "target_id": target_id,
        "case_id": case.get("case_id"),
        "kind": case.get("kind"),
        "source_scope_digest": scope_manifest_digest,
        "bundle_digest": bundle_digest,
        "source_input_digest": case.get("source_input_digest"),
        "bundle_input_digest": case.get("bundle_input_digest"),
        "tolerance_contract_digest": case.get("tolerance_contract_sha256"),
    }
    if not isinstance(receipt, dict):
        errors.append(f"{field} must contain a JSON object")
        return
    receipt_version = receipt.get("schema_version")
    if receipt_version not in (
        "scirel.extraction-reassembly-comparison.v1",
        "scirel.extraction-reassembly-comparison.v2",
    ):
        errors.append(f"{field}.schema_version is unsupported")
    if require_detailed and receipt_version != "scirel.extraction-reassembly-comparison.v2":
        errors.append(f"{field}.schema_version requires v2 for delivery closure")
    for name, value in expected.items():
        if receipt.get(name) != value:
            errors.append(f"{field}.{name} does not match the capability-progress record")

    if receipt_version == "scirel.extraction-reassembly-comparison.v2":
        for name in ("bundle_execution_ref", "bundle_execution_sha256"):
            if receipt.get(name) != case.get(name):
                errors.append(f"{field}.{name} does not match the capability-progress record")
        execution_ref = receipt.get("bundle_execution_receipt_ref")
        if not isinstance(execution_ref, str) or not execution_ref:
            errors.append(f"{field}.bundle_execution_receipt_ref is required")
            execution_path = None
        else:
            execution_path = _resolve_bound_evidence_file(
                run_root,
                execution_ref,
                receipt.get("bundle_execution_receipt_sha256"),
                f"{field}.bundle_execution_receipt_ref",
                errors,
            )
        execution = None
        if execution_path is not None:
            try:
                execution = json.loads(execution_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"{field}.bundle_execution_receipt is not readable JSON: {exc}")
            else:
                if (
                    not isinstance(execution, dict)
                    or type(execution.get("exit_code")) is not int
                    or execution["exit_code"] != 0
                ):
                    errors.append(f"{field}.bundle_execution_receipt.exit_code must equal 0")
        if bundle_execution_path is not None:
            try:
                bundle_execution = json.loads(bundle_execution_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"{field}.bundle_execution is not readable JSON: {exc}")
            else:
                original_digest = bundle_execution.get("bundle_digest") if isinstance(bundle_execution, dict) else None
                if not isinstance(original_digest, str) or len(original_digest) != 64:
                    errors.append(f"{field}.bundle_execution.bundle_digest is required for v2")
                elif original_digest != bundle_digest:
                    if execution_path is not None and isinstance(execution, dict):
                        _validate_execution_rebind(
                            receipt, case, bundle_execution, execution,
                            run_root=run_root, bundle_root=bundle_root, errors=errors,
                        )
                elif "execution_rebind_ref" in receipt or "execution_rebind_sha256" in receipt:
                    errors.append(f"{field} has an unnecessary execution rebind")

    expected_outputs = case.get("compared_terminal_output_ids")
    receipt_outputs = receipt.get("terminal_output_ids")
    if not isinstance(expected_outputs, list) or receipt_outputs != expected_outputs:
        errors.append(f"{field}.terminal_output_ids does not match the declared ordered outputs")
    comparisons = receipt.get("comparisons")
    if not isinstance(comparisons, list) or not comparisons:
        errors.append(f"{field}.comparisons must be a non-empty list")
        return
    comparison_ids = []
    for index, comparison in enumerate(comparisons):
        if not isinstance(comparison, dict):
            errors.append(f"{field}.comparisons[{index}] must be an object")
            continue
        output_id = comparison.get("output_id")
        comparison_ids.append(output_id)
        if comparison.get("status") != "passed":
            errors.append(f"{field}.comparisons[{index}].status must equal passed")
        if receipt_version == "scirel.extraction-reassembly-comparison.v2":
            if not isinstance(comparison.get("metric"), str) or not comparison["metric"].strip():
                errors.append(f"{field}.comparisons[{index}].metric must be non-empty")
            observed = comparison.get("observed_error")
            allowed = comparison.get("allowed_error")
            valid_errors = []
            for name, value in (("observed_error", observed), ("allowed_error", allowed)):
                try:
                    valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
                except OverflowError:
                    valid = False
                valid_errors.append(valid)
                if not valid:
                    errors.append(
                        f"{field}.comparisons[{index}].{name} must be finite and non-negative"
                    )
            if all(valid_errors) and observed > allowed:
                errors.append(f"{field}.comparisons[{index}].observed_error exceeds allowed_error")
    if comparison_ids != expected_outputs:
        errors.append(f"{field}.comparisons must cover every declared output exactly once and in order")


def _validate_bounded_delivery_review(
    document: dict[str, Any], run_root: Path, errors: list[str]
) -> None:
    signal = document.get("closure_signal")
    if not isinstance(signal, dict) or signal.get("kind") != "bounded_delivery":
        return
    review = signal.get("bounded_delivery_review")
    if not isinstance(review, dict):
        return
    path = _resolve_bound_evidence_file(
        run_root,
        review.get("receipt_ref"),
        review.get("receipt_sha256"),
        "closure_signal.bounded_delivery_review.receipt_ref",
        errors,
    )
    if path is None:
        return
    field = f"bounded delivery review {path}"
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{field} is not readable JSON: {exc}")
        return
    if not isinstance(receipt, dict):
        errors.append(f"{field} must contain a JSON object")
        return
    if receipt.get("reviewer_role") != "independent_subagent":
        errors.append(f"{field}.reviewer_role must equal independent_subagent")
    if receipt.get("verdict") != "pass":
        errors.append(f"{field}.verdict must equal pass")
    scope = document.get("scope")
    if isinstance(scope, dict):
        for name, expected in (
            ("source_scope_digest", scope.get("scope_manifest_digest")),
            ("bundle_digest", scope.get("bundle_digest")),
        ):
            if receipt.get(name) != expected:
                errors.append(f"{field}.{name} does not match the progress snapshot")
    delivered = signal.get("delivered_target_ids", [])
    reviewed = receipt.get("reviewed_target_ids")
    if not isinstance(reviewed, list) or any(
        not isinstance(value, str) or not value for value in reviewed
    ):
        errors.append(f"{field}.reviewed_target_ids must be a non-empty list of strings")
    elif set(reviewed) != set(delivered):
        errors.append(f"{field}.reviewed_target_ids must equal delivered_target_ids")
    for name in ("review_id", "claim_ceiling", "reopen_condition"):
        _require_nonempty_string(receipt.get(name), f"{field}.{name}", errors)
    for name in ("claim_ceiling", "reopen_condition"):
        if receipt.get(name) != signal.get(name):
            errors.append(f"{field}.{name} does not match closure_signal.{name}")
    reviewed_refs = receipt.get("reviewed_evidence_refs")
    if not isinstance(reviewed_refs, list) or not reviewed_refs or any(
        not isinstance(value, str) or not value for value in reviewed_refs
    ) or len(reviewed_refs) != len(set(reviewed_refs)):
        errors.append(f"{field}.reviewed_evidence_refs must be a non-empty unique list of strings")
    else:
        signal_refs = signal.get("evidence_refs")
        required_refs = {
            value for value in signal_refs if isinstance(value, str) and value
        } if isinstance(signal_refs, list) else set()
        for target in document.get("target_paths", []):
            if not isinstance(target, dict) or target.get("target_id") not in delivered:
                continue
            reassembly = target.get("reassembly_evidence")
            if not isinstance(reassembly, dict):
                continue
            for case in reassembly.get("cases", []):
                if isinstance(case, dict):
                    required_refs.update(
                        case[name]
                        for name in (
                            "source_oracle_ref",
                            "bundle_execution_ref",
                            "comparison_receipt_ref",
                            "tolerance_contract_ref",
                        )
                        if isinstance(case.get(name), str) and case[name]
                    )
        if not required_refs.issubset(reviewed_refs):
            errors.append(f"{field}.reviewed_evidence_refs must include closure and reassembly evidence")
    findings = receipt.get("findings")
    if not isinstance(findings, list) or any(
        not isinstance(value, str) or not value for value in findings
    ):
        errors.append(f"{field}.findings must be a list of non-empty strings")


def _validate_reassembly_external_bindings(
    document: dict[str, Any], bundle_root: Path, errors: list[str]
) -> None:
    run_root = bundle_root.parent
    scope = document.get("scope")
    if not isinstance(scope, dict):
        return
    signal = document.get("closure_signal")
    require_detailed = document.get("state") == "full_freeze" or (
        isinstance(signal, dict) and signal.get("kind") in ("bounded_delivery", "full_freeze")
    )
    for target_index, target in enumerate(document.get("target_paths", [])):
        if not isinstance(target, dict) or target.get("status") != "passed":
            continue
        evidence = target.get("reassembly_evidence")
        if not isinstance(evidence, dict):
            continue
        for case_index, case in enumerate(evidence.get("cases", [])):
            if not isinstance(case, dict):
                continue
            case_field = f"target_paths[{target_index}].reassembly_evidence.cases[{case_index}]"
            resolved: dict[str, Path] = {}
            for name in (
                "source_oracle",
                "bundle_execution",
                "comparison_receipt",
                "tolerance_contract",
            ):
                path = _resolve_bound_evidence_file(
                    run_root,
                    case.get(f"{name}_ref"),
                    case.get(f"{name}_sha256"),
                    f"{case_field}.{name}_ref",
                    errors,
                )
                if path is not None:
                    resolved[name] = path
            receipt_path = resolved.get("comparison_receipt")
            if receipt_path is not None:
                _validate_comparison_receipt(
                    receipt_path,
                    run_root=run_root,
                    bundle_root=bundle_root,
                    bundle_execution_path=resolved.get("bundle_execution"),
                    target_id=target.get("target_id"),
                    case=case,
                    scope_manifest_digest=scope.get("scope_manifest_digest"),
                    bundle_digest=scope.get("bundle_digest"),
                    require_detailed=require_detailed,
                    errors=errors,
                )


def _validate_full_freeze_delivery_surface(
    document: dict[str, Any], bundle_root: Path, errors: list[str]
) -> None:
    signal = document.get("closure_signal")
    if not isinstance(signal, dict) or signal.get("kind") != "full_freeze":
        return
    entry = bundle_root / "asset_entry.py"
    if entry.is_symlink() or not entry.is_file():
        errors.append(
            "closure_signal.kind=full_freeze requires a regular, non-symlinked "
            "root asset_entry.py"
        )
        return
    binding = signal.get("asset_entry_validation")
    if not isinstance(binding, dict):
        errors.append("closure_signal.kind=full_freeze requires asset_entry_validation")
        return
    path = _resolve_bound_evidence_file(
        bundle_root.parent,
        binding.get("receipt_ref"),
        binding.get("receipt_sha256"),
        "closure_signal.asset_entry_validation.receipt_ref",
        errors,
    )
    if path is None:
        errors.append("closure_signal.asset_entry_validation.receipt_ref is required for full_freeze")
        return
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"asset_entry_validation receipt is not readable JSON: {exc}")
        return
    if not isinstance(receipt, dict):
        errors.append("asset_entry_validation receipt must contain a JSON object")
        return
    for name, expected in (
        ("validator", "validate_asset_entry.py"),
        ("sandbox", "CODEFUSION_ASSET_SANDBOX=1"),
        ("exit_code", 0),
        ("asset_entry_sha256", compute_file_sha256(entry)),
        ("bundle_digest", document["scope"].get("bundle_digest")),
    ):
        if receipt.get(name) != expected or (name == "exit_code" and type(receipt.get(name)) is not int):
            errors.append(f"asset_entry_validation.{name} must equal {expected}")
    for name in ("operators", "task_graphs"):
        if type(receipt.get(name)) is not int or receipt[name] < 0:
            errors.append(f"asset_entry_validation.{name} must be a non-negative integer")


def validate_external_bindings(
    document: Any,
    *,
    scope_manifest: Path,
    capability_evidence_matrix: Path,
    ledger: Path,
    bundle_root: Path,
) -> list[str]:
    if not isinstance(document, dict) or not isinstance(document.get("scope"), dict):
        return ["external bindings require a valid scope object"]
    scope = document["scope"]
    checks = (
        ("scope_manifest_digest", scope_manifest, False),
        ("capability_evidence_matrix_digest", capability_evidence_matrix, False),
        ("ledger_digest", ledger, False),
        ("bundle_digest", bundle_root, True),
    )
    errors: list[str] = []
    _validate_full_freeze_delivery_surface(document, bundle_root, errors)
    _validate_bounded_delivery_review(document, bundle_root.parent, errors)
    for field, path, is_bundle in checks:
        try:
            actual = compute_bundle_digest(path) if is_bundle else compute_file_sha256(path)
        except OSError as exc:
            errors.append(f"scope.{field} binding could not be read: {exc}")
            continue
        expected = scope.get(field)
        if not isinstance(expected, str) or actual != expected.lower():
            errors.append(f"scope.{field} does not match {path}")
    _validate_reassembly_external_bindings(document, bundle_root, errors)
    return errors


def validate_progress_document(
    document: Any,
    *,
    require_closure_signal: bool = False,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["progress document must be an object"]

    schema_version = document.get("schema_version")
    if schema_version != "1.0":
        errors.append("schema_version must equal '1.0'")
    _require_nonempty_string(document.get("snapshot_id"), "snapshot_id", errors)

    scope = document.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
        return errors
    _require_nonempty_string(scope.get("scope_id"), "scope.scope_id", errors)
    census_status = scope.get("census_status")
    if census_status not in {"provisional", "frozen"}:
        errors.append("scope.census_status must be provisional or frozen")
    for field in (
        "scope_manifest_digest",
        "capability_evidence_matrix_digest",
        "ledger_digest",
        "bundle_digest",
    ):
        _require_sha256(scope.get(field), f"scope.{field}", errors)

    count_fields = (
        "source_partitions_mapped",
        "source_partitions_total",
        "target_paths_traced",
        "target_paths_total",
    )
    counts: dict[str, int] = {}
    for field in count_fields:
        value = scope.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"scope.{field} must be a non-negative integer")
        else:
            counts[field] = value
    for total_field in ("source_partitions_total", "target_paths_total"):
        if counts.get(total_field) == 0:
            errors.append(f"scope.{total_field} must be greater than zero")
    if counts.get("source_partitions_mapped", 0) > counts.get("source_partitions_total", 0):
        errors.append("source_partitions_mapped cannot exceed source_partitions_total")
    if counts.get("target_paths_traced", 0) > counts.get("target_paths_total", 0):
        errors.append("target_paths_traced cannot exceed target_paths_total")

    source_partitions = document.get("source_partitions")
    if not isinstance(source_partitions, list) or not source_partitions:
        errors.append("source_partitions must be a non-empty list")
        source_partitions = []
    source_partition_ids: set[str] = set()
    normalized_source_partitions: list[dict[str, Any]] = []
    for index, partition in enumerate(source_partitions):
        field = f"source_partitions[{index}]"
        if not isinstance(partition, dict):
            errors.append(f"{field} must be an object")
            continue
        partition_id = partition.get("partition_id")
        _require_nonempty_string(partition_id, f"{field}.partition_id", errors)
        if isinstance(partition_id, str):
            if partition_id in source_partition_ids:
                errors.append(f"duplicate source partition_id: {partition_id}")
            source_partition_ids.add(partition_id)
        if partition.get("material_role") not in SOURCE_PARTITION_ROLES:
            errors.append(
                f"{field}.material_role must be one of {sorted(SOURCE_PARTITION_ROLES)}"
            )
        if partition.get("status") not in SOURCE_PARTITION_STATES:
            errors.append(f"{field}.status must be one of {sorted(SOURCE_PARTITION_STATES)}")
        evidence_refs = partition.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs or any(
            not isinstance(value, str) or not value for value in evidence_refs
        ):
            errors.append(f"{field}.evidence_refs must be a non-empty list of strings")
        normalized_source_partitions.append(partition)
    if counts.get("source_partitions_total") != len(normalized_source_partitions):
        errors.append(
            "scope.source_partitions_total must equal the enumerated source_partitions length"
        )
    mapped_source_partitions = sum(
        partition.get("status") == "mapped" for partition in normalized_source_partitions
    )
    if counts.get("source_partitions_mapped") != mapped_source_partitions:
        errors.append(
            "scope.source_partitions_mapped must equal the mapped source_partitions count"
        )

    equation_anchors = document.get("equation_anchors")
    if not isinstance(equation_anchors, list) or not equation_anchors:
        errors.append("equation_anchors must be a non-empty list")
        equation_anchors = []
    equation_ids: set[str] = set()
    normalized_equations: list[dict[str, Any]] = []
    for index, equation in enumerate(equation_anchors):
        field = f"equation_anchors[{index}]"
        if not isinstance(equation, dict):
            errors.append(f"{field} must be an object")
            continue
        equation_id = equation.get("equation_id")
        _require_nonempty_string(equation_id, f"{field}.equation_id", errors)
        if isinstance(equation_id, str):
            if equation_id in equation_ids:
                errors.append(f"duplicate equation_id: {equation_id}")
            equation_ids.add(equation_id)
        if equation.get("equation_role") not in EQUATION_ROLES:
            errors.append(f"{field}.equation_role must be one of {sorted(EQUATION_ROLES)}")
        for name in ("target_paths", "authority_refs"):
            values = equation.get(name)
            if not isinstance(values, list) or not values or any(
                not isinstance(value, str) or not value for value in values
            ):
                errors.append(f"{field}.{name} must be a non-empty list of strings")
        normalized_equations.append(equation)

    work_units = document.get("work_units")
    if not isinstance(work_units, list) or not work_units:
        errors.append("work_units must be a non-empty list")
        work_units = []
    capability_ids: set[str] = set()
    normalized_units: list[dict[str, Any]] = []
    for index, unit in enumerate(work_units):
        field = f"work_units[{index}]"
        if not isinstance(unit, dict):
            errors.append(f"{field} must be an object")
            continue
        capability_id = unit.get("capability_id")
        _require_nonempty_string(capability_id, f"{field}.capability_id", errors)
        if isinstance(capability_id, str):
            if capability_id in capability_ids:
                errors.append(f"duplicate capability_id: {capability_id}")
            capability_ids.add(capability_id)
        if unit.get("anchor_kind") not in ANCHOR_KINDS:
            errors.append(f"{field}.anchor_kind must be one of {sorted(ANCHOR_KINDS)}")
        node_role = unit.get("node_role")
        if node_role not in NODE_ROLES:
            errors.append(f"{field}.node_role must be one of {sorted(NODE_ROLES)}")
        if node_role == "task_graph_subweb":
            for membership_field in ("participating_node_ids", "participating_edge_ids"):
                members = unit.get(membership_field)
                if not isinstance(members, list) or not members or any(
                    not isinstance(value, str) or not value for value in members
                ):
                    errors.append(
                        f"{field}.{membership_field} must be a non-empty list of strings "
                        "for task_graph_subweb"
                    )
        equation_anchor_ids = unit.get("equation_anchor_ids")
        if not isinstance(equation_anchor_ids, list) or not equation_anchor_ids or any(
            not isinstance(value, str) or not value for value in equation_anchor_ids
        ):
            errors.append(f"{field}.equation_anchor_ids must be a non-empty list of strings")
        else:
            unknown_equations = sorted(set(equation_anchor_ids) - equation_ids)
            if unknown_equations:
                errors.append(
                    f"{field}.equation_anchor_ids contains unknown ids: {unknown_equations}"
                )
        if unit.get("priority") not in PRIORITIES:
            errors.append(f"{field}.priority must be one of {sorted(PRIORITIES)}")
        disposition = unit.get("disposition")
        if disposition not in DISPOSITIONS:
            errors.append(f"{field}.disposition must be one of {sorted(DISPOSITIONS)}")
        required_for = unit.get("required_for")
        if not isinstance(required_for, list) or any(
            not isinstance(value, str) or not value for value in required_for
        ):
            errors.append(f"{field}.required_for must be a list of non-empty strings")
        gates = unit.get("gates")
        if not isinstance(gates, dict):
            errors.append(f"{field}.gates must be an object")
        else:
            unexpected = set(gates) - set(GATE_NAMES)
            missing = set(GATE_NAMES) - set(gates)
            if unexpected:
                errors.append(f"{field}.gates has unexpected keys: {sorted(unexpected)}")
            if missing:
                errors.append(f"{field}.gates is missing keys: {sorted(missing)}")
            for name in GATE_NAMES:
                if gates.get(name) not in GATE_STATES:
                    errors.append(f"{field}.gates.{name} must be one of {sorted(GATE_STATES)}")
        blocker = unit.get("blocker")
        if disposition == "emitted":
            if blocker is not None:
                errors.append(f"{field}.blocker must be null for emitted work")
        elif disposition in {"pending", "in_progress", "terminally_classified"}:
            _validate_blocker(blocker, f"{field}.blocker", errors)
        normalized_units.append(unit)

    partitions = document.get("coverage_partitions")
    if not isinstance(partitions, list) or not partitions:
        errors.append("coverage_partitions must be a non-empty list")
        partitions = []
    partition_ids: set[str] = set()
    normalized_partitions: list[dict[str, Any]] = []
    for index, partition in enumerate(partitions):
        field = f"coverage_partitions[{index}]"
        if not isinstance(partition, dict):
            errors.append(f"{field} must be an object")
            continue
        partition_id = partition.get("partition_id")
        _require_nonempty_string(partition_id, f"{field}.partition_id", errors)
        if isinstance(partition_id, str):
            if partition_id in partition_ids:
                errors.append(f"duplicate partition_id: {partition_id}")
            partition_ids.add(partition_id)
        if partition.get("status") not in PARTITION_STATES:
            errors.append(f"{field}.status must be one of {sorted(PARTITION_STATES)}")
        normalized_partitions.append(partition)

    target_paths = document.get("target_paths")
    if not isinstance(target_paths, list) or not target_paths:
        errors.append("target_paths must be a non-empty list")
        target_paths = []
    target_ids: set[str] = set()
    target_required_capabilities: dict[str, set[str]] = {}
    unresolved_targets: dict[str, str] = {}
    normalized_paths: list[dict[str, Any]] = []
    for index, path in enumerate(target_paths):
        field = f"target_paths[{index}]"
        if not isinstance(path, dict):
            errors.append(f"{field} must be an object")
            continue
        target_id = path.get("target_id")
        _require_nonempty_string(target_id, f"{field}.target_id", errors)
        if isinstance(target_id, str):
            if target_id in target_ids:
                errors.append(f"duplicate target_id: {target_id}")
            target_ids.add(target_id)
        required = path.get("required_capabilities")
        if (
            not isinstance(required, list)
            or not required
            or any(not isinstance(value, str) or not value for value in required)
        ):
            errors.append(
                f"{field}.required_capabilities must be a non-empty list of strings"
            )
        else:
            unknown = sorted(set(required) - capability_ids)
            if unknown:
                errors.append(f"{field}.required_capabilities contains unknown ids: {unknown}")
            if isinstance(target_id, str):
                target_required_capabilities[target_id] = set(required)
        status = path.get("status")
        if status not in PATH_STATES:
            errors.append(f"{field}.status must be one of {sorted(PATH_STATES)}")
        earliest = path.get("earliest_unresolved")
        if status == "passed":
            if earliest is not None:
                errors.append(f"{field}.earliest_unresolved must be null when status is passed")
        else:
            _require_nonempty_string(earliest, f"{field}.earliest_unresolved", errors)
            if isinstance(target_id, str) and isinstance(earliest, str) and earliest:
                unresolved_targets[target_id] = earliest
        trace_status = path.get("trace_status")
        if trace_status not in {"traced", "untraced"}:
            errors.append(f"{field}.trace_status must be traced or untraced")
        evidence_refs = path.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs or any(
            not isinstance(value, str) or not value for value in evidence_refs
        ):
            errors.append(f"{field}.evidence_refs must be a non-empty list of strings")
        if schema_version == "1.0" and status == "passed":
            _validate_reassembly_evidence(
                path.get("reassembly_evidence"),
                f"{field}.reassembly_evidence",
                scope_manifest_digest=scope.get("scope_manifest_digest"),
                bundle_digest=scope.get("bundle_digest"),
                errors=errors,
            )
        normalized_paths.append(path)

    if counts.get("target_paths_total") != len(normalized_paths):
        errors.append("scope.target_paths_total must equal the enumerated target_paths length")
    traced_target_paths = sum(
        path.get("trace_status") == "traced" for path in normalized_paths
    )
    if counts.get("target_paths_traced") != traced_target_paths:
        errors.append("scope.target_paths_traced must equal the traced target_paths count")

    for index, unit in enumerate(normalized_units):
        required_for = unit.get("required_for")
        if not isinstance(required_for, list) or any(
            not isinstance(value, str) or not value for value in required_for
        ):
            continue
        unknown_targets = sorted(set(required_for) - target_ids)
        if unknown_targets:
            errors.append(
                f"work_units[{index}].required_for contains unknown ids: {unknown_targets}"
            )

    web_edges = document.get("web_edges")
    if not isinstance(web_edges, list):
        errors.append("web_edges must be a list")
        web_edges = []
    edge_ids: set[str] = set()
    normalized_edges: dict[str, dict[str, Any]] = {}
    for index, edge in enumerate(web_edges):
        field = f"web_edges[{index}]"
        if not isinstance(edge, dict):
            errors.append(f"{field} must be an object")
            continue
        edge_id = edge.get("edge_id")
        _require_nonempty_string(edge_id, f"{field}.edge_id", errors)
        if isinstance(edge_id, str):
            if edge_id in edge_ids:
                errors.append(f"duplicate edge_id: {edge_id}")
            edge_ids.add(edge_id)
            normalized_edges[edge_id] = edge
        for name in ("from_node_id", "from_port", "to_node_id", "to_port"):
            _require_nonempty_string(edge.get(name), f"{field}.{name}", errors)
        endpoint_ids = {
            value
            for value in (edge.get("from_node_id"), edge.get("to_node_id"))
            if isinstance(value, str)
        }
        unknown_endpoints = sorted(endpoint_ids - capability_ids)
        if unknown_endpoints:
            errors.append(f"{field} endpoints contain unknown ids: {unknown_endpoints}")
        if edge.get("edge_role") not in EDGE_ROLES:
            errors.append(f"{field}.edge_role must be one of {sorted(EDGE_ROLES)}")
        closure_status = edge.get("closure_status")
        if closure_status not in EDGE_CLOSURE_STATES:
            errors.append(
                f"{field}.closure_status must be one of {sorted(EDGE_CLOSURE_STATES)}"
            )
        if closure_status == "proved":
            if edge.get("blocker") is not None:
                errors.append(f"{field}.blocker must be null for a proved edge")
        elif closure_status in {"pending", "blocked", "terminally_classified"}:
            _validate_blocker(edge.get("blocker"), f"{field}.blocker", errors)
        required_for = edge.get("required_for")
        if not isinstance(required_for, list) or any(
            not isinstance(value, str) or not value for value in required_for
        ):
            errors.append(f"{field}.required_for must be a list of non-empty strings")
        else:
            unknown_targets = sorted(set(required_for) - target_ids)
            if unknown_targets:
                errors.append(f"{field}.required_for contains unknown ids: {unknown_targets}")

    for index, unit in enumerate(normalized_units):
        if unit.get("node_role") != "task_graph_subweb":
            continue
        field = f"work_units[{index}]"
        node_values = unit.get("participating_node_ids", [])
        member_nodes = (
            {value for value in node_values if isinstance(value, str)}
            if isinstance(node_values, list)
            else set()
        )
        unknown_nodes = sorted(member_nodes - capability_ids)
        if unknown_nodes:
            errors.append(f"{field}.participating_node_ids contains unknown ids: {unknown_nodes}")
        if unit.get("capability_id") in member_nodes:
            errors.append(f"{field}.participating_node_ids cannot contain the subweb itself")
        edge_values = unit.get("participating_edge_ids", [])
        member_edges = (
            {value for value in edge_values if isinstance(value, str)}
            if isinstance(edge_values, list)
            else set()
        )
        unknown_edges = sorted(member_edges - edge_ids)
        if unknown_edges:
            errors.append(f"{field}.participating_edge_ids contains unknown ids: {unknown_edges}")
        for edge_id in sorted(member_edges & edge_ids):
            edge = normalized_edges[edge_id]
            endpoints = {
                value
                for value in (edge.get("from_node_id"), edge.get("to_node_id"))
                if isinstance(value, str)
            }
            if not endpoints <= member_nodes:
                errors.append(
                    f"{field}.participating_edge_ids edge {edge_id} endpoints must both "
                    "belong to participating_node_ids"
                )

    for index, partition in enumerate(normalized_partitions):
        required_for = partition.get("required_for")
        if not isinstance(required_for, list) or any(
            not isinstance(value, str) or not value for value in required_for
        ):
            errors.append(
                f"coverage_partitions[{index}].required_for must be a list of non-empty strings"
            )
        else:
            unknown_targets = sorted(set(required_for) - target_ids)
            if unknown_targets:
                errors.append(
                    f"coverage_partitions[{index}].required_for contains unknown ids: "
                    f"{unknown_targets}"
                )

    for target_id, earliest in unresolved_targets.items():
        target_capabilities = set(target_required_capabilities.get(target_id, set()))
        target_capabilities.update(
            unit.get("capability_id")
            for unit in normalized_units
            if isinstance(unit.get("required_for"), list)
            and target_id in unit["required_for"]
            and isinstance(unit.get("capability_id"), str)
        )
        target_edges = {
            edge_id
            for edge_id, edge in normalized_edges.items()
            if isinstance(edge.get("required_for"), list)
            and target_id in edge["required_for"]
        }
        if earliest not in target_capabilities | target_edges:
            errors.append(
                f"target {target_id}.earliest_unresolved contains unknown capability or edge id: "
                f"{earliest}"
            )

    for path in normalized_paths:
        if path.get("status") != "passed":
            continue
        target_id = path.get("target_id")
        for capability_id in sorted(target_required_capabilities.get(target_id, set())):
            matching_units = [
                unit
                for unit in normalized_units
                if unit.get("capability_id") == capability_id
            ]
            if not matching_units:
                continue
            unit = matching_units[0]
            gates = unit.get("gates")
            if not (
                unit.get("disposition") == "emitted"
                and isinstance(gates, dict)
                and all(gates.get(name) == "passed" for name in GATE_NAMES)
            ):
                errors.append(
                    "passed target requires fully passed capability: "
                    f"target={target_id}, capability={capability_id}"
                )
        unresolved_required_edges = sorted(
            edge_id
            for edge_id, edge in normalized_edges.items()
            if isinstance(edge.get("required_for"), list)
            and target_id in edge["required_for"]
            and edge.get("closure_status") != "proved"
        )
        if unresolved_required_edges:
            errors.append(
                f"passed target {target_id} has unresolved required edges: "
                f"{unresolved_required_edges}"
            )

    frontier = document.get("active_frontier")
    if not isinstance(frontier, list):
        errors.append("active_frontier must be a list")
        frontier = []
    frontier_targets: dict[str, str] = {}
    for index, item in enumerate(frontier):
        field = f"active_frontier[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{field} must be an object")
            continue
        target_id = item.get("target_id")
        capability_or_edge = item.get("capability_or_edge")
        _require_nonempty_string(target_id, f"{field}.target_id", errors)
        _require_nonempty_string(capability_or_edge, f"{field}.capability_or_edge", errors)
        if isinstance(target_id, str):
            if target_id in frontier_targets:
                errors.append(f"active_frontier contains duplicate target_id: {target_id}")
            if isinstance(capability_or_edge, str):
                frontier_targets[target_id] = capability_or_edge
        _validate_blocker(item, field, errors)
    for target_id, earliest in unresolved_targets.items():
        if frontier_targets.get(target_id) != earliest:
            errors.append(
                "active_frontier must contain the exact earliest_unresolved entry for "
                f"target {target_id}: {earliest}"
            )
    extra_frontier = sorted(set(frontier_targets) - set(unresolved_targets))
    if extra_frontier:
        errors.append(f"active_frontier contains passed or unknown targets: {extra_frontier}")
    for index, equation in enumerate(normalized_equations):
        equation_targets = equation.get("target_paths")
        if not isinstance(equation_targets, list) or any(
            not isinstance(value, str) or not value for value in equation_targets
        ):
            continue
        unknown_targets = sorted(set(equation_targets) - target_ids)
        if unknown_targets:
            errors.append(
                f"equation_anchors[{index}].target_paths contains unknown ids: {unknown_targets}"
            )

    progress = document.get("progress")
    if not isinstance(progress, dict):
        errors.append("progress must be an object")
        return errors

    source_ratio = _ratio(
        counts.get("source_partitions_mapped", 0),
        counts.get("source_partitions_total", 0),
    )
    target_trace_ratio = _ratio(
        counts.get("target_paths_traced", 0),
        counts.get("target_paths_total", 0),
    )
    expected: dict[str, float] = {
        "census_maturity": min(source_ratio, target_trace_ratio),
        "extraction_resolution": _ratio(
            sum(
                unit.get("disposition") in {"emitted", "terminally_classified"}
                for unit in normalized_units
            ),
            len(normalized_units),
        ),
    }
    core_units = [
        unit
        for unit in normalized_units
        if unit.get("priority") in {"P0_primary_solution", "P1_required_closure"}
    ]
    if not core_units:
        errors.append("work_units must include at least one P0 or P1 core capability")
    expected["usable_core_closure"] = _ratio(
        sum(
            unit.get("disposition") == "emitted"
            and isinstance(unit.get("gates"), dict)
            and all(unit["gates"].get(name) == "passed" for name in GATE_NAMES)
            for unit in core_units
        ),
        len(core_units),
    )
    expected["composition_edge_closure"] = _ratio(
        sum(edge.get("closure_status") == "proved" for edge in normalized_edges.values()),
        len(normalized_edges),
    )
    expected["branch_domain_coverage"] = _ratio(
        sum(partition.get("status") == "proved" for partition in normalized_partitions),
        len(normalized_partitions),
    )
    expected["target_path_reassembly"] = _ratio(
        sum(path.get("status") == "passed" for path in normalized_paths),
        len(normalized_paths),
    )

    for field in PROGRESS_FIELDS:
        actual = progress.get(field)
        if not _is_number(actual) or not 0.0 <= float(actual) <= 1.0:
            errors.append(f"progress.{field} must be a number in [0, 1]")
            continue
        if abs(float(actual) - expected[field]) > 1.0e-12:
            errors.append(
                f"progress.{field}={actual} does not match derived value {expected[field]}"
            )

    overall = progress.get("overall")
    if census_status == "provisional":
        if overall is not None:
            errors.append("progress.overall must be null while the census is provisional")
    elif census_status == "frozen":
        if expected["census_maturity"] != 1.0:
            errors.append("a frozen census must map all source partitions and trace all target paths")
        expected_overall = min(expected.values())
        if not _is_number(overall) or not 0.0 <= float(overall) <= 1.0:
            errors.append("progress.overall must be a number in [0, 1] for a frozen census")
        elif abs(float(overall) - expected_overall) > 1.0e-12:
            errors.append(
                f"progress.overall={overall} does not match conservative derived value "
                f"{expected_overall}"
            )

    if schema_version == "1.0":
        milestones = document.get("milestones")
        if not isinstance(milestones, dict):
            errors.append("milestones must be an object for schema_version '1.0'")
        else:
            missing_milestones = sorted(set(MILESTONE_IDS) - set(milestones))
            unexpected_milestones = sorted(set(milestones) - set(MILESTONE_IDS))
            if missing_milestones:
                errors.append(f"milestones is missing keys: {missing_milestones}")
            if unexpected_milestones:
                errors.append(f"milestones has unexpected keys: {unexpected_milestones}")

            normalized_paths_by_id = {
                path.get("target_id"): path
                for path in normalized_paths
                if isinstance(path.get("target_id"), str)
            }
            normalized_units_by_id = {
                unit.get("capability_id"): unit
                for unit in normalized_units
                if isinstance(unit.get("capability_id"), str)
            }
            normalized_partitions_by_id = {
                partition.get("partition_id"): partition
                for partition in normalized_partitions
                if isinstance(partition.get("partition_id"), str)
            }

            expected_milestone_status: dict[str, str] = {}
            if census_status == "frozen" and expected["census_maturity"] == 1.0:
                expected_milestone_status["M0_equation_census"] = "completed"
            elif counts.get("source_partitions_mapped", 0) or counts.get(
                "target_paths_traced", 0
            ):
                expected_milestone_status["M0_equation_census"] = "in_progress"
            else:
                expected_milestone_status["M0_equation_census"] = "pending"

            m1 = milestones.get("M1_minimal_golden_path")
            m1_targets: list[str] = []
            if isinstance(m1, dict):
                m1_targets = _milestone_id_list(
                    m1,
                    "M1_minimal_golden_path",
                    "target_ids",
                    set(normalized_paths_by_id),
                    errors,
                )
            m1_states = [normalized_paths_by_id[target]["status"] for target in m1_targets]
            for target in m1_targets:
                required_ids = target_required_capabilities.get(target, set())
                if not any(
                    normalized_units_by_id.get(capability_id, {}).get("priority")
                    == "P0_primary_solution"
                    for capability_id in required_ids
                ):
                    errors.append(
                        "milestones.M1_minimal_golden_path.target_ids target must include "
                        f"a P0_primary_solution capability: {target}"
                    )
            if (
                m1_states
                and all(state == "passed" for state in m1_states)
                and expected_milestone_status["M0_equation_census"] == "completed"
            ):
                expected_milestone_status["M1_minimal_golden_path"] = "completed"
            elif any(state in {"blocked", "terminally_classified"} for state in m1_states):
                expected_milestone_status["M1_minimal_golden_path"] = "blocked"
            elif m1_states:
                expected_milestone_status["M1_minimal_golden_path"] = "in_progress"
            else:
                expected_milestone_status["M1_minimal_golden_path"] = "pending"

            m2 = milestones.get("M2_replaceable_scientific_slices")
            m2_capabilities: list[str] = []
            m2_edges: list[str] = []
            if isinstance(m2, dict):
                m2_capabilities = _milestone_id_list(
                    m2,
                    "M2_replaceable_scientific_slices",
                    "capability_ids",
                    set(normalized_units_by_id),
                    errors,
                )
                m2_edges = _milestone_id_list(
                    m2,
                    "M2_replaceable_scientific_slices",
                    "edge_ids",
                    set(normalized_edges),
                    errors,
                    allow_empty=True,
                )
            m2_units = [normalized_units_by_id[item] for item in m2_capabilities]
            m2_edge_records = [normalized_edges[item] for item in m2_edges]
            m2_capability_set = set(m2_capabilities)
            m2_target_set = {
                target
                for unit in m2_units
                for target in (
                    unit.get("required_for")
                    if isinstance(unit.get("required_for"), list)
                    else []
                )
                if isinstance(target, str)
            }
            expected_m2_edges = {
                edge_id
                for edge_id, edge in normalized_edges.items()
                if (
                    (
                        isinstance(edge.get("from_node_id"), str)
                        and edge.get("from_node_id") in m2_capability_set
                    )
                    or (
                        isinstance(edge.get("to_node_id"), str)
                        and edge.get("to_node_id") in m2_capability_set
                    )
                )
                and isinstance(edge.get("required_for"), list)
                and bool(set(edge["required_for"]) & m2_target_set)
            }
            if set(m2_edges) != expected_m2_edges:
                errors.append(
                    "milestones.M2_replaceable_scientific_slices.edge_ids must equal "
                    "the material incident edges for the selected capabilities: "
                    f"{sorted(expected_m2_edges)}"
                )
            m2_complete = bool(m2_units) and all(
                unit.get("disposition") == "emitted"
                and isinstance(unit.get("gates"), dict)
                and all(unit["gates"].get(name) == "passed" for name in GATE_NAMES)
                for unit in m2_units
            ) and all(edge.get("closure_status") == "proved" for edge in m2_edge_records)
            m2_blocked = any(
                unit.get("disposition") == "terminally_classified" for unit in m2_units
            ) or any(
                edge.get("closure_status") in {"blocked", "terminally_classified"}
                for edge in m2_edge_records
            )
            if (
                m2_complete
                and expected_milestone_status["M1_minimal_golden_path"] == "completed"
            ):
                expected_milestone_status["M2_replaceable_scientific_slices"] = "completed"
            elif m2_blocked:
                expected_milestone_status["M2_replaceable_scientific_slices"] = "blocked"
            elif m2_units or m2_edge_records:
                expected_milestone_status["M2_replaceable_scientific_slices"] = "in_progress"
            else:
                expected_milestone_status["M2_replaceable_scientific_slices"] = "pending"

            m3 = milestones.get("M3_branch_lifecycle_expansion")
            m3_partitions: list[str] = []
            if isinstance(m3, dict):
                m3_partitions = _milestone_id_list(
                    m3,
                    "M3_branch_lifecycle_expansion",
                    "partition_ids",
                    set(normalized_partitions_by_id),
                    errors,
                )
            m3_states = [
                normalized_partitions_by_id[item]["status"] for item in m3_partitions
            ]
            if set(m3_partitions) != set(normalized_partitions_by_id):
                errors.append(
                    "milestones.M3_branch_lifecycle_expansion.partition_ids must equal "
                    "the declared coverage denominator: "
                    f"{sorted(normalized_partitions_by_id)}"
                )
            if (
                m3_states
                and all(state == "proved" for state in m3_states)
                and expected_milestone_status["M2_replaceable_scientific_slices"]
                == "completed"
            ):
                expected_milestone_status["M3_branch_lifecycle_expansion"] = "completed"
            elif any(state in {"blocked", "terminally_classified"} for state in m3_states):
                expected_milestone_status["M3_branch_lifecycle_expansion"] = "blocked"
            elif m3_states:
                expected_milestone_status["M3_branch_lifecycle_expansion"] = "in_progress"
            else:
                expected_milestone_status["M3_branch_lifecycle_expansion"] = "pending"

            if census_status == "frozen" and _is_number(overall) and float(overall) == 1.0:
                expected_milestone_status["M4_extraction_freeze"] = "completed"
            elif any(
                path.get("status") in {"blocked", "terminally_classified"}
                for path in normalized_paths
            ):
                expected_milestone_status["M4_extraction_freeze"] = "blocked"
            elif all(
                expected_milestone_status.get(name) == "completed"
                for name in MILESTONE_IDS[:-1]
            ):
                expected_milestone_status["M4_extraction_freeze"] = "in_progress"
            else:
                expected_milestone_status["M4_extraction_freeze"] = "pending"

            for name in MILESTONE_IDS:
                milestone = milestones.get(name)
                if not isinstance(milestone, dict):
                    if name in milestones:
                        errors.append(f"milestones.{name} must be an object")
                    continue
                status = milestone.get("status")
                if status not in MILESTONE_STATES:
                    errors.append(
                        f"milestones.{name}.status must be one of "
                        f"{sorted(MILESTONE_STATES)}"
                    )
                    continue
                expected_status = expected_milestone_status.get(name)
                if expected_status is not None and status != expected_status:
                    errors.append(
                        f"milestones.{name}.status={status} does not match derived "
                        f"status {expected_status}"
                    )

    _validate_closure_signal(document, errors, required=require_closure_signal)
    _validate_state_and_boundary_events(document, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a scientific capability progress record")
    parser.add_argument("progress_json", type=Path)
    parser.add_argument("--scope-manifest", type=Path, required=True)
    parser.add_argument("--capability-evidence-matrix", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument(
        "--require-closure-signal",
        action="store_true",
        help="require a machine-readable active, bounded, blocked, or full-freeze stop signal",
    )
    args = parser.parse_args()
    document, load_error = load_progress_document(args.progress_json)
    if load_error is not None:
        result = {"valid": False, "errors": [load_error]}
    else:
        errors = validate_progress_document(
            document,
            require_closure_signal=args.require_closure_signal,
        )
        errors.extend(
            validate_external_bindings(
                document,
                scope_manifest=args.scope_manifest,
                capability_evidence_matrix=args.capability_evidence_matrix,
                ledger=args.ledger,
                bundle_root=args.bundle_root,
            )
        )
        result = {"valid": not errors, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

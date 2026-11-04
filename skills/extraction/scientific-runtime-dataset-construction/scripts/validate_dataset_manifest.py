from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = "source-observation-dataset/v1"
SPLITS = {"extraction", "boundary", "holdout", "scientific_oracle"}
GAP_CLASSIFICATIONS = {
    "extraction_gap",
    "configuration_or_schema_need",
    "ai_completable_glue",
    "validation_oracle_gap",
    "cannot_complete",
}
SEMANTIC_STATUSES = {
    "normal_completion",
    "target_completed_outer_failure",
    "expected_failure",
    "source_failure",
    "capture_failure",
}
REQUIRED_TOP_LEVEL = {
    "schema_version",
    "dataset_id",
    "purpose",
    "gap",
    "source",
    "conventions",
    "coverage",
    "cases",
    "artifacts",
}


class ManifestError(ValueError):
    pass


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ManifestError(f"{label} must be an array")
    return value


def _require_nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{label} must be non-empty text")
    return value


def _safe_relative_path(value: Any, label: str) -> PurePosixPath:
    text = _require_nonempty_text(value, label).replace("\\", "/")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or any(":" in part for part in path.parts):
        raise ManifestError(f"{label} must stay inside the dataset root")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_manifest(path: Path, *, check_files: bool = False) -> dict[str, int]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read JSON manifest: {exc}") from exc

    root = _require_mapping(manifest, "manifest")
    missing = sorted(REQUIRED_TOP_LEVEL - root.keys())
    if missing:
        raise ManifestError(f"missing top-level fields: {', '.join(missing)}")
    if root["schema_version"] != SCHEMA_VERSION:
        raise ManifestError(f"schema_version must be {SCHEMA_VERSION!r}")
    _require_nonempty_text(root["dataset_id"], "dataset_id")
    _require_nonempty_text(root["purpose"], "purpose")

    gap = _require_mapping(root["gap"], "gap")
    for key in ("classifications", "statement", "target_mapping", "owner"):
        if key not in gap:
            raise ManifestError(f"gap.{key} is required")
    classifications = _require_list(gap["classifications"], "gap.classifications")
    if not classifications or any(not isinstance(item, str) or not item for item in classifications):
        raise ManifestError("gap.classifications must contain non-empty strings")
    unknown_classifications = sorted(set(classifications) - GAP_CLASSIFICATIONS)
    if unknown_classifications:
        raise ManifestError(
            f"unknown gap classifications: {', '.join(unknown_classifications)}"
        )
    for key in ("statement", "target_mapping", "owner"):
        _require_nonempty_text(gap[key], f"gap.{key}")

    source = _require_mapping(root["source"], "source")
    for key in ("project", "revision", "runtime", "probe_revision", "semantic_markers"):
        if key not in source:
            raise ManifestError(f"source.{key} is required")
    for key in ("project", "revision", "runtime", "probe_revision"):
        _require_nonempty_text(source[key], f"source.{key}")
    semantic_markers = _require_list(source["semantic_markers"], "source.semantic_markers")
    if not semantic_markers or any(
        not isinstance(item, str) or not item for item in semantic_markers
    ):
        raise ManifestError("source.semantic_markers must contain non-empty strings")
    _require_mapping(root["conventions"], "conventions")

    coverage = _require_mapping(root["coverage"], "coverage")
    coverage_sets: dict[str, set[str]] = {}
    for key in ("required_partitions", "covered_partitions", "uncovered_partitions"):
        items = _require_list(coverage.get(key), f"coverage.{key}")
        if any(not isinstance(item, str) or not item for item in items):
            raise ManifestError(f"coverage.{key} must contain non-empty strings")
        if len(items) != len(set(items)):
            raise ManifestError(f"coverage.{key} contains duplicates")
        coverage_sets[key] = set(items)
    required = coverage_sets["required_partitions"]
    covered = coverage_sets["covered_partitions"]
    uncovered = coverage_sets["uncovered_partitions"]
    if covered & uncovered:
        raise ManifestError("covered and uncovered partitions overlap")
    if covered | uncovered != required:
        raise ManifestError("covered plus uncovered partitions must equal required partitions")

    artifacts = _require_list(root["artifacts"], "artifacts")
    artifact_ids: set[str] = set()
    for index, raw_artifact in enumerate(artifacts):
        artifact = _require_mapping(raw_artifact, f"artifacts[{index}]")
        for key in ("artifact_id", "path", "role", "format", "size_bytes", "sha256"):
            if key not in artifact:
                raise ManifestError(f"artifacts[{index}].{key} is required")
        artifact_id = _require_nonempty_text(
            artifact["artifact_id"], f"artifacts[{index}].artifact_id"
        )
        if artifact_id in artifact_ids:
            raise ManifestError(f"duplicate artifact_id: {artifact_id}")
        artifact_ids.add(artifact_id)
        relative = _safe_relative_path(artifact["path"], f"artifacts[{index}].path")
        _require_nonempty_text(artifact["role"], f"artifacts[{index}].role")
        _require_nonempty_text(artifact["format"], f"artifacts[{index}].format")
        size_bytes = artifact["size_bytes"]
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 0:
            raise ManifestError(f"artifacts[{index}].size_bytes must be a non-negative integer")
        expected_hash = _require_nonempty_text(
            artifact["sha256"], f"artifacts[{index}].sha256"
        ).lower()
        if len(expected_hash) != 64 or any(char not in "0123456789abcdef" for char in expected_hash):
            raise ManifestError(f"artifacts[{index}].sha256 must be 64 hexadecimal characters")
        if check_files:
            dataset_root = path.parent.resolve()
            artifact_path = dataset_root.joinpath(*relative.parts).resolve()
            if not artifact_path.is_relative_to(dataset_root):
                raise ManifestError(f"artifact escapes dataset root: {relative.as_posix()}")
            if not artifact_path.is_file():
                raise ManifestError(f"missing artifact file: {relative.as_posix()}")
            if artifact_path.stat().st_size != size_bytes:
                raise ManifestError(f"artifact size mismatch: {relative.as_posix()}")
            if _sha256(artifact_path) != expected_hash:
                raise ManifestError(f"artifact hash mismatch: {relative.as_posix()}")

    cases = _require_list(root["cases"], "cases")
    if not cases:
        raise ManifestError("cases must contain at least one executed observation")
    case_ids: set[str] = set()
    referenced_artifacts: set[str] = set()
    observed_partitions: set[str] = set()
    required_case_fields = {
        "case_id",
        "split",
        "used_for_implementation",
        "partition_ids",
        "branch_selectors",
        "boundary_tags",
        "source_input_ref",
        "predecessor_state_ref",
        "predecessor_state_not_applicable_reason",
        "target_input_ref",
        "target_output_ref",
        "process_exit_code",
        "semantic_status",
        "oracle_refs",
        "artifact_refs",
    }
    for index, raw_case in enumerate(cases):
        case = _require_mapping(raw_case, f"cases[{index}]")
        missing_case = sorted(required_case_fields - case.keys())
        if missing_case:
            raise ManifestError(
                f"cases[{index}] missing fields: {', '.join(missing_case)}"
            )
        case_id = _require_nonempty_text(case["case_id"], f"cases[{index}].case_id")
        if case_id in case_ids:
            raise ManifestError(f"duplicate case_id: {case_id}")
        case_ids.add(case_id)
        split = case["split"]
        if split not in SPLITS:
            raise ManifestError(f"cases[{index}].split must be one of {sorted(SPLITS)}")
        used = case["used_for_implementation"]
        if not isinstance(used, bool):
            raise ManifestError(f"cases[{index}].used_for_implementation must be boolean")
        if split == "holdout" and used:
            raise ManifestError(f"holdout case {case_id} cannot be used for implementation")
        partition_ids = _require_list(case["partition_ids"], f"cases[{index}].partition_ids")
        if any(item not in required for item in partition_ids):
            raise ManifestError(f"case {case_id} references an undeclared partition")
        _require_mapping(case["branch_selectors"], f"cases[{index}].branch_selectors")
        _require_list(case["boundary_tags"], f"cases[{index}].boundary_tags")
        semantic_status = case["semantic_status"]
        if semantic_status not in SEMANTIC_STATUSES:
            raise ManifestError(
                f"cases[{index}].semantic_status must be one of {sorted(SEMANTIC_STATUSES)}"
            )
        exit_code = case["process_exit_code"]
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            raise ManifestError(f"cases[{index}].process_exit_code must be an integer")
        if case["source_input_ref"] is None:
            raise ManifestError(f"cases[{index}].source_input_ref is required")
        predecessor_ref = case["predecessor_state_ref"]
        predecessor_reason = case["predecessor_state_not_applicable_reason"]
        if predecessor_ref is None:
            _require_nonempty_text(
                predecessor_reason,
                f"cases[{index}].predecessor_state_not_applicable_reason",
            )
        elif predecessor_reason is not None:
            raise ManifestError(
                f"cases[{index}].predecessor_state_not_applicable_reason must be null "
                "when predecessor_state_ref is present"
            )
        if semantic_status in {
            "normal_completion",
            "target_completed_outer_failure",
            "expected_failure",
        }:
            if case["target_input_ref"] is None:
                raise ManifestError(f"cases[{index}].target_input_ref is required")
            observed_partitions.update(partition_ids)
        if semantic_status in {"normal_completion", "target_completed_outer_failure"} and case["target_output_ref"] is None:
            raise ManifestError(f"cases[{index}].target_output_ref is required")
        if semantic_status == "target_completed_outer_failure":
            claim_scope = _require_nonempty_text(case.get("claim_scope"), f"cases[{index}].claim_scope")
            if claim_scope != "target_local_mapping":
                raise ManifestError(
                    f"cases[{index}].claim_scope must be target_local_mapping for target_completed_outer_failure"
                )
            _require_nonempty_text(case.get("outer_failure_name"), f"cases[{index}].outer_failure_name")
            receipt_refs = {
                key: _require_nonempty_text(case.get(key), f"cases[{index}].{key}")
                for key in ("target_return_receipt_ref", "outer_failure_receipt_ref")
            }
            if len(set(receipt_refs.values())) != len(receipt_refs):
                raise ManifestError(
                    f"cases[{index}] target-return and outer-failure receipts must be distinct"
                )
            artifact_refs = _require_list(case["artifact_refs"], f"cases[{index}].artifact_refs")
            for key, reference in receipt_refs.items():
                if reference not in artifact_refs:
                    raise ManifestError(f"cases[{index}].{key} must also appear in artifact_refs")
                referenced_artifacts.add(reference)
        for key in (
            "source_input_ref",
            "predecessor_state_ref",
            "target_input_ref",
            "target_output_ref",
        ):
            value = case[key]
            if value is not None:
                referenced_artifacts.add(_require_nonempty_text(value, f"cases[{index}].{key}"))
        for key in ("oracle_refs", "artifact_refs"):
            values = _require_list(case[key], f"cases[{index}].{key}")
            if any(not isinstance(item, str) or not item for item in values):
                raise ManifestError(f"cases[{index}].{key} must contain non-empty strings")
            referenced_artifacts.update(values)
        receipt = case.get("external_payload_receipt")
        if receipt is not None:
            receipt = _require_mapping(
                receipt, f"cases[{index}].external_payload_receipt"
            )
            required_receipt_fields = {
                "expected_consumer_contract",
                "emitted",
                "artifact_ref",
                "consumer_admissible",
            }
            if receipt.get("emitted") is True:
                required_receipt_fields.update(
                    {"declared_identity", "type_or_schema", "active_extent"}
                )
            elif receipt.get("emitted") is False:
                required_receipt_fields.add("classification")
            else:
                raise ManifestError(
                    f"cases[{index}].external_payload_receipt.emitted must be boolean"
                )
            missing_receipt = sorted(required_receipt_fields - receipt.keys())
            if missing_receipt:
                raise ManifestError(
                    f"cases[{index}].external_payload_receipt missing fields: "
                    f"{', '.join(missing_receipt)}"
                )
            for key in required_receipt_fields - {"emitted", "consumer_admissible"}:
                _require_nonempty_text(
                    receipt[key], f"cases[{index}].external_payload_receipt.{key}"
                )
            if not isinstance(receipt["consumer_admissible"], bool):
                raise ManifestError(
                    f"cases[{index}].external_payload_receipt.consumer_admissible must be boolean"
                )
            if receipt["emitted"] is False:
                if receipt["consumer_admissible"] is not False:
                    raise ManifestError(
                        f"cases[{index}].external_payload_receipt.consumer_admissible must be false when no payload was emitted"
                    )
                if receipt["classification"] != "configuration_or_schema_need":
                    raise ManifestError(
                        f"cases[{index}].external_payload_receipt.classification must be configuration_or_schema_need when no payload was emitted"
                    )
            artifact_ref = receipt["artifact_ref"]
            artifact_refs = _require_list(
                case["artifact_refs"], f"cases[{index}].artifact_refs"
            )
            if artifact_ref not in artifact_refs:
                raise ManifestError(
                    f"cases[{index}].external_payload_receipt.artifact_ref must also appear in artifact_refs"
                )
            referenced_artifacts.add(artifact_ref)

    unknown_artifacts = sorted(referenced_artifacts - artifact_ids)
    if unknown_artifacts:
        raise ManifestError(f"unknown artifact references: {', '.join(unknown_artifacts)}")
    if observed_partitions != covered:
        raise ManifestError("covered_partitions must exactly match partitions represented by cases")

    return {
        "cases": len(cases),
        "artifacts": len(artifacts),
        "required_partitions": len(required),
        "covered_partitions": len(covered),
    }


def _self_test() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        payload = root / "cases" / "input.json"
        payload.parent.mkdir(parents=True)
        payload.write_text('{"value": 1}\n', encoding="utf-8")
        digest = _sha256(payload)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "dataset_id": "self-test-v1",
            "purpose": "validator self-test",
            "gap": {
                "classifications": ["validation_oracle_gap"],
                "statement": "self-test",
                "target_mapping": "input -> output",
                "owner": "scientific-runtime-dataset-construction",
            },
            "source": {
                "project": "self-test",
                "revision": "frozen",
                "runtime": "source-runtime@sha256:test",
                "probe_revision": "probe-v1",
                "semantic_markers": ["NORMAL_END"],
            },
            "conventions": {},
            "coverage": {
                "required_partitions": ["interior"],
                "covered_partitions": ["interior"],
                "uncovered_partitions": [],
            },
            "cases": [
                {
                    "case_id": "case-001",
                    "split": "holdout",
                    "used_for_implementation": False,
                    "partition_ids": ["interior"],
                    "branch_selectors": {},
                    "boundary_tags": [],
                    "source_input_ref": "input",
                    "predecessor_state_ref": None,
                    "predecessor_state_not_applicable_reason": "stateless self-test",
                    "target_input_ref": "input",
                    "target_output_ref": "input",
                    "process_exit_code": 0,
                    "semantic_status": "normal_completion",
                    "oracle_refs": ["input"],
                    "artifact_refs": ["input"],
                }
            ],
            "artifacts": [
                {
                    "artifact_id": "input",
                    "path": "cases/input.json",
                    "role": "source_input",
                    "format": "json",
                    "size_bytes": payload.stat().st_size,
                    "sha256": digest,
                }
            ],
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        result = validate_manifest(manifest_path, check_files=True)
        assert result == {
            "cases": 1,
            "artifacts": 1,
            "required_partitions": 1,
            "covered_partitions": 1,
        }
        manifest["cases"][0]["external_payload_receipt"] = {"emitted": True}
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        try:
            validate_manifest(manifest_path, check_files=True)
        except ManifestError as exc:
            assert "external_payload_receipt" in str(exc)
        else:
            raise AssertionError("incomplete external payload receipt was accepted")
        manifest["cases"][0]["external_payload_receipt"] = {
            "expected_consumer_contract": "self-test scalar input",
            "emitted": True,
            "artifact_ref": "input",
            "declared_identity": "self-test-input",
            "type_or_schema": "application/json scalar",
            "active_extent": "one scalar value",
            "consumer_admissible": True,
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        assert validate_manifest(manifest_path, check_files=True) == result
        manifest["cases"][0]["external_payload_receipt"] = {
            "expected_consumer_contract": "self-test scalar input",
            "emitted": False,
            "artifact_ref": "input",
            "consumer_admissible": True,
            "classification": "configuration_or_schema_need",
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        try:
            validate_manifest(manifest_path, check_files=True)
        except ManifestError as exc:
            assert "consumer_admissible" in str(exc)
        else:
            raise AssertionError("non-emission receipt marked consumer-admissible was accepted")
        manifest["cases"][0]["external_payload_receipt"]["consumer_admissible"] = False
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        assert validate_manifest(manifest_path, check_files=True) == result
        del manifest["cases"][0]["external_payload_receipt"]
        manifest["cases"][0]["semantic_status"] = "target_completed_outer_failure"
        manifest["cases"][0]["process_exit_code"] = 1
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        try:
            validate_manifest(manifest_path, check_files=True)
        except ManifestError as exc:
            assert "claim_scope" in str(exc)
        else:
            raise AssertionError("outer-failure case without bounded claim metadata was accepted")
        target_receipt = root / "cases" / "target-return.json"
        target_receipt.write_text("{}", encoding="utf-8")
        outer_failure_receipt = root / "cases" / "outer-failure.log"
        outer_failure_receipt.write_text("later stage failed", encoding="utf-8")
        manifest["cases"][0].update(
            {
                "claim_scope": "target_local_mapping",
                "target_return_receipt_ref": "target-return",
                "outer_failure_name": "later-stage-failure",
                "outer_failure_receipt_ref": "outer-failure",
            }
        )
        manifest["cases"][0]["artifact_refs"].extend(["target-return", "outer-failure"])
        manifest["artifacts"].extend(
            [
                {
                    "artifact_id": "target-return",
                    "path": "cases/target-return.json",
                    "role": "target_return_receipt",
                    "format": "json",
                    "size_bytes": target_receipt.stat().st_size,
                    "sha256": hashlib.sha256(target_receipt.read_bytes()).hexdigest(),
                },
                {
                    "artifact_id": "outer-failure",
                    "path": "cases/outer-failure.log",
                    "role": "outer_failure_receipt",
                    "format": "text",
                    "size_bytes": outer_failure_receipt.stat().st_size,
                    "sha256": hashlib.sha256(outer_failure_receipt.read_bytes()).hexdigest(),
                },
            ]
        )
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        target_result = validate_manifest(manifest_path, check_files=True)
        assert target_result == {**result, "artifacts": 3}
        manifest["cases"][0]["semantic_status"] = "normal_completion"
        manifest["cases"][0]["process_exit_code"] = 0
        manifest["cases"][0]["used_for_implementation"] = True
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        try:
            validate_manifest(manifest_path, check_files=True)
        except ManifestError as exc:
            assert "holdout" in str(exc)
        else:
            raise AssertionError("invalid holdout manifest was accepted")
        manifest["cases"][0]["used_for_implementation"] = False
        manifest["artifacts"][0]["size_bytes"] += 1
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        try:
            validate_manifest(manifest_path, check_files=True)
        except ManifestError as exc:
            assert "size mismatch" in str(exc)
        else:
            raise AssertionError("artifact size mismatch was accepted")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a source-observation dataset manifest.")
    parser.add_argument("manifest", nargs="?", type=Path)
    parser.add_argument("--check-files", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        _self_test()
        print("self-test=ok")
        return 0
    if args.manifest is None:
        parser.error("manifest is required unless --self-test is used")
    result = validate_manifest(args.manifest, check_files=args.check_files)
    print(json.dumps({"valid": True, **result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

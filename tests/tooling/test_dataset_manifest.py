"""直接测试 skills 内的数据集验证器：加载真实脚本，不复制算法。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / "skills/development/scientific-runtime-dataset-construction"
VALIDATOR = SKILL_DIR / "scripts/validate_dataset_manifest.py"
SKILL = SKILL_DIR / "SKILL.md"


def _load_validator():
    spec = importlib.util.spec_from_file_location("dataset_manifest_under_test", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(payload: Path) -> dict:
    return {
        "schema_version": "source-observation-dataset/v1",
        "dataset_id": "tooling-test-v1",
        "purpose": "validator behaviour test",
        "gap": {
            "classifications": ["validation_oracle_gap"],
            "statement": "tooling test",
            "target_mapping": "input -> output",
            "owner": "scientific-runtime-dataset-construction",
        },
        "source": {
            "project": "tooling-test",
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
                "predecessor_state_not_applicable_reason": "stateless tooling test",
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
                "sha256": _digest(payload),
            }
        ],
    }


def _write_package(root: Path, **changes) -> Path:
    payload = root / "cases" / "input.json"
    payload.parent.mkdir(parents=True)
    payload.write_text('{"value": 1}\n', encoding="utf-8")
    manifest = _manifest(payload)
    for key, value in changes.items():
        manifest[key] = value
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_the_loaded_module_is_the_skills_script():
    module = _load_validator()
    assert Path(module.__file__).resolve() == VALIDATOR.resolve()
    assert module.SCHEMA_VERSION == "source-observation-dataset/v1"


def test_skill_documents_the_entry_point_and_next_step():
    text = SKILL.read_text(encoding="utf-8")
    assert "scripts/validate_dataset_manifest.py" in text
    assert "--check-files" in text
    assert "--self-test" in text


def test_a_minimal_valid_package_passes_with_counts(tmp_path):
    module = _load_validator()
    package = _write_package(tmp_path)
    assert module.validate_manifest(package, check_files=True) == {
        "cases": 1,
        "artifacts": 1,
        "required_partitions": 1,
        "covered_partitions": 1,
    }


def test_missing_top_level_field_is_named(tmp_path):
    module = _load_validator()
    package = _write_package(tmp_path)
    manifest = json.loads(package.read_text(encoding="utf-8"))
    del manifest["purpose"]
    package.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(module.ManifestError, match="purpose"):
        module.validate_manifest(package, check_files=True)


def test_artifact_hash_mismatch_is_named(tmp_path):
    module = _load_validator()
    package = _write_package(tmp_path)
    manifest = json.loads(package.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["sha256"] = "0" * 64
    package.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(module.ManifestError, match="hash mismatch"):
        module.validate_manifest(package, check_files=True)


def test_artifact_size_mismatch_is_named(tmp_path):
    module = _load_validator()
    package = _write_package(tmp_path)
    manifest = json.loads(package.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["size_bytes"] += 1
    package.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(module.ManifestError, match="size mismatch"):
        module.validate_manifest(package, check_files=True)


def test_holdout_case_used_for_implementation_is_rejected(tmp_path):
    module = _load_validator()
    package = _write_package(tmp_path)
    manifest = json.loads(package.read_text(encoding="utf-8"))
    manifest["cases"][0]["used_for_implementation"] = True
    package.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(module.ManifestError, match="holdout"):
        module.validate_manifest(package, check_files=True)


def test_artifact_path_escaping_the_dataset_root_is_rejected(tmp_path):
    module = _load_validator()
    package = _write_package(tmp_path)
    manifest = json.loads(package.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["path"] = "../outside.json"
    package.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(module.ManifestError, match="inside the dataset root"):
        module.validate_manifest(package, check_files=True)


def test_coverage_partitions_must_match_the_cases(tmp_path):
    module = _load_validator()
    package = _write_package(tmp_path)
    manifest = json.loads(package.read_text(encoding="utf-8"))
    manifest["coverage"]["uncovered_partitions"] = ["other"]
    manifest["coverage"]["covered_partitions"] = ["interior"]
    package.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(module.ManifestError, match="covered plus uncovered"):
        module.validate_manifest(package, check_files=True)


def test_unknown_artifact_reference_is_named(tmp_path):
    module = _load_validator()
    package = _write_package(tmp_path)
    manifest = json.loads(package.read_text(encoding="utf-8"))
    manifest["cases"][0]["oracle_refs"] = ["missing-artifact"]
    package.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(module.ManifestError, match="unknown artifact references"):
        module.validate_manifest(package, check_files=True)


def _run_cli(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *arguments],
        capture_output=True,
        text=True,
    )


def test_cli_reports_a_valid_package_with_exit_zero(tmp_path):
    package = _write_package(tmp_path)
    done = _run_cli(str(package), "--check-files")
    assert done.returncode == 0, done.stderr
    report = json.loads(done.stdout)
    assert report["valid"] is True
    assert report["cases"] == 1 and report["artifacts"] == 1


def test_cli_exit_code_and_located_error_on_a_broken_package(tmp_path):
    package = _write_package(tmp_path)
    manifest = json.loads(package.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["sha256"] = "f" * 64
    package.write_text(json.dumps(manifest), encoding="utf-8")

    done = _run_cli(str(package), "--check-files")

    assert done.returncode != 0
    assert "hash mismatch" in done.stderr
    assert "cases/input.json" in done.stderr


def test_cli_requires_a_manifest_unless_self_test_runs():
    done = _run_cli()
    assert done.returncode == 2
    assert "manifest is required" in done.stderr

    self_test = _run_cli("--self-test")
    assert self_test.returncode == 0
    assert "self-test=ok" in self_test.stdout

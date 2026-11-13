"""The requirements-case validator runs from the skill and enforces the case contract."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/extraction/scientific-requirements-extraction"
SCRIPT = SKILL / "scripts/validate_package.py"
CASE_NAME = "示例题目"


def _load():
    spec = importlib.util.spec_from_file_location("requirement_case_package_validator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _manifest(**overrides) -> dict:
    manifest = {
        "id": "demo-requirement-case",
        "title": CASE_NAME,
        "status": "candidate",
        "coverage": ["demo-capability"],
        "replay": "replay.py",
        "public": {
            "statement": "题面/problem.md",
            "inputs": ["题面/inputs.json"],
            "output_spec": "题面/output-spec.json",
            "acceptance": "题面/acceptance.md",
        },
        "private": {"provenance": "参考/provenance.json"},
        "open_issues": ["HOLD: 参考运行与比较器尚未取得"],
        "scientific_review": "pending",
    }
    manifest.update(overrides)
    return manifest


def _candidate(tmp_path: Path, manifest: dict | None = None) -> Path:
    root = tmp_path / CASE_NAME
    for name in ["problem.md", "inputs.json", "output-spec.json", "acceptance.md"]:
        _write(root / "题面" / name, f"题面材料 {name}\n")
    _write(
        root / "参考/provenance.json",
        json.dumps({"source_revision": "abc123", "anchors": ["p.3 eq.2"]}, ensure_ascii=False),
    )
    _write(root / "case.json", json.dumps(manifest or _manifest(), ensure_ascii=False, indent=2))
    return root


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=ROOT
    )


def test_the_loaded_module_is_the_script_the_skill_tells_agents_to_run():
    assert Path(validator.__file__).resolve() == SCRIPT.resolve()
    documented = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "scripts/validate_package.py" in documented
    # No repository-level copy may stand in for the skill's own validator.
    assert not (ROOT / "scripts/validate_package.py").exists()


def test_a_minimal_candidate_packet_passes_and_names_each_held_back_material(tmp_path):
    result = validator.validate(_candidate(tmp_path))

    assert result["status"] == "PASS"
    assert result["errors"] == []
    assert result["case_id"] == "demo-requirement-case"
    assert result["case_status"] == "candidate"
    assert result["scientific_approval"] is False
    assert {warning.split("missing ", 1)[1] for warning in result["warnings"]} == {
        "private.source_bundle",
        "private.source_licenses",
        "private.runtime_manifest",
        "private.replay_contract",
        "replay",
        "private.reference_run",
        "private.replay_run",
        "private.comparator",
    }


def test_require_reference_rejects_the_candidate_that_holds_only_public_material(tmp_path):
    result = validator.validate(_candidate(tmp_path), require_reference=True)

    assert result["status"] == "FAIL"
    for key in [
        "source_bundle",
        "source_licenses",
        "runtime_manifest",
        "replay_contract",
        "reference_run",
        "replay_run",
        "comparator",
    ]:
        assert f"private.{key}: required for a reference-reproduced case" in result["errors"]
    assert "replay: file does not exist" in result["errors"]


def test_a_reference_reproduced_status_gates_the_same_material_without_the_flag(tmp_path):
    result = validator.validate(_candidate(tmp_path, _manifest(status="reference-reproduced")))

    assert result["status"] == "FAIL"
    assert "private.source_bundle: required for a reference-reproduced case" in result["errors"]
    assert "private.replay_run: required for a reference-reproduced case" in result["errors"]


@pytest.mark.parametrize(
    "declared",
    [
        "题面/../secret.md",
        "../题面/problem.md",
        "/etc/passwd",
        "题面\\problem.md",
        "C:/secret.md",
        "参考/provenance.json",
    ],
)
def test_a_declared_member_outside_the_case_root_is_rejected(tmp_path, declared):
    manifest = _manifest()
    manifest["public"]["inputs"] = [declared]

    result = validator.validate(_candidate(tmp_path, manifest))

    assert result["status"] == "FAIL"
    assert "public.inputs[0]: path must stay below 题面/" in result["errors"]


def test_linked_material_is_rejected_even_when_its_target_is_a_real_file(tmp_path):
    outside = _write(tmp_path / "outside.json", '{"secret": true}\n')
    root = _candidate(tmp_path)
    (root / "题面/inputs.json").unlink()
    os.symlink(outside, root / "题面/inputs.json")

    result = validator.validate(root)

    assert result["status"] == "FAIL"
    assert "case_root: linked member 题面/inputs.json" in result["errors"]
    rejected_member = "public.inputs[0]: links/reparse points are not accepted packet members"
    assert rejected_member in result["errors"]


def test_a_frozen_case_without_accepted_review_is_rejected(tmp_path):
    root = _candidate(tmp_path, _manifest(status="frozen", scientific_review="pending"))

    result = validator.validate(root)

    assert result["status"] == "FAIL"
    assert "frozen: accepted scientific review required" in result["errors"]


@pytest.mark.parametrize(
    ("review_record", "expected"),
    [
        (None, "private.review_record: nonempty relative path required"),
        ("参考/review-record.json", "private.review_record: file does not exist"),
    ],
)
def test_a_frozen_case_does_not_upgrade_itself_without_a_review_record(
    tmp_path, review_record, expected
):
    root = _candidate(tmp_path, _manifest(status="frozen", scientific_review="accepted"))
    manifest = json.loads((root / "case.json").read_text(encoding="utf-8"))
    if review_record is not None:
        manifest["private"]["review_record"] = review_record
    _write(root / "case.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    result = validator.validate(root)

    assert result["status"] == "FAIL"
    assert expected in result["errors"]


def test_a_dependency_lock_of_comments_and_punctuation_is_not_a_lock(tmp_path):
    root = _candidate(tmp_path)
    _write(root / "参考/runtime/README.md", "# 配方\n构建并运行 replay.py。\n")
    _write(root / "参考/runtime/Dockerfile", "FROM python:3.14-slim\n")
    _write(root / "参考/runtime/requirements.lock", "# 捕获失败\n==\n")
    _write(
        root / "参考/runtime/runtime.json",
        json.dumps(
            {
                "recipe": "参考/runtime/README.md",
                "dockerfile": "参考/runtime/Dockerfile",
                "dependency_locks": ["参考/runtime/requirements.lock"],
                "external_dependencies": [
                    {"kind": "oci-image", "identity": "python@sha256:demo", "purpose": "runtime"}
                ],
            },
            ensure_ascii=False,
        ),
    )
    manifest = _manifest()
    manifest["private"]["runtime_manifest"] = "参考/runtime/runtime.json"
    _write(root / "case.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    result = validator.validate(root)

    assert result["status"] == "FAIL"
    empty_lock = (
        "runtime.dependency_locks[0]: no dependency entries; captured lock contains only "
        "whitespace, comments or punctuation"
    )
    assert empty_lock in result["errors"]


def test_the_command_line_accepts_the_minimal_candidate(tmp_path):
    completed = _run(str(_candidate(tmp_path)))

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["status"] == "PASS"


def test_the_command_line_names_the_declaration_that_breaks_the_case(tmp_path):
    manifest = _manifest(
        replay="run.py",
        status="reference-ready",
        coverage=["demo-capability", "demo-capability"],
    )

    completed = _run(str(_candidate(tmp_path, manifest)))

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["status"] == "FAIL"
    assert "replay: expected the case-root entrypoint replay.py" in payload["errors"]
    assert "status: expected candidate, reference-reproduced or frozen" in payload["errors"]
    assert "coverage: duplicate capability IDs" in payload["errors"]


def test_the_command_line_fails_and_localizes_missing_reference_material(tmp_path):
    completed = _run(str(_candidate(tmp_path)), "--require-reference")

    assert completed.returncode == 1
    errors = json.loads(completed.stdout)["errors"]
    assert "private.source_bundle: required for a reference-reproduced case" in errors
    assert "private.comparator: required for a reference-reproduced case" in errors

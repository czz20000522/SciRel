"""Exercise public producer boundaries without importing payload callables."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "prepare_admission", ROOT / "scripts/prepare_admission.py"
)
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)


def _inputs(tmp_path):
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "LICENSE").write_bytes(b"MIT format fixture\n")
    (payload / "implementation.py").write_bytes(
        b"raise RuntimeError('must never execute payload')\n"
    )
    metadata = tmp_path / "metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "project_id": "fixture",
                "decomposition_scope": "partial",
                "limitations": ["format only"],
                "claim_ceiling": "not scientific approval",
                "evidence_policy": "exact bytes",
                "custody_note": "new output",
                "license": {"spdx": "MIT", "references": ["LICENSE"]},
            }
        ),
        encoding="utf-8",
    )
    return payload, metadata


def test_partial_fixed_point_and_exact_empty_map(tmp_path):
    payload, metadata = _inputs(tmp_path)
    output = tmp_path / "FINAL"
    before = metadata.read_bytes()
    report = producer.prepare(payload, metadata, output)
    assert report["status"] == "PASS", report
    assert report["scientific_acceptance"] == "NOT_ASSESSED"
    assert metadata.read_bytes() == before
    assert (output / "PATH_MAP.json").read_bytes() == b"{}\n"
    final = json.loads((output / "FINAL.json").read_text())
    files = json.loads((output / "FILES.json").read_text())["files"]
    assert final["payload_files"] == len(files) == 4
    assert final["payload_bytes"] == sum(f["bytes"] for f in files)
    assert final["payload_bytes"] == sum((output / f["path"]).stat().st_size for f in files)
    assert producer.admission.validate(output)["status"] == "PASS"


def test_direct_alias_has_no_copied_payload(tmp_path):
    payload, metadata = _inputs(tmp_path)
    aliases = tmp_path / "aliases.json"
    aliases.write_text('{"logical/license":"LICENSE"}\n')
    output = tmp_path / "FINAL"
    assert producer.prepare(payload, metadata, output, aliases)["status"] == "PASS"
    assert not (output / "logical").exists()
    assert len(json.loads((output / "FILES.json").read_text())["files"]) == 4


@pytest.mark.parametrize("encoding", ["ascii", "gbk"])
def test_producer_cli_reports_unicode_paths_and_invalid_alias_with_restricted_stdout(
    tmp_path, encoding
):
    payload, metadata = _inputs(tmp_path)
    cwd = tmp_path / "cwd-¹"
    cwd.mkdir()
    aliases = tmp_path / "aliases.json"
    aliases.write_bytes(producer.admission.json_bytes({"COM¹.txt": "LICENSE"}))
    for expected, code in [("PASS", 0), ("FAIL", 1)]:
        output = cwd / f"{expected}-FINAL-¹"
        args = ["--payload", payload, "--metadata", metadata, "--output", output]
        if expected == "FAIL":
            args += ["--path-map", aliases]
        run = subprocess.run(
            [
                sys.executable,
                "-S",
                "-B",
                str(ROOT / "scripts/prepare_admission.py"),
                *map(str, args),
            ],
            cwd=cwd,
            capture_output=True,
            timeout=30,
            env=dict(os.environ, PYTHONIOENCODING=encoding),
        )
        assert run.stderr == b""
        assert run.returncode == code
        report = json.loads(run.stdout.decode("ascii"))
        assert report["status"] == expected
        assert report["directory"] == str(output)
        if expected == "FAIL":
            assert any("COM¹.txt" in error for error in report["errors"])
            assert not output.exists()


@pytest.mark.parametrize(
    "mapping",
    [
        {"LICENSE": "LICENSE"},
        {"logical": "missing"},
        {"logical": "FINAL.json"},
        {"first": "second", "second": "LICENSE"},
        {"../escape": "LICENSE"},
        {"C:/drive": "LICENSE"},
        {"logical": "a\\b"},
        {"LICENSE/child": "LICENSE"},
        {"FILES.json/child": "LICENSE"},
        {"ROOT.sha256/child": "LICENSE"},
        {"logical": "LICENSE", "logical/child": "LICENSE"},
        {"logical/child": "LICENSE", "logical": "LICENSE"},
        {"Logical": "LICENSE", "logical/child": "LICENSE"},
        {"portable/com¹.txt": "LICENSE"},
        {"portable/LPT³": "LICENSE"},
        {"license": "LICENSE"},
        {"a": "LICENSE", "A": "LICENSE"},
        {"bad": []},
        ["bad"],
    ],
)
def test_bad_aliases_are_zero_write_preflight_failures(tmp_path, mapping):
    payload, metadata = _inputs(tmp_path)
    aliases = tmp_path / "aliases.json"
    aliases.write_text(json.dumps(mapping))
    output = tmp_path / "FINAL"
    assert producer.prepare(payload, metadata, output, aliases)["status"] == "FAIL"
    assert not output.exists()


@pytest.mark.parametrize("key", sorted(producer.admission.DERIVED_KEYS))
def test_derived_metadata_rejected_before_writing(tmp_path, key):
    payload, metadata = _inputs(tmp_path)
    data = json.loads(metadata.read_text())
    data[key] = "must not have two truths"
    metadata.write_text(json.dumps(data))
    output = tmp_path / "FINAL"
    assert producer.prepare(payload, metadata, output)["status"] == "FAIL"
    assert not output.exists()


@pytest.mark.parametrize("name", sorted(producer.admission.CONTROLS))
def test_payload_control_rejected_before_writing(tmp_path, name):
    payload, metadata = _inputs(tmp_path)
    (payload / name).write_bytes(b"frozen-control")
    output = tmp_path / "FINAL"
    assert producer.prepare(payload, metadata, output)["status"] == "FAIL"
    assert not output.exists()


def test_never_overwrites_existing_output_or_input(tmp_path):
    payload, metadata = _inputs(tmp_path)
    before = (payload / "LICENSE").read_bytes()
    assert producer.prepare(payload, metadata, payload)["status"] == "FAIL"
    assert (payload / "LICENSE").read_bytes() == before
    assert producer.prepare(payload, metadata, payload / "nested")["status"] == "FAIL"
    assert not (payload / "nested").exists()
    output = tmp_path / "FINAL"
    output.mkdir()
    (output / "marker").write_bytes(b"keep")
    assert producer.prepare(payload, metadata, output)["status"] == "FAIL"
    assert (output / "marker").read_bytes() == b"keep"


def test_missing_input_reports_not_run_without_output(tmp_path):
    report = producer.prepare(tmp_path / "absent", tmp_path / "absent.json", tmp_path / "FINAL")
    assert report["status"] == "NOT_RUN"
    assert not (tmp_path / "FINAL").exists()


def test_failed_new_directory_is_retained(tmp_path, monkeypatch):
    payload, metadata = _inputs(tmp_path)
    output = tmp_path / "FINAL"

    def fail_copy(*args):
        raise OSError("simulated copy failure")

    monkeypatch.setattr(producer.shutil, "copyfile", fail_copy)
    report = producer.prepare(payload, metadata, output)
    assert report["status"] == "FAIL"
    assert report["retained_output"] == str(output)
    assert output.is_dir()


def test_public_minimal_partial_example(tmp_path):
    example = ROOT / "contracts/admission/examples/minimal-partial"
    report = producer.prepare(example / "payload", example / "metadata.json", tmp_path / "FINAL")
    assert report["status"] == "PASS", report

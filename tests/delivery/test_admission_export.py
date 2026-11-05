"""An exported toolset boots using stdlib only from an unrelated cwd."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "export_admission_tools", ROOT / "scripts/export_admission_tools.py"
)
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)


def _run(script, args, cwd):
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(script), *map(str, args)],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_export_identity_and_cold_producer_validator(tmp_path):
    tools = tmp_path / "tools"
    report = exporter.export(tools)
    assert report["status"] == "PASS", report
    manifest = json.loads((tools / "TOOLS.json").read_text())
    entries = manifest["files"]
    assert (
        manifest["identity_sha256"]
        == hashlib.sha256(exporter.admission.json_bytes(entries)).hexdigest()
    )
    expected = {item["path"] for item in entries} | {"TOOLS.json"}
    assert expected == {p.relative_to(tools).as_posix() for p in tools.rglob("*") if p.is_file()}
    for item in entries:
        data = (tools / item["path"]).read_bytes()
        assert len(data) == item["bytes"]
        assert hashlib.sha256(data).hexdigest() == item["sha256"]
        assert item["path"].startswith(("scripts/", "contracts/admission/"))
    stranger = tmp_path / "stranger"
    stranger.mkdir()
    example = tools / "contracts/admission/examples/minimal-partial"
    output = stranger / "FINAL"
    producer_report = _run(
        tools / "scripts/prepare_admission.py",
        [
            "--payload",
            example / "payload",
            "--metadata",
            example / "metadata.json",
            "--output",
            output,
        ],
        stranger,
    )
    assert producer_report["status"] == "PASS"
    validated = _run(tools / "scripts/validate_admission.py", [output], stranger)
    assert validated["status"] == "PASS"
    # The exporter itself can also run without the repository or installed deps.
    cloned = stranger / "tools-again"
    _run(tools / "scripts/export_admission_tools.py", ["--output", cloned], stranger)
    assert (cloned / "TOOLS.json").read_bytes() == (tools / "TOOLS.json").read_bytes()


def test_export_refuses_existing_or_source_directory(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "marker"
    marker.write_bytes(b"keep")
    assert exporter.export(output)["status"] == "FAIL"
    assert marker.read_bytes() == b"keep"
    assert exporter.export(ROOT / "contracts/admission/nested-output")["status"] == "FAIL"
    assert not (ROOT / "contracts/admission/nested-output").exists()


@pytest.mark.parametrize("encoding", ["ascii", "gbk"])
def test_export_cli_reports_unicode_paths_with_restricted_stdout(tmp_path, encoding):
    cwd = tmp_path / "cwd-¹"
    cwd.mkdir()
    output = cwd / "tools-¹"
    for expected, code in [("PASS", 0), ("FAIL", 1)]:
        run = subprocess.run(
            [
                sys.executable,
                "-S",
                "-B",
                str(ROOT / "scripts/export_admission_tools.py"),
                "--output",
                str(output),
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

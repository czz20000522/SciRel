"""SciRel admission: the single external submission interface."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validate_admission", ROOT / "scripts" / "validate_admission.py")
admission = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(admission)


def _write_final(directory: Path, *, path_map_bytes=b"{}\n", **overrides) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "d0").mkdir(exist_ok=True)
    (directory / "d1").mkdir(exist_ok=True)
    source = directory / "d0" / "source.txt"
    report = directory / "d1" / "report.json"
    source.write_bytes(b"source-bytes\n")
    report.write_bytes(b'{"status":"ok"}\n')
    path_map = directory / "PATH_MAP.json"
    path_map.write_bytes(path_map_bytes)
    final = {
        "schema": "scirel.project-final",
        "project_id": "example",
        "decomposition_scope": "bounded core; stage prefix only",
        "limitations": ["only the declared inputs were tested"],
        "claim_ceiling": "does not establish continuum validity or universal inputs",
        "files": "FILES.json",
        "path_map": "PATH_MAP.json",
        "root_binding": "ROOT.sha256",
        "payload_files": 4,
        "payload_bytes": 1,
        "evidence_policy": "observations apply to the exact candidates only",
        "custody_note": "only this FINAL is the external result entrypoint",
        "license": {"spdx": "MIT", "references": ["d0/source.txt"]},
    }
    final.update(overrides)
    while True:
        final_path = directory / "FINAL.json"
        final_path.write_text(json.dumps(final, indent=1) + "\n", encoding="utf-8")
        total = sum(path.stat().st_size for path in (final_path, path_map, source, report))
        if final["payload_bytes"] == total:
            break
        final["payload_bytes"] = total
    entries = []
    for name in sorted({"FINAL.json", "PATH_MAP.json", "d0/source.txt", "d1/report.json"}):
        target = directory / name
        entries.append({"path": name, "bytes": target.stat().st_size,
                        "sha256": admission._sha(target)})
    (directory / "FILES.json").write_text(
        json.dumps({"schema": "scirel.final-files", "files": entries}, indent=1) + "\n",
        encoding="utf-8")
    admission._emit_root(directory)
    return directory


def test_valid_submission_passes(tmp_path):
    report = admission.validate(_write_final(tmp_path / "FINAL"))
    assert report["status"] == "PASS", report["errors"]


@pytest.mark.parametrize("data", [b"{ }\r\n", b"{}\r\n", b"{ }\n", b"{}"])
def test_empty_path_map_requires_exact_wire_bytes(tmp_path, data):
    final = _write_final(tmp_path / "FINAL", path_map_bytes=data)
    report = admission.validate(final)
    assert report["status"] == "FAIL"
    assert any("empty object must be exactly" in error for error in report["errors"])
    assert not any("mismatch" in error or "binding" in error for error in report["errors"])


@pytest.mark.parametrize("control", sorted(admission.CONTROLS))
def test_alias_cannot_be_nested_under_any_control_file(tmp_path, control):
    mapping = {f"{control.swapcase()}/child": "d0/source.txt"}
    final = _write_final(tmp_path / "FINAL", path_map_bytes=admission.json_bytes(mapping))
    report = admission.validate(final)
    assert report["status"] == "FAIL"
    assert any("nested under a stored file" in error for error in report["errors"])


@pytest.mark.parametrize("aliases", [("logical", "logical/child"), ("logical/child", "logical"),
                                     ("Logical", "logical/child")])
def test_file_aliases_cannot_be_nested(tmp_path, aliases):
    mapping = dict.fromkeys(aliases, "d0/source.txt")
    final = _write_final(tmp_path / "FINAL", path_map_bytes=admission.json_bytes(mapping))
    report = admission.validate(final)
    assert report["status"] == "FAIL"
    assert any("nested under another file alias" in error for error in report["errors"])


def test_tampered_final_breaks_root_binding(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    (final / "FINAL.json").write_text(
        (final / "FINAL.json").read_text() + " ", encoding="utf-8")
    report = admission.validate(final)
    assert report["status"] == "FAIL"
    assert any("ROOT.sha256" in error or "payload digest" in error for error in report["errors"])


def test_missing_claim_ceiling_rejected(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    payload = json.loads((final / "FINAL.json").read_text())
    payload.pop("claim_ceiling")
    (final / "FINAL.json").write_text(json.dumps(payload, indent=1) + "\n")
    admission._emit_root(final)
    report = admission.validate(final)
    assert report["status"] == "FAIL"
    assert any("claim_ceiling" in error for error in report["errors"])


def test_license_reference_must_be_a_member(tmp_path):
    final = _write_final(tmp_path / "FINAL", license={"spdx": "MIT", "references": ["NOTICE"]})
    admission._emit_root(final)
    report = admission.validate(final)
    assert report["status"] == "FAIL"
    assert any("license reference" in error for error in report["errors"])


def test_unsorted_manifest_rejected(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    manifest = json.loads((final / "FILES.json").read_text())
    manifest["files"].reverse()
    (final / "FILES.json").write_text(json.dumps(manifest, indent=1) + "\n")
    admission._emit_root(final)
    report = admission.validate(final)
    assert report["status"] == "FAIL"
    assert any("sorted" in error for error in report["errors"])


def test_payload_count_mismatch_rejected(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    payload = json.loads((final / "FINAL.json").read_text())
    payload["payload_files"] = 99
    (final / "FINAL.json").write_text(json.dumps(payload, indent=1) + "\n")
    admission._emit_root(final)
    report = admission.validate(final)
    assert report["status"] == "FAIL"
    assert any("payload_files" in error for error in report["errors"])


def test_missing_control_files_are_not_run(tmp_path):
    empty = tmp_path / "FINAL"
    empty.mkdir()
    report = admission.validate(empty)
    assert report["status"] == "NOT_RUN"
    assert admission.main([str(empty)]) == 2


def test_cli_writes_report(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    output = tmp_path / "report.json"
    assert admission.main([str(final), "--output", str(output)]) == 0
    assert json.loads(output.read_text())["status"] == "PASS"


@pytest.mark.parametrize("encoding", ["ascii", "gbk"])
def test_validator_cli_reports_unicode_paths_and_invalid_alias_with_restricted_stdout(tmp_path, encoding):
    cwd = tmp_path / "cwd-¹"
    cwd.mkdir()
    valid = _write_final(cwd / "valid-FINAL-¹")
    invalid = _write_final(cwd / "invalid-FINAL", path_map_bytes=admission.json_bytes({
        "COM¹.txt": "d0/source.txt"}))
    for final, expected, code in [(valid, "PASS", 0), (invalid, "FAIL", 1)]:
        run = subprocess.run([sys.executable, "-S", "-B", str(ROOT / "scripts/validate_admission.py"),
                              str(final)], cwd=cwd, capture_output=True, timeout=30,
                             env=dict(os.environ, PYTHONIOENCODING=encoding))
        assert run.stderr == b""
        assert run.returncode == code
        report = json.loads(run.stdout.decode("ascii"))
        assert report["status"] == expected
        assert report["directory"] == str(final)
        if expected == "FAIL":
            assert any("COM¹.txt" in error for error in report["errors"])


def test_unlisted_file_is_rejected(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    (final / "unlisted.txt").write_bytes(b"not bound")
    assert admission.validate(final)["status"] == "FAIL"


@pytest.mark.parametrize("entries", [[None], [{"path": []}], [42], ["payload"]])
def test_malformed_manifest_never_crashes(tmp_path, entries):
    final = _write_final(tmp_path / "FINAL")
    (final / "FILES.json").write_text(json.dumps({"schema": "scirel.final-files", "files": entries}))
    assert admission.validate(final)["status"] == "FAIL"


@pytest.mark.parametrize("field,value", [("identity", {"runtime": 3}), ("stage_evidence", ["bad"]),
                                        ("stage_evidence", {"D1": []})])
def test_schema_object_values_are_checked(tmp_path, field, value):
    final = _write_final(tmp_path / "FINAL", **{field: value})
    assert admission.validate(final)["status"] == "FAIL"


def test_unknown_manifest_property_is_rejected(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    manifest = json.loads((final / "FILES.json").read_text())
    manifest["extra"] = True
    (final / "FILES.json").write_text(json.dumps(manifest))
    admission._emit_root(final)
    assert admission.validate(final)["status"] == "FAIL"


@pytest.mark.parametrize("path", ["C:/outside", "C:outside", "//server/share", "a\\b",
                                  "../outside", "a/./b", "a//b", "a/\x00b", "a\nb"])
def test_unsafe_paths_are_rejected(path):
    errors = []
    assert not admission._safe_relative(path, errors, "test")
    assert errors


@pytest.mark.parametrize("character", '<>:"|?*')
def test_windows_forbidden_filename_characters_are_rejected(character):
    errors = []
    assert not admission._safe_relative(f"folder/a{character}b.txt", errors, "test")
    assert errors


@pytest.mark.parametrize("device", ["COM", "LPT"])
@pytest.mark.parametrize("number", "123456789¹²³")
@pytest.mark.parametrize("suffix", ["", ".txt"])
def test_windows_reserved_numbered_devices_are_rejected(device, number, suffix):
    errors = []
    assert not admission._safe_relative(f"folder/{device.lower()}{number}{suffix}", errors, "test")
    assert errors


def test_nonempty_alias_must_target_payload(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    (final / "PATH_MAP.json").write_text('{"logical":"missing"}\n')
    report = admission.validate(final, emit_root=True)
    assert report["status"] == "FAIL"


def test_emit_root_with_missing_control_is_not_run(tmp_path):
    final = tmp_path / "FINAL"
    final.mkdir()
    report = admission.validate(final, emit_root=True)
    assert report["status"] == "NOT_RUN"
    assert not (final / "ROOT.sha256").exists()


def test_report_cannot_mutate_package(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    before = (final / "FINAL.json").read_bytes()
    assert admission.main([str(final), "--output", str(final / "FINAL.json")]) == 1
    assert (final / "FINAL.json").read_bytes() == before


def test_root_wire_is_exact_lf(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    data = (final / "ROOT.sha256").read_bytes()
    assert b"\r" not in data
    assert [line.split(b"  ")[1] for line in data.splitlines()] == [
        b"ROOT.sha256", b"FINAL.json", b"FILES.json", b"PATH_MAP.json"]


def _directory_link(link, target):
    if os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                                capture_output=True, timeout=10)
        assert result.returncode == 0, result.stderr
    else:
        link.symlink_to(target, target_is_directory=True)


@pytest.mark.parametrize("location", ["root", "ancestor", "member"])
def test_links_rejected_before_emit_or_payload_reads(tmp_path, location):
    final = _write_final(tmp_path / "real" / "FINAL")
    before = (final / "ROOT.sha256").read_bytes()
    if location == "root":
        link = tmp_path / "linked-final"
        _directory_link(link, final)
        observed = link
    elif location == "ancestor":
        link = tmp_path / "linked-parent"
        _directory_link(link, final.parent)
        observed = link / "FINAL"
    else:
        target = tmp_path / "outside"
        target.mkdir()
        _directory_link(final / "linked-member", target)
        observed = final
    report = admission.validate(observed, emit_root=True)
    assert report["status"] == "FAIL"
    assert any("reparse" in e for e in report["errors"])
    assert (final / "ROOT.sha256").read_bytes() == before


def test_hardlinked_root_is_never_overwritten(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    outside = tmp_path / "external-root"
    os.link(final / "ROOT.sha256", outside)
    before = outside.read_bytes()
    assert admission.validate(final, emit_root=True)["status"] == "FAIL"
    assert outside.read_bytes() == before


def test_report_hardlink_cannot_mutate_package(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    outside = tmp_path / "external-report.json"
    os.link(final / "FINAL.json", outside)
    before = outside.read_bytes()
    assert admission.main([str(final), "--output", str(outside)]) == 1
    assert (final / "FINAL.json").read_bytes() == before


def test_schema_unknown_keyword_fails_even_in_absent_optional_property(tmp_path, monkeypatch):
    final = _write_final(tmp_path / "FINAL")
    schema = json.loads(admission.FINAL_SCHEMA.read_text())
    schema["properties"]["identity"]["minProperties"] = 1
    path = tmp_path / "unsupported.schema.json"
    path.write_text(json.dumps(schema))
    monkeypatch.setattr(admission, "FINAL_SCHEMA", path)
    report = admission.validate(final)
    assert report["status"] == "FAIL"
    assert any("unsupported schema" in e for e in report["errors"])


def test_duplicate_control_json_keys_fail(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    (final / "PATH_MAP.json").write_bytes(b'{"alias":"d0/source.txt","alias":"d1/report.json"}\n')
    assert admission.validate(final)["status"] == "FAIL"


def test_project_id_trailing_newline_is_rejected(tmp_path):
    final = _write_final(tmp_path / "FINAL", project_id="example\n")
    assert admission.validate(final)["status"] == "FAIL"


def test_manifest_digest_trailing_newline_is_rejected(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    manifest = json.loads((final / "FILES.json").read_text())
    manifest["files"][0]["sha256"] += "\n"
    (final / "FILES.json").write_bytes(admission.json_bytes(manifest))
    admission._emit_root(final)
    assert admission.validate(final)["status"] == "FAIL"


def test_emit_does_not_resign_invalid_members(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    before = (final / "ROOT.sha256").read_bytes()
    (final / "d0/source.txt").write_bytes(b"tampered")
    assert admission.validate(final, emit_root=True)["status"] == "FAIL"
    assert (final / "ROOT.sha256").read_bytes() == before


def test_root_crlf_is_rejected(tmp_path):
    final = _write_final(tmp_path / "FINAL")
    root = final / "ROOT.sha256"
    root.write_bytes(root.read_bytes().replace(b"\n", b"\r\n"))
    assert admission.validate(final)["status"] == "FAIL"


def test_each_declared_schema_keyword_is_enforced(tmp_path):
    schema = tmp_path / "finite-schema.json"
    schema.write_text(json.dumps({"type": "object", "additionalProperties": False,
        "required": ["n", "s", "a"], "properties": {
            "n": {"type": "integer", "minimum": 1},
            "s": {"type": "string", "minLength": 2, "pattern": "^a"},
            "a": {"type": "array", "minItems": 1, "items": {"const": "ok"}}}}))
    errors = []
    admission.check_schema({"n": 1.0, "s": "ab", "a": ["ok"]}, schema, errors, "fixture")
    assert not errors
    for value in [{}, {"n": True, "s": "ab", "a": ["ok"]},
                  {"n": 0, "s": "b", "a": []}, {"n": 1, "s": "ab", "a": ["bad"], "x": 1}]:
        errors = []
        admission.check_schema(value, schema, errors, "fixture")
        assert errors

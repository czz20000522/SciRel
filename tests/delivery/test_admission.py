"""SciRel admission: the single external submission interface."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validate_admission", ROOT / "scripts" / "validate_admission.py")
admission = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(admission)


def _write_final(directory: Path, **overrides) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "d0").mkdir(exist_ok=True)
    (directory / "d1").mkdir(exist_ok=True)
    source = directory / "d0" / "source.txt"
    report = directory / "d1" / "report.json"
    source.write_bytes(b"source-bytes\n")
    report.write_bytes(b'{"status":"ok"}\n')
    path_map = directory / "PATH_MAP.json"
    path_map.write_text(json.dumps({"d0/source.txt": "d0/source.txt"}, indent=1) + "\n")
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

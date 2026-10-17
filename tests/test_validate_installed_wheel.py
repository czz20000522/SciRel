from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
CURRENT = json.loads((ROOT / "release/CURRENT.json").read_text(encoding="utf-8"))
CURRENT_VERSION = CURRENT["version"]
sys.path.insert(0, str(ROOT))

from scripts import validate_installed_wheel as validator  # noqa: E402


def test_platform_id_parser_canonicalizes_architecture_and_python_line() -> None:
    assert validator._parse_platform_id("linux-amd64-cp314") == {
        "os": "linux",
        "architecture": "x86_64",
        "python_tag": "cp314",
        "python_line": "3.14",
    }
    assert validator._parse_platform_id("macos-arm64-cp312")["python_line"] == "3.12"


@pytest.mark.parametrize("value", ("linux", "linux-x86_64-py314", "linux-x86_64-cp3"))
def test_platform_id_parser_rejects_ambiguous_tags(value: str) -> None:
    with pytest.raises(ValueError):
        validator._parse_platform_id(value)


def test_validation_receipt_aggregates_successful_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(validator, "_runtime_identity", lambda expected_platform, expected_python: ({}, []))
    monkeypatch.setattr(validator, "_check_distribution", lambda: ({"status": "PASS"}, [], object()))
    monkeypatch.setattr(validator, "_check_dependencies", lambda: [{"name": "numpy", "status": "PASS"}])
    monkeypatch.setattr(validator, "_run_pip_check", lambda: ({"status": "PASS"}, []))
    monkeypatch.setattr(validator, "_run_simple_operator", lambda: ({"status": "PASS"}, []))
    monkeypatch.setattr(validator, "_run_cross_domain_task", lambda: ({"status": "PASS"}, []))

    receipt = validator.validate_installed_wheel(expected_platform="linux-x86_64-cp314")

    assert receipt["schema"] == "scirel.installed-wheel-validation.v1"
    assert receipt["status"] == "PASS"
    assert receipt["errors"] == []


def test_validation_receipt_preserves_failed_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(validator, "_runtime_identity", lambda expected_platform, expected_python: ({}, []))
    monkeypatch.setattr(validator, "_check_distribution", lambda: ({"status": "PASS"}, [], object()))
    monkeypatch.setattr(validator, "_check_dependencies", lambda: [{"name": "numpy", "status": "PASS"}])
    monkeypatch.setattr(validator, "_run_pip_check", lambda: ({"status": "FAIL"}, ["pip check failed with exit code 1"]))
    monkeypatch.setattr(validator, "_run_simple_operator", lambda: ({"status": "PASS"}, []))
    monkeypatch.setattr(validator, "_run_cross_domain_task", lambda: ({"status": "PASS"}, []))

    receipt = validator.validate_installed_wheel()

    assert receipt["status"] == "FAIL"
    assert receipt["pip_check"]["status"] == "FAIL"
    assert "pip check failed with exit code 1" in receipt["errors"]


def test_validation_receipt_binds_the_installed_wheel_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / f"scirel-{CURRENT_VERSION}-py3-none-any.whl"
    wheel.write_bytes(b"wheel-bytes")
    monkeypatch.setattr(validator, "_runtime_identity", lambda expected_platform, expected_python: ({}, []))
    monkeypatch.setattr(
        validator,
        "_check_distribution",
        lambda: ({"status": "PASS", "version": CURRENT_VERSION}, [], object()),
    )
    monkeypatch.setattr(validator, "_check_dependencies", lambda: [{"name": "numpy", "status": "PASS"}])
    monkeypatch.setattr(validator, "_run_pip_check", lambda: ({"status": "PASS"}, []))
    monkeypatch.setattr(validator, "_run_simple_operator", lambda: ({"status": "PASS"}, []))
    monkeypatch.setattr(validator, "_run_cross_domain_task", lambda: ({"status": "PASS"}, []))

    receipt = validator.validate_installed_wheel(
        expected_platform="linux-x86_64-cp314", wheel_path=wheel
    )

    assert receipt["artifact"] == {
        "path": wheel.name,
        "sha256": hashlib.sha256(b"wheel-bytes").hexdigest(),
        "bytes": len(b"wheel-bytes"),
    }


def test_wheel_payload_audit_accepts_runtime_files_and_reports_native_resources(tmp_path: Path) -> None:
    wheel = tmp_path / "scirel-0.1.0.dev9-py3-none-any.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr("scirel/__init__.py", "__version__ = '0.1.0.dev9'\n")
        archive.writestr(
            "scirel/kinetic/_native/current/initialize.m",
            "disp('ok');\n",
        )
        archive.writestr(
            "scirel-0.1.0.dev9.dist-info/METADATA",
            "Metadata-Version: 2.4\nName: scirel\nVersion: 0.1.0.dev9\n",
        )
        archive.writestr("scirel-0.1.0.dev9.dist-info/WHEEL", "Wheel-Version: 1.0\n")

    details, errors = validator._wheel_payload(wheel)

    assert errors == []
    assert details["status"] == "PASS"
    assert details["package_file_count"] == 2
    assert details["dist_info_file_count"] == 2
    assert details["native_resource_count"] == 1
    assert details["metadata_name"] == "scirel"
    assert details["metadata_version"] == "0.1.0.dev9"


def test_wheel_payload_audit_rejects_development_files_and_path_traversal(tmp_path: Path) -> None:
    wheel = tmp_path / "bad.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr("scirel/__init__.pyc", b"cache")
        archive.writestr("tests/test_bad.py", "pass\n")
        archive.writestr("../outside.txt", "bad\n")

    details, errors = validator._wheel_payload(wheel)

    assert details["status"] == "FAIL"
    assert any("interpreter cache" in error for error in errors)
    assert any("non-package top-level" in error for error in errors)
    assert any("escapes its archive root" in error for error in errors)

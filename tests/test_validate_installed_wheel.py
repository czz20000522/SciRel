from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
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

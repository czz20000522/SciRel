from __future__ import annotations

import hashlib
import json
from types import ModuleType
from types import SimpleNamespace
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
        "python_abi": "cpython-314",
    }
    assert validator._parse_platform_id("macos-arm64-cp312")["python_line"] == "3.12"
    assert validator._parse_platform_id("linux-x86_64-cp314t") == {
        "os": "linux",
        "architecture": "x86_64",
        "python_tag": "cp314t",
        "python_line": "3.14",
        "python_abi": "cpython-314t",
    }


@pytest.mark.parametrize("value", ("linux", "linux-x86_64-py314", "linux-x86_64-cp3", "linux-x86_64-cp314tt"))
def test_platform_id_parser_rejects_ambiguous_tags(value: str) -> None:
    with pytest.raises(ValueError):
        validator._parse_platform_id(value)


def test_runtime_identity_rejects_a_non_virtual_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(validator.sys, "prefix", "/tmp/scirel-system")
    monkeypatch.setattr(validator.sys, "base_prefix", "/tmp/scirel-system")
    expected_python = f"{sys.version_info.major}.{sys.version_info.minor}"

    actual, errors = validator._runtime_identity(None, expected_python)

    assert actual["is_virtualenv"] is False
    assert any("virtual environment" in error for error in errors)


def test_runtime_identity_rejects_external_site_packages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(validator.sys, "prefix", "/tmp/scirel-venv")
    monkeypatch.setattr(validator.sys, "base_prefix", "/tmp/scirel-python")
    monkeypatch.setattr(
        validator.sys,
        "path",
        [
            "/tmp/scirel-venv/lib/python3.14/site-packages",
            "/usr/lib/python3.14/site-packages",
        ],
    )
    expected_python = f"{sys.version_info.major}.{sys.version_info.minor}"

    actual, errors = validator._runtime_identity(None, expected_python)

    assert actual["external_site_paths"] == ["/usr/lib/python3.14/site-packages"]
    assert any("outside the virtual environment" in error for error in errors)


def test_runtime_identity_rejects_a_free_threaded_abi_for_regular_cpython(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        validator.sys,
        "implementation",
        SimpleNamespace(name="cpython", cache_tag="cpython-314t"),
    )
    monkeypatch.setattr(validator.platform, "python_implementation", lambda: "CPython")
    monkeypatch.setattr(validator.platform, "python_version", lambda: "3.14.0")
    monkeypatch.setattr(validator.platform, "system", lambda: "Linux")
    monkeypatch.setattr(validator.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(validator.sys, "version_info", SimpleNamespace(major=3, minor=14))
    monkeypatch.setattr(validator.sys, "prefix", "/tmp/scirel-venv")
    monkeypatch.setattr(validator.sys, "base_prefix", "/tmp/scirel-python")
    monkeypatch.setattr(validator.sys, "path", ["/tmp/scirel-venv/lib/python3.14/site-packages"])

    actual, errors = validator._runtime_identity("linux-x86_64-cp314", "3.14")

    assert actual["python_abi"] == "cpython-314t"
    assert any("Python ABI is cpython-314t, expected cpython-314" in error for error in errors)


def test_dependency_import_must_resolve_inside_environment_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "system-site-packages" / "fake_module.py"
    outside.parent.mkdir()
    outside.write_text("# test fixture\n", encoding="utf-8")
    monkeypatch.setattr(validator.metadata, "requires", lambda _: ["fake-dist==1"])
    monkeypatch.setattr(validator.metadata, "packages_distributions", lambda: {"fake_module": ["fake-dist"]})
    monkeypatch.setattr(validator.metadata, "version", lambda _: "1")
    monkeypatch.setattr(
        validator.importlib,
        "import_module",
        lambda _: SimpleNamespace(__file__=str(outside)),
    )

    checks = validator._check_dependencies()

    assert checks == [
        {
            "requirement": "fake-dist==1",
            "name": "fake-dist",
            "status": "FAIL",
            "import_candidates": ["fake_module"],
            "installed_version": "1",
            "imported_module": "fake_module",
            "imported_from": str(outside),
            "within_sys_prefix": False,
            "error": f"imported module is outside the current environment prefix: {outside}",
        }
    ]


def test_declared_extra_requirements_select_only_the_requested_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        validator.metadata,
        "requires",
        lambda _: [
            "numpy==2.5.4",
            'matplotlib==3.11.2; extra == "plot"',
            'netCDF4==1.7.4; extra == "netcdf"',
        ],
    )

    assert validator._declared_extra_requirements("plot") == [
        {
            "requirement": 'matplotlib==3.11.2; extra == "plot"',
            "name": "matplotlib",
            "extra": "plot",
        }
    ]
    assert validator._declared_extra_requirements("netcdf")[0]["name"] == "netCDF4"


def test_distribution_metadata_must_resolve_inside_environment_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    metadata_root = tmp_path / "system-site-packages" / "scirel-0.1.0.dev9.dist-info"
    metadata_root.mkdir(parents=True)
    distribution = SimpleNamespace(
        _path=metadata_root,
        version="0.1.0.dev9",
        metadata={"Requires-Python": ">=3.14,<3.15"},
    )
    monkeypatch.setattr(validator.metadata, "distribution", lambda _: distribution)
    installed_module = Path(sys.prefix) / "lib" / "python3.14" / "site-packages" / "scirel" / "__init__.py"
    monkeypatch.setattr(
        validator.importlib,
        "import_module",
        lambda _: SimpleNamespace(__file__=str(installed_module)),
    )

    details, errors, _ = validator._check_distribution()

    assert details["metadata_within_sys_prefix"] is False
    assert details["within_sys_prefix"] is True
    assert any("distribution metadata is outside" in error for error in errors)


def test_validation_receipt_aggregates_successful_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(validator, "_runtime_identity", lambda expected_platform, expected_python: ({}, []))
    monkeypatch.setattr(validator, "_check_distribution", lambda: ({"status": "PASS"}, [], object()))
    monkeypatch.setattr(validator, "_check_dependencies", lambda: [{"name": "numpy", "status": "PASS"}])
    monkeypatch.setattr(validator, "_run_pip_check", lambda: ({"status": "PASS"}, []))
    monkeypatch.setattr(validator, "_run_simple_operator", lambda: ({"status": "PASS"}, []))
    monkeypatch.setattr(validator, "_run_cross_domain_task", lambda: ({"status": "PASS"}, []))
    monkeypatch.setattr(
        validator,
        "_run_public_surface",
        lambda: (
            {
                "status": "PASS",
                "domain_count": 18,
                "export_count": 251,
                "nested_package_count": 1,
                "nested_module_count": 8,
                "nested_export_count": 47,
            },
            [],
        ),
    )

    receipt = validator.validate_installed_wheel(expected_platform="linux-x86_64-cp314")

    assert receipt["schema"] == "scirel.installed-wheel-validation.v1"
    assert receipt["status"] == "PASS"
    assert receipt["extras"] == {}
    assert receipt["errors"] == []
    assert receipt["public_surface"]["export_count"] == 251
    assert receipt["public_surface"]["nested_export_count"] == 47


def test_public_surface_resolves_current_installed_exports() -> None:
    details, errors = validator._run_public_surface()

    assert errors == []
    assert details["status"] == "PASS"
    assert details["domain_count"] == 18
    assert details["export_count"] == 251
    assert details["nested_package_count"] == 1
    assert details["nested_module_count"] == 8
    assert details["nested_export_count"] == 47


def test_public_surface_fails_closed_on_a_missing_export(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_domain = ModuleType("scirel.fake")
    fake_domain.__all__ = ["present", "missing"]
    fake_domain.present = object()

    fake_root = ModuleType("scirel")
    fake_root.__all__ = ["fake"]
    fake_root.fake = fake_domain

    monkeypatch.setattr(validator.importlib, "import_module", lambda name: fake_root)

    details, errors = validator._run_public_surface()

    assert details["status"] == "FAIL"
    assert details["domain_count"] == 1
    assert details["export_count"] == 2
    assert any("fake.missing cannot be resolved" in error for error in errors)


def test_validation_receipt_records_a_successful_optional_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeMetadata:
        def get_all(self, name: str):
            return ["plot"] if name == "Provides-Extra" else None

    monkeypatch.setattr(validator, "_runtime_identity", lambda expected_platform, expected_python: ({}, []))
    monkeypatch.setattr(
        validator,
        "_check_distribution",
        lambda: ({"status": "PASS"}, [], SimpleNamespace(metadata=FakeMetadata())),
    )
    monkeypatch.setattr(validator, "_check_dependencies", lambda requirements=None: [{"name": "numpy", "status": "PASS"}])
    monkeypatch.setattr(
        validator,
        "_declared_extra_requirements",
        lambda extra: [{"name": "matplotlib", "requirement": "matplotlib==3.11.2", "extra": extra}],
    )
    monkeypatch.setattr(validator, "_run_extra_smoke", lambda extra: ({"status": "PASS", "extra": extra}, []))
    monkeypatch.setattr(validator, "_run_pip_check", lambda: ({"status": "PASS"}, []))
    monkeypatch.setattr(validator, "_run_simple_operator", lambda: ({"status": "PASS"}, []))
    monkeypatch.setattr(validator, "_run_cross_domain_task", lambda: ({"status": "PASS"}, []))

    receipt = validator.validate_installed_wheel(extras=("plot",))

    assert receipt["status"] == "PASS"
    assert receipt["extras"]["plot"]["status"] == "PASS"
    assert receipt["extras"]["plot"]["smoke"]["extra"] == "plot"


def test_validation_receipt_rejects_an_undeclared_optional_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeMetadata:
        def get_all(self, name: str):
            return [] if name == "Provides-Extra" else None

    monkeypatch.setattr(validator, "_runtime_identity", lambda expected_platform, expected_python: ({}, []))
    monkeypatch.setattr(
        validator,
        "_check_distribution",
        lambda: ({"status": "PASS"}, [], SimpleNamespace(metadata=FakeMetadata())),
    )
    monkeypatch.setattr(validator, "_check_dependencies", lambda requirements=None: [])
    monkeypatch.setattr(validator, "_run_pip_check", lambda: ({"status": "PASS"}, []))
    monkeypatch.setattr(validator, "_run_simple_operator", lambda: ({"status": "PASS"}, []))
    monkeypatch.setattr(validator, "_run_cross_domain_task", lambda: ({"status": "PASS"}, []))

    receipt = validator.validate_installed_wheel(extras=("plot",))

    assert receipt["status"] == "FAIL"
    assert "not declared" in receipt["extras"]["plot"]["error"]


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

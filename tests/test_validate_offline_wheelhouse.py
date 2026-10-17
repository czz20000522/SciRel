from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from packaging.tags import parse_tag
from packaging.requirements import Requirement
from zipfile import ZipFile

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import validate_offline_wheelhouse as validator  # noqa: E402


def _write_test_wheel(path: Path, *, requires: tuple[str, ...] = ("numpy==1.0.0",)) -> None:
    metadata = [
        "Metadata-Version: 2.3",
        "Name: scirel",
        "Version: 0.1.0.dev9",
    ]
    metadata.extend(f"Requires-Dist: {requirement}" for requirement in requires)
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "scirel-0.1.0.dev9.dist-info/METADATA",
            "\n".join(metadata) + "\n\n",
        )


def _write_test_lock(path: Path, *, requirement: str = "numpy==1.0.0") -> None:
    name, _, specifier = requirement.partition("==")
    path.write_text(
        """version = 1
revision = 3
requires-python = \"==3.14.*\"

[[package]]
name = \"scirel\"
version = \"0.1.0.dev9\"
source = { editable = \".\" }
dependencies = [{ name = \"numpy\" }]

[package.metadata]
requires-dist = [{ name = \"%s\", specifier = \"==%s\" }]

[[package]]
name = \"numpy\"
version = \"%s\"
source = { registry = \"https://pypi.org/simple\" }
""" % (name, specifier, specifier),
        encoding="utf-8",
    )


def test_wheelhouse_inventory_is_sorted_and_content_bound(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "zeta-1.0-py3-none-any.whl").write_bytes(b"z")
    (wheelhouse / "alpha-1.0-py3-none-any.whl").write_bytes(b"alpha")
    (wheelhouse / "README.txt").write_text("ignored auxiliary file\n", encoding="utf-8")

    rows = validator._wheelhouse_inventory(wheelhouse)

    assert [row["filename"] for row in rows] == [
        "alpha-1.0-py3-none-any.whl",
        "zeta-1.0-py3-none-any.whl",
    ]
    assert rows[0]["bytes"] == 5
    assert len(rows[0]["sha256"]) == 64


def test_wheelhouse_inventory_requires_a_wheel(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()

    with pytest.raises(ValueError, match="contains no wheel files"):
        validator._wheelhouse_inventory(wheelhouse)


def test_pip_install_command_is_offline_and_binary_only(tmp_path: Path) -> None:
    command = validator._pip_install_command(
        tmp_path / "venv" / "bin" / "python",
        tmp_path / "scirel.whl",
        tmp_path / "wheelhouse",
    )

    assert "--no-index" in command
    assert "--only-binary=:all:" in command
    assert command[command.index("--find-links") + 1].endswith("wheelhouse")
    assert command[-1].endswith("scirel.whl")


def test_pip_install_extra_command_is_offline_and_names_the_extra(tmp_path: Path) -> None:
    command = validator._pip_install_extra_command(
        tmp_path / "venv" / "bin" / "python",
        "plot",
        tmp_path / "wheelhouse",
        tmp_path / "wheel-candidates",
    )

    assert "--no-index" in command
    assert "--only-binary=:all:" in command
    assert command[-1] == "scirel[plot]"
    second_links = command.index("--find-links", command.index("--find-links") + 1)
    assert command[second_links + 1].endswith("wheel-candidates")


def test_offline_validation_binds_clean_install_and_inner_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "scirel-0.1.0.dev9-py3-none-any.whl"
    wheel.write_bytes(b"wheel bytes")
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "numpy-2.5.4-cp314-cp314-manylinux.whl").write_bytes(b"numpy")

    commands: list[list[str]] = []

    def fake_run(command, *, cwd=None, env=None):
        del cwd, env
        command = list(command)
        commands.append(command)
        if "--output" in command:
            output = Path(command[command.index("--output") + 1])
            output.write_text('{"schema":"scirel.installed-wheel-validation.v1","status":"PASS"}\n')
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(validator, "_run", fake_run)
    receipt = validator.validate_offline_wheelhouse(
        wheel_path=wheel,
        wheelhouse_path=wheelhouse,
        expected_platform="linux-x86_64-cp314",
    )

    assert receipt["status"] == "PASS"
    assert receipt["execution"]["network_resolution"] is False
    assert receipt["execution"]["pip_install"]["status"] == "PASS"
    assert receipt["validation"]["status"] == "PASS"
    assert any("--no-index" in command for command in commands)
    assert any("--only-binary=:all:" in command for command in commands)
    validation_command = commands[-1]
    assert validation_command[validation_command.index("--expected-platform") + 1] == "linux-x86_64-cp314"


def test_offline_validation_stops_after_install_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "scirel.whl"
    wheel.write_bytes(b"wheel bytes")
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "numpy.whl").write_bytes(b"numpy")
    calls: list[list[str]] = []

    def fake_run(command, *, cwd=None, env=None):
        del cwd, env
        command = list(command)
        calls.append(command)
        code = 1 if "pip" in command else 0
        return subprocess.CompletedProcess(command, code, stdout="", stderr="missing wheel")

    monkeypatch.setattr(validator, "_run", fake_run)
    receipt = validator.validate_offline_wheelhouse(
        wheel_path=wheel,
        wheelhouse_path=wheelhouse,
    )

    assert receipt["status"] == "FAIL"
    assert receipt["execution"]["pip_install"]["status"] == "FAIL"
    assert len(calls) == 2
    assert any("offline pip installation failed" in error for error in receipt["errors"])


def test_offline_validation_installs_and_forwards_requested_extra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "scirel-0.1.0.dev9-py3-none-any.whl"
    wheel.write_bytes(b"wheel bytes")
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "numpy.whl").write_bytes(b"numpy")
    commands: list[list[str]] = []

    def fake_run(command, *, cwd=None, env=None):
        del cwd, env
        command = list(command)
        commands.append(command)
        if "--output" in command:
            output = Path(command[command.index("--output") + 1])
            output.write_text(
                '{"schema":"scirel.installed-wheel-validation.v1",'
                '"status":"PASS","extras":{"plot":{"status":"PASS"}}}\n',
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(validator, "_run", fake_run)
    receipt = validator.validate_offline_wheelhouse(
        wheel_path=wheel,
        wheelhouse_path=wheelhouse,
        extras=("plot",),
    )

    assert receipt["status"] == "PASS"
    assert receipt["extras"]["plot"]["install"]["status"] == "PASS"
    assert any(command[-1] == "scirel[plot]" for command in commands)
    extra_command = next(command for command in commands if command[-1] == "scirel[plot]")
    assert extra_command.count("--find-links") == 2
    validation_command = commands[-1]
    assert validation_command[-2:] == ["--extra", "plot"]


def test_dependency_closure_audit_binds_pep508_lock_and_platform_tags(tmp_path: Path) -> None:
    wheel = tmp_path / "scirel-0.1.0.dev9-py3-none-any.whl"
    _write_test_wheel(wheel)
    lockfile = tmp_path / "uv.lock"
    _write_test_lock(lockfile)
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "numpy-1.0.0-py3-none-any.whl").write_bytes(b"numpy")

    receipt = validator._dependency_closure_audit(
        wheel=wheel,
        wheelhouse=wheelhouse,
        lockfile=lockfile,
        expected_platform="linux-x86_64-cp314",
        expected_python="3.14",
        extras=(),
    )

    assert receipt["status"] == "PASS"
    assert receipt["expected_packages"] == [{"name": "numpy", "version": "1.0.0"}]
    assert receipt["direct_requirements"] == ["numpy==1.0.0"]
    assert receipt["incompatible_wheels"] == []


def test_dependency_closure_audit_reports_missing_and_incompatible_wheels(tmp_path: Path) -> None:
    wheel = tmp_path / "scirel-0.1.0.dev9-py3-none-any.whl"
    _write_test_wheel(wheel)
    lockfile = tmp_path / "uv.lock"
    _write_test_lock(lockfile)
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "numpy-1.0.0-py3-none-win_amd64.whl").write_bytes(b"numpy")

    receipt = validator._dependency_closure_audit(
        wheel=wheel,
        wheelhouse=wheelhouse,
        lockfile=lockfile,
        expected_platform="linux-x86_64-cp314",
        expected_python="3.14",
        extras=(),
    )

    assert receipt["status"] == "FAIL"
    assert receipt["missing_packages"] == []
    assert receipt["incompatible_wheels"] == ["numpy-1.0.0-py3-none-win_amd64.whl"]


def test_dependency_closure_audit_rejects_pep508_drift(tmp_path: Path) -> None:
    wheel = tmp_path / "scirel-0.1.0.dev9-py3-none-any.whl"
    _write_test_wheel(wheel, requires=("numpy==2.0.0",))
    lockfile = tmp_path / "uv.lock"
    _write_test_lock(lockfile)
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "numpy-1.0.0-py3-none-any.whl").write_bytes(b"numpy")

    with pytest.raises(ValueError, match="Requires-Dist"):
        validator._dependency_closure_audit(
            wheel=wheel,
            wheelhouse=wheelhouse,
            lockfile=lockfile,
            expected_platform="linux-x86_64-cp314",
            expected_python="3.14",
            extras=(),
        )


@pytest.mark.parametrize(
    ("wheel_tag", "platform", "expected"),
    (
        ("cp314-cp314-macosx_14_0_arm64", "macos-arm64-cp314", True),
        ("cp314-cp314-macosx_14_0_arm64", "linux-aarch64-cp314", False),
        ("cp314-cp314-win_arm64", "windows-arm64-cp314", True),
        ("cp314-cp314-win_amd64", "windows-arm64-cp314", False),
        ("cp314-cp314-musllinux_1_2_x86_64", "linux-x86_64-cp314", False),
    ),
)
def test_wheel_tag_compatibility_preserves_platform_architecture(
    wheel_tag: str, platform: str, expected: bool
) -> None:
    tags = parse_tag(wheel_tag)
    assert any(
        validator._wheel_tag_compatible(tag, platform, "3.14") for tag in tags
    ) is expected


def test_pep508_marker_environment_is_bound_to_target_platform() -> None:
    environment = validator._marker_environment("macos-arm64-cp314", "3.14")
    assert environment["sys_platform"] == "darwin"
    assert environment["platform_machine"] == "arm64"
    assert environment["platform_python_implementation"] == "CPython"
    requirement = Requirement(
        "netCDF4==1.7.4; extra == 'netcdf' and sys_platform == 'darwin'"
    )
    assert validator._requirement_applies(
        requirement, extras=("netcdf",), marker_environment=environment
    )
    linux_environment = validator._marker_environment("linux-x86_64-cp314", "3.14")
    assert not validator._requirement_applies(
        requirement, extras=("netcdf",), marker_environment=linux_environment
    )

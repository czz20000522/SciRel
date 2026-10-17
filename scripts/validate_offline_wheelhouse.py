"""Validate a SciRel wheel with a completely offline dependency wheelhouse.

This command consumes an already-built SciRel wheel and a directory of
dependency wheels.  It creates a temporary clean virtual environment, installs
the wheel using only the supplied wheelhouse, and then delegates the installed
package checks to :mod:`validate_installed_wheel`.

The command never builds a wheel and never changes release metadata.  Its
receipt is intentionally separate from the historical ``dev9`` Linux receipt:
it records whether dependency resolution was actually completed with
``--no-index`` and ``--only-binary=:all:``.

Without ``--source-revision`` the receipt is a standalone technical receipt.
Pass the exact lowercase Git commit when preparing a future candidate that
will bind this receipt into ``release/CURRENT.json``; the release validator
then checks that binding instead of trusting the wheel filename alone.

Typical Linux amd64 / CPython 3.14 invocation::

    python -I scripts/validate_offline_wheelhouse.py \
        --expected-platform linux-x86_64-cp314 \
        --wheel /artifacts/scirel-0.1.0.dev9-py3-none-any.whl \
        --wheelhouse /artifacts/linux-x86_64-cp314-wheelhouse \
        --lockfile uv.lock \
        --output offline-wheelhouse-validation.json

The wheelhouse must contain wheels for the SciRel runtime dependencies and all
of their transitive dependencies selected by pip.  Source archives are not
used: ``--only-binary=:all:`` makes a missing binary dependency fail closed.
When ``--lockfile`` is supplied, the receipt also compares the wheel's PEP 508
``Requires-Dist`` rows with ``uv.lock`` and records the selected transitive
closure, wheel versions, and target-platform tag compatibility.  Omitting it
retains the install-only technical receipt and marks that audit ``NOT_RUN``.
"""

from __future__ import annotations

import argparse
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from typing import Any, Sequence
from zipfile import BadZipFile, ZipFile

from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version


SCHEMA = "scirel.offline-wheelhouse-validation.v1"
DEFAULT_EXPECTED_PYTHON = "3.14"
VALIDATOR = Path(__file__).resolve().with_name("validate_installed_wheel.py")
_SOURCE_REVISION = re.compile(r"[0-9a-f]{40}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_regular_file(path: Path, *, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be a regular file: {path}")


def _wheelhouse_inventory(path: Path) -> list[dict[str, Any]]:
    """Return deterministic identity rows for every wheel in ``path``.

    A wheelhouse may contain auxiliary files used by a local mirror, but only
    regular ``.whl`` files participate in this acceptance.  Symlinked wheels
    are rejected so the receipt binds bytes at a stable path rather than a
    mutable link target.
    """

    path = path.resolve()
    if not path.is_dir() or path.is_symlink():
        raise ValueError(f"wheelhouse must be a regular directory: {path}")
    rows: list[dict[str, Any]] = []
    for wheel in sorted(path.glob("*.whl"), key=lambda value: value.name):
        _require_regular_file(wheel, label="wheelhouse member")
        rows.append(
            {
                "filename": wheel.name,
                "sha256": _sha256(wheel),
                "bytes": wheel.stat().st_size,
            }
        )
    if not rows:
        raise ValueError(f"wheelhouse contains no wheel files: {path}")
    return rows


def _marker_environment(expected_platform: str | None, expected_python: str) -> dict[str, str]:
    """Return a PEP 508 marker environment for the target acceptance platform."""

    environment = default_environment()
    python_line = expected_python.strip()
    if not re.fullmatch(r"\d+\.\d+", python_line):
        raise ValueError("expected Python must use the major.minor form")
    environment.update(
        {
            "python_version": python_line,
            "python_full_version": f"{python_line}.0",
            "implementation_name": "cpython",
            "implementation_version": f"{python_line}.0",
            "platform_python_implementation": "CPython",
        }
    )
    if expected_platform:
        parts = expected_platform.strip().lower().split("-")
        if len(parts) < 3:
            raise ValueError(
                "expected platform must use '<os>-<architecture>-cp314', "
                f"got {expected_platform!r}"
            )
        expected_cp = "cp" + python_line.replace(".", "")
        if parts[-1] not in {expected_cp, expected_cp + "t"}:
            raise ValueError(
                f"platform Python tag {parts[-1]!r} differs from expected Python {python_line}"
            )
        os_name = parts[0]
        if os_name == "linux":
            environment.update(
                {"sys_platform": "linux", "platform_system": "Linux", "os_name": "posix"}
            )
        elif os_name == "macos":
            environment.update(
                {"sys_platform": "darwin", "platform_system": "Darwin", "os_name": "posix"}
            )
        elif os_name == "windows":
            environment.update(
                {"sys_platform": "win32", "platform_system": "Windows", "os_name": "nt"}
            )
        else:
            raise ValueError(f"unsupported target OS in platform id: {expected_platform}")
        architecture = "-".join(parts[1:-1]).replace("-", "_")
        if os_name == "macos":
            environment["platform_machine"] = {
                "amd64": "x86_64",
                "x86_64": "x86_64",
                "arm64": "arm64",
                "aarch64": "arm64",
            }.get(architecture, architecture)
        elif os_name == "windows":
            environment["platform_machine"] = {
                "amd64": "AMD64",
                "x86_64": "AMD64",
                "arm64": "ARM64",
                "aarch64": "ARM64",
            }.get(architecture, architecture)
        else:
            environment["platform_machine"] = {
                "amd64": "x86_64",
                "x86_64": "x86_64",
                "arm64": "aarch64",
                "aarch64": "aarch64",
            }.get(architecture, architecture)
    return environment


def _requirement_key(requirement: Requirement) -> tuple[str, str, str | None]:
    return (
        canonicalize_name(requirement.name),
        str(requirement.specifier),
        str(requirement.marker) if requirement.marker else None,
    )


def _parse_requirement(raw: str, *, source: str) -> Requirement:
    try:
        return Requirement(raw)
    except InvalidRequirement as error:
        raise ValueError(f"{source} contains invalid PEP 508 requirement: {raw!r}") from error


def _lock_requirement_rows(lock: dict[str, Any], root_name: str) -> list[str]:
    packages = lock.get("package")
    if not isinstance(packages, list):
        raise ValueError("uv.lock package table is missing")
    matches = [
        package
        for package in packages
        if isinstance(package, dict)
        and canonicalize_name(str(package.get("name", ""))) == canonicalize_name(root_name)
    ]
    if len(matches) != 1:
        raise ValueError(f"uv.lock must contain exactly one {root_name!r} package")
    metadata = matches[0].get("metadata")
    rows = metadata.get("requires-dist") if isinstance(metadata, dict) else None
    if not isinstance(rows, list):
        raise ValueError("uv.lock root package lacks package.metadata.requires-dist")
    rendered: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            raise ValueError("uv.lock requires-dist row is invalid")
        rendered.append(
            f"{row['name']}{row.get('specifier', '')}"
            + (f"; {row['marker']}" if row.get("marker") else "")
        )
    return rendered


def _wheel_metadata_requirements(wheel: Path) -> tuple[str, str, list[str]]:
    try:
        with ZipFile(wheel) as archive:
            metadata_names = [
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_names) != 1:
                raise ValueError("wheel must contain exactly one .dist-info/METADATA")
            fields = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
    except (OSError, UnicodeDecodeError, BadZipFile) as error:
        raise ValueError(f"wheel metadata is unreadable: {wheel}") from error
    name = fields.get("Name")
    version = fields.get("Version")
    if not name or not version:
        raise ValueError("wheel metadata must declare Name and Version")
    return name, version, fields.get_all("Requires-Dist") or []


def _requirement_applies(
    requirement: Requirement,
    *,
    extras: Sequence[str],
    marker_environment: dict[str, str],
) -> bool:
    if requirement.marker is None:
        return True
    contexts = tuple(extras) or ("",)
    for extra in contexts:
        environment = dict(marker_environment)
        environment["extra"] = extra
        if requirement.marker.evaluate(environment):
            return True
    return False


def _lock_package_map(lock: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = lock.get("package")
    if not isinstance(rows, list):
        raise ValueError("uv.lock package table is missing")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            raise ValueError("uv.lock package row is invalid")
        name = canonicalize_name(row["name"])
        if name in result:
            raise ValueError(f"uv.lock repeats package {name}")
        if not isinstance(row.get("version"), str) or not row["version"]:
            raise ValueError(f"uv.lock package {name} lacks a version")
        result[name] = row
    return result


def _lock_closure(
    lock: dict[str, Any],
    *,
    extras: Sequence[str],
    marker_environment: dict[str, str],
    root_name: str,
) -> tuple[dict[str, str], set[str]]:
    packages = _lock_package_map(lock)
    root = packages.get(canonicalize_name(root_name))
    if root is None:
        raise ValueError(f"uv.lock has no root package {root_name!r}")
    queue: list[str] = []
    for dependency in root.get("dependencies", []):
        if not isinstance(dependency, dict) or not isinstance(dependency.get("name"), str):
            raise ValueError("uv.lock root dependency row is invalid")
        marker = dependency.get("marker")
        if marker:
            requirement = _parse_requirement(
                f"{dependency['name']}; {marker}", source="uv.lock dependency"
            )
            if not _requirement_applies(
                requirement, extras=(), marker_environment=marker_environment
            ):
                continue
        queue.append(canonicalize_name(dependency["name"]))
    optional = root.get("optional-dependencies", {})
    if not isinstance(optional, dict):
        raise ValueError("uv.lock root optional-dependencies is invalid")
    for extra in extras:
        dependencies = optional.get(extra)
        if dependencies is None:
            raise ValueError(f"uv.lock has no optional dependency group {extra!r}")
        if not isinstance(dependencies, list):
            raise ValueError(f"uv.lock optional dependency group {extra!r} is invalid")
        for dependency in dependencies:
            if not isinstance(dependency, dict) or not isinstance(dependency.get("name"), str):
                raise ValueError(f"uv.lock optional dependency row is invalid: {extra}")
            queue.append(canonicalize_name(dependency["name"]))

    closure: dict[str, str] = {}
    while queue:
        name = queue.pop(0)
        if name in closure:
            continue
        package = packages.get(name)
        if package is None:
            raise ValueError(f"uv.lock dependency is not declared as a package: {name}")
        closure[name] = str(package["version"])
        dependencies = package.get("dependencies", [])
        if not isinstance(dependencies, list):
            raise ValueError(f"uv.lock dependencies for {name} are invalid")
        for dependency in dependencies:
            if not isinstance(dependency, dict) or not isinstance(dependency.get("name"), str):
                raise ValueError(f"uv.lock dependency row is invalid: {name}")
            marker = dependency.get("marker")
            if marker:
                requirement = _parse_requirement(
                    f"{dependency['name']}; {marker}", source=f"uv.lock {name} dependency"
                )
                if not _requirement_applies(
                    requirement, extras=(), marker_environment=marker_environment
                ):
                    continue
            queue.append(canonicalize_name(dependency["name"]))
    return closure, set(closure)


def _wheel_tag_compatible(tag: Any, expected_platform: str | None, expected_python: str) -> bool:
    if expected_platform is None:
        return True
    parts = expected_platform.lower().split("-")
    if len(parts) < 3:
        raise ValueError(f"invalid expected platform: {expected_platform}")
    expected_cp = "cp" + expected_python.replace(".", "")
    if parts[-1] not in {expected_cp, expected_cp + "t"}:
        raise ValueError(
            f"platform Python tag {parts[-1]!r} differs from expected Python {expected_python}"
        )
    interpreter = str(tag.interpreter).lower()
    abi = str(tag.abi).lower()
    target_interpreter = parts[-1]
    if interpreter not in {"py2", "py3", "py2.py3", target_interpreter}:
        if not (interpreter.startswith("cp") and abi == "abi3" and interpreter[2:].isdigit()):
            return False
    platform_tag = str(tag.platform).lower()
    if platform_tag == "any":
        return True
    target_os = parts[0]
    target_arch = "-".join(parts[1:-1]).replace("-", "_")
    if target_os == "macos":
        target_arch = {"amd64": "x86_64", "aarch64": "arm64"}.get(
            target_arch, target_arch
        )
    elif target_os == "windows":
        target_arch = {"amd64": "amd64", "x86_64": "amd64", "aarch64": "arm64"}.get(
            target_arch, target_arch
        )
    elif target_arch in {"amd64", "x86_64"}:
        target_arch = "x86_64"
    elif target_arch in {"arm64", "aarch64"}:
        target_arch = "aarch64"
    if target_os == "linux":
        if platform_tag.startswith("musllinux"):
            return False
        return platform_tag.endswith("_" + target_arch) or platform_tag == "linux_" + target_arch
    if target_os == "macos":
        return platform_tag.startswith("macosx_") and (
            platform_tag.endswith("_" + target_arch) or platform_tag.endswith("_universal2")
        )
    if target_os == "windows":
        return platform_tag == "win_" + target_arch
    return False


def _dependency_closure_audit(
    *,
    wheel: Path,
    wheelhouse: Path,
    lockfile: Path | None,
    expected_platform: str | None,
    expected_python: str,
    extras: Sequence[str],
) -> dict[str, Any]:
    """Audit PEP 508 metadata and the selected uv.lock transitive closure."""

    if lockfile is None:
        return {
            "status": "NOT_RUN",
            "reason": "no uv.lock supplied; pass --lockfile for closure evidence",
        }
    lock_path = lockfile.resolve()
    if not lock_path.is_file() or lock_path.is_symlink():
        raise ValueError(f"uv.lock must be a regular file: {lock_path}")
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    environment = _marker_environment(expected_platform, expected_python)
    lock_requires_python = lock.get("requires-python")
    if not isinstance(lock_requires_python, str) or not lock_requires_python.strip():
        raise ValueError("uv.lock requires-python is missing or invalid")
    try:
        lock_python_compatible = SpecifierSet(lock_requires_python).contains(
            Version(expected_python), prereleases=True
        )
    except (InvalidSpecifier, InvalidVersion) as error:
        raise ValueError(
            f"uv.lock requires-python is invalid: {lock_requires_python!r}"
        ) from error
    if not lock_python_compatible:
        raise ValueError(
            f"uv.lock requires-python {lock_requires_python!r} does not admit "
            f"CPython {expected_python}"
        )
    wheel_name, wheel_version, wheel_requirements = _wheel_metadata_requirements(wheel)
    if canonicalize_name(wheel_name) != "scirel":
        raise ValueError(f"wheel metadata names {wheel_name!r}, expected scirel")
    lock_packages = _lock_package_map(lock)
    root = lock_packages.get("scirel")
    if root is None or str(root.get("version")) != wheel_version:
        raise ValueError("uv.lock root scirel version differs from wheel metadata")
    lock_raw_requirements = _lock_requirement_rows(lock, wheel_name)
    wheel_requirements_parsed = [
        _parse_requirement(raw, source="wheel METADATA Requires-Dist")
        for raw in wheel_requirements
    ]
    lock_requirements_parsed = [
        _parse_requirement(raw, source="uv.lock package.metadata.requires-dist")
        for raw in lock_raw_requirements
    ]
    wheel_keys = sorted(_requirement_key(item) for item in wheel_requirements_parsed)
    lock_keys = sorted(_requirement_key(item) for item in lock_requirements_parsed)
    if wheel_keys != lock_keys:
        raise ValueError("wheel Requires-Dist differs from uv.lock package.metadata.requires-dist")
    selected_wheel = {
        (canonicalize_name(req.name), str(req.specifier))
        for req in wheel_requirements_parsed
        if _requirement_applies(req, extras=extras, marker_environment=environment)
    }
    closure, expected_names = _lock_closure(
        lock,
        extras=extras,
        marker_environment=environment,
        root_name=wheel_name,
    )
    selected_lock = {
        (canonicalize_name(req.name), str(req.specifier))
        for req in lock_requirements_parsed
        if _requirement_applies(req, extras=extras, marker_environment=environment)
    }
    if selected_wheel != selected_lock:
        raise ValueError("selected wheel PEP 508 requirements differ from uv.lock")

    wheel_rows: list[dict[str, Any]] = []
    by_name: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(wheelhouse.glob("*.whl"), key=lambda value: value.name):
        _require_regular_file(path, label="wheelhouse member")
        try:
            parsed_name, parsed_version, _, tags = parse_wheel_filename(path.name)
        except Exception as error:
            raise ValueError(f"wheelhouse member has an invalid wheel filename: {path.name}") from error
        name = canonicalize_name(str(parsed_name))
        row = {
            "filename": path.name,
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
            "name": name,
            "version": str(parsed_version),
            "tags": sorted(str(tag) for tag in tags),
            "platform_compatible": any(
                _wheel_tag_compatible(tag, expected_platform, expected_python) for tag in tags
            ),
        }
        wheel_rows.append(row)
        by_name.setdefault(name, []).append(row)
    missing = sorted(name for name in expected_names if name not in by_name)
    version_mismatches = sorted(
        {
            name
            for name, expected_version in closure.items()
            if name in by_name and any(row["version"] != expected_version for row in by_name[name])
        }
    )
    duplicates = sorted(name for name, rows in by_name.items() if len(rows) > 1)
    unknown = sorted(name for name in by_name if name not in lock_packages)
    unneeded = sorted(name for name in by_name if name in lock_packages and name not in expected_names)
    incompatible = sorted(
        row["filename"]
        for row in wheel_rows
        if not row["platform_compatible"]
    )
    # A wheelhouse can intentionally be the union used by core and several
    # optional extras.  Keep unneeded lock packages visible for size/audit
    # reporting, but fail only when the selected closure is incomplete or a
    # wheel is invalid for that target.
    return {
        "status": "PASS"
        if not (missing or version_mismatches or duplicates or unknown or incompatible)
        else "FAIL",
        "lockfile": {"path": str(lock_path), "sha256": _sha256(lock_path)},
        "lock_requires_python": lock_requires_python,
        "target_python": expected_python,
        "requested_extras": sorted({extra.strip().lower() for extra in extras if extra.strip()}),
        "direct_requirements": sorted(
            {str(requirement) for requirement in lock_requirements_parsed}
        ),
        "expected_packages": [
            {"name": name, "version": closure[name]} for name in sorted(closure)
        ],
        "wheelhouse_packages": wheel_rows,
        "missing_packages": missing,
        "version_mismatches": version_mismatches,
        "duplicate_packages": duplicates,
        "unknown_packages": unknown,
        "unneeded_packages": unneeded,
        "incompatible_wheels": incompatible,
    }


def _pip_install_command(python: Path, wheel: Path, wheelhouse: Path) -> list[str]:
    """Build the fail-closed pip command used for offline installation."""

    return [
        str(python),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--no-index",
        "--only-binary=:all:",
        "--find-links",
        str(wheelhouse),
        str(wheel),
    ]


def _pip_install_extra_command(
    python: Path, extra: str, wheelhouse: Path, wheel_candidates: Path
) -> list[str]:
    """Build the offline command that resolves one extra from the exact wheel."""

    extra = extra.strip().lower()
    if not extra:
        raise ValueError("extra name must not be empty")
    return [
        str(python),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--no-index",
        "--only-binary=:all:",
        "--find-links",
        str(wheelhouse),
        "--find-links",
        str(wheel_candidates),
        f"scirel[{extra}]",
    ]


def _run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _trim(value: str | None, limit: int = 8000) -> str:
    return (value or "").strip()[-limit:]


def _venv_python(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _clean_environment() -> dict[str, str]:
    """Remove import-path and pip-index overrides from child processes."""

    env = dict(os.environ)
    for key in (
        "PYTHONPATH",
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
        "PIP_FIND_LINKS",
        "PIP_NO_INDEX",
        "PIP_TRUSTED_HOST",
    ):
        env.pop(key, None)
    return env


def _normalise_source_revision(value: str | None) -> str | None:
    if value is None:
        return None
    if _SOURCE_REVISION.fullmatch(value) is None:
        raise ValueError("source revision must be a 40-character lowercase Git commit")
    return value


def validate_offline_wheelhouse(
    *,
    wheel_path: Path,
    wheelhouse_path: Path,
    expected_platform: str | None = None,
    expected_python: str = DEFAULT_EXPECTED_PYTHON,
    source_revision: str | None = None,
    validator_path: Path = VALIDATOR,
    extras: Sequence[str] = (),
    lockfile: Path | None = None,
) -> dict[str, Any]:
    """Install and validate one wheel with no network or source fallback."""

    wheel = wheel_path.resolve()
    wheelhouse = wheelhouse_path.resolve()
    validator = validator_path.resolve()
    source_revision = _normalise_source_revision(source_revision)
    _require_regular_file(wheel, label="SciRel wheel")
    _require_regular_file(validator, label="installed-wheel validator")
    inventory = _wheelhouse_inventory(wheelhouse)
    normalised_extras: list[str] = []
    seen_extras: set[str] = set()
    for raw_extra in extras:
        extra = raw_extra.strip().lower()
        if extra and extra not in seen_extras:
            seen_extras.add(extra)
            normalised_extras.append(extra)
    dependency_closure = _dependency_closure_audit(
        wheel=wheel,
        wheelhouse=wheelhouse,
        lockfile=lockfile,
        expected_platform=expected_platform,
        expected_python=expected_python,
        extras=tuple(normalised_extras),
    )
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "FAIL",
        "source_revision": source_revision,
        "artifact": {
            "filename": wheel.name,
            "sha256": _sha256(wheel),
            "bytes": wheel.stat().st_size,
        },
        "wheelhouse": {
            "path": str(wheelhouse),
            "wheel_count": len(inventory),
            "wheels": inventory,
        },
        "execution": {
            "network_resolution": False,
            "pip_install": "not_run",
            "commands": [],
        },
        "validation": {},
        "extras": {},
        "dependency_closure": dependency_closure,
        "errors": [],
    }
    if dependency_closure.get("status") == "FAIL":
        receipt["errors"].append("PEP 508/uv.lock dependency closure audit failed")
        return receipt

    environment = _clean_environment()
    with tempfile.TemporaryDirectory(prefix="scirel-offline-wheelhouse-") as temporary:
        workspace = Path(temporary)
        venv = workspace / "venv"
        create_command = [sys.executable, "-m", "venv", str(venv)]
        receipt["execution"]["commands"].append(create_command)
        created = _run(create_command, env=environment)
        receipt["execution"]["venv"] = {
            "returncode": created.returncode,
            "stdout": _trim(created.stdout),
            "stderr": _trim(created.stderr),
        }
        if created.returncode:
            receipt["errors"].append(
                f"clean virtual environment creation failed with exit code {created.returncode}"
            )
            return receipt

        python = _venv_python(venv)
        install_command = _pip_install_command(python, wheel, wheelhouse)
        receipt["execution"]["commands"].append(install_command)
        installed = _run(install_command, env=environment)
        receipt["execution"]["pip_install"] = {
            "status": "PASS" if installed.returncode == 0 else "FAIL",
            "returncode": installed.returncode,
            "stdout": _trim(installed.stdout),
            "stderr": _trim(installed.stderr),
        }
        if installed.returncode:
            receipt["errors"].append(
                "offline pip installation failed; dependency resolution did not complete "
                f"with exit code {installed.returncode}"
            )
            return receipt

        # pip resolves an extra by project name.  Stage only this exact wheel
        # in a private candidate directory so the extra install remains
        # offline while staying bound to the wheel already installed above.
        wheel_candidates = workspace / "scirel-wheel-candidate"
        wheel_candidates.mkdir()
        shutil.copy2(wheel, wheel_candidates / wheel.name)

        for extra in normalised_extras:
            extra_install = _pip_install_extra_command(
                python, extra, wheelhouse, wheel_candidates
            )
            receipt["execution"]["commands"].append(extra_install)
            extra_result = _run(extra_install, env=environment)
            receipt["extras"][extra] = {
                "install": {
                    "status": "PASS" if extra_result.returncode == 0 else "FAIL",
                    "returncode": extra_result.returncode,
                    "stdout": _trim(extra_result.stdout),
                    "stderr": _trim(extra_result.stderr),
                }
            }
            if extra_result.returncode:
                receipt["errors"].append(
                    f"offline installation of extra {extra!r} failed with exit code "
                    f"{extra_result.returncode}"
                )

        validation_path = workspace / "installed-wheel-validation.json"
        validate_command = [
            str(python),
            "-I",
            str(validator),
            "--expected-python",
            expected_python,
            "--wheel",
            str(wheel),
            "--output",
            str(validation_path),
        ]
        if expected_platform:
            validate_command[3:3] = ["--expected-platform", expected_platform]
        for extra in normalised_extras:
            validate_command.extend(["--extra", extra])
        receipt["execution"]["commands"].append(validate_command)
        validated = _run(validate_command, env=environment)
        if validation_path.is_file():
            try:
                receipt["validation"] = json.loads(validation_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                receipt["errors"].append(f"installed-wheel validation receipt is unreadable: {error}")
        else:
            receipt["errors"].append("installed-wheel validator produced no receipt")
        if validated.returncode:
            receipt["errors"].append(
                f"installed-wheel validation failed with exit code {validated.returncode}"
            )
        if receipt.get("validation", {}).get("status") != "PASS":
            receipt["errors"].append("installed-wheel validation receipt is not PASS")

    receipt["status"] = "PASS" if not receipt["errors"] else "FAIL"
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--expected-platform", help="for example linux-x86_64-cp314")
    parser.add_argument(
        "--source-revision",
        help="optional exact lowercase Git commit; required when binding this receipt to CURRENT",
    )
    parser.add_argument(
        "--expected-python",
        default=DEFAULT_EXPECTED_PYTHON,
        help=f"expected CPython major.minor line (default: {DEFAULT_EXPECTED_PYTHON})",
    )
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        dest="extras",
        metavar="NAME",
        help="install and validate an optional extra; repeat for multiple extras",
    )
    parser.add_argument(
        "--lockfile",
        type=Path,
        help="optional uv.lock used to audit direct and transitive dependency closure",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = validate_offline_wheelhouse(
            wheel_path=args.wheel,
            wheelhouse_path=args.wheelhouse,
            expected_platform=args.expected_platform,
            expected_python=args.expected_python,
            source_revision=args.source_revision,
            extras=tuple(args.extras),
            lockfile=args.lockfile,
        )
    except Exception as error:  # keep command failures machine-readable
        receipt = {
            "schema": SCHEMA,
            "status": "FAIL",
            "errors": [f"validation setup failed: {type(error).__name__}: {error}"],
        }
    rendered = json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if receipt.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

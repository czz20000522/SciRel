"""Validate the explicit SciRel platform and capability support matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any
import tomllib


ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"PASS", "PARTIAL", "FAIL", "BLOCKED", "NOT_RUN"}
_CPYTHON_LINE = re.compile(r"^CPython (?P<major>\d+)\.(?P<minor>\d+)$")
_PLATFORM_ID = re.compile(
    r"^(?P<os>[a-z0-9]+)-(?P<architecture>[a-z0-9_]+)-cp"
    r"(?P<major>\d)(?P<minor>\d+)$"
)
_PYTHON_SPECIFIER = re.compile(
    r"^(?P<operator>===|~=|==|!=|<=|>=|<|>)"
    r"(?P<version>\d+(?:\.\d+){0,2})(?P<wildcard>\.\*)?$"
)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _cpython_line(value: object, *, field: str) -> tuple[int, int]:
    if not isinstance(value, str):
        raise ValueError(f"{field} must identify a CPython version line")
    match = _CPYTHON_LINE.fullmatch(value)
    if match is None:
        raise ValueError(f"{field} must use the 'CPython X.Y' form")
    return int(match.group("major")), int(match.group("minor"))


def _version_tuple(value: str) -> tuple[int, int, int]:
    parts = tuple(int(part) for part in value.split("."))
    return (parts + (0, 0, 0))[:3]


def _requires_python_supports(specifier: object, version: tuple[int, int]) -> bool:
    """Return whether a Python version line is admitted by a simple PEP 440 set.

    The project currently uses the ordinary comma-separated comparison form
    (for example ``>=3.14,<3.15``).  Keeping this parser local avoids making
    the release validator depend on an installed runtime package while still
    rejecting malformed or unsupported declarations fail closed.
    """

    if not isinstance(specifier, str) or not specifier.strip():
        raise ValueError("project.requires-python must be a non-empty string")
    target = (*version, 0)
    for raw_token in specifier.split(","):
        token = raw_token.strip()
        match = _PYTHON_SPECIFIER.fullmatch(token)
        if match is None:
            raise ValueError(
                "project.requires-python contains an unsupported specifier: "
                f"{token!r}"
            )
        operator = match.group("operator")
        bound_text = match.group("version")
        bound = _version_tuple(bound_text)
        wildcard = match.group("wildcard") is not None
        if wildcard and operator not in {"==", "!="}:
            raise ValueError(
                "project.requires-python wildcard is only valid with == or !="
            )
        if wildcard:
            prefix = tuple(int(part) for part in bound_text.split("."))
            matches = target[: len(prefix)] == prefix
            allowed = matches if operator == "==" else not matches
        elif operator in {"==", "==="}:
            allowed = target == bound
        elif operator == "!=":
            allowed = target != bound
        elif operator == ">=":
            allowed = target >= bound
        elif operator == ">":
            allowed = target > bound
        elif operator == "<=":
            allowed = target <= bound
        elif operator == "<":
            allowed = target < bound
        else:  # ~=
            if len(bound_text.split(".")) == 1:
                upper = (bound[0] + 1, 0, 0)
            elif len(bound_text.split(".")) == 2:
                upper = (bound[0] + 1, 0, 0)
            else:
                upper = (bound[0], bound[1] + 1, 0)
            allowed = target >= bound and target < upper
        if not allowed:
            return False
    return True


def _validate_platform_identity(
    identifier: object,
    row: dict[str, Any],
    binding_python: tuple[int, int],
    project_requires_python: object,
) -> str:
    if not isinstance(identifier, str) or not identifier:
        raise ValueError(f"duplicate or invalid platform id: {identifier!r}")
    match = _PLATFORM_ID.fullmatch(identifier)
    if match is None:
        raise ValueError(f"platform id has an invalid canonical form: {identifier}")
    expected = {
        "os": match.group("os"),
        "architecture": match.group("architecture"),
        "python": f"CPython {int(match.group('major'))}.{int(match.group('minor'))}",
    }
    for field in ("os", "architecture", "python"):
        if row[field] != expected[field]:
            raise ValueError(
                f"platform {identifier} {field} differs from its canonical id"
            )
    row_python = _cpython_line(row["python"], field=f"platform {identifier} python")
    if row_python != binding_python:
        raise ValueError(
            f"platform {identifier} Python line differs from runtime_binding.python"
        )
    if not _requires_python_supports(project_requires_python, row_python):
        raise ValueError(
            f"platform {identifier} Python line is outside project.requires-python"
        )
    return identifier


def validate_matrix(root: Path = ROOT) -> dict[str, Any]:
    path = root / "release/platform-support-matrix.json"
    matrix = _read(path)
    if matrix.get("schema") != "scirel.platform-support-matrix.v1":
        raise ValueError("unsupported platform matrix schema")
    if not matrix.get("package_version") or not matrix.get("runtime_binding"):
        raise ValueError("platform matrix must bind package version and runtime")
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    current = _read(root / "release/CURRENT.json")
    project_version = project.get("project", {}).get("version")
    if matrix["package_version"] != project_version or matrix["package_version"] != current.get("version"):
        raise ValueError("platform matrix package_version differs from project/current release")
    binding = matrix["runtime_binding"]
    if not isinstance(binding, dict) or binding.get("release_tuple") != "release/CURRENT.json":
        raise ValueError("platform matrix runtime_binding.release_tuple is invalid")
    binding_python = _cpython_line(
        binding.get("python"), field="platform matrix runtime_binding.python"
    )
    project_requires_python = project.get("project", {}).get("requires-python")

    platforms = matrix.get("platforms")
    if not isinstance(platforms, list) or not platforms:
        raise ValueError("platform matrix must declare platforms")
    platform_ids: set[str] = set()
    for row in platforms:
        if not isinstance(row, dict):
            raise ValueError("platform row must be an object")
        required = {"id", "os", "architecture", "python", "status", "evidence", "scope"}
        if set(row) != required:
            raise ValueError(f"platform row keys must be {sorted(required)}")
        identifier = row["id"]
        if not isinstance(identifier, str) or not identifier or identifier in platform_ids:
            raise ValueError(f"duplicate or invalid platform id: {identifier!r}")
        _validate_platform_identity(
            identifier,
            row,
            binding_python,
            project_requires_python,
        )
        platform_ids.add(identifier)
        if row["status"] not in STATUSES:
            raise ValueError(f"invalid platform status: {identifier}")
        if not isinstance(row["evidence"], list):
            raise ValueError(f"platform evidence must be a list: {identifier}")
        for evidence in row["evidence"]:
            if not isinstance(evidence, str) or not evidence or Path(evidence).is_absolute():
                raise ValueError(f"platform evidence must be repository-relative: {identifier}")
            if not (root / evidence).is_file():
                raise ValueError(f"platform evidence is missing: {evidence}")

    capabilities = matrix.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        raise ValueError("platform matrix must declare capabilities")
    capability_ids: set[str] = set()
    for row in capabilities:
        if not isinstance(row, dict):
            raise ValueError("capability row must be an object")
        identifier = row.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in capability_ids:
            raise ValueError(f"duplicate or invalid capability id: {identifier!r}")
        capability_ids.add(identifier)
        if row.get("status") not in STATUSES:
            raise ValueError(f"invalid capability status: {identifier}")
        declared_platforms = row.get("platforms")
        if not isinstance(declared_platforms, list) or not declared_platforms:
            raise ValueError(f"capability has no platforms: {identifier}")
        if not set(declared_platforms) <= platform_ids:
            raise ValueError(f"capability references undeclared platform: {identifier}")
        if row["status"] == "PASS" and not row.get("reason"):
            raise ValueError(f"PASS capability needs evidence reason: {identifier}")

    return {
        "schema": matrix["schema"],
        "package_version": matrix["package_version"],
        "platform_count": len(platforms),
        "capability_count": len(capabilities),
        "platforms": {row["id"]: row["status"] for row in platforms},
        "capabilities": {row["id"]: row["status"] for row in capabilities},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        print(json.dumps(validate_matrix(args.root), ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

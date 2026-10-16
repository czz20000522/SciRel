"""Validate the explicit SciRel platform and capability support matrix."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import tomllib


ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"PASS", "PARTIAL", "FAIL", "BLOCKED", "NOT_RUN"}


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


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

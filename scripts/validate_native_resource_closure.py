"""Validate SciRel's explicit native capability resource closure.

The closure is a source-side inventory.  It documents which native files are
kept for each capability group and gives the wheel builder a fail-closed list
to compare with its package-data output.  It does not claim that an external
runtime is installed or that a capability is scientifically released.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tomllib
import zipfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tools/wheel/native-resource-closure.json"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"native closure is not readable JSON: {path}") from error
    if not isinstance(value, dict):
        raise ValueError("native closure must be a JSON object")
    return value


def _safe_relative(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{field} is unsafe: {value!r}")
    return path.as_posix()


def _matches(pattern: str, relative: str) -> bool:
    """Match the small package-data pattern vocabulary used by this project."""

    if pattern.endswith("/**/*"):
        prefix = pattern[: -len("**/*")]
        return relative.startswith(prefix)
    return PurePosixPath(relative).match(pattern)


def _source_resources(root: Path) -> set[str]:
    kinetic = root / "src/scirel/kinetic"
    resources: set[str] = set()
    for path in (kinetic / "_fluidbw_native").rglob("*"):
        if path.is_file() and path.suffix == ".m":
            resources.add(path.relative_to(kinetic).as_posix())
    for path in (kinetic / "pdrk/_native").rglob("*"):
        if path.is_file():
            resources.add(path.relative_to(kinetic).as_posix())
    return resources


def _group_file_map(root: Path, manifest: dict[str, Any]) -> tuple[dict[str, set[str]], set[str]]:
    groups = manifest.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("native closure groups must be a non-empty list")
    by_group: dict[str, set[str]] = {}
    owners: dict[str, str] = {}
    for index, group in enumerate(groups):
        if not isinstance(group, dict):
            raise ValueError(f"native closure group {index} is invalid")
        group_id = group.get("id")
        if not isinstance(group_id, str) or not group_id or group_id in by_group:
            raise ValueError(f"native closure group {index} has a duplicate or invalid id")
        files = group.get("files")
        digests = group.get("file_digests")
        if not isinstance(files, list) or not files:
            raise ValueError(f"native closure group {group_id} has no files")
        if not isinstance(digests, dict):
            raise ValueError(f"native closure group {group_id} has no file_digests")
        listed: set[str] = set()
        for item in files:
            relative = _safe_relative(item, field=f"native closure {group_id}.files")
            if relative in listed:
                raise ValueError(f"native closure group {group_id} repeats {relative}")
            path = (root / "src/scirel/kinetic" / relative).resolve()
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"native closure group {group_id} names a missing/non-file resource: {relative}")
            summary = digests.get(relative)
            if (
                not isinstance(summary, dict)
                or not isinstance(summary.get("sha256"), str)
                or len(summary["sha256"]) != 64
                or any(character not in "0123456789abcdef" for character in summary["sha256"])
                or not isinstance(summary.get("bytes"), int)
                or isinstance(summary["bytes"], bool)
            ):
                raise ValueError(f"native closure group {group_id} has an invalid digest for {relative}")
            data = path.read_bytes()
            if summary["bytes"] != len(data) or summary["sha256"] != hashlib.sha256(data).hexdigest():
                raise ValueError(f"native closure digest differs from source resource: {relative}")
            listed.add(relative)
            previous = owners.get(relative)
            if previous is not None:
                raise ValueError(f"native closure resource appears in both {previous} and {group_id}: {relative}")
            owners[relative] = group_id
        if set(digests) != listed:
            raise ValueError(f"native closure group {group_id} file_digests differ from files")
        by_group[group_id] = listed
    return by_group, set(owners)


def _validate_bindings(manifest: dict[str, Any], by_group: dict[str, set[str]]) -> None:
    bindings = manifest.get("package_data_bindings")
    if not isinstance(bindings, list) or not bindings:
        raise ValueError("native closure package_data_bindings must be a non-empty list")
    referenced: set[str] = set()
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            raise ValueError(f"native closure package-data binding {index} is invalid")
        package = binding.get("package")
        patterns = binding.get("patterns")
        groups_value = binding.get("group", binding.get("groups"))
        group_ids = [groups_value] if isinstance(groups_value, str) else groups_value
        if not isinstance(package, str) or not package.startswith("scirel"):
            raise ValueError(f"native closure package-data binding {index} has an invalid package")
        if not isinstance(patterns, list) or not patterns or any(not isinstance(p, str) for p in patterns):
            raise ValueError(f"native closure package-data binding {index} has invalid patterns")
        if not isinstance(group_ids, list) or not group_ids or any(g not in by_group for g in group_ids):
            raise ValueError(f"native closure package-data binding {index} names unknown groups")
        package_parts = package.split(".")
        if package_parts[:2] != ["scirel", "kinetic"]:
            raise ValueError(f"native closure package-data binding {index} has an invalid package")
        # The manifest paths are relative to ``src/scirel/kinetic``.  Thus
        # ``scirel.kinetic`` has an empty prefix and ``scirel.kinetic.pdrk``
        # has the single prefix ``pdrk``.
        source_prefix = "/".join(package_parts[2:])
        for group_id in group_ids:
            for resource in by_group[group_id]:
                if source_prefix:
                    prefix = source_prefix + "/"
                    if not resource.startswith(prefix):
                        raise ValueError(
                            f"native closure resource {resource} does not belong to package {package}"
                        )
                    package_relative = resource[len(prefix) :]
                else:
                    package_relative = resource
                if not any(_matches(pattern, package_relative) for pattern in patterns):
                    raise ValueError(
                        f"native closure resource {resource} is not covered by {package} package-data patterns"
                    )
                referenced.add(resource)
    all_resources = set().union(*by_group.values())
    if referenced != all_resources:
        missing = sorted(all_resources - referenced)
        raise ValueError("native closure resources are not covered by package-data bindings: " + ", ".join(missing))


def _validate_pyproject_package_data(root: Path, manifest: dict[str, Any]) -> None:
    """Require the manifest's package-data declarations to match pyproject."""

    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ValueError("pyproject.toml is not readable for native package-data validation") from error
    actual = project.get("tool", {}).get("setuptools", {}).get("package-data", {})
    if not isinstance(actual, dict):
        raise ValueError("pyproject.toml package-data table is invalid")
    expected: dict[str, set[str]] = {}
    for binding in manifest["package_data_bindings"]:
        package = binding["package"]
        patterns = binding["patterns"]
        expected.setdefault(package, set()).update(patterns)
    for package, patterns in expected.items():
        actual_patterns = actual.get(package)
        if not isinstance(actual_patterns, list) or any(not isinstance(p, str) for p in actual_patterns):
            raise ValueError(f"pyproject.toml has no valid package-data for native package {package}")
        if set(actual_patterns) != patterns:
            raise ValueError(
                f"pyproject.toml package-data differs from native closure for {package}"
            )


def _validate_catalog_capabilities(root: Path, manifest: dict[str, Any], *, required: bool = True) -> None:
    known: set[str] = set()
    catalog = root / "catalog/examples"
    if catalog.is_dir():
        for path in catalog.glob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if isinstance(value, dict) and isinstance(value.get("asset_id"), str):
                known.add(value["asset_id"])
    for group in manifest["groups"]:
        capabilities = group.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities or any(not isinstance(c, str) for c in capabilities):
            raise ValueError(f"native closure group {group['id']} must declare capabilities")
        if required and known:
            unknown = sorted(set(capabilities) - known)
            if unknown:
                raise ValueError(f"native closure group {group['id']} names unknown catalog capabilities: {', '.join(unknown)}")


def _validate_wheel(
    wheel: Path,
    expected_resources: set[str],
    expected_digests: dict[str, dict[str, Any]],
) -> None:
    try:
        with zipfile.ZipFile(wheel) as archive:
            names = set(archive.namelist())
    except (OSError, zipfile.BadZipFile) as error:
        raise ValueError(f"wheel is not a readable ZIP: {wheel}") from error
    expected_members = {"scirel/kinetic/" + resource for resource in expected_resources}
    actual_members = {
        name
        for name in names
        if name.startswith("scirel/kinetic/_fluidbw_native/")
        or name.startswith("scirel/kinetic/pdrk/_native/")
    }
    if actual_members != expected_members:
        missing = sorted(expected_members - actual_members)
        extra = sorted(actual_members - expected_members)
        detail = []
        if missing:
            detail.append("missing: " + ", ".join(missing))
        if extra:
            detail.append("extra: " + ", ".join(extra))
        raise ValueError("wheel native resource members differ from closure (" + "; ".join(detail) + ")")
    with zipfile.ZipFile(wheel) as archive:
        for resource in sorted(expected_resources):
            member = "scirel/kinetic/" + resource
            data = archive.read(member)
            summary = expected_digests[resource]
            if len(data) != summary["bytes"] or hashlib.sha256(data).hexdigest() != summary["sha256"]:
                raise ValueError(f"wheel native resource bytes differ from closure: {resource}")


def validate(root: Path = ROOT, *, manifest_path: Path = MANIFEST, wheel: Path | None = None) -> dict[str, Any]:
    manifest = _read(manifest_path)
    if manifest.get("schema") != "scirel.native-resource-closure.v1":
        raise ValueError("native closure has an invalid schema")
    if manifest.get("package") != "scirel":
        raise ValueError("native closure names an unexpected package")
    source_root = manifest.get("source_root")
    if source_root != "src/scirel/kinetic":
        raise ValueError("native closure source_root must be src/scirel/kinetic")
    by_group, listed = _group_file_map(root, manifest)
    source = _source_resources(root)
    if listed != source:
        missing = sorted(source - listed)
        extra = sorted(listed - source)
        detail = []
        if missing:
            detail.append("missing: " + ", ".join(missing))
        if extra:
            detail.append("extra: " + ", ".join(extra))
        raise ValueError("native closure does not exactly cover source resources (" + "; ".join(detail) + ")")
    _validate_bindings(manifest, by_group)
    _validate_pyproject_package_data(root, manifest)
    _validate_catalog_capabilities(root, manifest)
    digest_map = {
        path: summary
        for group in manifest["groups"]
        for path, summary in group["file_digests"].items()
    }
    if set(digest_map) != listed:
        raise ValueError("native closure digest map does not cover all resources")
    if wheel is not None:
        _validate_wheel(wheel.resolve(), listed, digest_map)
    return {
        "schema": manifest["schema"],
        "groups": {group_id: len(files) for group_id, files in by_group.items()},
        "resource_count": len(listed),
        "wheel_checked": wheel is not None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--wheel", type=Path)
    args = parser.parse_args()
    result = validate(args.root.resolve(), manifest_path=args.manifest.resolve(), wheel=args.wheel)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

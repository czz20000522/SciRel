"""Validate a fresh-process SciRel capability runtime-closure receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import tomllib
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "scirel.capability-runtime-closure"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def _fail(message: str) -> None:
    raise ValueError(message)


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{field} must be a non-empty string")
    return value


def validate_receipt(
    value: dict[str, Any],
    *,
    expected_revision: str | None = None,
    require_clean_source: bool = False,
    require_bound: bool = False,
    expected_system: str | None = None,
    expected_machine: str | None = None,
    expected_python_implementation: str | None = None,
    expected_python_line: str | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        _fail("receipt schema is invalid")
    if value.get("status") not in {"PASS", "FAIL"}:
        _fail("receipt status must be PASS or FAIL")
    binding_status = value.get("binding_status")
    if binding_status not in {"BOUND", "UNBOUND"}:
        _fail("receipt binding_status must be BOUND or UNBOUND")
    binding_reasons = value.get("binding_reasons")
    if not isinstance(binding_reasons, list) or any(
        not isinstance(reason, str) or not reason for reason in binding_reasons
    ):
        _fail("receipt binding_reasons must be a string array")
    if binding_reasons != sorted(set(binding_reasons)):
        _fail("receipt binding_reasons must be sorted and unique")
    if binding_status == "UNBOUND" and not binding_reasons:
        _fail("UNBOUND receipt must preserve binding reasons")
    mode = value.get("mode")
    if mode not in {"import", "probe"}:
        _fail("receipt mode must be import or probe")

    source = value.get("source")
    if not isinstance(source, dict):
        _fail("receipt source binding is missing")
    _string(source.get("root"), "source.root")
    revision = source.get("revision")
    if revision is not None and (not isinstance(revision, str) or not _GIT_SHA.fullmatch(revision)):
        _fail("source.revision must be null or an exact Git SHA")
    dirty = source.get("dirty")
    if not isinstance(dirty, bool):
        _fail("source.dirty must be boolean")
    if "content_sha256" not in source:
        _fail("source.content_sha256 is missing")
    content_sha = source.get("content_sha256")
    if content_sha is not None and (
        not isinstance(content_sha, str) or not _SHA256.fullmatch(content_sha)
    ):
        _fail("source.content_sha256 must be null or a SHA-256 digest")
    if require_clean_source:
        if revision is None:
            _fail("clean source requires an exact Git revision")
        if dirty:
            _fail("source tree is dirty")
    source_after = value.get("source_after")
    if not isinstance(source_after, dict):
        _fail("receipt source_after binding is missing")
    for field in ("root", "revision", "dirty", "package_version", "content_sha256"):
        if field not in source_after:
            _fail(f"source_after.{field} is missing")
    if source_after.get("root") != source.get("root"):
        _fail("source_after.root differs from source.root")
    after_revision = source_after.get("revision")
    if after_revision is not None and (
        not isinstance(after_revision, str) or not _GIT_SHA.fullmatch(after_revision)
    ):
        _fail("source_after.revision must be null or an exact Git SHA")
    if not isinstance(source_after.get("dirty"), bool):
        _fail("source_after.dirty must be boolean")
    _string(source_after.get("package_version"), "source_after.package_version")
    after_content_sha = source_after.get("content_sha256")
    if after_content_sha is not None and (
        not isinstance(after_content_sha, str) or not _SHA256.fullmatch(after_content_sha)
    ):
        _fail("source_after.content_sha256 must be null or a SHA-256 digest")
    if expected_revision is not None:
        if not _GIT_SHA.fullmatch(expected_revision):
            _fail("expected_revision must be an exact Git SHA")
        if revision != expected_revision:
            _fail("source revision differs from expected revision")
    package_version = _string(source.get("package_version"), "source.package_version")
    project_path = Path(source["root"]) / "pyproject.toml"
    try:
        project = tomllib.loads(project_path.read_text(encoding="utf-8"))
        expected_version = project.get("project", {}).get("version")
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, AttributeError):
        expected_version = None
    if isinstance(expected_version, str) and package_version != expected_version:
        _fail("source.package_version differs from pyproject.toml")
    if binding_status == "BOUND":
        if source != source_after:
            _fail("BOUND receipt source identity changed during measurement")
        if revision is None or dirty:
            _fail("BOUND receipt requires an exact clean Git source")
        if binding_reasons:
            _fail("BOUND receipt must not have binding reasons")
    if require_bound and binding_status != "BOUND":
        _fail("receipt is not BOUND")

    child = value.get("child")
    if not isinstance(child, dict):
        _fail("receipt child is missing")
    if not isinstance(child.get("isolated"), bool) or not isinstance(child.get("executed"), bool):
        _fail("receipt child must declare boolean isolated and executed")
    if binding_status == "BOUND" and (
        not child["executed"] or not child["isolated"]
    ):
        _fail("BOUND receipt child must be an executed isolated process")
    if value["status"] == "PASS" and (
        not child["executed"] or not child["isolated"]
    ):
        _fail("PASS receipt child must be an executed isolated process")
    argv = child.get("argv")
    if argv != [value.get("python", {}).get("executable"), "-I", "-c"]:
        _fail("receipt child argv does not declare the isolated interpreter")

    python = value.get("python")
    if not isinstance(python, dict):
        _fail("receipt Python identity is missing")
    _string(python.get("implementation"), "python.implementation")
    _string(python.get("version"), "python.version")
    _string(python.get("executable"), "python.executable")
    platform = value.get("platform")
    if not isinstance(platform, dict):
        _fail("receipt platform identity is missing")
    _string(platform.get("system"), "platform.system")
    _string(platform.get("machine"), "platform.machine")
    if expected_system is not None and platform["system"] != expected_system:
        _fail("platform.system differs from expected system")
    if expected_machine is not None and platform["machine"] != expected_machine:
        _fail("platform.machine differs from expected machine")
    if expected_python_implementation is not None and python["implementation"] != expected_python_implementation:
        _fail("python implementation differs from expected implementation")
    if expected_python_line is not None:
        version = python["version"]
        if version != expected_python_line and not version.startswith(expected_python_line + "."):
            _fail("python version differs from expected Python line")

    target = value.get("target")
    if not isinstance(target, dict) or not target:
        _fail("receipt target is missing")
    if mode == "probe":
        probe_sha256 = value.get("probe_sha256")
        if probe_sha256 is None:
            if value["status"] == "PASS" or child["executed"]:
                _fail("executed probe receipt requires probe_sha256")
        elif not isinstance(probe_sha256, str) or not _SHA256.fullmatch(probe_sha256):
            _fail("probe_sha256 must be null or a SHA-256 digest")
        probe_after = value.get("probe_sha256_after")
        if probe_after is not None and (
            not isinstance(probe_after, str) or not _SHA256.fullmatch(probe_after)
        ):
            _fail("probe_sha256_after must be null or a SHA-256 digest")
        if binding_status == "BOUND" and probe_after is None:
            _fail("BOUND probe receipt requires probe_sha256_after")
    elif value.get("probe_sha256") is not None:
        _fail("import mode must not carry probe_sha256")
    elif value.get("probe_sha256_after") is not None:
        _fail("import mode must not carry probe_sha256_after")
    if value.get("probe_sha256") != value.get("probe_sha256_after") and binding_status == "BOUND":
        _fail("BOUND receipt probe identity changed during measurement")

    roots = value.get("external_import_roots")
    if not isinstance(roots, list) or any(not isinstance(item, str) or not item for item in roots):
        _fail("external_import_roots must be a string array")
    if roots != sorted(set(roots)):
        _fail("external_import_roots must be sorted and unique")
    distributions = value.get("distributions")
    if not isinstance(distributions, list):
        _fail("distributions must be an array")
    distribution_roots: list[str] = []
    for index, row in enumerate(distributions):
        if not isinstance(row, dict):
            _fail(f"distributions[{index}] must be an object")
        root = _string(row.get("import_root"), f"distributions[{index}].import_root")
        distribution_roots.append(root)
        entries = row.get("distributions")
        if not isinstance(entries, list):
            _fail(f"distributions[{index}].distributions must be an array")
        for entry in entries:
            if not isinstance(entry, dict):
                _fail(f"distributions[{index}] entry must be an object")
            _string(entry.get("name"), "distribution.name")
            if entry.get("version") is not None and not isinstance(entry.get("version"), str):
                _fail("distribution.version must be null or a string")
    if distribution_roots != sorted(set(distribution_roots)):
        _fail("distributions must be sorted and unique")
    if distribution_roots != roots:
        _fail("distributions must cover external_import_roots exactly")

    if not isinstance(value.get("loaded_module_count"), int) or value["loaded_module_count"] < 0:
        _fail("loaded_module_count must be a nonnegative integer")
    loaded = value.get("loaded_scirel_modules")
    if not isinstance(loaded, list) or any(not isinstance(item, str) for item in loaded):
        _fail("loaded_scirel_modules must be a string array")
    if loaded != sorted(set(loaded)) or any(
        item != "scirel" and not item.startswith("scirel.") for item in loaded
    ):
        _fail("loaded_scirel_modules must be sorted, unique SciRel modules")
    child_returncode = value.get("child_returncode")
    if not isinstance(child_returncode, int):
        _fail("child_returncode must be an integer")
    if value["status"] == "PASS" and child_returncode != 0:
        _fail("PASS receipt must have child_returncode 0")
    if value["status"] == "FAIL" and value.get("error") is None:
        _fail("FAIL receipt must preserve an error")
    if not isinstance(value.get("duration_ms"), (int, float)) or value["duration_ms"] < 0:
        _fail("duration_ms must be nonnegative")
    error = value.get("error")
    if error is not None and not isinstance(error, dict):
        _fail("error must be null or an object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--expected-revision")
    parser.add_argument("--require-clean-source", action="store_true")
    parser.add_argument("--require-bound", action="store_true")
    parser.add_argument("--expected-system")
    parser.add_argument("--expected-machine")
    parser.add_argument("--expected-python-implementation")
    parser.add_argument("--expected-python-line")
    args = parser.parse_args(argv)
    try:
        value = json.loads(args.receipt.read_text(encoding="utf-8"))
        validate_receipt(
            value,
            expected_revision=args.expected_revision,
            require_clean_source=args.require_clean_source,
            require_bound=args.require_bound,
            expected_system=args.expected_system,
            expected_machine=args.expected_machine,
            expected_python_implementation=args.expected_python_implementation,
            expected_python_line=args.expected_python_line,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(f"runtime closure receipt validation failed: {error}")
        return 1
    print(json.dumps({"schema": SCHEMA, "status": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

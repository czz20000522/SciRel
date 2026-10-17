"""Build one SciRel wheel from an exact Git commit.

The source checkout is the versioned truth. This helper archives the requested
Git ref into a temporary directory before invoking the build backend, so the
wheel never depends on an uncommitted working tree or checkout file mtimes.
The output directory is deliberately required to live outside the repository;
the wheel and its manifest are build artifacts, not another source snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def resolve_revision(ref: str) -> str:
    """Resolve ``ref`` to a full commit id and reject non-commit objects."""

    revision = _run_git("rev-parse", "--verify", f"{ref}^{{commit}}")
    if len(revision) != 40 or any(ch not in "0123456789abcdef" for ch in revision):
        raise ValueError(f"Git ref did not resolve to a full commit: {ref}")
    return revision


def commit_epoch(revision: str) -> int:
    value = _run_git("show", "-s", "--format=%ct", revision)
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"Git commit has an invalid commit timestamp: {revision}") from error


def _project_metadata(source_root: Path) -> tuple[str, str]:
    try:
        metadata = tomllib.loads((source_root / "pyproject.toml").read_text(encoding="utf-8"))
        project = metadata["project"]
        name = project["name"]
        version = project["version"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        raise ValueError("archived source has no readable project name/version") from error
    if not isinstance(name, str) or not name:
        raise ValueError("archived project.name must be a non-empty string")
    if not isinstance(version, str) or not version:
        raise ValueError("archived project.version must be a non-empty string")
    return name, version


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json_object(path: Path, *, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not readable JSON: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return value


def _source_relative_path(source: Path, value: object, *, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must be a safe relative path: {value}")
    resolved = (source / path).resolve()
    if not resolved.is_relative_to(source.resolve()) or not resolved.is_file() or resolved.is_symlink():
        raise ValueError(f"{field} does not name a regular source file: {value}")
    return resolved


def _source_file_summary(source: Path, value: object, *, field: str) -> dict[str, object]:
    path = _source_relative_path(source, value, field=field)
    relative = path.relative_to(source).as_posix()
    return {
        "path": relative,
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _wheel_content_binding(wheel: Path) -> dict[str, object]:
    """Summarize every wheel member and its package subset.

    The summary lives beside the external wheel rather than inside it.  It is
    intentionally derived from the final ZIP bytes, so a later validator can
    detect a changed member even when the outer artifact digest was copied
    incorrectly.
    """

    try:
        with zipfile.ZipFile(wheel) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ValueError("wheel contains duplicate members")
            members: list[dict[str, object]] = []
            for info in sorted(infos, key=lambda item: item.filename):
                if info.is_dir() or info.filename.endswith("/"):
                    raise ValueError(f"wheel contains a directory member: {info.filename}")
                if "\\" in info.filename or info.filename.startswith("/"):
                    raise ValueError(f"wheel member has an unsafe path: {info.filename}")
                path = PurePosixPath(info.filename)
                if any(part in {"", ".", ".."} for part in path.parts):
                    raise ValueError(f"wheel member has an unsafe path: {info.filename}")
                data = archive.read(info)
                members.append(
                    {
                        "path": info.filename,
                        "sha256": _sha256_bytes(data),
                        "bytes": len(data),
                    }
                )
    except zipfile.BadZipFile as error:
        raise ValueError(f"wheel is not a valid ZIP archive: {wheel}") from error

    package_members = [
        entry["path"]
        for entry in members
        if isinstance(entry.get("path"), str)
        and entry["path"].startswith("scirel/")
    ]
    return {
        "schema": "scirel.wheel-contents.v1",
        "members": members,
        "package_members": package_members,
    }


def _native_resource_closure_binding(
    source: Path,
    *,
    wheel_contents: dict[str, object],
) -> dict[str, object] | None:
    """Bind the source native-resource closure to actual wheel ZIP members.

    The closure is optional for historical refs.  Once a source ref carries
    it, a build fails closed if a resource is missing, extra, or byte-different
    in the wheel.  This keeps future split/package decisions in Git while
    leaving old dev9 manifests untouched.
    """

    closure_path = source / "release/wheel/native-resource-closure.json"
    if not closure_path.is_file() or closure_path.is_symlink():
        return None
    closure = _read_json_object(closure_path, label="native resource closure")
    if closure.get("schema") != "scirel.native-resource-closure.v1":
        raise ValueError("native resource closure has an invalid schema")
    if closure.get("package") != "scirel":
        raise ValueError("native resource closure names an unexpected package")
    groups = closure.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("native resource closure groups are invalid")
    expected: dict[str, dict[str, object]] = {}
    group_counts: dict[str, int] = {}
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("id"), str):
            raise ValueError("native resource closure group is invalid")
        group_id = group["id"]
        digests = group.get("file_digests")
        if not isinstance(digests, dict) or not digests:
            raise ValueError(f"native resource closure group has no file_digests: {group_id}")
        group_counts[group_id] = len(digests)
        for relative, summary in digests.items():
            if not isinstance(relative, str) or not isinstance(summary, dict):
                raise ValueError(f"native resource closure digest row is invalid: {group_id}")
            path = PurePosixPath(relative)
            if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
                raise ValueError(f"native resource closure path is unsafe: {relative}")
            if relative in expected:
                raise ValueError(f"native resource closure repeats resource: {relative}")
            source_file = (source / "src/scirel/kinetic" / path).resolve()
            if not source_file.is_file() or source_file.is_symlink():
                raise ValueError(f"native resource closure source file is missing: {relative}")
            digest = summary.get("sha256")
            size = summary.get("bytes")
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
                or not isinstance(size, int)
                or isinstance(size, bool)
            ):
                raise ValueError(f"native resource closure digest is invalid: {relative}")
            if _sha256(source_file) != digest or source_file.stat().st_size != size:
                raise ValueError(f"native resource closure digest differs from source: {relative}")
            expected[relative] = {"sha256": digest, "bytes": size, "group": group_id}
    package_members = set(wheel_contents.get("package_members", []))
    member_rows = {
        row.get("path"): row
        for row in wheel_contents.get("members", [])
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }
    expected_members = {"scirel/kinetic/" + relative for relative in expected}
    actual_native = {
        member
        for member in package_members
        if member.startswith("scirel/kinetic/_fluidbw_native/")
        or member.startswith("scirel/kinetic/pdrk/_native/")
    }
    if actual_native != expected_members:
        missing = sorted(expected_members - actual_native)
        extra = sorted(actual_native - expected_members)
        detail = []
        if missing:
            detail.append("missing: " + ", ".join(missing))
        if extra:
            detail.append("extra: " + ", ".join(extra))
        raise ValueError("wheel native resource members differ from source closure (" + "; ".join(detail) + ")")
    for relative, summary in expected.items():
        row = member_rows.get("scirel/kinetic/" + relative)
        if row is None or row.get("sha256") != summary["sha256"] or row.get("bytes") != summary["bytes"]:
            raise ValueError(f"wheel native resource bytes differ from source closure: {relative}")
    return {
        "schema": "scirel.native-resource-closure.v1",
        "path": closure_path.relative_to(source).as_posix(),
        "sha256": _sha256(closure_path),
        "bytes": closure_path.stat().st_size,
        "resource_count": len(expected),
        "group_counts": group_counts,
    }


def _module_wheel_member(module: str, package_members: set[str]) -> str:
    if not isinstance(module, str) or not module or not module.startswith("scirel"):
        raise ValueError(f"document public_api.python.module is invalid: {module!r}")
    module_path = module.replace(".", "/")
    direct = module_path + ".py"
    package = module_path + "/__init__.py"
    if direct in package_members:
        return direct
    if package in package_members:
        return package
    raise ValueError(f"document public API module is absent from wheel: {module}")


def _release_binding(
    source: Path,
    *,
    revision: str,
    version: str,
    wheel_contents: dict[str, object],
) -> dict[str, object] | None:
    """Bind a v2 source release tuple to the final wheel ZIP.

    Older refs intentionally have no binding because their release tuple was
    issued before this extension.  That preserves historical dev9 manifests;
    a later ref must carry a self-contained v2 tuple before the extension is
    emitted.
    """

    current_path = source / "release/CURRENT.json"
    if not current_path.is_file() or current_path.is_symlink():
        return None
    current = _read_json_object(current_path, label="release CURRENT")
    if current.get("schema") != "scirel.release-current.v2":
        return None
    # ``release/CURRENT.json`` is written after the source commit that it
    # describes: adding the tuple changes the Git commit hash, so a source
    # archive cannot contain a self-referential CURRENT record.  A ref whose
    # tuple still points at an older commit is therefore an ordinary
    # development build and receives no embedded release binding.  The later
    # coordination commit binds its external manifests back to this source
    # revision through the alignment validator.
    if current.get("package") != "scirel" or current.get("version") != version:
        return None
    if current.get("source_revision") != revision:
        return None
    wheel = current.get("wheel")
    docs = current.get("documentation")
    if not isinstance(wheel, dict) or not isinstance(docs, dict):
        raise ValueError("release CURRENT lacks wheel/documentation objects")
    layout_value = wheel.get("package_layout")
    selection_value = docs.get("source_documents")
    handbook_value = docs.get("handbook")
    integration_value = docs.get("integration_record")
    matrix_value = "release/platform-support-matrix.json"
    layout_path = _source_relative_path(source, layout_value, field="wheel package_layout")
    selection_path = _source_relative_path(source, selection_value, field="documentation source_documents")
    handbook_path = _source_relative_path(source, handbook_value, field="documentation handbook")
    integration_path = _source_relative_path(source, integration_value, field="documentation integration_record")
    matrix_path = _source_relative_path(source, matrix_value, field="platform support matrix")

    layout = _read_json_object(layout_path, label="wheel layout")
    if layout.get("schema") != "scirel.wheel-layout.v1":
        raise ValueError("wheel layout has an invalid schema")
    domain_packages = layout.get("domain_packages")
    organized = layout.get("organized_general_primitives")
    if not isinstance(domain_packages, list) or any(not isinstance(item, str) for item in domain_packages):
        raise ValueError("wheel layout domain_packages is invalid")
    if not isinstance(organized, dict):
        raise ValueError("wheel layout organized_general_primitives is invalid")
    package_members = set(wheel_contents.get("package_members", []))
    expected_layout_members: set[str] = set()
    for domain in domain_packages:
        expected_layout_members.add(f"scirel/{domain}/__init__.py")
    for package, modules in organized.items():
        if not isinstance(package, str) or not isinstance(modules, list):
            raise ValueError("wheel layout organized_general_primitives has an invalid entry")
        for module in modules:
            if not isinstance(module, str):
                raise ValueError("wheel layout primitive module is invalid")
            expected_layout_members.add(f"scirel/{package}/{module}.py")
    missing_layout = sorted(expected_layout_members - package_members)
    if missing_layout:
        raise ValueError("wheel is missing layout package members: " + ", ".join(missing_layout))

    selection = _read_json_object(selection_path, label="selected document set")
    if selection.get("schema") != "scirel.selected-document-set.v1":
        raise ValueError("selected document set has an invalid schema")
    rows = selection.get("records")
    if not isinstance(rows, list) or not rows:
        raise ValueError("selected document set is empty")
    capabilities: list[dict[str, object]] = []
    seen_assets: set[str] = set()
    counts = {"operators": 0, "task_graphs": 0, "document_closure": len(rows)}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"asset_id", "path", "sha256"}:
            raise ValueError("selected document set contains an invalid row")
        asset_id = row["asset_id"]
        if not isinstance(asset_id, str) or not asset_id or asset_id in seen_assets:
            raise ValueError("selected document set repeats or lacks asset_id")
        seen_assets.add(asset_id)
        document_path = _source_relative_path(source, row["path"], field=f"document[{asset_id}]")
        if _sha256(document_path) != row["sha256"]:
            raise ValueError(f"document digest differs from selection: {asset_id}")
        document = _read_json_object(document_path, label=f"document[{asset_id}]")
        if document.get("asset_id") != asset_id:
            raise ValueError(f"document asset_id differs from selection: {asset_id}")
        kind = document.get("kind")
        if kind == "operator":
            counts["operators"] += 1
        elif kind == "task_graph":
            counts["task_graphs"] += 1
        else:
            raise ValueError(f"selected document has unsupported kind: {asset_id}")
        document_version = document.get("version")
        if not isinstance(document_version, dict) or document_version.get("implementation_version") != version:
            raise ValueError(f"document implementation version differs: {asset_id}")
        public_api = document.get("public_api")
        python_api = public_api.get("python") if isinstance(public_api, dict) else None
        if not isinstance(python_api, dict):
            raise ValueError(f"document lacks Python public API: {asset_id}")
        module = python_api.get("module")
        symbol = python_api.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            raise ValueError(f"document public API symbol is invalid: {asset_id}")
        wheel_member = _module_wheel_member(module, package_members)
        capability: dict[str, object] = {
            "asset_id": asset_id,
            "kind": kind,
            "module": module,
            "symbol": symbol,
            "wheel_member": wheel_member,
        }
        canonical_module = python_api.get("canonical_module")
        canonical_symbol = python_api.get("canonical_symbol")
        if canonical_module is not None or canonical_symbol is not None:
            if (
                not isinstance(canonical_module, str)
                or not isinstance(canonical_symbol, str)
                or not canonical_module
                or not canonical_symbol
                or not canonical_module.startswith("scirel.")
                or not all(part.isidentifier() for part in canonical_module.split("."))
                or not canonical_symbol.isidentifier()
            ):
                raise ValueError(f"document canonical public API is invalid: {asset_id}")
            canonical_wheel_member = _module_wheel_member(
                canonical_module, package_members
            )
            if not canonical_wheel_member.endswith("/__init__.py"):
                raise ValueError(
                    f"document canonical module is not a package: {asset_id}"
                )
            capability.update(
                {
                    "canonical_module": canonical_module,
                    "canonical_symbol": canonical_symbol,
                    "canonical_wheel_member": canonical_wheel_member,
                }
            )
        capabilities.append(capability)
    expected_counts = wheel.get("selected_capabilities")
    doc_counts = docs.get("capability_counts")
    if expected_counts != counts or doc_counts != counts:
        raise ValueError("release CURRENT capability counts differ from selected documents")

    matrix = _read_json_object(matrix_path, label="platform support matrix")
    if matrix.get("schema") != "scirel.platform-support-matrix.v1":
        raise ValueError("platform support matrix has an invalid schema")
    if matrix.get("package") != "scirel" or matrix.get("package_version") != version:
        raise ValueError("platform support matrix package/version differs")

    integration = _read_json_object(integration_path, label="document integration record")
    if integration.get("status") != "PASS":
        raise ValueError("document integration record is not PASS")
    if integration.get("project_version") != version:
        raise ValueError("document integration record version differs")
    if integration.get("source_revision") != revision:
        raise ValueError("document integration record source_revision differs")
    selection_binding = integration.get("selection")
    handbook_binding = integration.get("handbook")
    if not isinstance(selection_binding, dict) or not isinstance(handbook_binding, dict):
        raise ValueError("document integration record lacks selection/handbook binding")

    selection_relative = selection_path.relative_to(source).as_posix()
    handbook_relative = handbook_path.relative_to(source).as_posix()
    selection_digest = _sha256(selection_path)
    handbook_digest = _sha256(handbook_path)
    if (
        selection_binding.get("path") != selection_relative
        or selection_binding.get("sha256") != selection_digest
    ):
        raise ValueError("integration selection digest/path differs from source files")
    if (
        handbook_binding.get("path") != handbook_relative
        or handbook_binding.get("sha256") != handbook_digest
    ):
        raise ValueError("integration handbook digest/path differs from source files")

    def file_summary(path: Path) -> dict[str, object]:
        return {
            "path": path.relative_to(source).as_posix(),
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }

    return {
        "schema": "scirel.release-binding.v1",
        "source": {"revision": revision, "version": version},
        "files": {
            "current": file_summary(current_path),
            "layout": file_summary(layout_path),
            "selection": file_summary(selection_path),
            "handbook": file_summary(handbook_path),
            "integration": file_summary(integration_path),
            "platform_matrix": file_summary(matrix_path),
        },
        "layout": {
            "path": layout_path.relative_to(source).as_posix(),
            "sha256": _sha256(layout_path),
            "domain_packages": sorted(domain_packages),
            "organized_general_primitives": organized,
            "members": sorted(expected_layout_members),
        },
        "selection": {
            "path": selection_relative,
            "sha256": selection_digest,
            "counts": counts,
            "capabilities": capabilities,
        },
        "handbook": {
            "path": handbook_relative,
            "sha256": handbook_digest,
            "scope": docs.get("handbook_scope", "exact"),
        },
        "integration": {
            "path": integration_path.relative_to(source).as_posix(),
            "sha256": _sha256(integration_path),
            "selection_sha256": selection_binding.get("sha256"),
            "handbook_sha256": handbook_binding.get("sha256"),
        },
        "platform_matrix": {
            "path": matrix_path.relative_to(source).as_posix(),
            "sha256": _sha256(matrix_path),
            "platform_ids": sorted(
                row["id"] for row in matrix.get("platforms", [])
                if isinstance(row, dict) and isinstance(row.get("id"), str)
            ),
        },
        "capability_counts": counts,
        "wheel_members": sorted(package_members),
    }


def _file_summary(path: Path, *, relative: str) -> dict[str, object]:
    """Return the stable identity of one build input file."""

    if not path.is_file() or path.is_symlink():
        raise ValueError(f"build input is not a regular file: {relative}")
    return {
        "path": relative,
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _safe_relative_path(value: str, *, field: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must be a relative path: {value}")
    return path


def _license_input_paths(source: Path, metadata: dict[str, object]) -> list[Path]:
    """Resolve the license files declared by the archived project metadata.

    PEP 639 uses ``project.license-files`` as a list of relative glob
    patterns.  Older refs may not declare it, so fall back to the repository's
    conventional ``licenses/`` tree without making that absence a build
    failure.  Directories and symlinks are excluded because neither is a
    license payload copied into a wheel.
    """

    project = metadata.get("project")
    if not isinstance(project, dict):
        raise ValueError("archived pyproject.toml has no project table")
    declared = project.get("license-files")
    if declared is None:
        patterns: list[str] = []
    elif isinstance(declared, str):
        patterns = [declared]
    elif isinstance(declared, list) and all(isinstance(item, str) for item in declared):
        patterns = list(declared)
    else:
        raise ValueError("project.license-files must be a string or list of strings")

    candidates: set[Path] = set()
    if patterns:
        for pattern in patterns:
            _safe_relative_path(pattern, field="project.license-files")
            for path in source.glob(pattern):
                if path.is_file() and not path.is_symlink():
                    candidates.add(path)
    else:
        licenses = source / "licenses"
        if licenses.is_dir() and not licenses.is_symlink():
            candidates.update(
                path
                for path in licenses.rglob("*")
                if path.is_file() and not path.is_symlink()
            )
    return sorted(candidates, key=lambda path: path.relative_to(source).as_posix())


def build_input_binding(source: Path, *, helper_paths: Iterable[str]) -> dict[str, object]:
    """Summarize source and helper inputs that affect a ref-bound build.

    This is additive metadata in the existing ``scirel.git-build.v1`` and
    ``scirel.git-docs-build.v1`` manifests.  It does not alter ``CURRENT`` or
    require historical manifests to be regenerated.  ``uv.lock`` is optional
    for older Git refs, but when present its bytes are always bound.
    """

    source = source.resolve()
    pyproject = source / "pyproject.toml"
    if not pyproject.is_file() or pyproject.is_symlink():
        raise ValueError("archived source has no regular pyproject.toml")
    try:
        metadata = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError("archived pyproject.toml is not readable TOML") from error

    files: dict[str, dict[str, object]] = {
        "pyproject.toml": _file_summary(pyproject, relative="pyproject.toml")
    }
    lockfile = source / "uv.lock"
    if lockfile.is_file() and not lockfile.is_symlink():
        files["uv.lock"] = _file_summary(lockfile, relative="uv.lock")
    license_files = _license_input_paths(source, metadata)
    for path in license_files:
        relative = path.relative_to(source).as_posix()
        files[relative] = _file_summary(path, relative=relative)

    return {
        "schema": "scirel.build-inputs.v1",
        "files": files,
        "license_files": [
            path.relative_to(source).as_posix() for path in license_files
        ],
        "helper": helper_binding(helper_paths),
    }


def helper_binding(paths: Iterable[str]) -> dict[str, object]:
    """Bind the exact helper source used by an external build.

    The Git revision identifies the checkout baseline while per-file digests
    detect a locally modified helper.  This keeps the old ref-bound build
    workflow usable while making a dirty helper explicit in the manifest.
    """

    normalized = sorted(
        {
            _safe_relative_path(path, field="helper path").as_posix()
            for path in paths
        }
    )
    files: dict[str, dict[str, object]] = {}
    for relative in normalized:
        path = ROOT / relative
        files[relative] = _file_summary(path, relative=relative)
    try:
        revision = resolve_revision("HEAD")
        status = _run_git("status", "--porcelain", "--", *normalized) if normalized else ""
    except (OSError, subprocess.CalledProcessError, ValueError):
        revision = None
        status = ""
    return {
        "revision": revision,
        "dirty": bool(status),
        "files": files,
    }


def _archive_ref(revision: str, epoch: int, destination: Path) -> Path:
    archive = destination / "source.tar"
    with archive.open("wb") as stream:
        subprocess.run(
            ["git", "archive", "--format=tar", f"--mtime=@{epoch}", revision],
            cwd=ROOT,
            check=True,
            stdout=stream,
        )
    source = destination / "source"
    source.mkdir()
    with tarfile.open(archive, mode="r") as tar:
        tar.extractall(source, filter="data")
    archive.unlink()
    _normalize_archive_modes(source)
    return source


def _normalize_archive_modes(source: Path) -> None:
    """Normalize extracted Git-tree permissions before invoking the backend.

    ``git archive`` records the repository mode (normally ``0644`` for regular
    files and ``0755`` for executable files), but a tar extractor applies the
    host process' umask while creating those paths.  A Linux container with a
    permissive umask can therefore materialize package data as ``0664`` while
    the same archive on macOS materializes it as ``0644``.  Setuptools carries
    those modes into ZIP external attributes, making otherwise identical
    ``py3-none-any`` wheels differ byte-for-byte.  Keep executable bits where
    they were present and make every other regular file and directory
    deterministic across hosts.
    """

    if not source.is_dir():
        raise ValueError(f"archived source is not a directory: {source}")
    for path in sorted(source.rglob("*"), key=lambda candidate: candidate.as_posix()):
        if path.is_symlink():
            # ``filter='data'`` normally rejects unsafe links.  Do not follow
            # a link while normalizing modes if a repository deliberately
            # contains a safe one.
            continue
        if path.is_dir():
            path.chmod(0o755)
        elif path.is_file():
            current_mode = path.stat().st_mode
            path.chmod(0o755 if current_mode & 0o111 else 0o644)
        else:
            raise ValueError(f"archived source contains a non-regular path: {path}")


def build_from_ref(
    ref: str,
    output_dir: Path,
    *,
    uv: str = "uv",
    python: str | None = None,
) -> dict[str, object]:
    """Build and return a stable manifest for one exact Git commit."""

    output_dir = output_dir.expanduser().resolve()
    if output_dir == ROOT or output_dir.is_relative_to(ROOT):
        raise ValueError("output-dir must be outside the SciRel repository")
    if output_dir.exists():
        if not output_dir.is_dir() or any(output_dir.iterdir()):
            raise ValueError(f"output-dir must be a new empty directory: {output_dir}")
    else:
        output_dir.mkdir(parents=True)

    uv_path = shutil.which(uv) if os.path.sep not in uv else uv
    if not uv_path:
        raise FileNotFoundError(f"build executable not found: {uv}")

    revision = resolve_revision(ref)
    epoch = commit_epoch(revision)
    try:
        previous_umask = os.umask(0o022)
    except (AttributeError, NotImplementedError):
        previous_umask = None
    try:
        with tempfile.TemporaryDirectory(prefix="scirel-git-build-") as temporary:
            staging = Path(temporary)
            source = _archive_ref(revision, epoch, staging)
            name, version = _project_metadata(source)
            wheel_dir = staging / "wheel"
            wheel_dir.mkdir()
            environment = dict(os.environ)
            environment.update(
                {
                    "SOURCE_DATE_EPOCH": str(epoch),
                    "PYTHONHASHSEED": "0",
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
            command = [
                uv_path,
                "build",
                "--wheel",
                "--no-create-gitignore",
                "--out-dir",
                str(wheel_dir),
            ]
            if python is not None:
                command.extend(["--python", python])
            command.append(str(source))
            build_result = subprocess.run(
                command,
                cwd=source,
                env=environment,
                capture_output=True,
                text=True,
            )
            if build_result.returncode:
                if build_result.stdout:
                    sys.stderr.write(build_result.stdout)
                if build_result.stderr:
                    sys.stderr.write(build_result.stderr)
                build_result.check_returncode()
            wheels = sorted(wheel_dir.glob("*.whl"))
            if len(wheels) != 1:
                raise ValueError(f"expected exactly one wheel, found {len(wheels)}")
            wheel = wheels[0]
            expected_prefix = f"{name.replace('-', '_')}-{version}-"
            if not wheel.name.startswith(expected_prefix):
                raise ValueError(
                    f"wheel filename {wheel.name!r} does not match {name} {version}"
                )
            target = output_dir / wheel.name
            shutil.copyfile(wheel, target)
            wheel_contents = _wheel_content_binding(target)
            release_binding = _release_binding(
                source,
                revision=revision,
                version=version,
                wheel_contents=wheel_contents,
            )
            native_resource_closure = _native_resource_closure_binding(
                source,
                wheel_contents=wheel_contents,
            )
            inputs = build_input_binding(
                source,
                helper_paths=("scripts/build_scirel_from_ref.py",),
            )
    finally:
        if previous_umask is not None:
            os.umask(previous_umask)

    uv_version = subprocess.run(
        [uv_path, "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest: dict[str, object] = {
        "schema": "scirel.git-build.v1",
        "source": {
            "ref": ref,
            "revision": revision,
            "commit_epoch": epoch,
        },
        "project": {"name": name, "version": version},
        "inputs": inputs,
        "wheel": {
            "filename": target.name,
            "sha256": _sha256(target),
            "bytes": target.stat().st_size,
        },
        "contents": wheel_contents,
        "builder": {
            "command": "uv build --wheel",
            "source_date_epoch": epoch,
            "python_hash_seed": 0,
            "umask": "022",
            "source": "git archive",
            "uv_version": uv_version,
            "python_selector": python or "uv default",
            "runner_python": sys.version,
            "host_platform": platform.platform(),
            "host_machine": platform.machine(),
        },
    }
    if release_binding is not None:
        manifest["release_binding"] = release_binding
    if native_resource_closure is not None:
        manifest["native_resource_closure"] = native_resource_closure
    (output_dir / "build-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, help="Git ref or commit to archive")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="new directory outside the repository for the wheel and manifest",
    )
    parser.add_argument("--uv", default="uv", help="uv executable (default: uv)")
    parser.add_argument(
        "--python",
        help="Python selector passed to uv build, for example 3.14 or /path/to/python",
    )
    args = parser.parse_args()
    manifest = build_from_ref(args.ref, args.output_dir, uv=args.uv, python=args.python)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

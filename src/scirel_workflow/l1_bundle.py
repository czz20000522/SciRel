"""Canonical UTF-8 transport for saved L1 project bundles.

The CodeFusion body runner transports UTF-8 JSON, not an archive byte stream.
This module converts a saved ImportIntake directory or ZIP into a deterministic,
content-addressed JSON document without executing any supplied code.  Importing
that document projects only structural facts into the existing L1 inventory
shape; scientific normalization remains model-owned.
"""

from __future__ import annotations

import argparse
import base64
import binascii
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata
from typing import Any
import zipfile

from .l1_inventory import (
    INVENTORY_SCHEMA,
    L1AssetEntry,
    L1Inventory,
    L1ProjectInventory,
)
from .models import canonical_json


L1_BUNDLE_SCHEMA = "scirel.l1-bundle.dev"
MAX_L1_BUNDLE_FILES = 4096
MAX_L1_FILE_BYTES = 4 * 1024 * 1024
MAX_L1_TOTAL_BYTES = 10 * 1024 * 1024
MAX_L1_BUNDLE_JSON_BYTES = 14 * 1024 * 1024

_GENERATED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__MACOSX",
    "__pycache__",
}
_ROOT_MARKERS = {
    "asset_entry.py",
    "configs",
    "docker",
    "extraction_ledger.md",
    "extraction_report.md",
    "operators",
    "program_framework_map.md",
    "task_graphs",
}
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_ASSET_REF = re.compile(
    r"(?:^|[{,])\s*asset_ref\s*:\s*"
    r'(?:"([^\"]+)"|\'([^\']+)\'|([^,}#\r\n]+))'
)
_NULL_ASSET_REFS = {"null", "Null", "NULL", "~"}


@dataclass(frozen=True)
class _BundleFile:
    path: str
    content: bytes

    @property
    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.content).hexdigest()

    def manifest_entry(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "digest": self.digest,
            "size": len(self.content),
            "content_base64": base64.b64encode(self.content).decode("ascii"),
        }

    def identity_entry(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "digest": self.digest,
            "size": len(self.content),
        }


def _project_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("L1 bundle project_id must be a non-empty string")
    value = unicodedata.normalize("NFC", value.strip())
    if len(value) > 128 or value in {".", ".."} or any(
        char in value for char in ("/", "\\", "\x00")
    ):
        raise ValueError("L1 bundle project_id is not portable")
    return value


def _relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ValueError("L1 bundle paths must be non-empty POSIX paths")
    value = unicodedata.normalize("NFC", value)
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or re.match(r"^[A-Za-z]:", value)
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"unsafe L1 bundle path: {value!r}")
    normalized = path.as_posix()
    if len(normalized.encode("utf-8")) > 1024:
        raise ValueError("L1 bundle path is too long")
    return normalized


def _is_generated(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return any(part in _GENERATED_PARTS for part in parts) or path.endswith(
        (".pyc", ".pyo")
    )


def _tree_digest(files: Iterable[_BundleFile]) -> str:
    hasher = hashlib.sha256()
    for item in sorted(files, key=lambda candidate: candidate.path):
        hasher.update(item.path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(item.content)
        hasher.update(b"\0")
    return "sha256:" + hasher.hexdigest()


def _bounded_files(files: Iterable[_BundleFile]) -> tuple[_BundleFile, ...]:
    bounded: list[_BundleFile] = []
    seen: set[str] = set()
    total = 0
    for item in sorted(files, key=lambda candidate: candidate.path):
        path = _relative_path(item.path)
        collision_key = path.casefold()
        if collision_key in seen:
            raise ValueError(f"duplicate or case-colliding L1 bundle path: {path}")
        seen.add(collision_key)
        if len(item.content) > MAX_L1_FILE_BYTES:
            raise ValueError(f"L1 bundle file exceeds the per-file limit: {path}")
        total += len(item.content)
        if total > MAX_L1_TOTAL_BYTES:
            raise ValueError("L1 bundle exceeds the uncompressed content limit")
        bounded.append(_BundleFile(path, item.content))
        if len(bounded) > MAX_L1_BUNDLE_FILES:
            raise ValueError("L1 bundle contains too many files")
    if not bounded:
        raise ValueError("L1 bundle contains no files")
    return tuple(bounded)


def _bundle(project_id: str, files: Iterable[_BundleFile]) -> dict[str, Any]:
    project_id = _project_id(project_id)
    bounded = _bounded_files(files)
    payload = {
        "schema": L1_BUNDLE_SCHEMA,
        "project_id": project_id,
        "bundle_digest": _tree_digest(bounded),
        "file_count": len(bounded),
        "total_bytes": sum(len(item.content) for item in bounded),
        "files": [item.manifest_entry() for item in bounded],
    }
    encoded = canonical_json(payload)
    if len(encoded) > MAX_L1_BUNDLE_JSON_BYTES:
        raise ValueError("L1 bundle JSON exceeds the body-wire transport limit")
    l1_bundle_to_payload(payload)
    return payload


def _directory_files(root: Path) -> tuple[_BundleFile, ...]:
    if root.is_symlink():
        raise ValueError("L1 project root may not be a symlink")
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"L1 project directory does not exist: {root}")
    files: list[_BundleFile] = []
    total = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise ValueError(f"L1 project may not contain symlinks: {path}")
        relative = _relative_path(path.relative_to(root).as_posix())
        if _is_generated(relative):
            continue
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"L1 project contains a non-regular file: {relative}")
        size = path.stat().st_size
        if size > MAX_L1_FILE_BYTES:
            raise ValueError(f"L1 bundle file exceeds the per-file limit: {relative}")
        total += size
        if total > MAX_L1_TOTAL_BYTES:
            raise ValueError("L1 bundle exceeds the uncompressed content limit")
        if len(files) >= MAX_L1_BUNDLE_FILES:
            raise ValueError("L1 bundle contains too many files")
        files.append(_BundleFile(relative, path.read_bytes()))
    return tuple(files)


def _strip_archive_root(paths: list[str]) -> dict[str, str]:
    if any(PurePosixPath(path).parts[0] in _ROOT_MARKERS for path in paths):
        return {path: path for path in paths}
    first_parts = {PurePosixPath(path).parts[0] for path in paths}
    if len(first_parts) != 1:
        return {path: path for path in paths}
    mapped = {
        path: PurePosixPath(*PurePosixPath(path).parts[1:]).as_posix()
        for path in paths
        if len(PurePosixPath(path).parts) > 1
    }
    if mapped and any(
        PurePosixPath(path).parts[0] in _ROOT_MARKERS for path in mapped.values()
    ):
        return mapped
    return {path: path for path in paths}


def _zip_files(archive_path: Path) -> tuple[_BundleFile, ...]:
    if archive_path.is_symlink():
        raise ValueError("L1 ZIP may not be a symlink")
    if not archive_path.is_file():
        raise ValueError(f"L1 ZIP does not exist: {archive_path}")
    try:
        archive = zipfile.ZipFile(archive_path)
    except zipfile.BadZipFile as exc:
        raise ValueError("L1 archive is not a valid ZIP") from exc
    with archive:
        candidates: list[tuple[zipfile.ZipInfo, str]] = []
        for info in archive.infolist():
            raw_path = info.filename.rstrip("/") if info.is_dir() else info.filename
            if not raw_path:
                continue
            normalized = _relative_path(raw_path)
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise ValueError(f"L1 ZIP may not contain symlinks: {normalized}")
            if info.is_dir() or _is_generated(normalized):
                continue
            if info.flag_bits & 0x1:
                raise ValueError(f"L1 ZIP may not contain encrypted files: {normalized}")
            if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
                raise ValueError(f"L1 ZIP uses an unsupported compression method: {normalized}")
            if info.file_size > MAX_L1_FILE_BYTES:
                raise ValueError(f"L1 bundle file exceeds the per-file limit: {normalized}")
            candidates.append((info, normalized))
        if len(candidates) > MAX_L1_BUNDLE_FILES:
            raise ValueError("L1 bundle contains too many files")
        if sum(info.file_size for info, _ in candidates) > MAX_L1_TOTAL_BYTES:
            raise ValueError("L1 bundle exceeds the uncompressed content limit")
        roots = _strip_archive_root([path for _, path in candidates])
        files: list[_BundleFile] = []
        for info, original in candidates:
            mapped = roots.get(original)
            if not mapped:
                continue
            mapped = _relative_path(mapped)
            with archive.open(info) as member:
                content = member.read(MAX_L1_FILE_BYTES + 1)
            if len(content) > MAX_L1_FILE_BYTES or len(content) != info.file_size:
                raise ValueError(f"L1 ZIP member size is invalid: {mapped}")
            files.append(_BundleFile(mapped, content))
    return tuple(files)


def build_l1_bundle(
    source: str | Path, *, project_id: str | None = None
) -> dict[str, Any]:
    """Build one canonical bundle from an ImportIntake directory or ZIP."""

    path = Path(source)
    if path.is_dir():
        files = _directory_files(path)
        inferred_id = path.name
    elif path.is_file():
        files = _zip_files(path)
        inferred_id = path.stem
    else:
        raise ValueError(f"L1 bundle source does not exist: {path}")
    return _bundle(project_id or inferred_id, files)


def canonical_l1_bundle_bytes(
    source: str | Path, *, project_id: str | None = None
) -> bytes:
    """Return the exact UTF-8 JSON artifact body accepted by import_l1."""

    return canonical_json(build_l1_bundle(source, project_id=project_id))


def _decode_bundle(payload: Mapping[str, Any]) -> tuple[str, tuple[_BundleFile, ...]]:
    required = {
        "schema",
        "project_id",
        "bundle_digest",
        "file_count",
        "total_bytes",
        "files",
    }
    missing = required.difference(payload)
    unknown = set(payload).difference(required)
    if missing:
        raise ValueError("L1 bundle is missing fields: " + ", ".join(sorted(missing)))
    if unknown:
        raise ValueError("L1 bundle has unknown fields: " + ", ".join(sorted(unknown)))
    if payload["schema"] != L1_BUNDLE_SCHEMA:
        raise ValueError(f"unsupported L1 bundle schema: {payload['schema']}")
    project_id = _project_id(payload["project_id"])
    if payload["project_id"] != project_id:
        raise ValueError("L1 bundle project_id must use its canonical form")
    if not isinstance(payload["files"], list):
        raise ValueError("L1 bundle files must be an array")
    if len(payload["files"]) > MAX_L1_BUNDLE_FILES:
        raise ValueError("L1 bundle contains too many files")
    files: list[_BundleFile] = []
    total = 0
    seen: set[str] = set()
    for index, entry in enumerate(payload["files"]):
        if not isinstance(entry, Mapping):
            raise ValueError(f"L1 bundle files[{index}] must be an object")
        expected = {"path", "digest", "size", "content_base64"}
        if set(entry) != expected:
            raise ValueError(f"L1 bundle files[{index}] fields are invalid")
        path = _relative_path(entry["path"])
        if entry["path"] != path:
            raise ValueError(f"L1 bundle path must use its canonical form: {path}")
        if _is_generated(path):
            raise ValueError(f"generated files are not allowed in an L1 bundle: {path}")
        collision_key = path.casefold()
        if collision_key in seen:
            raise ValueError(f"duplicate or case-colliding L1 bundle path: {path}")
        seen.add(collision_key)
        if not isinstance(entry["size"], int) or isinstance(entry["size"], bool):
            raise ValueError(f"L1 bundle files[{index}].size must be an integer")
        if not 0 <= entry["size"] <= MAX_L1_FILE_BYTES:
            raise ValueError(f"L1 bundle file size is outside the limit: {path}")
        total += entry["size"]
        if total > MAX_L1_TOTAL_BYTES:
            raise ValueError("L1 bundle exceeds the uncompressed content limit")
        if not isinstance(entry["content_base64"], str):
            raise ValueError(f"L1 bundle files[{index}].content_base64 must be a string")
        if len(entry["content_base64"]) > 4 * ((MAX_L1_FILE_BYTES + 2) // 3):
            raise ValueError(f"L1 bundle encoded file exceeds the limit: {path}")
        try:
            content = base64.b64decode(entry["content_base64"], validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(
                f"L1 bundle files[{index}].content_base64 is invalid"
            ) from exc
        item = _BundleFile(path, content)
        if entry["size"] != len(content):
            raise ValueError(f"L1 bundle file size does not match content: {path}")
        if not isinstance(entry["digest"], str) or not _SHA256.fullmatch(
            entry["digest"]
        ):
            raise ValueError(f"L1 bundle file digest is invalid: {path}")
        if entry["digest"] != item.digest:
            raise ValueError(f"L1 bundle file digest does not match content: {path}")
        files.append(item)
    bounded = _bounded_files(files)
    if not isinstance(payload["file_count"], int) or isinstance(
        payload["file_count"], bool
    ):
        raise ValueError("L1 bundle file_count must be an integer")
    if payload["file_count"] != len(bounded):
        raise ValueError("L1 bundle file_count does not match files")
    if not isinstance(payload["total_bytes"], int) or isinstance(
        payload["total_bytes"], bool
    ):
        raise ValueError("L1 bundle total_bytes must be an integer")
    if payload["total_bytes"] != total:
        raise ValueError("L1 bundle total_bytes does not match files")
    if not isinstance(payload["bundle_digest"], str) or not _SHA256.fullmatch(
        payload["bundle_digest"]
    ):
        raise ValueError("L1 bundle bundle_digest is invalid")
    if payload["bundle_digest"] != _tree_digest(bounded):
        raise ValueError("L1 bundle digest does not match file contents")
    if len(canonical_json(dict(payload))) > MAX_L1_BUNDLE_JSON_BYTES:
        raise ValueError("L1 bundle JSON exceeds the body-wire transport limit")
    return project_id, bounded


def _dependency_refs(content: bytes) -> tuple[str, ...]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("TaskGraph contract must be UTF-8") from exc
    refs: list[str] = []
    for line in text.splitlines():
        for match in _ASSET_REF.finditer(line):
            ref = next(value for value in match.groups() if value is not None)
            ref = ref.strip().replace("\\", "/")
            if ref and ref not in _NULL_ASSET_REFS and ref not in refs:
                refs.append(ref)
    return tuple(refs)


def _asset_projection(
    project_id: str, files: tuple[_BundleFile, ...]
) -> tuple[tuple[L1AssetEntry, ...], dict[str, dict[str, Any]]]:
    by_path = {item.path: item for item in files}
    assets: list[L1AssetEntry] = []
    enriched: dict[str, dict[str, Any]] = {}
    for kind, root in (("operator", "operators"), ("task_graph", "task_graphs")):
        names = sorted(
            {
                parts[1]
                for path in by_path
                if len(parts := PurePosixPath(path).parts) >= 3
                and parts[0] == root
            }
        )
        for name in names:
            prefix = f"{root}/{name}/"
            package_files = tuple(
                item for item in files if item.path.startswith(prefix)
            )
            if kind == "operator":
                contract_path = prefix + "operator.md"
                documentation_path = contract_path
                python_impl = prefix + "scientific_operator.py"
                c_impl = prefix + "scientific_operator.c"
                c_header = prefix + "scientific_operator.h"
                if python_impl in by_path:
                    implementation_paths = [python_impl]
                elif c_impl in by_path and c_header in by_path:
                    implementation_paths = [c_impl, c_header]
                else:
                    implementation_paths = []
                test_paths = [
                    path
                    for path in (
                        prefix + "test_scientific_operator.py",
                        prefix + "test_scientific_operator.c",
                    )
                    if path in by_path
                ]
            else:
                contract_path = prefix + "task_graph.yaml"
                documentation_path = prefix + "task_graph.md"
                implementation_paths = (
                    [prefix + "graph.py"] if prefix + "graph.py" in by_path else []
                )
                test_paths = (
                    [prefix + "test_task_graph.py"]
                    if prefix + "test_task_graph.py" in by_path
                    else []
                )
            gaps: list[str] = []
            if contract_path not in by_path:
                gaps.append(f"missing_contract:{contract_path}")
            if documentation_path not in by_path:
                gaps.append(f"missing_documentation:{documentation_path}")
            if not implementation_paths:
                gaps.append(f"missing_implementation:{prefix.rstrip('/')}")
            if not test_paths:
                gaps.append(f"missing_test:{prefix.rstrip('/')}")
            dependencies: tuple[str, ...] = ()
            if kind == "task_graph" and contract_path in by_path:
                try:
                    dependencies = _dependency_refs(by_path[contract_path].content)
                except ValueError:
                    gaps.append(f"invalid_utf8_contract:{contract_path}")
            asset = L1AssetEntry(
                project_id=project_id,
                kind=kind,
                name=name,
                asset_path=f"{root}/{name}",
                contract_path=contract_path if contract_path in by_path else None,
                implementation_path=(
                    implementation_paths[0] if implementation_paths else None
                ),
                direct_test_path=test_paths[0] if test_paths else None,
                dependency_refs=dependencies,
                source_digest=_tree_digest(package_files),
                gaps=tuple(gaps),
            )
            assets.append(asset)
            record = asset.to_dict()
            record.update(
                {
                    "documentation_path": (
                        documentation_path if documentation_path in by_path else None
                    ),
                    "implementation_paths": implementation_paths,
                    "direct_test_paths": test_paths,
                    "package_files": [
                        item.identity_entry() for item in package_files
                    ],
                }
            )
            enriched[asset.asset_id] = record
    return tuple(assets), enriched


def l1_bundle_to_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a canonical bundle and project its real structural facts."""

    if not isinstance(payload, Mapping):
        raise ValueError("L1 bundle must be a JSON object")
    project_id, files = _decode_bundle(payload)
    by_path = {item.path: item for item in files}
    assets, enriched = _asset_projection(project_id, files)
    if not assets:
        raise ValueError("L1 bundle contains no operator or TaskGraph packages")
    project_gaps = []
    for path, gap in (
        ("asset_entry.py", "missing_asset_entry"),
        ("extraction_ledger.md", "missing_extraction_ledger"),
        ("extraction_report.md", "missing_extraction_report"),
        ("program_framework_map.md", "missing_program_framework_map"),
    ):
        if path not in by_path:
            project_gaps.append(gap)
    for root in ("operators", "task_graphs"):
        if any(
            len(PurePosixPath(path).parts) == 2
            and PurePosixPath(path).parts[0] == root
            for path in by_path
        ):
            project_gaps.append(f"unexpected_{root}_root_file")
    ledger = by_path.get("extraction_ledger.md")
    framework = by_path.get("program_framework_map.md")
    project = L1ProjectInventory(
        project_id=project_id,
        ledger_path="extraction_ledger.md" if ledger else None,
        framework_map_path="program_framework_map.md" if framework else None,
        ledger_digest=ledger.digest if ledger else None,
        framework_map_digest=framework.digest if framework else None,
        assets=assets,
        gaps=tuple(project_gaps),
    )
    inventory = L1Inventory(projects=(project,), source_root="uploaded-l1-bundle")
    result = inventory.to_project_l1_payloads()[0]
    result["inventory_id"] = (
        "l1-bundle-" + payload["bundle_digest"].removeprefix("sha256:")[:16]
    )
    result["inventory_digest"] = payload["bundle_digest"]
    result["assets"] = [enriched[asset.asset_id] for asset in assets]
    result["automated_checks"] = [
        {
            "name": "l1_bundle_integrity",
            "project_id": project_id,
            "status": "passed",
            "bundle_digest": payload["bundle_digest"],
            "file_count": payload["file_count"],
            "issues": [],
        },
        *result["automated_checks"],
    ]
    result["schema"] = INVENTORY_SCHEMA
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a canonical SciRel L1 bundle JSON from a directory or ZIP."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--project-id")
    args = parser.parse_args(argv)
    body = canonical_l1_bundle_bytes(args.source, project_id=args.project_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as stream:
        stream.write(body)
    summary = json.loads(body)
    print(
        json.dumps(
            {
                "schema": summary["schema"],
                "project_id": summary["project_id"],
                "bundle_digest": summary["bundle_digest"],
                "file_count": summary["file_count"],
                "total_bytes": summary["total_bytes"],
                "output": str(args.output.resolve()),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

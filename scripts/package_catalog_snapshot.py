"""Package one verified catalog directory as a deterministic ZIP snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


CATALOG_SCHEMA = "scirel.catalog-release"


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _partition_path(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError(f"invalid catalog partition path: {relative!r}")
    posix = PurePosixPath(relative)
    if posix.is_absolute() or posix.as_posix() != relative or any(part in {".", ".."} for part in posix.parts):
        raise ValueError(f"invalid catalog partition path: {relative!r}")
    path = root.joinpath(*posix.parts)
    if any(root.joinpath(*posix.parts[:depth]).is_symlink() for depth in range(1, len(posix.parts) + 1)):
        raise ValueError(f"catalog partition contains a symlink: {relative}")
    if not path.resolve().is_relative_to(root):
        raise ValueError(f"catalog partition escapes snapshot: {relative}")
    return path


def package_catalog_snapshot(catalog_dir: Path, output_path: Path) -> dict[str, object]:
    root = catalog_dir.resolve(strict=True)
    output = output_path.resolve()
    if output.exists():
        raise FileExistsError(f"catalog snapshot already exists: {output}")
    if output.is_relative_to(root):
        raise ValueError("catalog snapshot output must be outside the catalog directory")

    release_path = root / "release.json"
    if release_path.is_symlink():
        raise ValueError("catalog release.json may not be a symlink")
    release_bytes = release_path.read_bytes()
    release = json.loads(release_bytes)
    if not isinstance(release, dict) or release.get("schema") != CATALOG_SCHEMA:
        raise ValueError("invalid catalog release schema")
    unsigned = {key: value for key, value in release.items() if key != "root_digest"}
    if release.get("root_digest") != _digest(_canonical_json(unsigned)):
        raise ValueError("catalog root digest does not match release.json")
    partitions = release.get("partitions")
    if not isinstance(partitions, list) or not partitions:
        raise ValueError("catalog release has no partitions")

    files = {"release.json": release_bytes}
    for partition in partitions:
        if not isinstance(partition, dict):
            raise ValueError("catalog partition entry must be an object")
        relative = partition.get("path")
        path = _partition_path(root, relative)
        if relative in files:
            raise ValueError(f"duplicate catalog partition: {relative}")
        payload = path.read_bytes()
        if partition.get("bytes") != len(payload) or partition.get("sha256") != _digest(payload):
            raise ValueError(f"catalog partition digest or size mismatch: {relative}")
        files[relative] = payload

    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"catalog contains a symlink: {path}")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != files.keys():
        raise ValueError(f"catalog files differ from release partitions: {sorted(actual ^ files.keys())}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative, payload in sorted(files.items()):
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    return {
        "output": str(output),
        "bytes": output.stat().st_size,
        "sha256": _digest(output.read_bytes()),
        "file_count": len(files),
        "release_json_sha256": _digest(release_bytes),
        "root_digest": release["root_digest"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package_catalog_snapshot(args.catalog_dir, args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Legacy release CLI, disabled until trusted-version binding is implemented."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read JSON from {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _validate_catalog(catalog_dir: Path) -> dict[str, Any]:
    release_path = catalog_dir / "release.json"
    release = _read_json(release_path)
    if release.get("schema") != "scirel.catalog-release.v1":
        raise ValueError("catalog release has an unsupported schema")
    expected_root_digest = release.get("root_digest")
    unsigned = dict(release)
    unsigned.pop("root_digest", None)
    if expected_root_digest != _digest(_canonical_json(unsigned)):
        raise ValueError("catalog root digest does not match its release document")
    partitions = release.get("partitions")
    if not isinstance(partitions, list) or not partitions:
        raise ValueError("catalog release must declare its partitions")
    partition_paths: set[str] = set()
    for partition in partitions:
        if not isinstance(partition, dict) or not isinstance(partition.get("path"), str):
            raise ValueError("catalog release contains an invalid partition")
        if partition["path"] in partition_paths:
            raise ValueError(f"catalog release repeats a partition: {partition['path']}")
        partition_paths.add(partition["path"])
        path = (catalog_dir / partition["path"]).resolve()
        try:
            path.relative_to(catalog_dir.resolve())
        except ValueError as error:
            raise ValueError("catalog partition escapes the catalog directory") from error
        if not path.is_file():
            raise ValueError(f"catalog partition is missing: {partition['path']}")
        payload = path.read_bytes()
        if partition.get("bytes") != len(payload):
            raise ValueError(f"catalog partition byte count differs: {partition['path']}")
        if partition.get("sha256") != _digest(payload):
            raise ValueError(f"catalog partition digest differs: {partition['path']}")
    return release


def finalize_release(
    *,
    workflow_snapshot: Path,
    documents_dir: Path,
    catalog_dir: Path,
    wheel: Path,
    output_dir: Path,
    release_id: str,
    expected_coverage_status: str,
    expected_included_asset_count: int,
    expected_declared_total_asset_count: int,
) -> dict[str, Any]:
    raise ValueError(
        "release requires expert approval of an exact trusted version; "
        "the legacy per-item finalizer is disabled"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-snapshot", type=Path, required=True)
    parser.add_argument("--documents-dir", type=Path, required=True)
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument(
        "--expected-coverage-status", choices=("partial", "complete"), required=True
    )
    parser.add_argument("--expected-included-asset-count", type=int, required=True)
    parser.add_argument(
        "--expected-declared-total-asset-count", type=int, required=True
    )
    args = parser.parse_args()
    try:
        result = finalize_release(
            workflow_snapshot=args.workflow_snapshot.resolve(),
            documents_dir=args.documents_dir.resolve(),
            catalog_dir=args.catalog_dir.resolve(),
            wheel=args.wheel.resolve(),
            output_dir=args.output_dir.resolve(),
            release_id=args.release_id,
            expected_coverage_status=args.expected_coverage_status,
            expected_included_asset_count=args.expected_included_asset_count,
            expected_declared_total_asset_count=(
                args.expected_declared_total_asset_count
            ),
        )
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(f"release finalization failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

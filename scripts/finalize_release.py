"""Bind an approved SciRel workflow to an already built catalog and wheel."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from scirel_workflow import SciRelWorkflow, WorkflowStatus  # noqa: E402
from validate_asset_documents import load_document_set  # noqa: E402


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


def _artifact_ref(path: Path, release_root: Path, *, label: str) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(release_root.resolve())
    except ValueError as error:
        raise ValueError(f"{label} must be inside the release root") from error
    return relative.as_posix()


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
    if output_dir.exists():
        raise FileExistsError(f"release metadata output already exists: {output_dir}")
    workflow = SciRelWorkflow.from_dict(_read_json(workflow_snapshot))
    if workflow.status is not WorkflowStatus.APPROVED:
        raise ValueError("release finalization requires an approved workflow snapshot")
    draft = workflow.record.draft
    if draft is None:
        raise ValueError("approved workflow has no standardized draft")

    documents = {
        document["asset_id"]: document
        for document in load_document_set(documents_dir)
    }
    for asset in draft.assets:
        asset_id = asset["asset_id"]
        document = documents.get(asset_id)
        if document is None:
            raise ValueError(f"approved asset is absent from the release documents: {asset_id}")
        if _canonical_json(asset) != _canonical_json(document):
            raise ValueError(f"approved asset differs from the release document: {asset_id}")

    catalog = _validate_catalog(catalog_dir)
    catalog_documents = {
        document["asset_id"]: document
        for document in (
            _read_json(path)
            for path in sorted((catalog_dir / "records").rglob("*.json"))
        )
    }
    if set(catalog_documents) != set(documents):
        raise ValueError(
            "built catalog asset IDs differ from the release document set"
        )
    for asset_id, document in documents.items():
        if _canonical_json(catalog_documents[asset_id]) != _canonical_json(document):
            raise ValueError(f"built catalog record differs from the release document: {asset_id}")
    coverage = catalog.get("coverage")
    if not isinstance(coverage, dict):
        raise ValueError("catalog release has no valid coverage declaration")
    included = coverage.get("included_asset_count")
    declared = coverage.get("declared_total_asset_count")
    status = coverage.get("status")
    if included != len(catalog_documents):
        raise ValueError("catalog included asset count differs from its records")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared < included:
        raise ValueError("catalog declared asset count is invalid")
    if status not in {"partial", "complete"}:
        raise ValueError("catalog coverage status is invalid")
    if status == "complete" and declared != included:
        raise ValueError("complete catalog coverage requires equal asset counts")
    if status != expected_coverage_status:
        raise ValueError(
            "catalog coverage status differs from the release policy: "
            f"expected {expected_coverage_status}, got {status}"
        )
    if included != expected_included_asset_count:
        raise ValueError(
            "catalog included asset count differs from the release policy: "
            f"expected {expected_included_asset_count}, got {included}"
        )
    if declared != expected_declared_total_asset_count:
        raise ValueError(
            "catalog declared asset count differs from the release policy: "
            f"expected {expected_declared_total_asset_count}, got {declared}"
        )
    if not wheel.is_file():
        raise ValueError(f"release wheel is missing: {wheel}")
    release_root = output_dir.parent.resolve()
    catalog_ref = _artifact_ref(
        catalog_dir / "release.json", release_root, label="catalog release"
    )
    wheel_ref = _artifact_ref(wheel, release_root, label="wheel")
    wheel_digest = _digest(wheel.read_bytes())
    release = workflow.release(
        release_id=release_id,
        catalog_ref=catalog_ref,
        catalog_digest=catalog["root_digest"],
        wheel_ref=wheel_ref,
        wheel_digest=wheel_digest,
        release_version=catalog["release_version"],
    )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}-", dir=output_dir.parent
    ) as temporary:
        staging = Path(temporary)
        manifest_path = staging / "release-manifest.json"
        snapshot_path = staging / "workflow-state.json"
        manifest_path.write_text(
            json.dumps(release.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        snapshot_path.write_text(
            json.dumps(workflow.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        Path(temporary).replace(output_dir)

    return {
        "schema": "scirel.release-finalization-result.v1",
        "release_manifest": str(output_dir / "release-manifest.json"),
        "released_workflow": str(output_dir / "workflow-state.json"),
        "release_digest": release.release_digest,
        "catalog_digest": release.catalog_digest,
        "wheel_digest": release.wheel_digest,
    }


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

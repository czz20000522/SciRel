"""Build a deterministic framework-neutral catalog from SciRel asset documents."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

from validate_asset_documents import load_document_set


CATALOG_SCHEMA = "scirel.catalog-release.v1"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [_canonical_json(value).decode("utf-8") for value in values]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def build_catalog(
    documents_dir: Path,
    output_dir: Path,
    *,
    catalog_id: str,
    release_version: str,
    coverage_status: str,
    declared_total: int,
) -> dict[str, Any]:
    documents = sorted(load_document_set(documents_dir), key=lambda item: item["asset_id"])
    if output_dir.exists():
        raise FileExistsError(f"catalog output already exists: {output_dir}")
    if coverage_status not in {"partial", "complete"}:
        raise ValueError("coverage_status must be partial or complete")
    document_versions = {
        document["version"]["implementation_version"] for document in documents
    }
    if document_versions != {release_version}:
        raise ValueError(
            "every document implementation_version must match catalog release_version"
        )
    if declared_total < len(documents):
        raise ValueError("declared_total cannot be smaller than included assets")
    if coverage_status == "complete" and declared_total != len(documents):
        raise ValueError("complete coverage requires every declared asset")

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}-", dir=output_dir.parent
    ) as temporary:
        root = Path(temporary)
        exact_refs = {}
        for document in documents:
            asset_id = document["asset_id"]
            prefix = hashlib.sha256(asset_id.encode("utf-8")).hexdigest()[:2]
            relative = Path("records") / prefix / f"{asset_id}.json"
            _write_json(root / relative, document)
            exact_refs[asset_id] = {"path": relative.as_posix()}

        routes = []
        summaries = []
        reverse = {document["asset_id"]: [] for document in documents}
        for document in documents:
            asset_id = document["asset_id"]
            for dependency in document["version"]["dependencies"]:
                reverse[dependency["asset_id"]].append(asset_id)
            routes.append(
                {
                    "asset_id": asset_id,
                    "kind": document["kind"],
                    "taxonomy": document["taxonomy"],
                    "relation": document["identity"]["relation"],
                    "direction": document["identity"]["direction"],
                    "outputs": [
                        {"name": port["name"], "units": port["units"]}
                        for port in document["outputs"]
                    ],
                    "facets": {
                        field: document["identity"][field]
                        for field in ("model", "geometry", "coordinates", "boundary")
                    },
                    "exact_record": exact_refs[asset_id],
                }
            )
            summaries.append(
                {
                    "asset_id": asset_id,
                    "kind": document["kind"],
                    "title": document["title"],
                    "summary": document["summary"],
                    "identity": {
                        field: document["identity"][field]
                        for field in ("model", "geometry", "coordinates", "boundary")
                    },
                    "inputs": [
                        {
                            field: port[field]
                            for field in (
                                "name",
                                "units",
                                "shape",
                                "dtype",
                                "required",
                                "default",
                            )
                            if field in port
                        }
                        for port in document["inputs"]
                    ],
                    "outputs": [
                        {
                            field: port[field]
                            for field in ("name", "units", "shape", "dtype")
                        }
                        for port in document["outputs"]
                    ],
                    "public_callable": (
                        f"{document['public_api']['python']['module']}."
                        f"{document['public_api']['python']['symbol']}"
                    ),
                    "supported": document["applicability"]["supported"],
                    "known_limitations": document["verification"]["known_limitations"],
                    "evidence_ceiling": document["verification"]["evidence_ceiling"],
                    "exact_record": exact_refs[asset_id],
                }
            )

        route_path = root / "routes" / "all.jsonl"
        summary_path = root / "summaries" / "all.jsonl"
        reverse_path = root / "reverse-dependencies" / "all.jsonl"
        _write_jsonl(route_path, routes)
        _write_jsonl(summary_path, summaries)
        _write_jsonl(
            reverse_path,
            [
                {"asset_id": asset_id, "consumers": sorted(consumers)}
                for asset_id, consumers in sorted(reverse.items())
            ],
        )

        partition_paths = [route_path, summary_path, reverse_path]
        partition_paths.extend(sorted((root / "records").rglob("*.json")))
        partitions = []
        for path in partition_paths:
            payload = path.read_bytes()
            partitions.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "bytes": len(payload),
                    "sha256": _digest(payload),
                }
            )
        release = {
            "schema": CATALOG_SCHEMA,
            "catalog_id": catalog_id,
            "release_version": release_version,
            "coverage": {
                "status": coverage_status,
                "included_asset_count": len(documents),
                "declared_total_asset_count": declared_total,
            },
            "progressive_disclosure": ["routes", "summaries", "exact_records"],
            "partitions": sorted(partitions, key=lambda item: item["path"]),
        }
        release["root_digest"] = _digest(_canonical_json(release))
        _write_json(root / "release.json", release)
        Path(temporary).replace(output_dir)
    return {
        "output_dir": str(output_dir),
        "asset_count": len(documents),
        "root_digest": release["root_digest"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("documents_dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--coverage-status", choices=("partial", "complete"), required=True)
    parser.add_argument("--declared-total", type=int, required=True)
    args = parser.parse_args()
    try:
        result = build_catalog(
            args.documents_dir.resolve(),
            args.output_dir.resolve(),
            catalog_id=args.catalog_id,
            release_version=args.release_version,
            coverage_status=args.coverage_status,
            declared_total=args.declared_total,
        )
    except Exception as error:
        print(f"catalog build failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

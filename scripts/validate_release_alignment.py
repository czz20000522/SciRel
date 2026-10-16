"""Validate the canonical current SciRel release tuple.

``release/CURRENT.json`` is the one mutable coordination record for the
checkout.  The old wheel and documentation ``CURRENT.json`` files are kept as
thin compatibility pointers; prior versions live in Git history and short
release notes rather than parallel metadata directories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _project_version(root: Path) -> str:
    path = root / "pyproject.toml"
    try:
        metadata = tomllib.loads(path.read_text(encoding="utf-8"))
        version = metadata["project"]["version"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        raise ValueError("pyproject.toml does not declare a readable project version") from error
    if not isinstance(version, str) or not version:
        raise ValueError("pyproject.toml project.version must be a non-empty string")
    return version


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_path(root: Path, value: str, *, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty relative path")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"{field} escapes the repository: {value}")
    if not path.is_file():
        raise ValueError(f"{field} does not name a file: {value}")
    return path


def _selected_documents(root: Path, record: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], str]:
    selection_path = _repo_path(root, record["source_documents"], field="source_documents")
    selection_digest = _sha256(selection_path)
    selection = _read_json(selection_path)
    if selection.get("schema") != "scirel.selected-document-set.v1":
        raise ValueError("source document selection has an invalid schema")
    rows = selection.get("records")
    if not isinstance(rows, list) or not rows:
        raise ValueError("source document selection is empty")
    documents: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"asset_id", "path", "sha256"}:
            raise ValueError("source document selection contains an invalid row")
        asset_id = row["asset_id"]
        document_path = _repo_path(root, row["path"], field=f"document[{asset_id}]")
        if _sha256(document_path) != row["sha256"]:
            raise ValueError(f"document digest differs from selection: {asset_id}")
        document = _read_json(document_path)
        if document.get("asset_id") != asset_id:
            raise ValueError(f"document asset ID differs from selection: {asset_id}")
        if asset_id in documents:
            raise ValueError(f"source document selection repeats {asset_id}")
        documents[asset_id] = document
    return documents, selection_digest


def _handbook_assets(root: Path, record: dict[str, Any]) -> tuple[set[str], str]:
    handbook_path = _repo_path(root, record["handbook"], field="handbook")
    handbook = _read_json(handbook_path)
    if handbook.get("schema") != "scirel.handbook.v1":
        raise ValueError("handbook has an invalid schema")
    assets: list[str] = []
    for chapter in handbook.get("chapters", []):
        for topic in chapter.get("topics", []):
            topic_assets = topic.get("assets")
            if not isinstance(topic_assets, list) or not topic_assets:
                raise ValueError("handbook contains an empty topic")
            assets.extend(topic_assets)
    if len(assets) != len(set(assets)):
        raise ValueError("handbook repeats an asset")
    return set(assets), _sha256(handbook_path)


def _validate_catalog_source_revision(
    root: Path, record: dict[str, Any], expected_source_revision: str | None
) -> None:
    """Check a built catalog when the current tuple points at one.

    Development CURRENT records may point at ``catalog/examples`` rather than a
    built ``release.json``. In that case there is no catalog release tuple to
    compare and the existing document selection checks remain authoritative.
    """
    catalog_value = record.get("catalog_root")
    if not isinstance(catalog_value, str) or not catalog_value:
        return
    catalog_root = (root / catalog_value).resolve()
    if not catalog_root.is_relative_to(root.resolve()):
        raise ValueError("documentation catalog_root escapes the repository")
    release_path = catalog_root / "release.json"
    if not release_path.is_file():
        return
    release = _read_json(release_path)
    if release.get("schema") != "scirel.catalog-release.v1":
        raise ValueError("documentation catalog release has an invalid schema")
    catalog_revision = release.get("source_revision")
    if not isinstance(catalog_revision, str) or re.fullmatch(r"[0-9a-f]{40}", catalog_revision) is None:
        raise ValueError("documentation catalog release lacks an exact source_revision")
    required_revision = expected_source_revision
    if required_revision is None:
        required_revision = record.get("source_revision")
    if required_revision is not None and catalog_revision != required_revision:
        raise ValueError("documentation catalog source_revision differs from release CURRENT")


def _validate_compat_pointer(root: Path, path: Path, *, line: str) -> None:
    pointer = _read_json(path)
    if pointer.get("schema") != "scirel.release-compat-pointer.v1":
        raise ValueError(f"{line} CURRENT is not a compatibility pointer")
    if pointer.get("line") != line or pointer.get("canonical") != "../CURRENT.json":
        raise ValueError(f"{line} CURRENT points somewhere other than release/CURRENT.json")
    target = (path.parent / pointer["canonical"]).resolve()
    if target != (root / "release/CURRENT.json").resolve():
        raise ValueError(f"{line} CURRENT canonical target is invalid")


def _validate_platform_receipts(root: Path, wheel: dict[str, Any]) -> None:
    receipts = wheel.get("platform_receipts")
    if not isinstance(receipts, list) or not receipts:
        raise ValueError("wheel platform_receipts must be a non-empty list")
    for row in receipts:
        if not isinstance(row, dict) or set(row) != {"platform", "path", "sha256"}:
            raise ValueError("wheel platform receipt has an invalid shape")
        receipt_path = _repo_path(root, row["path"], field="wheel platform receipt")
        if _sha256(receipt_path) != row["sha256"]:
            raise ValueError(f"platform receipt digest differs: {row['platform']}")
        receipt = _read_json(receipt_path)
        if receipt.get("schema") != "scirel.installed-wheel-validation.v1":
            raise ValueError(f"platform receipt has an invalid schema: {row['platform']}")
        if receipt.get("status") != "PASS":
            raise ValueError(f"platform receipt is not PASS: {row['platform']}")
        package = receipt.get("package")
        if not isinstance(package, dict) or package.get("version") != wheel["version"]:
            raise ValueError(f"platform receipt package version differs: {row['platform']}")
        receipt_artifact = receipt.get("artifact")
        expected_artifact = wheel.get("artifact")
        if (
            not isinstance(receipt_artifact, dict)
            or receipt_artifact.get("sha256") != expected_artifact.get("sha256")
            or receipt_artifact.get("bytes") != expected_artifact.get("bytes")
        ):
            raise ValueError(f"platform receipt wheel artifact differs: {row['platform']}")
        runtime = receipt.get("runtime")
        if not isinstance(runtime, dict) or runtime.get("expected_platform") != row["platform"]:
            raise ValueError(f"platform receipt target differs: {row['platform']}")


def _validate_platform_matrix(root: Path, *, version: str, receipt_paths: set[str]) -> None:
    matrix = _read_json(root / "release/platform-support-matrix.json")
    if matrix.get("schema") != "scirel.platform-support-matrix.v1":
        raise ValueError("platform support matrix has an invalid schema")
    if matrix.get("package") != "scirel":
        raise ValueError("platform support matrix names an unexpected package")
    if matrix.get("package_version") != version:
        raise ValueError("platform support matrix version differs from current release")
    binding = matrix.get("runtime_binding")
    if not isinstance(binding, dict) or binding.get("release_tuple") != "release/CURRENT.json":
        raise ValueError("platform support matrix is not bound to release/CURRENT.json")
    if binding.get("dependency_lock") != "uv.lock" or not (root / "uv.lock").is_file():
        raise ValueError("platform support matrix dependency lock is invalid")
    rows = matrix.get("platforms")
    if not isinstance(rows, list):
        raise ValueError("platform support matrix platforms must be a list")
    evidence_paths: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("evidence"), list):
            raise ValueError("platform support matrix contains an invalid evidence row")
        evidence_paths.update(value for value in row["evidence"] if isinstance(value, str))
    if not receipt_paths <= evidence_paths:
        raise ValueError("current platform receipt is missing from the support matrix")


def validate_alignment(
    root: Path = ROOT, *, expected_source_revision: str | None = None
) -> dict[str, Any]:
    canonical_path = root / "release/CURRENT.json"
    current = _read_json(canonical_path)
    if current.get("schema") != "scirel.release-current.v1":
        raise ValueError("release CURRENT has an invalid schema")
    if current.get("package") != "scirel":
        raise ValueError("release CURRENT names an unexpected package")
    version = current.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("release CURRENT version must be a non-empty string")
    if _project_version(root) != version:
        raise ValueError("release CURRENT version differs from pyproject.toml project.version")
    source_revision = current.get("source_revision")
    if source_revision is not None and (not isinstance(source_revision, str) or not source_revision):
        raise ValueError("source_revision must be null or a non-empty string")
    if expected_source_revision is not None and source_revision != expected_source_revision:
        raise ValueError(
            "release CURRENT source_revision differs from the expected Git revision"
        )

    wheel = current.get("wheel")
    docs = current.get("documentation")
    if not isinstance(wheel, dict) or not isinstance(docs, dict):
        raise ValueError("release CURRENT must contain wheel and documentation objects")
    if wheel.get("version") != version:
        raise ValueError("release CURRENT version differs from wheel tuple")
    if docs.get("compatible_wheel") != version:
        raise ValueError("documentation tuple is compatible with a different wheel")
    if wheel.get("status") != current.get("status") or docs.get("status") != current.get("status"):
        raise ValueError("release tuple statuses differ")
    if not isinstance(wheel.get("artifact"), dict):
        raise ValueError("wheel tuple lacks artifact metadata")
    artifact = wheel["artifact"]
    if not isinstance(artifact.get("sha256"), str) or len(artifact["sha256"]) != 64:
        raise ValueError("wheel artifact has an invalid sha256")
    artifact_relpath = artifact.get("path")
    if not isinstance(artifact_relpath, str) or not artifact_relpath:
        raise ValueError("wheel artifact path is invalid")
    artifact_path = (root / artifact_relpath).resolve()
    if not artifact_path.is_relative_to(root.resolve()):
        raise ValueError("wheel artifact path escapes the repository")
    if artifact_path.is_file():
        if _sha256(artifact_path) != artifact["sha256"]:
            raise ValueError("wheel artifact digest differs from release CURRENT")
        if artifact_path.stat().st_size != artifact.get("bytes"):
            raise ValueError("wheel artifact byte size differs from release CURRENT")
    _validate_platform_receipts(root, wheel)
    _validate_platform_matrix(
        root,
        version=version,
        receipt_paths={row["path"] for row in wheel["platform_receipts"]},
    )

    _validate_compat_pointer(root, root / "release/wheel/CURRENT.json", line="wheel")
    _validate_compat_pointer(root, root / "release/docs/CURRENT.json", line="documentation")

    selected, selection_digest = _selected_documents(root, docs)
    _validate_catalog_source_revision(root, docs, source_revision)
    handbook_assets, handbook_digest = _handbook_assets(root, docs)
    selected_ids = set(selected)
    if handbook_assets != selected_ids:
        raise ValueError("handbook coverage differs from selected document closure")

    counts = {"operators": 0, "task_graphs": 0}
    for document in selected.values():
        kind = document.get("kind")
        if kind == "operator":
            counts["operators"] += 1
        elif kind == "task_graph":
            counts["task_graphs"] += 1
        else:
            raise ValueError(f"unsupported document kind: {kind}")
        implementation_version = document.get("version", {}).get("implementation_version")
        baseline_versions = docs.get("asset_implementation_baselines")
        if (
            not isinstance(baseline_versions, list)
            or not baseline_versions
            or implementation_version not in baseline_versions
        ):
            raise ValueError(
                f"document {document.get('asset_id')} targets {implementation_version}, "
                "which is outside documentation asset_implementation_baselines"
            )
    counts["document_closure"] = len(selected)
    expected = wheel.get("selected_capabilities")
    if expected != counts:
        raise ValueError(f"document counts {counts} differ from wheel selection {expected}")
    if docs.get("capability_counts") != counts:
        raise ValueError("documentation record capability_counts differ from its selection")

    if docs.get("selection_sha256") != selection_digest:
        raise ValueError("release CURRENT selection_sha256 differs from selected docs")
    if docs.get("handbook_sha256") != handbook_digest:
        raise ValueError("release CURRENT handbook_sha256 differs from handbook")
    snapshot_sha256 = docs.get("snapshot_sha256")
    if not isinstance(snapshot_sha256, str) or len(snapshot_sha256) != 64:
        raise ValueError("release CURRENT documentation snapshot_sha256 is invalid")

    return {
        "wheel_version": version,
        "documentation_selection": docs["selection_id"],
        "source_revision": source_revision,
        "capability_counts": counts,
        "selection_sha256": selection_digest,
        "handbook_sha256": handbook_digest,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--expected-source-revision",
        help="require CURRENT.source_revision to match this exact Git commit",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            validate_alignment(
                args.root.resolve(), expected_source_revision=args.expected_source_revision
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

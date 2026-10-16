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
from pathlib import PurePosixPath
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


def _external_ref(value: object, *, field: str) -> PurePosixPath:
    """Validate a logical POSIX key used below an external artifact root."""

    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty logical artifact reference")
    if "\\" in value or value.startswith("/"):
        raise ValueError(f"{field} must be a relative POSIX artifact reference")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{field} contains an unsafe artifact reference: {value}")
    return path


def _external_artifact_path(root: Path, value: object, *, field: str) -> Path:
    logical = _external_ref(value, field=field)
    root = root.expanduser().resolve()
    path = (root / Path(*logical.parts)).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{field} escapes the external artifact root")
    return path


def _validate_external_manifest_digest(path: Path, expected: object, *, field: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"{field} does not name an external manifest: {path}")
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ValueError(f"{field} has an invalid manifest_sha256")
    if _sha256(path) != expected:
        raise ValueError(f"{field} manifest digest differs")
    manifest = _read_json(path)
    return manifest


def _validate_external_artifacts(
    root: Path,
    current: dict[str, Any],
    *,
    version: str,
    source_revision: str | None,
    artifact_root: Path | None,
) -> str:
    """Validate external wheel/docs manifests when an artifact root is supplied.

    The repository deliberately cannot prove external bytes without a storage
    root.  In that mode this function still validates the logical reference
    shape and returns ``external_artifact_unchecked``; release gates must pass
    ``--artifact-root`` to obtain byte-level proof.
    """

    wheel = current["wheel"]
    docs = current["documentation"]
    wheel_artifact = wheel.get("artifact")
    docs_artifact = docs.get("artifact")
    if not isinstance(wheel_artifact, dict) or not isinstance(docs_artifact, dict):
        raise ValueError("release CURRENT v2 requires wheel and documentation artifact objects")

    wheel_manifest_ref = _external_ref(
        wheel_artifact.get("manifest_ref"), field="wheel artifact manifest_ref"
    )
    docs_manifest_ref = _external_ref(
        docs_artifact.get("manifest_ref"), field="documentation artifact manifest_ref"
    )
    filename_ref = _external_ref(
        wheel_artifact.get("filename"), field="wheel artifact filename"
    )
    if len(filename_ref.parts) != 1:
        raise ValueError("wheel artifact filename must be a single file name")
    _external_ref(
        docs_artifact.get("snapshot_ref"), field="documentation artifact snapshot_ref"
    )
    for field, value in (
        ("wheel artifact manifest_sha256", wheel_artifact.get("manifest_sha256")),
        ("documentation artifact manifest_sha256", docs_artifact.get("manifest_sha256")),
        ("wheel artifact sha256", wheel_artifact.get("sha256")),
        ("documentation artifact snapshot_sha256", docs_artifact.get("snapshot_sha256")),
    ):
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError(f"{field} is invalid")
    for field, value in (
        ("wheel artifact bytes", wheel_artifact.get("bytes")),
        ("documentation artifact snapshot_bytes", docs_artifact.get("snapshot_bytes")),
    ):
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{field} is invalid")

    if artifact_root is None:
        return "external_artifact_unchecked"

    wheel_manifest_path = _external_artifact_path(
        artifact_root, wheel_manifest_ref.as_posix(), field="wheel artifact manifest_ref"
    )
    docs_manifest_path = _external_artifact_path(
        artifact_root, docs_manifest_ref.as_posix(), field="documentation artifact manifest_ref"
    )
    wheel_manifest = _validate_external_manifest_digest(
        wheel_manifest_path,
        wheel_artifact.get("manifest_sha256"),
        field="wheel artifact",
    )
    docs_manifest = _validate_external_manifest_digest(
        docs_manifest_path,
        docs_artifact.get("manifest_sha256"),
        field="documentation artifact",
    )

    if wheel_manifest.get("schema") != "scirel.git-build.v1":
        raise ValueError("external wheel manifest has an invalid schema")
    if docs_manifest.get("schema") != "scirel.git-docs-build.v1":
        raise ValueError("external documentation manifest has an invalid schema")
    for label, manifest in (("wheel", wheel_manifest), ("documentation", docs_manifest)):
        source = manifest.get("source")
        project = manifest.get("project")
        if not isinstance(source, dict) or not isinstance(project, dict):
            raise ValueError(f"external {label} manifest lacks source/project binding")
        if project.get("name") != "scirel" or project.get("version") != version:
            raise ValueError(f"external {label} manifest project differs from release CURRENT")
        if source_revision is not None and source.get("revision") != source_revision:
            raise ValueError(f"external {label} manifest source revision differs")

    wheel_info = wheel_manifest.get("wheel")
    if not isinstance(wheel_info, dict):
        raise ValueError("external wheel manifest lacks wheel metadata")
    if {
        "filename": wheel_info.get("filename"),
        "sha256": wheel_info.get("sha256"),
        "bytes": wheel_info.get("bytes"),
    } != {
        "filename": wheel_artifact["filename"],
        "sha256": wheel_artifact["sha256"],
        "bytes": wheel_artifact["bytes"],
    }:
        raise ValueError("external wheel manifest artifact differs from release CURRENT")
    wheel_path = wheel_manifest_path.parent / filename_ref.name
    if not wheel_path.is_file() or wheel_path.is_symlink():
        raise ValueError("external wheel filename does not resolve beside its manifest")
    if _sha256(wheel_path) != wheel_artifact["sha256"] or wheel_path.stat().st_size != wheel_artifact["bytes"]:
        raise ValueError("external wheel bytes differ from release CURRENT")

    snapshot_info = docs_manifest.get("snapshot")
    selection_info = docs_manifest.get("selection")
    if not isinstance(snapshot_info, dict) or not isinstance(selection_info, dict):
        raise ValueError("external documentation manifest lacks snapshot/selection metadata")
    if {
        "sha256": snapshot_info.get("sha256"),
        "bytes": snapshot_info.get("bytes"),
    } != {
        "sha256": docs_artifact["snapshot_sha256"],
        "bytes": docs_artifact["snapshot_bytes"],
    }:
        raise ValueError("external documentation snapshot differs from release CURRENT")
    if docs.get("snapshot_sha256") != snapshot_info.get("sha256"):
        raise ValueError("documentation snapshot_sha256 differs from external manifest")
    if selection_info.get("sha256") != docs.get("selection_sha256"):
        raise ValueError("external documentation selection differs from release CURRENT")
    snapshot_ref = _external_ref(
        docs_artifact["snapshot_ref"], field="documentation artifact snapshot_ref"
    )
    manifest_snapshot_ref = _external_ref(
        snapshot_info.get("path"), field="external documentation snapshot.path"
    )
    if snapshot_ref != manifest_snapshot_ref:
        raise ValueError("documentation snapshot_ref differs from external manifest")
    snapshot_path = _external_artifact_path(
        docs_manifest_path.parent,
        manifest_snapshot_ref.as_posix(),
        field="external documentation snapshot.path",
    )
    if not snapshot_path.is_dir() or snapshot_path.is_symlink():
        raise ValueError("external documentation snapshot path is not a directory")
    snapshot_manifest_path = snapshot_path / "manifest.json"
    if not snapshot_manifest_path.is_file() or snapshot_manifest_path.is_symlink():
        raise ValueError("external documentation snapshot has no manifest.json")
    snapshot_manifest = _read_json(snapshot_manifest_path)
    if snapshot_manifest.get("schema") != "scirel.documentation-snapshot.v1":
        raise ValueError("external documentation snapshot has an invalid schema")
    unsigned = {key: value for key, value in snapshot_manifest.items() if key != "snapshot_sha256"}
    encoded = (json.dumps(unsigned, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    if hashlib.sha256(encoded).hexdigest() != snapshot_manifest.get("snapshot_sha256"):
        raise ValueError("external documentation snapshot manifest digest differs")
    if snapshot_manifest.get("snapshot_sha256") != snapshot_info.get("sha256"):
        raise ValueError("external documentation snapshot digest differs")
    if snapshot_manifest.get("source_revision") != source_revision:
        raise ValueError("external documentation snapshot source revision differs")
    if snapshot_manifest.get("project_version") != version:
        raise ValueError("external documentation snapshot project version differs")
    files = snapshot_manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("external documentation snapshot files index is invalid")
    actual_files: dict[str, Path] = {}
    for path in snapshot_path.rglob("*"):
        if path == snapshot_manifest_path:
            continue
        if path.is_symlink():
            raise ValueError("external documentation snapshot contains a non-regular file")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("external documentation snapshot contains a non-regular file")
        relative = path.relative_to(snapshot_path).as_posix()
        actual_files[relative] = path
    if set(files) != set(actual_files):
        raise ValueError("external documentation snapshot file set differs from its manifest")
    for relative, metadata in files.items():
        if not isinstance(metadata, dict):
            raise ValueError("external documentation snapshot file metadata is invalid")
        path = actual_files[relative]
        if (
            metadata.get("bytes") != path.stat().st_size
            or metadata.get("sha256") != _sha256(path)
        ):
            raise ValueError(f"external documentation snapshot file differs: {relative}")
    total_bytes = snapshot_manifest_path.stat().st_size + sum(
        path.stat().st_size for path in actual_files.values()
    )
    if total_bytes != docs_artifact["snapshot_bytes"]:
        raise ValueError("external documentation snapshot byte size differs")
    return "external_artifact_verified"


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


def _validate_platform_receipts(
    root: Path, wheel: dict[str, Any], *, expected_source_revision: str | None = None
) -> None:
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
        schema = receipt.get("schema")
        if schema == "scirel.installed-wheel-validation.v1":
            bound = receipt
            receipt_source_revision = receipt.get("source_revision")
        elif schema == "scirel.dev9-linux-acceptance.v1":
            # The platform runner wraps the installed-wheel validator with
            # reproducible-build and source-archive evidence.  Keep the inner
            # validator as the runtime contract while checking the outer source
            # binding and status here.
            if receipt.get("status") != "PASS":
                raise ValueError(f"platform receipt is not PASS: {row['platform']}")
            source = receipt.get("source")
            validation = receipt.get("validation")
            if not isinstance(source, dict) or not isinstance(validation, dict):
                raise ValueError(f"platform receipt lacks wrapped validation: {row['platform']}")
            receipt_source_revision = source.get("revision")
            if validation.get("schema") != "scirel.installed-wheel-validation.v1":
                raise ValueError(f"platform receipt inner schema is invalid: {row['platform']}")
            bound = validation
        else:
            raise ValueError(f"platform receipt has an invalid schema: {row['platform']}")
        if receipt.get("status") != "PASS" and schema == "scirel.installed-wheel-validation.v1":
            raise ValueError(f"platform receipt is not PASS: {row['platform']}")
        if expected_source_revision is not None:
            if (
                not isinstance(receipt_source_revision, str)
                or len(receipt_source_revision) != 40
            ):
                raise ValueError(
                    f"platform receipt lacks source revision: {row['platform']}"
                )
            if receipt_source_revision != expected_source_revision:
                raise ValueError(f"platform receipt source revision differs: {row['platform']}")
        package = bound.get("package")
        if not isinstance(package, dict) or package.get("version") != wheel["version"]:
            raise ValueError(f"platform receipt package version differs: {row['platform']}")
        receipt_artifact = bound.get("artifact")
        expected_artifact = wheel.get("artifact")
        if (
            not isinstance(receipt_artifact, dict)
            or receipt_artifact.get("sha256") != expected_artifact.get("sha256")
            or receipt_artifact.get("bytes") != expected_artifact.get("bytes")
        ):
            raise ValueError(f"platform receipt wheel artifact differs: {row['platform']}")
        runtime = bound.get("runtime")
        if not isinstance(runtime, dict) or runtime.get("expected_platform") != row["platform"]:
            raise ValueError(f"platform receipt target differs: {row['platform']}")


def _validate_document_integration(
    root: Path,
    docs: dict[str, Any],
    *,
    version: str,
    source_revision: str | None,
    wheel: dict[str, Any],
    selection_digest: str,
    handbook_digest: str,
) -> None:
    record_value = docs.get("integration_record")
    record_path = _repo_path(root, record_value, field="integration_record")
    record = _read_json(record_path)
    if record.get("status") != "PASS":
        raise ValueError("documentation integration record is not PASS")
    if record.get("project_version") != version:
        raise ValueError("documentation integration record version differs")
    if source_revision is not None and record.get("source_revision") != source_revision:
        raise ValueError("documentation integration source revision differs")

    record_wheel = record.get("wheel")
    artifact = wheel.get("artifact")
    if (
        not isinstance(record_wheel, dict)
        or record_wheel.get("sha256") != artifact.get("sha256")
        or record_wheel.get("bytes") != artifact.get("bytes")
    ):
        raise ValueError("documentation integration wheel artifact differs")

    record_selection = record.get("selection")
    if (
        not isinstance(record_selection, dict)
        or record_selection.get("path") != docs.get("source_documents")
        or record_selection.get("sha256") != selection_digest
    ):
        raise ValueError("documentation integration selection differs")
    record_handbook = record.get("handbook")
    if (
        not isinstance(record_handbook, dict)
        or record_handbook.get("path") != docs.get("handbook")
        or record_handbook.get("sha256") != handbook_digest
    ):
        raise ValueError("documentation integration handbook differs")
    if record_handbook.get("scope", "exact") != docs.get("handbook_scope", "exact"):
        raise ValueError("documentation integration handbook scope differs")
    snapshot = record.get("snapshot")
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("sha256") != docs.get("snapshot_sha256")
    ):
        raise ValueError("documentation integration snapshot differs")


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
    root: Path = ROOT,
    *,
    expected_source_revision: str | None = None,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    canonical_path = root / "release/CURRENT.json"
    current = _read_json(canonical_path)
    if current.get("schema") != "scirel.release-current.v2":
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
    artifact_status = _validate_external_artifacts(
        root,
        current,
        version=version,
        source_revision=source_revision,
        artifact_root=artifact_root,
    )
    _validate_platform_receipts(root, wheel, expected_source_revision=source_revision)
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
    handbook_scope = docs.get("handbook_scope", "exact")
    if handbook_scope == "repository":
        if not selected_ids <= handbook_assets:
            raise ValueError("repository handbook does not cover selected document closure")
    elif handbook_scope == "exact":
        if handbook_assets != selected_ids:
            raise ValueError("handbook coverage differs from selected document closure")
    else:
        raise ValueError("documentation handbook_scope is invalid")

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
    _validate_document_integration(
        root,
        docs,
        version=version,
        source_revision=source_revision,
        wheel=wheel,
        selection_digest=selection_digest,
        handbook_digest=handbook_digest,
    )

    return {
        "wheel_version": version,
        "documentation_selection": docs["selection_id"],
        "source_revision": source_revision,
        "capability_counts": counts,
        "selection_sha256": selection_digest,
        "handbook_sha256": handbook_digest,
        "external_artifacts": artifact_status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--expected-source-revision",
        help="require CURRENT.source_revision to match this exact Git commit",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        help="external root containing logical wheel/documentation artifact references",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            validate_alignment(
                args.root.resolve(),
                expected_source_revision=args.expected_source_revision,
                artifact_root=args.artifact_root.resolve() if args.artifact_root else None,
            ),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

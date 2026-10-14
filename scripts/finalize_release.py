"""Bind an approved SciRel workflow to an already built catalog and wheel."""

from __future__ import annotations

import argparse
import ast
import hashlib
from importlib.util import resolve_name
import json
from pathlib import Path
from pathlib import PurePosixPath
import subprocess
import sys
import tempfile
from typing import Any
from zipfile import ZipFile, BadZipFile

from email.parser import Parser


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from scirel_workflow import SciRelWorkflow, WorkflowStatus  # noqa: E402
from scirel_plugin.adapter import review_item_from_body  # noqa: E402
from validate_asset_documents import load_document_set  # noqa: E402
from release_index import append_entry, current_unpublished_entries, read_index  # noqa: E402


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
    actual_paths = {
        path.relative_to(catalog_dir).as_posix()
        for path in catalog_dir.rglob("*")
        if path.is_file() and path != release_path
    }
    if partition_paths != actual_paths:
        raise ValueError("catalog partitions do not cover its exact files")
    return release


def _artifact_ref(path: Path, release_root: Path, *, label: str) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(release_root.resolve())
    except ValueError as error:
        raise ValueError(f"{label} must be inside the release root") from error
    return relative.as_posix()


def finalize_single_draft_fixture(
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


def _review_artifact(
    directory: Path, revision: str, item_ref: str
) -> tuple[bytes, dict[str, Any]]:
    if not isinstance(revision, str) or len(revision) != 71 or not all(
        character in "0123456789abcdef" for character in revision[7:]
    ) or not revision.startswith("sha256:"):
        raise ValueError("review artifact revision is invalid")
    path = directory / f"{revision[7:]}.json"
    body = path.read_bytes()
    if _digest(body) != revision:
        raise ValueError(f"review artifact digest differs: {revision}")
    return body, review_item_from_body(body, item_ref=item_ref)


def _relative_file(root: Path, name: str, prefix: str) -> Path:
    if not isinstance(name, str):
        raise ValueError("approved material file path must be a string")
    relative = PurePosixPath(name)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or "\\" in name
        or not name.startswith(prefix)
    ):
        raise ValueError(f"approved material path is outside {prefix}: {name}")
    path = (root / name).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"approved material path escapes the source root: {name}") from error
    if not path.is_file():
        raise ValueError(f"approved material file is missing: {name}")
    return path


def _material_files(material: Any, field: str, *, prefix: str) -> dict[str, str]:
    if not isinstance(material, dict):
        raise ValueError(f"approved {field} is missing")
    unsigned = {key: value for key, value in material.items() if key != "digest"}
    if material.get("digest") != _digest(_canonical_json(unsigned)):
        raise ValueError(f"approved {field} digest differs from its content")
    content = material.get("content")
    if not isinstance(content, dict) or set(content) != {"files"}:
        raise ValueError(f"approved {field} must contain exact files")
    files = content["files"]
    if not isinstance(files, dict) or not files:
        raise ValueError(f"approved {field} files must be nonempty")
    for name, body in files.items():
        if not isinstance(name, str) or not name.startswith(prefix) or not isinstance(body, str):
            raise ValueError(f"approved {field} file is invalid")
    return files


def _git_revision(source_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source_root, capture_output=True, text=True,
        check=True,
    )
    return result.stdout.strip()


def _git_changed_files(source_root: Path, candidate_revision: str) -> set[str]:
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", candidate_revision, "HEAD"],
        cwd=source_root, capture_output=True,
    )
    if ancestor.returncode != 0:
        raise ValueError("candidate Git revision is not an ancestor of release source")
    result = subprocess.run(
        ["git", "diff", "--name-only", candidate_revision, "HEAD", "--",
         "src/scirel", "tests", "catalog/examples"],
        cwd=source_root, capture_output=True, text=True, check=True,
    )
    return set(result.stdout.splitlines())


def _require_clean_release_sources(source_root: Path) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", "src", "tests", "catalog/examples"],
        cwd=source_root, capture_output=True, text=True, check=True,
    )
    if result.stdout.strip():
        raise ValueError("release source, tests, or documents differ from the Git revision")


def _wheel_contents(wheel: Path, release_version: str) -> dict[str, bytes]:
    try:
        with ZipFile(wheel) as archive:
            if archive.testzip() is not None:
                raise ValueError("release wheel contains a corrupt member")
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("release wheel repeats a member")
            metadata = [name for name in names if name.endswith(".dist-info/METADATA")]
            if len(metadata) != 1:
                raise ValueError("release wheel needs exactly one distribution METADATA")
            fields = Parser().parsestr(archive.read(metadata[0]).decode("utf-8"))
            if fields.get("Name", "").lower() != "scirel" or fields.get("Version") != release_version:
                raise ValueError("release wheel distribution/version differs from catalog")
            metadata_root = metadata[0].removesuffix("METADATA")
            if any(
                not name.startswith(("scirel/", metadata_root))
                for name in names
            ):
                raise ValueError("release wheel contains files outside the reviewed SciRel package")
            if any(
                name.startswith("scirel/") and name.endswith((".pyc", ".pyd", ".so", ".dll"))
                for name in names
            ):
                raise ValueError("release wheel contains unreviewed executable content")
            return {
                name: archive.read(name)
                for name in names if name.startswith("scirel/")
            }
    except BadZipFile as error:
        raise ValueError("release wheel is not a valid wheel archive") from error


def _validate_wheel_import_closure(wheel_members: dict[str, bytes], source_root: Path) -> None:
    modules = {
        name.removesuffix("/__init__.py").removesuffix(".py").replace("/", ".")
        for name in wheel_members
        if name.startswith("scirel/") and name.endswith(".py")
    }

    def present(module: str) -> bool:
        return module in modules or any(name.startswith(module + ".") for name in modules)

    def check(module: str, owner: str) -> None:
        if (module == "scirel" or module.startswith("scirel.")) and not present(module):
            raise ValueError(f"release wheel has a missing internal import {module} in {owner}")

    for name, body in wheel_members.items():
        if not name.startswith("scirel/") or not name.endswith(".py"):
            continue
        module = name.removesuffix("/__init__.py").removesuffix(".py").replace("/", ".")
        package = module if name.endswith("/__init__.py") else module.rpartition(".")[0]
        tree = ast.parse(body.decode("utf-8"), filename=name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    check(alias.name, name)
            elif isinstance(node, ast.ImportFrom):
                imported = resolve_name("." * node.level + (node.module or ""), package) if node.level else node.module
                if not imported:
                    continue
                check(imported, name)
                for alias in node.names:
                    candidate = imported + "." + alias.name
                    source = source_root / "src" / Path(*candidate.split("."))
                    if source.with_suffix(".py").is_file() or (source / "__init__.py").is_file():
                        check(candidate, name)


def _reviewed_initializers(
    documents: dict[str, dict[str, Any]], support_modules: set[str]
) -> dict[str, bytes]:
    exports: dict[str, list[tuple[str, str]]] = {}
    packages = {"scirel"}
    for document in documents.values():
        api = document["public_api"]["python"]
        module = api["module"]
        package = module.rpartition(".")[0]
        exports.setdefault(package, []).append((module, api["symbol"]))
        parts = package.split(".")
        packages.update(".".join(parts[:index]) for index in range(1, len(parts) + 1))
    for module in support_modules:
        parts = module.split(".")[:-1]
        packages.update(".".join(parts[:index]) for index in range(1, len(parts) + 1))

    initializers = {}
    for package in sorted(packages):
        members = sorted(exports.get(package, []))
        public_children = sorted(
            child.rsplit(".", 1)[1]
            for child in packages
            if child.rpartition(".")[0] == package and not child.rsplit(".", 1)[1].startswith("_")
        )
        lines = [f"from . import {child}" for child in public_children]
        lines.extend(
            f"from .{module.removeprefix(package + '.')} import {symbol}"
            for module, symbol in members
        )
        names = [*public_children, *(symbol for _, symbol in members)]
        if len(names) != len(set(names)):
            raise ValueError(f"reviewed package exports duplicate a name: {package}")
        lines.append(f"__all__ = {sorted(names)!r}")
        path = package.replace(".", "/") + "/__init__.py"
        initializers[path] = ("\n".join(lines) + "\n").encode("utf-8")
    return initializers


def finalize_reviewed_release(
    *,
    release_index: Path,
    candidate_entry_id: str,
    approved_results: Path,
    review_artifacts_dir: Path,
    documents_dir: Path,
    catalog_dir: Path,
    wheel: Path,
    output_dir: Path,
    release_id: str,
    source_root: Path,
) -> dict[str, Any]:
    """Finalize only an exact, independently approved and tested item subset."""
    if output_dir.exists():
        raise FileExistsError(f"release metadata output already exists: {output_dir}")
    if not isinstance(release_id, str) or not release_id.strip():
        raise ValueError("release ID must be nonempty")
    index = read_index(release_index)
    candidates = [
        entry for entry in index["entries"]
        if entry["status"] == "candidate" and entry["entry_id"] == candidate_entry_id
    ]
    if len(candidates) != 1:
        raise ValueError("release index does not contain the selected candidate entry")
    if candidates[0] not in current_unpublished_entries(index):
        raise ValueError("selected candidate is no longer current")
    candidate = candidates[0]
    released_entries = [entry for entry in index["entries"] if entry["status"] == "released"]
    if any(entry["predecessor_entry_id"] == candidate_entry_id for entry in released_entries):
        raise ValueError("selected candidate has already been released")
    results = _read_json(approved_results)
    if results.get("schema") != "scirel.review-completed-results.dev":
        raise ValueError("approved results schema is invalid")
    completed = results.get("completed_items")
    approved = results.get("approved_items")
    if not isinstance(completed, list) or not isinstance(approved, list) or not approved:
        raise ValueError("release requires at least one approved item")
    if any(item not in completed for item in approved):
        raise ValueError("approved item is absent from completed results")
    candidate_items = {item["item_ref"]: item for item in candidate["items"]}
    if len(candidate_items) != len(candidate["items"]):
        raise ValueError("candidate repeats a review item")
    approved_by_asset: dict[str, dict[str, Any]] = {}
    test_files: dict[str, str] = {}
    code_files: dict[str, str] = {}
    bindings = []
    for projection in approved:
        if not isinstance(projection, dict):
            raise ValueError("approved item projection is invalid")
        item_ref = projection.get("item_ref")
        candidate_item = candidate_items.get(item_ref)
        if candidate_item is None:
            raise ValueError(f"approved item is absent from candidate: {item_ref}")
        revision = projection.get("revision")
        successor_body, item = _review_artifact(review_artifacts_dir, revision, item_ref)
        successor = json.loads(successor_body)
        if successor.get("schema") != "codefusion.plugin-reviewer-successor-snapshot.v1":
            raise ValueError("approved revision must be a reviewer successor artifact")
        if item["status"] != "approved" or item["gaps"]:
            raise ValueError("review artifact is not an approved item without gaps")
        decision = item["decision"]
        if decision["outcome"] != "approved":
            raise ValueError("review decision does not approve the item")
        if any(projection.get(field) != item[field] for field in (
            "item_ref", "asset", "dependency_asset_ids", "evidence", "decision"
        )):
            raise ValueError("approved projection differs from its exact review artifact")
        if item["candidate_id"] != candidate["candidate_id"] or item["draft_id"] != candidate["draft_id"]:
            raise ValueError("approved item belongs to a different candidate or draft")
        asset_id = item["asset"].get("asset_id")
        if asset_id != candidate_item["asset_id"] or asset_id in approved_by_asset:
            raise ValueError("approved item asset identity is invalid or repeated")
        _, submitted = _review_artifact(
            review_artifacts_dir, decision["submitted_revision"], item_ref
        )
        if successor["predecessor"] != decision["submitted_artifact"]:
            raise ValueError("review successor predecessor differs from approval decision")
        if submitted["status"] != "review_pending" or any(
            submitted[field] != item[field]
            for field in ("item_ref", "candidate_id", "draft_id", "asset", "dependency_asset_ids", "evidence", "gaps")
        ):
            raise ValueError("approved item differs from the submitted review revision")
        _, initial = _review_artifact(
            review_artifacts_dir, candidate_item["initial_revision"], item_ref
        )
        if (
            initial["status"] != "review_pending"
            or initial["item_ref"] != item_ref
            or initial["candidate_id"] != candidate["candidate_id"]
            or initial["draft_id"] != candidate["draft_id"]
            or _digest(_canonical_json(initial["asset"])) != candidate_item["document_digest"]
            or initial["dependency_asset_ids"] != candidate_item["dependency_asset_ids"]
        ):
            raise ValueError("candidate initial revision differs from its indexed item")
        units = [record for record in item["evidence"] if record.get("kind") == "standardization_review_unit"]
        if len(units) != 1 or units[0].get("asset_id") != asset_id or units[0].get("gaps"):
            raise ValueError("approved item needs one gap-free standardization review unit")
        unit = units[0]
        code = unit.get("candidate_code")
        if not isinstance(code, dict) or code.get("kind") not in {"files", "none"}:
            raise ValueError("approved code must be exact files or an explicit reuse")
        if code["kind"] == "files":
            for name, body in _material_files(code, "candidate_code", prefix="src/scirel/").items():
                if name in code_files and code_files[name] != body:
                    raise ValueError("approved items disagree on a source file")
                code_files[name] = body
        elif code.get("content") is not None or code.get("digest") != _digest(_canonical_json({
            key: value for key, value in code.items() if key != "digest"
        })):
            raise ValueError("approved code reuse evidence is invalid")
        for name, body in _material_files(unit.get("candidate_tests"), "candidate_tests", prefix="tests/").items():
            if name in test_files and test_files[name] != body:
                raise ValueError("approved items disagree on a test file")
            test_files[name] = body
        approved_by_asset[asset_id] = item
        bindings.append({
            "item_ref": item_ref,
            "asset_id": asset_id,
            "revision": revision,
            "submitted_revision": decision["submitted_revision"],
            "decision_digest": _digest(_canonical_json(decision)),
        })

    source_root = source_root.resolve()
    release_git_revision = _git_revision(source_root)
    changed_files = _git_changed_files(source_root, candidate["git_revision"])
    _require_clean_release_sources(source_root)
    documents = {document["asset_id"]: document for document in load_document_set(documents_dir)}
    document_files = {
        _read_json(path)["asset_id"]: path
        for path in documents_dir.rglob("*.json")
    }
    latest_release = released_entries[-1] if released_entries else None
    baseline = set(latest_release["included_assets"]) if latest_release else set()
    if set(documents) != set(approved_by_asset) | baseline:
        raise ValueError("release documents must equal approved items and prior released baseline")
    release_modules = {
        document["public_api"]["python"]["module"] for document in documents.values()
    }
    source_documents = load_document_set(
        source_root / "catalog/examples",
        additional_directories=tuple(
            source_root / "catalog" / family
            for family in ("pleiades-maintained", "torax-algebra-grid", "torax-bootstrap-fvm")
            if (source_root / "catalog" / family).is_dir()
        ),
    )
    for source_document in source_documents:
        if (
            source_document["public_api"]["python"]["module"] in release_modules
            and source_document["asset_id"] not in documents
        ):
            raise ValueError(
                f"release module contains an unapproved asset in a shared module: {source_document['asset_id']}"
            )
    for asset_id, item in approved_by_asset.items():
        if _canonical_json(documents[asset_id]) != _canonical_json(item["asset"]):
            raise ValueError(f"approved asset differs from release document: {asset_id}")
        if documents[asset_id]["provenance"]["license_status"] != "approved-for-public-release":
            raise ValueError(f"release license is not approved: {asset_id}")
    for asset_id, document in documents.items():
        dependency_ids = {
            dependency["asset_id"]
            for dependency in document["version"]["dependencies"]
        }
        if not dependency_ids <= set(documents):
            raise ValueError(f"release dependency closure is incomplete: {asset_id}")
        if asset_id in approved_by_asset and dependency_ids != set(approved_by_asset[asset_id]["dependency_asset_ids"]):
            raise ValueError(f"approved dependency list differs from document: {asset_id}")
    approved_paths = set(code_files) | set(test_files)
    for asset_id in approved_by_asset:
        try:
            approved_paths.add(document_files[asset_id].resolve().relative_to(source_root).as_posix())
        except ValueError:
            pass
    if changed_files - approved_paths:
        raise ValueError("release source changes since candidate include unapproved files")

    catalog = _validate_catalog(catalog_dir)
    catalog_documents = {
        document["asset_id"]: document
        for document in (_read_json(path) for path in (catalog_dir / "records").rglob("*.json"))
    }
    if catalog_documents != documents:
        raise ValueError("catalog records differ from approved release documents")
    coverage = catalog.get("coverage")
    if not isinstance(coverage, dict) or coverage.get("included_asset_count") != len(documents):
        raise ValueError("catalog coverage differs from release documents")
    if not baseline and coverage.get("status") != "complete":
        raise ValueError("first public release requires complete catalog coverage")
    if coverage.get("status") == "complete" and coverage.get("declared_total_asset_count") != len(documents):
        raise ValueError("complete catalog coverage count differs from release documents")
    release_version = catalog.get("release_version")
    if not isinstance(release_version, str) or any(
        document["version"]["implementation_version"] != release_version
        for document in documents.values()
    ):
        raise ValueError("catalog and document implementation versions differ")
    wheel_members = _wheel_contents(wheel, release_version)
    _validate_wheel_import_closure(wheel_members, source_root)
    approved_modules = {
        document["public_api"]["python"]["module"].replace(".", "/") + ".py"
        for document in documents.values()
    }
    support_modules = {
        name.removeprefix("src/").removesuffix(".py").replace("/", ".")
        for name in code_files
        if name.endswith(".py") and any(part.startswith("_") for part in PurePosixPath(name).parts[2:])
    }
    expected_initializers = _reviewed_initializers(documents, support_modules)
    for wheel_name in wheel_members:
        parts = PurePosixPath(wheel_name).parts
        if (
            parts[0] == "scirel"
            and wheel_name.endswith(".py")
            and not any(part.startswith("_") for part in parts[1:])
            and wheel_name not in approved_modules
        ):
            raise ValueError(f"release wheel contains an unapproved scientific module: {wheel_name}")
        if (
            wheel_name.endswith(".py") and not wheel_name.endswith("/__init__.py")
            and any(part.startswith("_") for part in parts[1:])
            and wheel_name.removesuffix(".py").replace("/", ".") not in support_modules
        ):
            raise ValueError(f"release wheel contains an unreviewed support module: {wheel_name}")
    for wheel_name, body in wheel_members.items():
        if wheel_name.endswith(".py"):
            if wheel_name.endswith("/__init__.py"):
                if body != expected_initializers.get(wheel_name):
                    raise ValueError(f"release wheel has an unreviewed package initializer: {wheel_name}")
                continue
            source_name = "src/" + wheel_name
            source_path = _relative_file(source_root, source_name, "src/")
            if source_path.read_bytes() != body:
                raise ValueError(f"release wheel differs from source: {wheel_name}")
    for asset_id, document in documents.items():
        module = document["public_api"]["python"]["module"]
        source_name = "src/" + module.replace(".", "/") + ".py"
        source_path = _relative_file(source_root, source_name, "src/scirel/")
        wheel_name = source_name.removeprefix("src/")
        if wheel_members.get(wheel_name) != source_path.read_bytes():
            raise ValueError(f"release wheel differs from source module: {asset_id}")
    for name, body in code_files.items():
        source_path = _relative_file(source_root, name, "src/scirel/")
        if source_path.read_bytes() != body.encode("utf-8") or wheel_members.get(name.removeprefix("src/")) != source_path.read_bytes():
            raise ValueError(f"approved code differs from source or wheel: {name}")
    for name, body in test_files.items():
        if _relative_file(source_root, name, "tests/").read_bytes() != body.encode("utf-8"):
            raise ValueError(f"approved test differs from source: {name}")
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", *sorted(test_files)],
        cwd=source_root, capture_output=True, text=True, timeout=600,
    )
    if run.returncode != 0:
        raise ValueError(f"approved tests failed on release source: {run.stdout[-2000:]} {run.stderr[-1000:]}")
    release_root = output_dir.parent.resolve()
    catalog_ref = _artifact_ref(catalog_dir / "release.json", release_root, label="catalog release")
    wheel_ref = _artifact_ref(wheel, release_root, label="wheel")
    manifest = {
        "schema": "scirel.reviewed-release-manifest.dev",
        "release_id": release_id,
        "candidate_entry_id": candidate["entry_id"],
        "candidate_entry_digest": candidate["entry_digest"],
        "candidate_id": candidate["candidate_id"],
        "draft_id": candidate["draft_id"],
        "candidate_git_revision": candidate["git_revision"],
        "git_revision": release_git_revision,
        "approved_items": sorted(bindings, key=lambda item: item["item_ref"]),
        "included_assets": sorted(documents),
        "release_version": release_version,
        "catalog_ref": catalog_ref,
        "catalog_digest": catalog["root_digest"],
        "wheel_ref": wheel_ref,
        "wheel_digest": _digest(wheel.read_bytes()),
        "verified_tests": sorted(test_files),
        "verified_test_run": {
            "command": ["python", "-m", "pytest", "-p", "no:cacheprovider", *sorted(test_files)],
            "exit_code": run.returncode,
            "stdout_digest": _digest(run.stdout.encode("utf-8")),
            "stderr_digest": _digest(run.stderr.encode("utf-8")),
        },
    }
    released = append_entry(index, {
        "entry_id": f"release:{release_id}",
        "status": "released",
        "predecessor_entry_id": candidate["entry_id"],
        "baseline_entry_id": latest_release["entry_id"] if latest_release else None,
        "included_assets": manifest["included_assets"],
        "manifest_digest": _digest(_canonical_json(manifest)),
    })
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output_dir.name}-", dir=output_dir.parent) as temporary:
        staging = Path(temporary)
        for name, value in (("release-manifest.json", manifest), ("release-index.json", released)):
            (staging / name).write_text(
                json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8", newline="\n",
            )
        staging.replace(output_dir)
    return {
        "release_manifest": str(output_dir / "release-manifest.json"),
        "release_index": str(output_dir / "release-index.json"),
        "release_digest": _digest(_canonical_json(manifest)),
        "catalog_digest": manifest["catalog_digest"],
        "wheel_digest": manifest["wheel_digest"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-index", type=Path, required=True)
    parser.add_argument("--candidate-entry-id", required=True)
    parser.add_argument("--approved-results", type=Path, required=True)
    parser.add_argument("--review-artifacts-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--documents-dir", type=Path, required=True)
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    args = parser.parse_args()
    try:
        result = finalize_reviewed_release(
            release_index=args.release_index.resolve(),
            candidate_entry_id=args.candidate_entry_id,
            approved_results=args.approved_results.resolve(),
            review_artifacts_dir=args.review_artifacts_dir.resolve(),
            source_root=args.source_root.resolve(),
            documents_dir=args.documents_dir.resolve(),
            catalog_dir=args.catalog_dir.resolve(),
            wheel=args.wheel.resolve(),
            output_dir=args.output_dir.resolve(),
            release_id=args.release_id,
        )
    except (KeyError, OSError, subprocess.CalledProcessError, TypeError, ValueError) as error:
        print(f"release finalization failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Prepare a first-release source tree from exact reviewed asset projections."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import subprocess
import tempfile
import tomllib
from typing import Any

from finalize_release import (
    _material_files,
    _read_json,
    _relative_file,
    _review_artifact,
    _reviewed_initializers,
    _validate_wheel_import_closure,
)
from scientific_runtime import baseline_receipt, build_requirements, pin_dependencies, python_requirement
from release_index import current_unpublished_entries, read_index
from validate_asset_documents import ASSET_ID_RE, load_document_set


ROOT = Path(__file__).resolve().parents[1]
_GIT_REVISION = re.compile(r"[0-9a-f]{40}")


def _git_revision(source_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=source_root,
        capture_output=True,
        text=True,
        check=True,
    )
    revision = result.stdout.strip()
    if _GIT_REVISION.fullmatch(revision) is None:
        raise ValueError("source checkout did not provide an exact Git revision")
    return revision


def _source_dirty(source_root: Path) -> bool:
    result = subprocess.run(
        [
            "git", "status", "--porcelain", "--",
            "pyproject.toml", "src", "tests", "catalog/examples",
        ],
        cwd=source_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(result.stdout.strip())


def _project_for_release(source_root: Path, documents: dict) -> str:
    """Validate the source checkout as the sole release-version authority.

    Reviewed documents are inputs to a release, not a second version source.
    A historical document set must be explicitly requalified before it can be
    staged for a newer package version; this function never rewrites
    ``pyproject.toml`` from document metadata.
    """
    project = (source_root / "pyproject.toml").read_text(encoding="utf-8")
    metadata = tomllib.loads(project)
    version = metadata.get("project", {}).get("version")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9A-Za-z.+!-]+", version):
        raise ValueError("pyproject.toml must declare one simple project version")
    document_versions = {
        document["version"]["implementation_version"]
        for document in documents.values()
    }
    if len(document_versions) != 1:
        raise ValueError("reviewed documents must share one implementation_version")
    if document_versions != {version}:
        raise ValueError(
            "reviewed documents must match pyproject.toml project.version; "
            "requalify historical documents before staging"
        )
    requirements = metadata["project"]["dependencies"]
    if (
        requirements != pin_dependencies(requirements)
        or metadata["project"]["requires-python"] != python_requirement()
        or metadata["build-system"]["requires"] != build_requirements()
    ):
        raise ValueError(
            "source project must use the maintained scientific runtime baseline; "
            "requalify historical inputs"
        )
    return project


def prepare_reviewed_distribution(
    *,
    release_index: Path,
    candidate_entry_id: str,
    approved_results: Path,
    review_artifacts_dir: Path,
    source_root: Path,
    staging_dir: Path,
) -> dict[str, Any]:
    if staging_dir.exists():
        raise FileExistsError(f"reviewed staging directory already exists: {staging_dir}")
    index = read_index(release_index)
    if any(entry["status"] == "released" for entry in index["entries"]):
        raise ValueError("incremental release needs an exact prior released baseline")
    matches = [
        entry for entry in index["entries"]
        if entry["status"] == "candidate" and entry["entry_id"] == candidate_entry_id
    ]
    if len(matches) != 1:
        raise ValueError("release index does not contain the selected candidate entry")
    if matches[0] not in current_unpublished_entries(index):
        raise ValueError("selected candidate is no longer current")
    candidate = matches[0]
    candidate_items = {item["item_ref"]: item for item in candidate["items"]}
    if len(candidate_items) != len(candidate["items"]):
        raise ValueError("candidate repeats a review item")
    results = _read_json(approved_results)
    if results.get("schema") != "scirel.review-completed-results.dev":
        raise ValueError("approved results schema is invalid")
    approved = results.get("approved_items")
    completed = results.get("completed_items")
    if not isinstance(approved, list) or not approved or not isinstance(completed, list):
        raise ValueError("release requires completed and approved review items")
    if any(item not in completed for item in approved):
        raise ValueError("approved item is absent from completed results")

    documents: dict[str, dict[str, Any]] = {}
    code_files: dict[str, str] = {}
    test_files: dict[str, str] = {}
    for projection in approved:
        if not isinstance(projection, dict):
            raise ValueError("approved item projection is invalid")
        item_ref = projection.get("item_ref")
        indexed = candidate_items.get(item_ref)
        if indexed is None:
            raise ValueError(f"approved item is absent from candidate: {item_ref}")
        _, item = _review_artifact(review_artifacts_dir, projection.get("revision"), item_ref)
        if item["status"] != "approved" or item["gaps"]:
            raise ValueError("review artifact is not an approved item without gaps")
        if any(projection.get(field) != item[field] for field in (
            "item_ref", "asset", "dependency_asset_ids", "evidence", "decision"
        )):
            raise ValueError("approved projection differs from its exact review artifact")
        if item["candidate_id"] != candidate["candidate_id"] or item["draft_id"] != candidate["draft_id"]:
            raise ValueError("approved item belongs to a different candidate or draft")
        asset_id = item["asset"].get("asset_id")
        if (
            not isinstance(asset_id, str) or not ASSET_ID_RE.fullmatch(asset_id)
            or asset_id != indexed["asset_id"] or asset_id in documents
        ):
            raise ValueError("approved asset identity is invalid or repeated")
        if item["asset"]["provenance"]["license_status"] != "approved-for-public-release":
            raise ValueError(f"release license is not approved: {asset_id}")
        documents[asset_id] = item["asset"]
        units = [record for record in item["evidence"] if record.get("kind") == "standardization_review_unit"]
        if len(units) != 1 or units[0].get("asset_id") != asset_id or units[0].get("gaps"):
            raise ValueError("approved item needs one gap-free review unit")
        unit = units[0]
        code = unit.get("candidate_code")
        if not isinstance(code, dict) or code.get("kind") not in {"files", "none"}:
            raise ValueError("approved code must be exact files or an explicit reuse")
        if code["kind"] == "files":
            files = _material_files(code, "candidate_code", prefix="src/scirel/")
            for name, body in files.items():
                if name in code_files and code_files[name] != body:
                    raise ValueError("approved items disagree on a source file")
                code_files[name] = body
        tests = _material_files(unit.get("candidate_tests"), "candidate_tests", prefix="tests/")
        for name, body in tests.items():
            if name in test_files and test_files[name] != body:
                raise ValueError("approved items disagree on a test file")
            test_files[name] = body

    source_root = source_root.resolve()
    source_revision = _git_revision(source_root)
    source_dirty = _source_dirty(source_root)
    selected_modules: dict[str, str] = {}
    test_paths = set()
    for asset_id, document in documents.items():
        dependencies = {part["asset_id"] for part in document["version"]["dependencies"]}
        if not dependencies <= documents.keys():
            raise ValueError(f"release dependency closure is incomplete: {asset_id}")
        module = document["public_api"]["python"]["module"]
        parts = module.split(".")
        if len(parts) < 3 or parts[0] != "scirel" or not all(part.isidentifier() for part in parts):
            raise ValueError(f"approved Python module is invalid: {module}")
        selected_modules["src/" + module.replace(".", "/") + ".py"] = module
        test_paths.update(document["verification"]["tests"])
    if not test_paths <= test_files.keys():
        raise ValueError("reviewed test files do not cover every selected document")
    project = _project_for_release(source_root, documents)

    support_modules = set()
    for name, body in code_files.items():
        if name.endswith("/__init__.py"):
            raise ValueError(f"reviewed package initializer must be generated: {name}")
        path = Path(name)
        if path.suffix != ".py":
            raise ValueError(f"approved source file is not a Python module: {name}")
        module = name.removeprefix("src/").removesuffix(".py").replace("/", ".")
        if name not in selected_modules:
            if not any(part.startswith("_") for part in module.split(".")[1:]):
                raise ValueError(f"approved source file is outside selected assets: {name}")
            support_modules.add(module)
        source = _relative_file(source_root, name, "src/scirel/")
        if source.read_bytes() != body.encode("utf-8"):
            raise ValueError(f"approved code differs from maintained source: {name}")
    for name, body in test_files.items():
        source = _relative_file(source_root, name, "tests/")
        if source.read_bytes() != body.encode("utf-8"):
            raise ValueError(f"approved test differs from maintained source: {name}")

    staging_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{staging_dir.name}-", dir=staging_dir.parent) as temporary:
        stage = Path(temporary)
        (stage / "pyproject.toml").write_text(project, encoding="utf-8", newline="\n")
        members = {}
        for name in sorted(set(selected_modules) | set(code_files)):
            relative = name.removeprefix("src/")
            body = (source_root / name).read_bytes()
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
            members[relative] = body
        for name, body in _reviewed_initializers(documents, support_modules).items():
            destination = stage / "src" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
            members[name] = body
        _validate_wheel_import_closure(members, source_root)
        document_dir = stage / "documents"
        document_dir.mkdir()
        for asset_id, document in sorted(documents.items()):
            (document_dir / f"{asset_id}.json").write_text(
                json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8", newline="\n",
            )
        load_document_set(document_dir)
        (stage / "selection.json").write_text(
            json.dumps({
                "schema": "scirel.reviewed-distribution-selection.dev",
                "candidate_entry_id": candidate_entry_id,
                "source_revision": source_revision,
                "source_dirty": source_dirty,
                "scientific_runtime_baseline": baseline_receipt(),
                "asset_ids": sorted(documents),
                "test_paths": sorted(test_paths),
            }, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        stage.replace(staging_dir)
    return {
        "staging_dir": str(staging_dir),
        "documents_dir": str(staging_dir / "documents"),
        "asset_count": len(documents),
        "test_paths": sorted(test_paths),
        "source_revision": source_revision,
        "source_dirty": source_dirty,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-index", type=Path, required=True)
    parser.add_argument("--candidate-entry-id", required=True)
    parser.add_argument("--approved-results", type=Path, required=True)
    parser.add_argument("--review-artifacts-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--staging-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare_reviewed_distribution(
            release_index=args.release_index.resolve(),
            candidate_entry_id=args.candidate_entry_id,
            approved_results=args.approved_results.resolve(),
            review_artifacts_dir=args.review_artifacts_dir.resolve(),
            source_root=args.source_root.resolve(),
            staging_dir=args.staging_dir.resolve(),
        )
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(f"reviewed distribution preparation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

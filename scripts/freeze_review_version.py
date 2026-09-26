"""Freeze an internal SciRel development build for whole-version expert review.

This records evidence and exact artifact bytes; it never approves or releases them.
"""

from __future__ import annotations

import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any
import zipfile

from finalize_release import _validate_catalog
from validate_asset_documents import load_document_set


ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=True
    )
    return result.stdout.strip()


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _tracked_path(path: Path) -> str:
    resolved = path.resolve(strict=True)
    try:
        relative = resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"review source must be inside the repository: {path}") from error
    _git("ls-files", "--error-unmatch", "--", relative)
    return relative


def _is_candidate_material(relative: str) -> bool:
    parts = relative.split("/")
    if len(parts) == 3 and parts[0] == "review_candidates" and parts[2] == "review.md":
        return True
    if len(parts) == 4 and parts[0] == "review_candidates" and parts[2] == "proposal":
        name = parts[3]
        return name.endswith((".py", ".json")) and name not in (".py", ".json")
    return False


def _wheel_version(wheel: Path) -> str:
    with zipfile.ZipFile(wheel) as archive:
        metadata_paths = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_paths) != 1:
            raise ValueError("wheel must contain exactly one distribution METADATA")
        metadata = BytesParser().parsebytes(archive.read(metadata_paths[0]))
    if metadata.get("Name", "").lower().replace("_", "-") != "scirel":
        raise ValueError("wheel distribution is not scirel")
    version = metadata.get("Version")
    if not version:
        raise ValueError("wheel has no version")
    return version


def _validate_wheel_source(wheel: Path, commit: str) -> None:
    tracked = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "--name-only", commit, "--", "src/scirel"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout
    source_modules = {
        path.removeprefix("src/"): path
        for path in tracked.decode("utf-8").split("\0")
        if path.endswith(".py")
    }
    if "scirel/__init__.py" not in source_modules:
        raise ValueError("committed SciRel package source is missing")

    def normalized_python(source: bytes) -> bytes:
        return source.replace(b"\r\n", b"\n")

    with zipfile.ZipFile(wheel) as archive:
        wheel_modules = [
            name for name in archive.namelist()
            if name.startswith("scirel/") and name.endswith(".py")
        ]
        if (
            len(wheel_modules) != len(set(wheel_modules))
            or set(wheel_modules) != source_modules.keys()
        ):
            raise ValueError("wheel package differs from committed source")
        for name in wheel_modules:
            committed = subprocess.run(
                ["git", "show", f"{commit}:{source_modules[name]}"],
                cwd=ROOT, capture_output=True, check=True,
            ).stdout
            if normalized_python(archive.read(name)) != normalized_python(committed):
                raise ValueError("wheel package differs from committed source")


def freeze_review_version(
    *,
    documents_dir: Path,
    catalog_dir: Path,
    wheel: Path,
    review_dossier: Path,
    test_evidence: Path,
    output_dir: Path,
    review_materials: list[Path] | None = None,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"review snapshot already exists: {output_dir}")
    if output_dir.resolve().is_relative_to(catalog_dir.resolve()):
        raise ValueError("review snapshot cannot be written inside its input catalog")
    if _git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("review snapshot requires a clean Git worktree")
    commit = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    dossier_ref = _tracked_path(review_dossier)
    material_refs: dict[str, tuple[Path, str]] = {}
    for material in review_materials or []:
        relative = _tracked_path(material)
        if not (
            (relative.startswith("docs/") and relative.endswith(".md"))
            or _is_candidate_material(relative)
        ):
            raise ValueError(
                "review material must be a tracked docs Markdown file, or a "
                "candidate batch review.md (review_candidates/<batch>/review.md) "
                "or proposal module/document (review_candidates/<batch>/proposal/"
                "*.py|*.json): "
                f"{relative}"
            )
        if relative in material_refs:
            raise ValueError(f"review material is repeated: {relative}")
        material_refs[relative] = (material, _digest(material))
    document_refs = {
        _tracked_path(path): (path, _digest(path))
        for path in sorted(documents_dir.rglob("*.json"))
    }
    documents = load_document_set(documents_dir)
    catalog = _validate_catalog(catalog_dir)
    coverage = catalog["coverage"]
    if coverage["included_asset_count"] != len(documents):
        raise ValueError("catalog coverage differs from exact document count")
    if catalog["release_version"] != _wheel_version(wheel):
        raise ValueError("catalog and development wheel versions differ")
    _validate_wheel_source(wheel, commit)
    if any(
        document["version"]["implementation_version"] != catalog["release_version"]
        for document in documents
    ):
        raise ValueError("exact document and development wheel versions differ")
    catalog_records = {}
    for path in (catalog_dir / "records").rglob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["asset_id"] in catalog_records:
            raise ValueError(f"catalog repeats asset ID: {record['asset_id']}")
        catalog_records[record["asset_id"]] = record
    document_map = {document["asset_id"]: document for document in documents}
    if catalog_records != document_map:
        raise ValueError("catalog records differ from exact documents")
    if not test_evidence.is_file():
        raise ValueError(f"test evidence is missing: {test_evidence}")

    manifest = {
        "schema": "scirel.review-version.dev",
        "review_status": "pending_unapproved",
        "trusted_baseline": None,
        "git_commit": commit,
        "git_tree": tree,
        "implementation_version": catalog["release_version"],
        "review_dossier": {
            "path": dossier_ref,
            "snapshot_path": f"review-dossier/{dossier_ref}",
            "sha256": _digest(review_dossier),
        },
        "review_materials": [
            {
                "path": path,
                "snapshot_path": f"review-materials/{path}",
                "sha256": digest,
            }
            for path, (_, digest) in sorted(material_refs.items())
        ],
        "test_evidence": {"path": "test-evidence.md", "sha256": _digest(test_evidence)},
        "exact_documents": [
            {
                "path": path,
                "snapshot_path": f"exact-documents/{path}",
                "sha256": digest,
            }
            for path, (_, digest) in sorted(document_refs.items())
        ],
        "catalog": {
            "path": "catalog/release.json",
            "root_digest": catalog["root_digest"],
            "coverage": coverage,
        },
        "wheel": {"path": f"wheel/{wheel.name}", "sha256": _digest(wheel)},
    }
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}-", dir=output_dir.parent
    ) as temporary:
        staging = Path(temporary)
        shutil.copytree(catalog_dir, staging / "catalog")
        if _validate_catalog(staging / "catalog") != catalog:
            raise ValueError("catalog changed during freeze")
        dossier_copy = staging / manifest["review_dossier"]["snapshot_path"]
        dossier_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(review_dossier, dossier_copy)
        if _digest(dossier_copy) != manifest["review_dossier"]["sha256"]:
            raise ValueError("review dossier changed during freeze")
        for source_ref, (source, digest) in material_refs.items():
            target = staging / "review-materials" / source_ref
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if _digest(target) != digest:
                raise ValueError(f"review material changed during freeze: {source_ref}")
        for source_ref, (source, _) in document_refs.items():
            target = staging / "exact-documents" / source_ref
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        for entry in manifest["exact_documents"]:
            copied = staging / entry["snapshot_path"]
            if _digest(copied) != entry["sha256"]:
                raise ValueError(f"exact document changed during freeze: {entry['path']}")
        (staging / "wheel").mkdir()
        shutil.copy2(wheel, staging / "wheel" / wheel.name)
        shutil.copy2(test_evidence, staging / "test-evidence.md")
        if _digest(staging / "wheel" / wheel.name) != manifest["wheel"]["sha256"]:
            raise ValueError("wheel changed during freeze")
        if _digest(staging / "test-evidence.md") != manifest["test_evidence"]["sha256"]:
            raise ValueError("test evidence changed during freeze")
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        status_args = ["status", "--porcelain", "--untracked-files=all"]
        if staging.is_relative_to(ROOT.resolve()):
            relative_staging = staging.relative_to(ROOT.resolve()).as_posix()
            status_args.extend(("--", ".", f":(exclude){relative_staging}/**"))
        if _git("rev-parse", "HEAD") != commit or _git(*status_args):
            raise ValueError("review source changed during freeze")
        staging.replace(output_dir)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents-dir", type=Path, required=True)
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--review-dossier", type=Path, required=True)
    parser.add_argument("--test-evidence", type=Path, required=True)
    parser.add_argument("--review-material", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = freeze_review_version(
            documents_dir=args.documents_dir,
            catalog_dir=args.catalog_dir,
            wheel=args.wheel,
            review_dossier=args.review_dossier,
            test_evidence=args.test_evidence,
            output_dir=args.output_dir,
            review_materials=args.review_material,
        )
    except (OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        print(f"review freeze failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

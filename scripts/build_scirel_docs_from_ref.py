"""Build a SciRel documentation snapshot from an exact Git commit.

The snapshot is generated from the same archived source tree used for a
ref-bound wheel. The rendered snapshot and its build manifest stay outside the
repository; the checkout retains only the canonical handbook and short release
notes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import shutil
import subprocess
import sys
import tempfile

from build_scirel_from_ref import (
    ROOT,
    _archive_ref,
    _project_metadata,
    commit_epoch,
    resolve_revision,
)


def _new_external_directory(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path == ROOT or path.is_relative_to(ROOT):
        raise ValueError("output-dir must be outside the SciRel repository")
    if path.exists():
        if not path.is_dir() or any(path.iterdir()):
            raise ValueError(f"output-dir must be a new empty directory: {path}")
    else:
        path.mkdir(parents=True)
    return path


def _legacy_git_adapter(staging: Path, revision: str, environment: dict[str, str]) -> None:
    """Bind old archived doc builders that query Git directly.

    Early SciRel documentation builders did not accept an explicit source
    revision and only queried ``git rev-parse HEAD`` and
    ``git status --porcelain``.  An archive intentionally has no ``.git``
    directory, so provide a deliberately narrow command shim for those two
    queries.  Any other Git command fails closed instead of exposing the
    current checkout to the archived build.
    """

    shim_dir = staging / "git-shim"
    shim_dir.mkdir()
    if os.name == "nt":
        shim = shim_dir / "git.cmd"
        shim.write_text(
            "@echo off\r\n"
            'if "%~1"=="rev-parse" if "%~2"=="HEAD" (echo %SCIREL_REF% & exit /b 0)\r\n'
            'if "%~1"=="status" if "%~2"=="--porcelain" exit /b 0\r\n'
            "echo unsupported Git query >&2\r\n"
            "exit /b 127\r\n",
            encoding="utf-8",
        )
    else:
        shim = shim_dir / "git"
        shim.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "rev-parse" ] && [ "$2" = "HEAD" ]; then\n'
            '  printf "%s\\n" "$SCIREL_REF"\n'
            "  exit 0\n"
            "fi\n"
            'if [ "$1" = "status" ] && [ "$2" = "--porcelain" ]; then\n'
            "  exit 0\n"
            "fi\n"
            "echo 'unsupported Git query' >&2\n"
            "exit 127\n",
            encoding="utf-8",
        )
        shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    environment["SCIREL_REF"] = revision
    environment["PATH"] = str(shim_dir) + os.pathsep + environment.get("PATH", "")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _materialize_selection(source: Path, selection: str, staging: Path) -> dict[str, object]:
    """Materialize one exact selected-document-set without adding a source copy."""

    selection_path = (source / selection).resolve()
    if not selection_path.is_relative_to(source.resolve()) or not selection_path.is_file():
        raise ValueError(f"selection path is outside archived source or missing: {selection}")
    try:
        value = json.loads(selection_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"selection is not readable JSON: {selection}") from error
    if not isinstance(value, dict) or value.get("schema") != "scirel.selected-document-set.v1":
        raise ValueError("selection has an unsupported schema")
    records = value.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("selection must contain a non-empty records list")

    selected = staging / "selected-documents"
    selected.mkdir(parents=True)
    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != {"asset_id", "path", "sha256"}:
            raise ValueError(f"selection record {index} has an invalid shape")
        asset_id = record["asset_id"]
        relative_path = record["path"]
        expected_digest = record["sha256"]
        if (
            not isinstance(asset_id, str)
            or not isinstance(relative_path, str)
            or not isinstance(expected_digest, str)
            or len(expected_digest) != 64
            or any(character not in "0123456789abcdef" for character in expected_digest)
        ):
            raise ValueError(f"selection record {index} has invalid identity or digest")
        if Path(asset_id).name != asset_id or "/" in asset_id or "\\" in asset_id:
            raise ValueError(f"selection record {index} has an unsafe asset_id")
        if asset_id in seen_ids:
            raise ValueError(f"selection repeats asset_id: {asset_id}")
        seen_ids.add(asset_id)
        document_path = (source / relative_path).resolve()
        if not document_path.is_relative_to(source.resolve()) or not document_path.is_file():
            raise ValueError(f"selection document path is outside archived source: {relative_path}")
        actual_digest = _sha256(document_path)
        if actual_digest != expected_digest:
            raise ValueError(f"selection document digest differs: {relative_path}")
        try:
            document = json.loads(document_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"selection document is not readable JSON: {relative_path}") from error
        if not isinstance(document, dict) or document.get("asset_id") != asset_id:
            raise ValueError(f"selection asset_id differs from document: {relative_path}")
        (selected / f"{asset_id}.json").write_bytes(document_path.read_bytes())

    return {
        "path": selection,
        "sha256": _sha256(selection_path),
        "asset_count": len(records),
        # Kept only for the in-process reader projection; it is removed from
        # the external manifest so that the selection file remains the single
        # asset-list source of truth.
        "_asset_ids": sorted(seen_ids),
    }


def _materialize_translations(
    source: Path, asset_ids: set[str], staging: Path
) -> dict[str, object]:
    """Create one exact reader bundle for a selected document closure.

    The repository keeps reader translations in domain bundles.  A release
    selection may be a strict subset of that repository set, so pass the
    archived builder a temporary filtered bundle instead of allowing unrelated
    reader records to widen the selected closure.
    """

    translation_root = (source / "tools/docs/zh").resolve()
    if not translation_root.is_relative_to(source.resolve()) or not translation_root.is_dir():
        raise ValueError("archived source has no reader translation directory")
    records: dict[str, dict[str, object]] = {}
    for path in sorted(translation_root.glob("*.json")):
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"reader translation is not readable JSON: {path}") from error
        if (
            not isinstance(bundle, dict)
            or bundle.get("schema") != "scirel.reader-translation.v1"
            or bundle.get("language") != "zh-CN"
        ):
            raise ValueError(f"reader translation has an unsupported schema: {path}")
        bundle_records = bundle.get("records")
        if not isinstance(bundle_records, list):
            raise ValueError(f"reader translation records must be a list: {path}")
        for record in bundle_records:
            if (
                not isinstance(record, dict)
                or not isinstance(record.get("asset_id"), str)
                or not record["asset_id"]
            ):
                raise ValueError(f"reader translation record has no asset_id: {path}")
            asset_id = record["asset_id"]
            if asset_id in records:
                raise ValueError(f"reader translation repeats asset_id: {asset_id}")
            records[asset_id] = record
    missing = asset_ids - set(records)
    if missing:
        raise ValueError("reader translations do not cover selected documents: " + str(sorted(missing)))

    selected_records = [records[asset_id] for asset_id in sorted(asset_ids)]
    target = staging / "selected-reader-bundle.json"
    target.write_text(
        json.dumps(
            {
                "schema": "scirel.reader-translation.v1",
                "language": "zh-CN",
                "records": selected_records,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "source": "tools/docs/zh/*.json",
        "sha256": _sha256(target),
        "asset_count": len(selected_records),
    }


def build_from_ref(
    ref: str,
    output_dir: Path,
    *,
    documents: str = "catalog/examples",
    selection: str | None = None,
    python: str | None = None,
) -> dict[str, object]:
    """Build and return a stable manifest for one exact Git commit."""

    output_dir = _new_external_directory(output_dir)
    revision = resolve_revision(ref)
    epoch = commit_epoch(revision)
    runner = python or sys.executable
    if os.path.sep not in runner:
        runner_path = shutil.which(runner)
    else:
        # Keep virtual-environment symlinks intact.  ``Path.resolve()`` would
        # collapse ``.venv/bin/python`` to the base interpreter and lose the
        # environment's documentation dependencies.
        runner_path = os.path.abspath(os.path.expanduser(runner))
    if not runner_path or not Path(runner_path).is_file():
        raise FileNotFoundError(f"documentation Python executable not found: {runner}")

    try:
        previous_umask = os.umask(0o022)
    except (AttributeError, NotImplementedError):
        previous_umask = None
    try:
        with tempfile.TemporaryDirectory(prefix="scirel-docs-git-build-") as temporary:
            staging = Path(temporary)
            source = _archive_ref(revision, epoch, staging)
            name, version = _project_metadata(source)
            source_root = source.resolve()
            selection_info = None
            translation_info = None
            if selection is not None:
                selection_info = _materialize_selection(source_root, selection, staging)
                document_root = staging / "selected-documents"
                translation_info = _materialize_translations(
                    source_root, set(selection_info.pop("_asset_ids")), staging
                )
            else:
                document_root = (source_root / documents).resolve()
            if not document_root.is_relative_to(source_root) or not document_root.is_dir():
                if selection is None:
                    raise ValueError(f"documents path is outside archived source: {documents}")
                if not document_root.is_dir():
                    raise ValueError("materialized selection directory is missing")
            snapshot = output_dir / "snapshot"
            environment = dict(os.environ)
            environment.update(
                {
                    "SOURCE_DATE_EPOCH": str(epoch),
                    "PYTHONHASHSEED": "0",
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
            docs_script = source / "scripts/scirel_docs.py"
            command = [
                runner_path,
                str(docs_script),
                "build",
                "--documents",
                str(document_root),
                "--output",
                str(snapshot),
            ]
            if "--source-revision" in docs_script.read_text(encoding="utf-8"):
                command.extend(["--source-revision", revision])
            else:
                _legacy_git_adapter(staging, revision, environment)
            if translation_info is not None:
                if "--translations" not in docs_script.read_text(encoding="utf-8"):
                    raise ValueError(
                        "selected-document build requires an archived docs builder with --translations"
                    )
                command.extend(["--translations", str(staging / "selected-reader-bundle.json")])
            build_result = subprocess.run(
                command,
                cwd=source,
                env=environment,
                capture_output=True,
                text=True,
            )
            if build_result.returncode:
                if build_result.stdout:
                    sys.stderr.write(build_result.stdout)
                if build_result.stderr:
                    sys.stderr.write(build_result.stderr)
                build_result.check_returncode()
            manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
            manifest_source = manifest.get("source_revision", manifest.get("source_commit"))
            if manifest_source != revision or manifest.get("source_dirty") is not False:
                raise ValueError("documentation snapshot is not cleanly bound to the requested ref")
            manifest_version = manifest.get("project_version", version)
            if manifest_version != version:
                raise ValueError("documentation snapshot version differs from archived project")
            snapshot_digest = manifest.get("snapshot_sha256")
            if not isinstance(snapshot_digest, str) or len(snapshot_digest) != 64:
                raise ValueError("documentation snapshot has no valid snapshot_sha256")
            snapshot_bytes = sum(path.stat().st_size for path in snapshot.rglob("*") if path.is_file())
    finally:
        if previous_umask is not None:
            os.umask(previous_umask)

    runner_version = subprocess.run(
        [runner_path, "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    result: dict[str, object] = {
        "schema": "scirel.git-docs-build.v1",
        "source": {"ref": ref, "revision": revision, "commit_epoch": epoch},
        "project": {"name": name, "version": version},
        "snapshot": {
            "path": "snapshot",
            "sha256": snapshot_digest,
            "bytes": snapshot_bytes,
        },
        "selection": selection_info,
        "translations": translation_info,
        "builder": {
            "command": "python scripts/scirel_docs.py build",
            "source": "git archive",
            "source_date_epoch": epoch,
            "python_hash_seed": 0,
            "umask": "022",
            "runner": runner_path,
            "runner_version": runner_version,
            "host_platform": platform.platform(),
            "host_machine": platform.machine(),
        },
    }
    (output_dir / "build-manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, help="Git ref or commit to archive")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="new directory outside the repository for the snapshot and manifest",
    )
    parser.add_argument("--documents", default="catalog/examples")
    parser.add_argument(
        "--selection",
        help="project-relative selected-document-set JSON inside the archived ref",
    )
    parser.add_argument("--python", help="Python executable for the documentation builder")
    args = parser.parse_args()
    result = build_from_ref(
        args.ref,
        args.output_dir,
        documents=args.documents,
        selection=args.selection,
        python=args.python,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

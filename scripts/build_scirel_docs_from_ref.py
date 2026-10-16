"""Build a SciRel documentation snapshot from an exact Git commit.

The snapshot is generated from the same archived source tree used for a
ref-bound wheel. The rendered snapshot and its build manifest stay outside the
repository; the checkout retains only the canonical handbook and short release
notes.
"""

from __future__ import annotations

import argparse
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


def build_from_ref(
    ref: str,
    output_dir: Path,
    *,
    documents: str = "catalog/examples",
    python: str | None = None,
) -> dict[str, object]:
    """Build and return a stable manifest for one exact Git commit."""

    output_dir = _new_external_directory(output_dir)
    revision = resolve_revision(ref)
    epoch = commit_epoch(revision)
    runner = python or sys.executable
    runner_path = shutil.which(runner) if os.path.sep not in runner else runner
    if not runner_path:
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
            document_root = (source_root / documents).resolve()
            if not document_root.is_relative_to(source_root) or not document_root.is_dir():
                raise ValueError(f"documents path is outside archived source: {documents}")
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
    parser.add_argument("--python", help="Python executable for the documentation builder")
    args = parser.parse_args()
    result = build_from_ref(
        args.ref,
        args.output_dir,
        documents=args.documents,
        python=args.python,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

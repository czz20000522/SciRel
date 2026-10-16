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
            subprocess.run(
                [
                    runner_path,
                    str(source / "scripts/scirel_docs.py"),
                    "build",
                    "--documents",
                    str(document_root),
                    "--output",
                    str(snapshot),
                    "--source-revision",
                    revision,
                ],
                check=True,
                cwd=source,
                env=environment,
            )
            manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
            if manifest.get("source_revision") != revision or manifest.get("source_dirty") is not False:
                raise ValueError("documentation snapshot is not cleanly bound to the requested ref")
            if manifest.get("project_version") != version:
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

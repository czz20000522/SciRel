"""Build one SciRel wheel from an exact Git commit.

The source checkout is the versioned truth. This helper archives the requested
Git ref into a temporary directory before invoking the build backend, so the
wheel never depends on an uncommitted working tree or checkout file mtimes.
The output directory is deliberately required to live outside the repository;
the wheel and its manifest are build artifacts, not another source snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def resolve_revision(ref: str) -> str:
    """Resolve ``ref`` to a full commit id and reject non-commit objects."""

    revision = _run_git("rev-parse", "--verify", f"{ref}^{{commit}}")
    if len(revision) != 40 or any(ch not in "0123456789abcdef" for ch in revision):
        raise ValueError(f"Git ref did not resolve to a full commit: {ref}")
    return revision


def commit_epoch(revision: str) -> int:
    value = _run_git("show", "-s", "--format=%ct", revision)
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"Git commit has an invalid commit timestamp: {revision}") from error


def _project_metadata(source_root: Path) -> tuple[str, str]:
    try:
        metadata = tomllib.loads((source_root / "pyproject.toml").read_text(encoding="utf-8"))
        project = metadata["project"]
        name = project["name"]
        version = project["version"]
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as error:
        raise ValueError("archived source has no readable project name/version") from error
    if not isinstance(name, str) or not name:
        raise ValueError("archived project.name must be a non-empty string")
    if not isinstance(version, str) or not version:
        raise ValueError("archived project.version must be a non-empty string")
    return name, version


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _archive_ref(revision: str, epoch: int, destination: Path) -> Path:
    archive = destination / "source.tar"
    with archive.open("wb") as stream:
        subprocess.run(
            ["git", "archive", "--format=tar", f"--mtime=@{epoch}", revision],
            cwd=ROOT,
            check=True,
            stdout=stream,
        )
    source = destination / "source"
    source.mkdir()
    with tarfile.open(archive, mode="r") as tar:
        tar.extractall(source, filter="data")
    archive.unlink()
    return source


def build_from_ref(
    ref: str,
    output_dir: Path,
    *,
    uv: str = "uv",
    python: str | None = None,
) -> dict[str, object]:
    """Build and return a stable manifest for one exact Git commit."""

    output_dir = output_dir.expanduser().resolve()
    if output_dir == ROOT or output_dir.is_relative_to(ROOT):
        raise ValueError("output-dir must be outside the SciRel repository")
    if output_dir.exists():
        if not output_dir.is_dir() or any(output_dir.iterdir()):
            raise ValueError(f"output-dir must be a new empty directory: {output_dir}")
    else:
        output_dir.mkdir(parents=True)

    uv_path = shutil.which(uv) if os.path.sep not in uv else uv
    if not uv_path:
        raise FileNotFoundError(f"build executable not found: {uv}")

    revision = resolve_revision(ref)
    epoch = commit_epoch(revision)
    try:
        previous_umask = os.umask(0o022)
    except (AttributeError, NotImplementedError):
        previous_umask = None
    try:
        with tempfile.TemporaryDirectory(prefix="scirel-git-build-") as temporary:
            staging = Path(temporary)
            source = _archive_ref(revision, epoch, staging)
            name, version = _project_metadata(source)
            wheel_dir = staging / "wheel"
            wheel_dir.mkdir()
            environment = dict(os.environ)
            environment.update(
                {
                    "SOURCE_DATE_EPOCH": str(epoch),
                    "PYTHONHASHSEED": "0",
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
            command = [
                uv_path,
                "build",
                "--wheel",
                "--no-create-gitignore",
                "--out-dir",
                str(wheel_dir),
            ]
            if python is not None:
                command.extend(["--python", python])
            command.append(str(source))
            subprocess.run(
                command,
                check=True,
                cwd=source,
                env=environment,
            )
            wheels = sorted(wheel_dir.glob("*.whl"))
            if len(wheels) != 1:
                raise ValueError(f"expected exactly one wheel, found {len(wheels)}")
            wheel = wheels[0]
            expected_prefix = f"{name.replace('-', '_')}-{version}-"
            if not wheel.name.startswith(expected_prefix):
                raise ValueError(
                    f"wheel filename {wheel.name!r} does not match {name} {version}"
                )
            target = output_dir / wheel.name
            shutil.copyfile(wheel, target)
    finally:
        if previous_umask is not None:
            os.umask(previous_umask)

    uv_version = subprocess.run(
        [uv_path, "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest: dict[str, object] = {
        "schema": "scirel.git-build.v1",
        "source": {
            "ref": ref,
            "revision": revision,
            "commit_epoch": epoch,
        },
        "project": {"name": name, "version": version},
        "wheel": {
            "filename": target.name,
            "sha256": _sha256(target),
            "bytes": target.stat().st_size,
        },
        "builder": {
            "command": "uv build --wheel",
            "source_date_epoch": epoch,
            "python_hash_seed": 0,
            "umask": "022",
            "source": "git archive",
            "uv_version": uv_version,
            "python_selector": python or "uv default",
            "runner_python": sys.version,
            "host_platform": platform.platform(),
            "host_machine": platform.machine(),
        },
    }
    (output_dir / "build-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, help="Git ref or commit to archive")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="new directory outside the repository for the wheel and manifest",
    )
    parser.add_argument("--uv", default="uv", help="uv executable (default: uv)")
    parser.add_argument(
        "--python",
        help="Python selector passed to uv build, for example 3.14 or /path/to/python",
    )
    args = parser.parse_args()
    manifest = build_from_ref(args.ref, args.output_dir, uv=args.uv, python=args.python)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

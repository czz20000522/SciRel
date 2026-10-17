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
from typing import Iterable


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


def _file_summary(path: Path, *, relative: str) -> dict[str, object]:
    """Return the stable identity of one build input file."""

    if not path.is_file() or path.is_symlink():
        raise ValueError(f"build input is not a regular file: {relative}")
    return {
        "path": relative,
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _safe_relative_path(value: str, *, field: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must be a relative path: {value}")
    return path


def _license_input_paths(source: Path, metadata: dict[str, object]) -> list[Path]:
    """Resolve the license files declared by the archived project metadata.

    PEP 639 uses ``project.license-files`` as a list of relative glob
    patterns.  Older refs may not declare it, so fall back to the repository's
    conventional ``licenses/`` tree without making that absence a build
    failure.  Directories and symlinks are excluded because neither is a
    license payload copied into a wheel.
    """

    project = metadata.get("project")
    if not isinstance(project, dict):
        raise ValueError("archived pyproject.toml has no project table")
    declared = project.get("license-files")
    if declared is None:
        patterns: list[str] = []
    elif isinstance(declared, str):
        patterns = [declared]
    elif isinstance(declared, list) and all(isinstance(item, str) for item in declared):
        patterns = list(declared)
    else:
        raise ValueError("project.license-files must be a string or list of strings")

    candidates: set[Path] = set()
    if patterns:
        for pattern in patterns:
            _safe_relative_path(pattern, field="project.license-files")
            for path in source.glob(pattern):
                if path.is_file() and not path.is_symlink():
                    candidates.add(path)
    else:
        licenses = source / "licenses"
        if licenses.is_dir() and not licenses.is_symlink():
            candidates.update(
                path
                for path in licenses.rglob("*")
                if path.is_file() and not path.is_symlink()
            )
    return sorted(candidates, key=lambda path: path.relative_to(source).as_posix())


def build_input_binding(source: Path, *, helper_paths: Iterable[str]) -> dict[str, object]:
    """Summarize source and helper inputs that affect a ref-bound build.

    This is additive metadata in the existing ``scirel.git-build.v1`` and
    ``scirel.git-docs-build.v1`` manifests.  It does not alter ``CURRENT`` or
    require historical manifests to be regenerated.  ``uv.lock`` is optional
    for older Git refs, but when present its bytes are always bound.
    """

    source = source.resolve()
    pyproject = source / "pyproject.toml"
    if not pyproject.is_file() or pyproject.is_symlink():
        raise ValueError("archived source has no regular pyproject.toml")
    try:
        metadata = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError("archived pyproject.toml is not readable TOML") from error

    files: dict[str, dict[str, object]] = {
        "pyproject.toml": _file_summary(pyproject, relative="pyproject.toml")
    }
    lockfile = source / "uv.lock"
    if lockfile.is_file() and not lockfile.is_symlink():
        files["uv.lock"] = _file_summary(lockfile, relative="uv.lock")
    license_files = _license_input_paths(source, metadata)
    for path in license_files:
        relative = path.relative_to(source).as_posix()
        files[relative] = _file_summary(path, relative=relative)

    return {
        "schema": "scirel.build-inputs.v1",
        "files": files,
        "license_files": [
            path.relative_to(source).as_posix() for path in license_files
        ],
        "helper": helper_binding(helper_paths),
    }


def helper_binding(paths: Iterable[str]) -> dict[str, object]:
    """Bind the exact helper source used by an external build.

    The Git revision identifies the checkout baseline while per-file digests
    detect a locally modified helper.  This keeps the old ref-bound build
    workflow usable while making a dirty helper explicit in the manifest.
    """

    normalized = sorted(
        {
            _safe_relative_path(path, field="helper path").as_posix()
            for path in paths
        }
    )
    files: dict[str, dict[str, object]] = {}
    for relative in normalized:
        path = ROOT / relative
        files[relative] = _file_summary(path, relative=relative)
    try:
        revision = resolve_revision("HEAD")
        status = _run_git("status", "--porcelain", "--", *normalized) if normalized else ""
    except (OSError, subprocess.CalledProcessError, ValueError):
        revision = None
        status = ""
    return {
        "revision": revision,
        "dirty": bool(status),
        "files": files,
    }


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
    _normalize_archive_modes(source)
    return source


def _normalize_archive_modes(source: Path) -> None:
    """Normalize extracted Git-tree permissions before invoking the backend.

    ``git archive`` records the repository mode (normally ``0644`` for regular
    files and ``0755`` for executable files), but a tar extractor applies the
    host process' umask while creating those paths.  A Linux container with a
    permissive umask can therefore materialize package data as ``0664`` while
    the same archive on macOS materializes it as ``0644``.  Setuptools carries
    those modes into ZIP external attributes, making otherwise identical
    ``py3-none-any`` wheels differ byte-for-byte.  Keep executable bits where
    they were present and make every other regular file and directory
    deterministic across hosts.
    """

    if not source.is_dir():
        raise ValueError(f"archived source is not a directory: {source}")
    for path in sorted(source.rglob("*"), key=lambda candidate: candidate.as_posix()):
        if path.is_symlink():
            # ``filter='data'`` normally rejects unsafe links.  Do not follow
            # a link while normalizing modes if a repository deliberately
            # contains a safe one.
            continue
        if path.is_dir():
            path.chmod(0o755)
        elif path.is_file():
            current_mode = path.stat().st_mode
            path.chmod(0o755 if current_mode & 0o111 else 0o644)
        else:
            raise ValueError(f"archived source contains a non-regular path: {path}")


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
            inputs = build_input_binding(
                source,
                helper_paths=("scripts/build_scirel_from_ref.py",),
            )
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
        "inputs": inputs,
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

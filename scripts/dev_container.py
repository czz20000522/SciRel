#!/usr/bin/env python3
"""Run SciRel development commands in the repository's isolated Linux container."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "containers" / "dev" / "compose.yaml"
IMAGE = "scirel-dev-python:3.14.7"
SYNC = "uv sync --locked --group test"
PYTHON = "uv run --frozen python -B"
GIT_COMMON_MOUNT = "/scirel-git"
CHECK_RECEIPT_SCHEMA = 2
CHECK_RECEIPT_MAX_ENTRIES = 16
CHECK_RECEIPT_MAX_AGE_SECONDS = 30 * 24 * 60 * 60
CHECK_RECEIPT_TEMP_PREFIX = "check-receipt-"
RECEIPT_CACHE_COMPONENTS = ("scirel-acceptance", "receipts")


class ReceiptCacheUnavailable(RuntimeError):
    """Raised when the receipt cache cannot be proven safe to access."""


class ContainerLockUnavailable(RuntimeError):
    """Raised when the per-worktree container lock cannot be used safely."""


RECEIPT_CACHE_ERRORS = (
    OSError,
    RuntimeError,
    UnicodeError,
    ValueError,
    OverflowError,
    TypeError,
)


def project_name() -> str:
    identity = os.path.normcase(str(ROOT))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10]
    return f"scirel-dev-{digest}"


def python_version() -> str:
    return (ROOT / ".python-version").read_text(encoding="utf-8").strip()


def venv_volume() -> str:
    checkout = project_name().removeprefix("scirel-dev-")
    return f"scirel-venv-{checkout}"


def uv_cache_volume() -> str:
    return f"scirel-uv-cache-{python_version()}"


def _container_proxy(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("127.0.0.1", "host.docker.internal").replace(
        "localhost", "host.docker.internal"
    )


def environment() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("SCIReL_IMAGE_KEY", "3.14.7")
    env["SCIReL_HTTP_PROXY"] = _container_proxy(env.get("HTTP_PROXY") or env.get("http_proxy"))
    env["SCIReL_HTTPS_PROXY"] = _container_proxy(env.get("HTTPS_PROXY") or env.get("https_proxy"))
    env["SCIReL_ALL_PROXY"] = _container_proxy(env.get("ALL_PROXY") or env.get("all_proxy"))
    env["SCIReL_NO_PROXY"] = env.get("NO_PROXY") or env.get("no_proxy") or ""
    env.setdefault("SCIReL_VENV_VOLUME", venv_volume())
    env.setdefault("SCIReL_UV_CACHE_VOLUME", uv_cache_volume())
    return env


def compose_command(*args: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--file",
        str(COMPOSE),
        "--project-name",
        project_name(),
        *args,
    ]


def git_discovery_environment() -> dict[str, str]:
    """Return an environment that discovers Git from the checkout, not an outer run."""
    env = os.environ.copy()
    for name in ("GIT_DIR", "GIT_WORK_TREE"):
        env.pop(name, None)
    return env


def git_output(*arguments: str) -> str:
    done = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        env=git_discovery_environment(),
        check=False,
        capture_output=True,
        text=True,
    )
    if done.returncode:
        detail = done.stderr.strip() or done.stdout.strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {detail}")
    return done.stdout.strip()


def git_common_directory() -> Path:
    """Return project metadata shared by every linked worktree."""
    return Path(
        git_output(
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        )
    )


def worktree_git_directory() -> Path:
    """Return this checkout's private Git metadata directory."""
    return Path(git_output("rev-parse", "--absolute-git-dir"))


def _worktree_path_parts(path: Path) -> tuple[Path, tuple[str, ...]]:
    """Return the real worktree Git directory and a validated relative path."""
    git_directory = worktree_git_directory()
    try:
        real_git_directory = git_directory.resolve(strict=True)
    except OSError as error:
        raise ContainerLockUnavailable(f"cannot resolve worktree Git directory: {error}") from error
    if not real_git_directory.is_dir():
        raise ContainerLockUnavailable("worktree Git directory is not a directory")

    relative = None
    for base in (git_directory, real_git_directory):
        try:
            candidate = path.relative_to(base)
        except ValueError:
            continue
        if relative is not None and candidate != relative:
            raise ContainerLockUnavailable("container lock has conflicting Git roots")
        relative = candidate
    if relative is None:
        raise ContainerLockUnavailable("container lock is outside the worktree Git directory")

    parts = relative.parts
    if (
        len(parts) != 2
        or parts[0] != RECEIPT_CACHE_COMPONENTS[0]
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise ContainerLockUnavailable("container lock path is not a direct lock file")
    return real_git_directory, parts


def _resolved_worktree_path(git_directory: Path, path: Path) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ContainerLockUnavailable(f"cannot resolve container lock path: {error}") from error
    if resolved == git_directory or not resolved.is_relative_to(git_directory):
        raise ContainerLockUnavailable("container lock resolves outside the worktree Git directory")
    return resolved


def validated_container_lock_path(*, create_directory: bool = False) -> Path:
    """Return a verified regular lock path strictly inside worktree Git metadata."""
    git_directory, parts = _worktree_path_parts(container_lock_path())
    directory = git_directory / parts[0]
    if _is_link_like(directory):
        raise ContainerLockUnavailable("container lock directory is a symlink or junction")
    try:
        directory.lstat()
    except FileNotFoundError:
        if not create_directory:
            raise ContainerLockUnavailable("container lock directory does not exist") from None
        try:
            directory.mkdir()
        except FileExistsError:
            pass
        except OSError as error:
            raise ContainerLockUnavailable(
                f"cannot create container lock directory: {error}"
            ) from error
    except OSError as error:
        raise ContainerLockUnavailable(
            f"cannot inspect container lock directory: {error}"
        ) from error

    if _is_link_like(directory) or not directory.is_dir():
        raise ContainerLockUnavailable("container lock directory is not a real directory")
    _resolved_worktree_path(git_directory, directory)

    path = directory / parts[1]
    if _is_link_like(path):
        raise ContainerLockUnavailable("container lock file is a symlink or junction")
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return path
    except OSError as error:
        raise ContainerLockUnavailable(f"cannot inspect container lock file: {error}") from error
    if not stat.S_ISREG(mode):
        raise ContainerLockUnavailable("container lock path is not a regular file")
    _resolved_worktree_path(git_directory, path)
    return path


def check_receipt_directory() -> Path:
    """Return the bounded receipt cache inside shared project metadata."""
    return git_common_directory().joinpath(*RECEIPT_CACHE_COMPONENTS)


def _is_link_like(path: Path) -> bool:
    """Return true for symlinks and Windows junctions, failing closed on errors."""
    try:
        return path.is_symlink() or path.is_junction()
    except OSError:
        return True


def _receipt_path_parts(path: Path) -> tuple[Path, tuple[str, ...]]:
    """Return the real Git common directory and a validated cache-relative path."""
    common = git_common_directory()
    try:
        common_real = common.resolve(strict=True)
    except OSError as error:
        raise ReceiptCacheUnavailable(f"cannot resolve Git common directory: {error}") from error
    if not common_real.is_dir():
        raise ReceiptCacheUnavailable("Git common directory is not a directory")

    relative = None
    for base in (common, common_real):
        try:
            candidate = path.relative_to(base)
        except ValueError:
            continue
        if relative is not None and candidate != relative:
            raise ReceiptCacheUnavailable("receipt path has conflicting common-directory roots")
        relative = candidate
    if relative is None:
        raise ReceiptCacheUnavailable("receipt path is outside the Git common directory")

    parts = relative.parts
    if (
        len(parts) < len(RECEIPT_CACHE_COMPONENTS)
        or parts[: len(RECEIPT_CACHE_COMPONENTS)] != RECEIPT_CACHE_COMPONENTS
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise ReceiptCacheUnavailable("receipt path is outside the receipt cache")
    return common_real, parts


def _resolved_inside(common: Path, path: Path) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ReceiptCacheUnavailable(f"cannot resolve receipt path: {error}") from error
    if resolved == common or not resolved.is_relative_to(common):
        raise ReceiptCacheUnavailable("receipt path resolves outside the Git common directory")
    return resolved


def validated_receipt_directory(*, create: bool = False) -> Path:
    """Return a real receipt directory whose existing components are not links."""
    common, parts = _receipt_path_parts(check_receipt_directory())
    if parts != RECEIPT_CACHE_COMPONENTS:
        raise ReceiptCacheUnavailable("unexpected receipt cache directory path")

    current = common
    for part in parts:
        current = current / part
        if _is_link_like(current):
            raise ReceiptCacheUnavailable("receipt cache path contains a symlink or junction")
        try:
            current.lstat()
        except FileNotFoundError:
            if not create:
                raise ReceiptCacheUnavailable("receipt cache directory does not exist") from None
            try:
                current.mkdir()
            except FileExistsError:
                pass
            except OSError as error:
                raise ReceiptCacheUnavailable(
                    f"cannot create receipt cache directory: {error}"
                ) from error
        except OSError as error:
            raise ReceiptCacheUnavailable(
                f"cannot inspect receipt cache directory: {error}"
            ) from error

        if _is_link_like(current) or not current.is_dir():
            raise ReceiptCacheUnavailable("receipt cache path is not a real directory")
        _resolved_inside(common, current)
    return current


def validated_receipt_file(path: Path, *, create_directory: bool = False) -> Path:
    """Return a direct child file of the validated real receipt directory."""
    common, parts = _receipt_path_parts(path)
    if len(parts) != len(RECEIPT_CACHE_COMPONENTS) + 1:
        raise ReceiptCacheUnavailable("receipt file is not a direct cache child")
    directory = validated_receipt_directory(create=create_directory)
    candidate = directory / parts[-1]
    if _is_link_like(candidate):
        raise ReceiptCacheUnavailable("receipt file is a symlink or junction")
    try:
        mode = candidate.lstat().st_mode
    except FileNotFoundError:
        return candidate
    except OSError as error:
        raise ReceiptCacheUnavailable(f"cannot inspect receipt file: {error}") from error
    if not stat.S_ISREG(mode):
        raise ReceiptCacheUnavailable("receipt path is not a regular file")
    _resolved_inside(common, candidate)
    return candidate


def _check_receipt_filename(tree: str, architecture: str) -> str:
    identity = f"{CHECK_RECEIPT_SCHEMA}\0{tree}\0{architecture}".encode("utf-8")
    return f"{hashlib.sha256(identity).hexdigest()}.json"


def check_receipt_path(tree: str | None = None, architecture: str | None = None) -> Path:
    """Return the cache file for an exact HEAD tree and host architecture."""
    if tree is None:
        tree = git_output("rev-parse", "HEAD^{tree}")
    if architecture is None:
        architecture = platform.machine()
    return check_receipt_directory() / _check_receipt_filename(tree, architecture)


def candidate_tree() -> str | None:
    """Return the exact index tree, or None when untracked/unstaged files dilute it."""
    unstaged = subprocess.run(
        ["git", "diff", "--quiet", "--ignore-submodules", "--"],
        cwd=ROOT,
        env=git_discovery_environment(),
        check=False,
    )
    if unstaged.returncode:
        return None
    if git_output("ls-files", "--others", "--exclude-standard"):
        return None
    return git_output("write-tree")


def _remove_receipt_cache_file(path: Path) -> None:
    try:
        validated_receipt_file(path).unlink(missing_ok=True)
    except RECEIPT_CACHE_ERRORS as error:
        print(
            f"WARNING: could not prune local check receipt {ascii(path.name)}: {ascii(str(error))}",
            file=sys.stderr,
        )


def _receipt_timestamp(value: object) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        timestamp = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return timestamp if math.isfinite(timestamp) else None


def _read_check_receipt(
    path: Path,
    *,
    expected_tree: str | None = None,
    expected_architecture: str | None = None,
) -> tuple[dict[str, object] | None, str | None]:
    try:
        safe_path = validated_receipt_file(path)
    except RECEIPT_CACHE_ERRORS as error:
        return None, f"local check receipt unavailable: {error}"
    try:
        receipt = json.loads(safe_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, None
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, f"unreadable local check receipt: {error}"
    if not isinstance(receipt, dict):
        return None, "invalid local check receipt"

    schema = receipt.get("schema")
    if type(schema) is not int or schema != CHECK_RECEIPT_SCHEMA:
        return None, "stale local check receipt schema"
    tree = receipt.get("tree")
    architecture = receipt.get("architecture")
    checked_at = receipt.get("checked_at_unix")
    if not isinstance(tree, str) or not tree:
        return None, "invalid local check receipt tree"
    if not isinstance(architecture, str) or not architecture:
        return None, "invalid local check receipt architecture"
    if _receipt_timestamp(checked_at) is None:
        return None, "invalid local check receipt timestamp"
    if expected_tree is not None and tree != expected_tree:
        return None, "local check receipt is for another Git tree"
    if expected_architecture is not None and architecture != expected_architecture:
        return None, "local check receipt is for another host architecture"
    try:
        expected_name = _check_receipt_filename(tree, architecture)
    except UnicodeError:
        return None, "invalid local check receipt key"
    if safe_path.name != expected_name:
        return None, "local check receipt key does not match its file"
    return receipt, None


def _check_receipt_is_fresh(receipt: dict[str, object], now: float) -> bool:
    checked_at = _receipt_timestamp(receipt.get("checked_at_unix"))
    if checked_at is None or not math.isfinite(now):
        return False
    age = now - checked_at
    return 0 <= age < CHECK_RECEIPT_MAX_AGE_SECONDS


def _prune_check_receipts(directory: Path, now: float) -> None:
    """Remove expired, corrupt, temporary, and excess entries while cache-locked."""
    directory = validated_receipt_directory()
    valid: list[tuple[float, Path]] = []
    try:
        candidate_paths = sorted(directory.glob("*.json"))
    except RECEIPT_CACHE_ERRORS as error:
        raise ReceiptCacheUnavailable(f"cannot enumerate receipt cache: {error}") from error
    for path in candidate_paths:
        try:
            safe_path = validated_receipt_file(path)
        except RECEIPT_CACHE_ERRORS:
            continue
        try:
            receipt, _ = _read_check_receipt(safe_path)
        except RECEIPT_CACHE_ERRORS:
            receipt = None
        if receipt is None or not _check_receipt_is_fresh(receipt, now):
            _remove_receipt_cache_file(safe_path)
            continue
        checked_at = _receipt_timestamp(receipt.get("checked_at_unix"))
        if checked_at is not None:
            valid.append((checked_at, safe_path))

    # Writers create temporary files only while holding this same lock, so an
    # unlocked cleaner cannot delete a receipt that is actively being written.
    for path in directory.glob(f"{CHECK_RECEIPT_TEMP_PREFIX}*.tmp"):
        _remove_receipt_cache_file(path)

    valid.sort(key=lambda item: (item[0], item[1].name), reverse=True)
    for _, path in valid[CHECK_RECEIPT_MAX_ENTRIES:]:
        _remove_receipt_cache_file(path)


def _write_check_receipt(receipt: dict[str, object], path: Path) -> bool:
    temporary = None
    try:
        with check_receipt_lock():
            safe_path = validated_receipt_file(path, create_directory=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix=CHECK_RECEIPT_TEMP_PREFIX,
                suffix=".tmp",
                dir=safe_path.parent,
                delete=False,
            ) as stream:
                json.dump(receipt, stream, sort_keys=True, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
                temporary = Path(stream.name)
            safe_path = validated_receipt_file(path, create_directory=True)
            os.replace(temporary, safe_path)
            temporary = None
            checked_at = _receipt_timestamp(receipt.get("checked_at_unix"))
            if checked_at is None:
                raise ReceiptCacheUnavailable("new receipt has an invalid timestamp")
            _prune_check_receipts(safe_path.parent, checked_at)
    except RECEIPT_CACHE_ERRORS as error:
        print(f"Local check receipt not written: {error}")
        return False
    finally:
        if temporary is not None:
            _remove_receipt_cache_file(temporary)
    return True


def clear_check_receipt() -> None:
    """Invalidate only the receipt for the candidate tree being checked."""
    tree = candidate_tree()
    if tree is None:
        return
    try:
        path = check_receipt_path(tree)
        with check_receipt_lock():
            safe_path = validated_receipt_file(path, create_directory=True)
            _remove_receipt_cache_file(safe_path)
            _prune_check_receipts(safe_path.parent, time.time())
    except RECEIPT_CACHE_ERRORS as error:
        print(f"WARNING: could not clear local check receipt: {error}", file=sys.stderr)


def record_check_receipt(tree: str | None = None) -> bool:
    if tree is None:
        tree = candidate_tree()
    if tree is None:
        print(
            "Local check receipt not written: commit or clean unstaged and untracked files first."
        )
        return False
    architecture = platform.machine()
    receipt = {
        "schema": CHECK_RECEIPT_SCHEMA,
        "tree": tree,
        "architecture": architecture,
        "checked_at_unix": time.time(),
    }
    try:
        path = check_receipt_path(tree, architecture)
    except RECEIPT_CACHE_ERRORS as error:
        print(f"Local check receipt not written: {error}")
        return False
    if not _write_check_receipt(receipt, path):
        return False
    print(f"Recorded local check receipt for tree {tree[:12]} on {architecture}.")
    return True


def check_receipt_status() -> tuple[bool, str]:
    try:
        head = git_output("rev-parse", "HEAD^{tree}")
        architecture = platform.machine()
        path = check_receipt_path(head, architecture)
        with check_receipt_lock():
            now = time.time()
            receipt, reason = _read_check_receipt(
                path,
                expected_tree=head,
                expected_architecture=architecture,
            )
            if receipt is None:
                reason = reason or "no local check receipt"
            elif not _check_receipt_is_fresh(receipt, now):
                receipt = None
                reason = "expired local check receipt"
            _prune_check_receipts(path.parent, now)
    except RECEIPT_CACHE_ERRORS as error:
        return False, f"local check receipt unavailable: {error}"
    if receipt is None:
        return False, reason or "no local check receipt"
    return True, f"local acceptance already passed for tree {head[:12]} on {architecture}"


def run_check() -> int:
    clear_check_receipt()
    script = f"{SYNC} && {PYTHON} skills/development/scirel-acceptance/scripts/check_all.py"
    code = run_in_container(shell_command(script))
    if not code:
        record_check_receipt()
    return code


def pre_push() -> int:
    valid, reason = check_receipt_status()
    if valid:
        print(f"{reason}; skipping the duplicate full check.")
        return 0
    print(f"{reason}; running the complete local check.")
    return run_check()


def linked_worktree_git_context() -> tuple[Path, str] | None:
    """Return shared Git metadata for a linked worktree, or ``None`` otherwise."""
    if not (ROOT / ".git").is_file():
        return None
    commands = (
        ["git", "rev-parse", "--absolute-git-dir"],
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
    )
    resolved = []
    for command in commands:
        done = subprocess.run(
            command,
            cwd=ROOT,
            env=git_discovery_environment(),
            check=False,
            capture_output=True,
            text=True,
        )
        if done.returncode:
            detail = done.stderr.strip() or done.stdout.strip()
            raise RuntimeError(f"cannot resolve linked-worktree Git metadata: {detail}")
        resolved.append(Path(done.stdout.strip()))
    git_dir, common_dir = resolved
    try:
        relative_git_dir = git_dir.relative_to(common_dir)
    except ValueError as error:
        raise RuntimeError(
            "linked-worktree Git directory is outside its common directory"
        ) from error
    if not relative_git_dir.parts:
        raise RuntimeError("linked-worktree Git directory has no path below its common directory")
    return common_dir, relative_git_dir.as_posix()


@contextmanager
def container_git_mount() -> Iterator[list[str]]:
    """Expose linked-worktree Git metadata without changing the run environment."""
    context = linked_worktree_git_context()
    if context is None:
        yield []
        return
    common_dir, relative_git_dir = context
    pointer = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="scirel-container-gitdir-",
            dir=common_dir,
            delete=False,
        ) as stream:
            stream.write(f"gitdir: {GIT_COMMON_MOUNT}/{relative_git_dir}\n")
            pointer = Path(stream.name)
        yield [
            "--volume",
            f"{common_dir}:{GIT_COMMON_MOUNT}",
            "--volume",
            f"{pointer}:/workspace/.git:ro",
        ]
    finally:
        if pointer is not None:
            pointer.unlink(missing_ok=True)


def run(command: list[str], *, interactive: bool = False) -> int:
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            env=environment(),
            stdin=sys.stdin if interactive else None,
        ).returncode
    except FileNotFoundError:
        print("Docker is not installed or is not on PATH.", file=sys.stderr)
        return 127


def docker_ready() -> bool:
    done = subprocess.run(
        ["docker", "info"],
        cwd=ROOT,
        env=environment(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if done.returncode:
        print(
            "Docker engine is not reachable. Start Docker Desktop or a Docker-compatible "
            "runtime, then retry. This repository does not start host services itself.",
            file=sys.stderr,
        )
        return False
    return True


def build() -> int:
    return run(compose_command("build"))


def ensure_uv_cache_volume() -> int:
    volume = environment()["SCIReL_UV_CACHE_VOLUME"]
    done = subprocess.run(
        ["docker", "volume", "create", volume],
        cwd=ROOT,
        env=environment(),
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if done.returncode:
        print(
            f"Could not create the shared uv cache volume: {done.stderr.strip()}", file=sys.stderr
        )
    return done.returncode


def container_lock_path() -> Path:
    return worktree_git_directory() / "scirel-acceptance" / f"{project_name()}.container.lock"


def check_receipt_lock_path() -> Path:
    return check_receipt_directory() / "receipt-cache.lock"


def _lock_stream(stream) -> None:
    if sys.platform == "win32":
        import msvcrt

        while True:
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError as error:
                if error.errno not in {errno.EACCES, errno.EDEADLK}:
                    raise
                time.sleep(0.1)
    else:
        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)


def _unlock_stream(stream) -> None:
    if sys.platform == "win32":
        import msvcrt

        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _open_lock_stream(path: Path, *, label: str, unavailable):
    flags = os.O_RDWR | os.O_CREAT | os.O_APPEND
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags, 0o600)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise unavailable(f"{label} is not a regular file")
        stream = os.fdopen(descriptor, "a+b")
        descriptor = -1
        return stream
    except OSError as error:
        raise unavailable(f"cannot open {label}: {error}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


@contextmanager
def container_project_lock() -> Iterator[None]:
    """Serialize Compose mutations for one checkout while other worktrees stay parallel."""
    path = validated_container_lock_path(create_directory=True)
    stream = _open_lock_stream(
        path,
        label="container lock",
        unavailable=ContainerLockUnavailable,
    )
    with stream:
        validated_container_lock_path()
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        _lock_stream(stream)
        try:
            yield
        finally:
            _unlock_stream(stream)


@contextmanager
def check_receipt_lock() -> Iterator[None]:
    """Serialize the shared receipt cache across every linked worktree."""
    path = validated_receipt_file(check_receipt_lock_path(), create_directory=True)
    stream = _open_lock_stream(
        path,
        label="receipt cache lock",
        unavailable=ReceiptCacheUnavailable,
    )
    with stream:
        validated_receipt_file(path, create_directory=True)
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        _lock_stream(stream)
        try:
            yield
        finally:
            _unlock_stream(stream)


def cleanup_compose_project() -> bool:
    """Remove this checkout's Compose container and network, reporting failures."""
    project = project_name()
    down_detail = None
    try:
        down = subprocess.run(
            compose_command("down", "--remove-orphans"),
            cwd=ROOT,
            env=environment(),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        down_detail = f"could not start Compose cleanup: {error}"
    else:
        if down.returncode != 0:
            detail = (down.stderr or down.stdout).strip()
            down_detail = f"Compose cleanup exited {down.returncode}"
            if detail:
                down_detail += f": {detail}"

    network = f"{project}_default"
    try:
        removed = subprocess.run(
            ["docker", "network", "rm", network],
            cwd=ROOT,
            env=environment(),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        prefix = down_detail or "Compose cleanup reported success"
        print(
            f"WARNING: {prefix}; network removal could not start: {error}",
            file=sys.stderr,
        )
        return False
    if removed.returncode == 0:
        return True
    detail = (removed.stderr or removed.stdout).strip()
    if "no such network" in detail.lower() or "not found" in detail.lower():
        return True
    suffix = f": {detail}" if detail else ""
    prefix = down_detail or "Compose cleanup reported success"
    print(
        f"WARNING: {prefix}; network removal failed ({removed.returncode}){suffix}",
        file=sys.stderr,
    )
    return False


def run_in_container(arguments: list[str], *, interactive: bool = False) -> int:
    if not docker_ready():
        return 2
    with container_project_lock():
        cache = ensure_uv_cache_volume()
        if cache:
            return cache
        built = build()
        if built:
            return built
        command = compose_command("run", "--rm")
        if interactive:
            command.append("--interactive")
        try:
            with container_git_mount() as git_mount:
                return run([*command, *git_mount, "dev", *arguments], interactive=interactive)
        finally:
            cleanup_compose_project()
            try:
                clean_generated_caches()
            except OSError as error:
                print(f"WARNING: generated-cache cleanup failed: {error}", file=sys.stderr)


def clean_generated_caches() -> None:
    """Remove interpreter caches that bind-mounted source can leave on the host."""
    for name in (".pytest_cache", ".ruff_cache", ".mypy_cache"):
        shutil.rmtree(ROOT / name, ignore_errors=True)
    for current, directories, files in os.walk(ROOT):
        if Path(current) == ROOT and ".git" in directories:
            directories.remove(".git")
        for name in list(directories):
            if name != "__pycache__":
                continue
            path = Path(current) / name
            if not path.is_symlink():
                shutil.rmtree(path, ignore_errors=True)
            directories.remove(name)
        for name in files:
            if not name.endswith(".pyc"):
                continue
            try:
                (Path(current) / name).unlink(missing_ok=True)
            except OSError as error:
                print(f"WARNING: could not remove generated cache {name}: {error}", file=sys.stderr)


def shell_command(script: str) -> list[str]:
    return ["bash", "-lc", script]


def clean(*, remove_cache: bool = False, remove_image: bool = False) -> int:
    with container_project_lock():
        removal = ["down", "--remove-orphans"]
        if remove_image:
            removal.extend(["--rmi", "local"])
        code = run(compose_command(*removal))
        env = environment()
        volumes = [env["SCIReL_VENV_VOLUME"]]
        if remove_cache:
            volumes.append(env["SCIReL_UV_CACHE_VOLUME"])
        for volume in volumes:
            removed = run(["docker", "volume", "rm", "--force", volume])
            if not code:
                code = removed
        return code


def doctor() -> int:
    if not docker_ready():
        return 2
    commands = [
        ["docker", "context", "show"],
        ["docker", "compose", "version"],
        ["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"],
    ]
    for command in commands:
        code = run(command)
        if code:
            print(f"command failed ({code}): {' '.join(command)}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="check Docker and the development image")
    subparsers.add_parser("prepare", help="sync the locked test environment")
    subparsers.add_parser("shell", help="open a shell in the development container")
    subparsers.add_parser("check", help="run the complete acceptance check")
    subparsers.add_parser("precommit", help="run the staged-file pre-commit check")
    subparsers.add_parser(
        "pre-push", help="reuse an exact local check receipt or run the full check"
    )
    pytest_parser = subparsers.add_parser("pytest", help="run pytest with optional arguments")
    pytest_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    clean_parser = subparsers.add_parser(
        "clean", help="remove this checkout's virtualenv; optionally the shared image or uv cache"
    )
    clean_parser.add_argument("--image", action="store_true", help="also remove the shared image")
    clean_parser.add_argument(
        "--cache", action="store_true", help="also remove the shared uv cache"
    )

    args = parser.parse_args()
    if args.command == "doctor":
        return doctor()
    if args.command == "prepare":
        return run_in_container(shell_command(SYNC))
    if args.command == "shell":
        return run_in_container(["bash", "-l"], interactive=True)
    if args.command == "check":
        return run_check()
    if args.command == "precommit":
        script = (
            f"{SYNC} && {PYTHON} skills/development/scirel-acceptance/scripts/precommit_check.py"
        )
        return run_in_container(shell_command(script))
    if args.command == "pre-push":
        return pre_push()
    if args.command == "pytest":
        arguments = args.arguments or ["-q"]
        script = f"{SYNC} && {PYTHON} -m pytest {shlex.join(arguments)}"
        return run_in_container(shell_command(script))
    if args.command == "clean":
        return clean(remove_cache=args.cache, remove_image=args.image)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

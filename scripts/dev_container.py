#!/usr/bin/env python3
"""Run SciRel development commands in the repository's isolated Linux container."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
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
CHECK_RECEIPT_SCHEMA = 1


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


def check_receipt_path() -> Path:
    return Path(
        git_output(
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "scirel-acceptance/check-receipt.json",
        )
    )


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


def clear_check_receipt() -> None:
    try:
        check_receipt_path().unlink(missing_ok=True)
    except (OSError, RuntimeError):
        pass


def record_check_receipt() -> bool:
    tree = candidate_tree()
    if tree is None:
        print(
            "Local check receipt not written: commit or clean unstaged and untracked files first."
        )
        return False
    path = check_receipt_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": CHECK_RECEIPT_SCHEMA,
        "tree": tree,
        "architecture": platform.machine(),
        "checked_at_unix": time.time(),
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="check-receipt-",
            dir=path.parent,
            delete=False,
        ) as stream:
            json.dump(receipt, stream, sort_keys=True, indent=2)
            stream.write("\n")
            temporary = Path(stream.name)
        os.replace(temporary, path)
    except OSError as error:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        print(f"Local check receipt not written: {error}")
        return False
    print(f"Recorded local check receipt for tree {tree[:12]}.")
    return True


def check_receipt_status() -> tuple[bool, str]:
    path = check_receipt_path()
    if not path.is_file():
        return False, "no local check receipt"
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return False, f"unreadable local check receipt: {error}"
    if receipt.get("schema") != CHECK_RECEIPT_SCHEMA:
        return False, "stale local check receipt schema"
    if receipt.get("architecture") != platform.machine():
        return False, "local check receipt is for another host architecture"
    head = git_output("rev-parse", "HEAD^{tree}")
    if receipt.get("tree") != head:
        return False, "local check receipt is for another Git tree"
    return True, f"local acceptance already passed for tree {head[:12]}"


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
    return check_receipt_path().parent / f"{project_name()}.container.lock"


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


@contextmanager
def container_project_lock() -> Iterator[None]:
    """Serialize Compose mutations for one checkout while other worktrees stay parallel."""
    path = container_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
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

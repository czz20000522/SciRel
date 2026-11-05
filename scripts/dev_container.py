#!/usr/bin/env python3
"""Run SciRel development commands in the repository's isolated Linux container."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "containers" / "dev" / "compose.yaml"
IMAGE = "scirel-dev-python:3.14.7"
SYNC = "uv sync --locked --group test"
PYTHON = "uv run --frozen python -B"
GIT_COMMON_MOUNT = "/scirel-git"


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
        raise RuntimeError("linked-worktree Git directory is outside its common directory") from error
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


def run_in_container(arguments: list[str], *, interactive: bool = False) -> int:
    if not docker_ready():
        return 2
    built = build()
    if built:
        return built
    command = compose_command("run", "--rm")
    if interactive:
        command.append("--interactive")
    with container_git_mount() as git_mount:
        code = run([*command, *git_mount, "dev", *arguments], interactive=interactive)
    clean_generated_caches()
    return code


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
            if name.endswith(".pyc"):
                (Path(current) / name).unlink(missing_ok=True)


def shell_command(script: str) -> list[str]:
    return ["bash", "-lc", script]


def clean(*, remove_cache: bool = False, remove_image: bool = False) -> int:
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
    pytest_parser = subparsers.add_parser("pytest", help="run pytest with optional arguments")
    pytest_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    clean_parser = subparsers.add_parser(
        "clean", help="remove this checkout's virtualenv; optionally the shared image or uv cache"
    )
    clean_parser.add_argument("--image", action="store_true", help="also remove the shared image")
    clean_parser.add_argument("--cache", action="store_true", help="also remove the shared uv cache")

    args = parser.parse_args()
    if args.command == "doctor":
        return doctor()
    if args.command == "prepare":
        return run_in_container(shell_command(SYNC))
    if args.command == "shell":
        return run_in_container(["bash", "-l"], interactive=True)
    if args.command == "check":
        script = f"{SYNC} && {PYTHON} skills/development/scirel-acceptance/scripts/check_all.py"
        return run_in_container(shell_command(script))
    if args.command == "precommit":
        script = (
            f"{SYNC} && {PYTHON} skills/development/scirel-acceptance/scripts/precommit_check.py"
        )
        return run_in_container(shell_command(script))
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

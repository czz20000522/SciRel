#!/usr/bin/env python3
"""Run SciRel development commands in the repository's isolated Linux container."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "containers" / "dev" / "compose.yaml"
IMAGE = "scirel-dev-python:3.14.7"
SYNC = "uv sync --locked --group test"
PYTHON = "uv run --frozen python -B"


def project_name() -> str:
    identity = os.path.normcase(str(ROOT))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10]
    return f"scirel-dev-{digest}"


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
    code = run([*command, "dev", *arguments], interactive=interactive)
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
        "clean", help="remove this checkout's container volumes; optionally the shared image"
    )
    clean_parser.add_argument("--image", action="store_true", help="also remove the shared image")

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
        removal = ["down", "--volumes", "--remove-orphans"]
        if args.image:
            removal.append("--rmi")
            removal.append("local")
        return run(compose_command(*removal))
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

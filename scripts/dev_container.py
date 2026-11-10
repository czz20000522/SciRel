#!/usr/bin/env python3
"""Run SciRel development commands in the repository's isolated Linux container."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager
import errno
import hashlib
import os
from pathlib import Path
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
METADATA_DIRECTORY = "scirel-acceptance"
DOCKER_CONTEXT_ENV = "SCIReL_DOCKER_CONTEXT"
DOCKER_CONTEXT_FILENAME = "docker-context"


class DockerContextError(RuntimeError):
    """Raised when the project Docker context is missing or unsafe."""


class ContainerLockUnavailable(RuntimeError):
    """Raised when the per-worktree container lock cannot be used safely."""


class RepositoryConfigError(RuntimeError):
    """Raised when repository-local Git configuration is unsafe for discovery."""


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


def docker_context_path(*, create_directory: bool = False) -> Path:
    """Return the validated per-clone Docker context file in shared Git metadata."""
    common = git_common_directory()
    try:
        common_real = common.resolve(strict=True)
    except OSError as error:
        raise DockerContextError(f"cannot resolve Git common directory: {error}") from error
    if not common_real.is_dir():
        raise DockerContextError("Git common directory is not a directory")

    directory = common / METADATA_DIRECTORY
    if _is_link_like(directory):
        raise DockerContextError("Docker context directory is a symlink or junction")
    try:
        directory.lstat()
    except FileNotFoundError:
        if not create_directory:
            raise DockerContextError("Docker context is not configured") from None
        try:
            directory.mkdir()
        except FileExistsError:
            pass
        except OSError as error:
            raise DockerContextError(f"cannot create Docker context directory: {error}") from error
    except OSError as error:
        raise DockerContextError(f"cannot inspect Docker context directory: {error}") from error
    if _is_link_like(directory) or not directory.is_dir():
        raise DockerContextError("Docker context path is not a real directory")

    path = directory / DOCKER_CONTEXT_FILENAME
    if _is_link_like(path):
        raise DockerContextError("Docker context file is a symlink or junction")
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return path
    except OSError as error:
        raise DockerContextError(f"cannot inspect Docker context file: {error}") from error
    if not stat.S_ISREG(mode):
        raise DockerContextError("Docker context path is not a regular file")
    try:
        path.resolve(strict=True).relative_to(common_real)
    except (OSError, ValueError) as error:
        raise DockerContextError("Docker context file resolves outside Git metadata") from error
    return path


def _validated_docker_context(value: str, source: str) -> str:
    context = value.strip()
    if not context:
        raise DockerContextError(f"{source} is empty")
    if context == "default":
        raise DockerContextError(
            "the Docker context 'default' is not allowed for SciRel development; "
            "choose the project-specific context explicitly"
        )
    if any(character.isspace() for character in context):
        raise DockerContextError(f"{source} contains whitespace")
    return context


def resolve_docker_context() -> tuple[str, str]:
    """Return the selected context and a short source description."""
    project_value = os.environ.get(DOCKER_CONTEXT_ENV, "")
    if project_value.strip():
        return _validated_docker_context(project_value, DOCKER_CONTEXT_ENV), DOCKER_CONTEXT_ENV

    path = docker_context_path()
    try:
        value = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        pass
    except OSError as error:
        raise DockerContextError(f"cannot read Docker context {path}: {error}") from error
    else:
        return _validated_docker_context(value, str(path)), str(path)

    raise DockerContextError(
        "Docker context is not configured. Run "
        "`python3 scripts/dev_container.py context <docker-context>` once per clone, "
        f"or set {DOCKER_CONTEXT_ENV}."
    )


def configure_docker_context(name: str) -> int:
    """Validate and persist one explicit Docker context for this clone."""
    try:
        context = _validated_docker_context(name, "Docker context")
    except DockerContextError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env.pop("DOCKER_HOST", None)
    env["DOCKER_CONTEXT"] = context
    try:
        done = subprocess.run(
            ["docker", "context", "inspect", context],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("Docker is not installed or is not on PATH.", file=sys.stderr)
        return 127
    if done.returncode:
        detail = (done.stderr or done.stdout).strip()
        message = f"Docker context {context!r} is not available"
        if detail:
            message += f": {detail}"
        print(f"ERROR: {message}", file=sys.stderr)
        return done.returncode

    try:
        path = docker_context_path(create_directory=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="docker-context-",
            dir=path.parent,
            delete=False,
        ) as stream:
            stream.write(f"{context}\n")
            temporary = Path(stream.name)
        try:
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    except (DockerContextError, OSError) as error:
        print(f"ERROR: cannot store Docker context: {error}", file=sys.stderr)
        return 1

    print(f"SciRel Docker context set to {context!r} in {path}")
    return 0


def environment() -> dict[str, str]:
    env = os.environ.copy()
    context, _ = resolve_docker_context()
    env["DOCKER_CONTEXT"] = context
    env.pop("DOCKER_HOST", None)
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


def _read_metadata_file(path: Path, label: str) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise RepositoryConfigError(f"cannot read {label} {path}: {error}") from error


def _resolve_metadata_path(base: Path, value: str, label: str) -> Path:
    if not value:
        raise RepositoryConfigError(f"{label} is empty")
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    try:
        return path.resolve(strict=True)
    except OSError as error:
        raise RepositoryConfigError(f"cannot resolve {label} {path}: {error}") from error


def _git_config_values(path: Path, key: str) -> list[str]:
    """Read one explicit Git config file without consulting repository discovery."""
    env = os.environ.copy()
    for name in ("GIT_DIR", "GIT_WORK_TREE"):
        env.pop(name, None)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    try:
        done = subprocess.run(
            ["git", "config", "--file", str(path), "--get-all", key],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise RepositoryConfigError(f"cannot run Git config for {path}: {error}") from error
    if done.returncode == 1:
        return []
    if done.returncode:
        detail = done.stderr.strip() or done.stdout.strip()
        raise RepositoryConfigError(f"cannot read Git config {path}: {detail}")
    return done.stdout.splitlines()


def _config_bool(path: Path, key: str, value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "on", "1"}:
        return True
    if normalized in {"false", "no", "off", "0"}:
        return False
    raise RepositoryConfigError(f"{path} has invalid boolean {key}={value!r}")


def _is_absolute_path_value(value: str) -> bool:
    import ntpath
    import posixpath

    return Path(value).is_absolute() or ntpath.isabs(value) or posixpath.isabs(value)


def _is_local_worktree_path(value: str) -> bool:
    """Return whether an absolute worktree config value names this checkout."""
    import ntpath

    if not _is_absolute_path_value(value):
        return True
    if os.name != "nt" and ntpath.isabs(value) and not Path(value).is_absolute():
        return False
    try:
        configured = Path(value).expanduser().resolve(strict=False)
        root = ROOT.resolve(strict=False)
    except OSError:
        return False
    return os.path.normcase(os.path.abspath(configured)) == os.path.normcase(os.path.abspath(root))


def repository_config_paths() -> tuple[Path, Path | None]:
    """Return the common config and active worktree config paths without Git discovery."""
    dot_git = ROOT / ".git"
    if dot_git.is_dir():
        git_directory = dot_git.resolve(strict=True)
        common_directory = git_directory
    elif dot_git.is_file():
        metadata = _read_metadata_file(dot_git, "Git metadata file")
        first_line = metadata.splitlines()[0].strip() if metadata else ""
        if not first_line.startswith("gitdir:"):
            raise RepositoryConfigError(f"invalid Git metadata file {dot_git}: {first_line!r}")
        git_directory = _resolve_metadata_path(
            ROOT, first_line[len("gitdir:") :].strip(), "gitdir from .git"
        )
        commondir_file = git_directory / "commondir"
        if commondir_file.is_file():
            common_directory = _resolve_metadata_path(
                git_directory,
                _read_metadata_file(commondir_file, "commondir file"),
                "commondir from worktree metadata",
            )
        else:
            common_directory = git_directory
    else:
        raise RepositoryConfigError(f"cannot find Git metadata at {dot_git}")

    common_config = common_directory / "config"
    if not common_config.is_file():
        raise RepositoryConfigError(f"cannot find repository-local Git config at {common_config}")

    worktree_config = None
    worktree_config_values = _git_config_values(common_config, "extensions.worktreeConfig")
    if worktree_config_values and _config_bool(
        common_config, "extensions.worktreeConfig", worktree_config_values[-1]
    ):
        candidate = git_directory / "config.worktree"
        if candidate.is_file():
            worktree_config = candidate
    return common_config, worktree_config


def guard_repository_config() -> None:
    """Reject repository-local worktree paths that can break Git discovery."""
    common_config, worktree_config = repository_config_paths()
    values = _git_config_values(common_config, "core.worktree")
    if values:
        raise RepositoryConfigError(
            f"unsafe repository-local Git config {common_config} sets "
            f"core.worktree={values[-1]!r}; remove that local entry after checking "
            "that no legitimate per-worktree configuration depends on it"
        )

    if worktree_config is not None:
        values = _git_config_values(worktree_config, "core.worktree")
        for value in values:
            if not _is_local_worktree_path(value):
                raise RepositoryConfigError(
                    f"unsafe worktree Git config {worktree_config} sets "
                    f"core.worktree={value!r}; it does not name this checkout"
                )


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
        or parts[0] != METADATA_DIRECTORY
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


def _is_link_like(path: Path) -> bool:
    """Return true for symlinks and Windows junctions, failing closed on errors."""
    try:
        return path.is_symlink() or path.is_junction()
    except OSError:
        return True


def run_check() -> int:
    script = f"{SYNC} && {PYTHON} skills/development/scirel-acceptance/scripts/check_all.py"
    return run_in_container(shell_command(script))


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
    common_config = common_dir / "config"
    if not common_config.is_file():
        raise RuntimeError(f"cannot find repository-local Git config at {common_config}")
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
            f"{common_config}:{GIT_COMMON_MOUNT}/config:ro",
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
    except DockerContextError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


def docker_ready() -> bool:
    try:
        env = environment()
    except DockerContextError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return False
    done = subprocess.run(
        ["docker", "info"],
        cwd=ROOT,
        env=env,
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
    return worktree_git_directory() / METADATA_DIRECTORY / f"{project_name()}.container.lock"


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
        ["docker", "info", "--format", "engine={{.Name}}"],
        ["docker", "compose", "version"],
        ["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"],
    ]
    for command in commands:
        code = run(command)
        if code:
            print(f"command failed ({code}): {' '.join(command)}", file=sys.stderr)
    return 0


def main() -> int:
    try:
        guard_repository_config()
    except RepositoryConfigError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    context_parser = subparsers.add_parser(
        "context", help="show or set the explicit Docker context for this clone"
    )
    context_parser.add_argument("name", nargs="?")
    subparsers.add_parser("doctor", help="check Docker and the development image")
    subparsers.add_parser("prepare", help="sync the locked test environment")
    subparsers.add_parser("shell", help="open a shell in the development container")
    subparsers.add_parser("check", help="run the complete acceptance check")
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
    if args.command == "context":
        if args.name is not None:
            return configure_docker_context(args.name)
        try:
            selected, source = resolve_docker_context()
        except DockerContextError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(f"{selected} ({source})")
        return 0
    if args.command == "doctor":
        return doctor()
    if args.command == "prepare":
        return run_in_container(shell_command(SYNC))
    if args.command == "shell":
        return run_in_container(["bash", "-l"], interactive=True)
    if args.command == "check":
        return run_check()
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

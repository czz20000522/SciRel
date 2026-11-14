#!/usr/bin/env python3
"""Run SciRel development commands in the project's own uv environment on this machine.

Every run artifact stays inside the project directory, under the ignored ``.runtime/``:

- the main checkout's ``.runtime/`` holds what all worktrees of the clone share: the uv
  managed Python, download cache and the clone-wide lock;
- each worktree's own ``.runtime/`` holds its virtual environment, bytecode, ruff cache and
  temporary files.

The interpreter pinned in ``.python-version`` also stays in the project. No Python links
are installed into the user bin directory, and no Windows registry entries are created.
``uv.lock`` decides everything installed into the environment.

The acceptance check takes an exclusive lock shared by every worktree of the clone, and
``pytest`` takes a shared lock on the same file, so the check that serves as merge evidence
never runs alongside another test run started through this script.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
import errno
import os
from pathlib import Path
import shutil
import signal
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ".runtime"
CHECK_ALL = "skills/development/scirel-acceptance/scripts/check_all.py"
SYNC = ["uv", "sync", "--locked", "--group", "test"]
LOCK_NAME = "acceptance.lock"
EXCLUSIVE_RECORD = "acceptance-exclusive"
EXCLUSIVE_MARKER = "SCIREL_EXCLUSIVE_TOKEN"
STOP_TIMEOUT = 5


class LockBusy(RuntimeError):
    """Raised when another test run or acceptance check holds the clone-wide lock."""


def stop_command(process: subprocess.Popen, signum: int) -> None:
    """Stop and reap our child before the caller can release the clone lock."""
    permission_denied = False
    permission_reported = False
    group_absent = False

    def denied(operation: str, error: PermissionError) -> None:
        nonlocal permission_denied, permission_reported
        if not permission_reported:
            print(
                f"STOPPING  permission denied while {operation} for command {process.pid}: "
                f"{error}; "
                "clone lock retained; waiting for permission recovery or confirmed exit",
                file=sys.stderr,
            )
            permission_reported = True
        permission_denied = True

    def send(forced: bool = False) -> bool:
        nonlocal group_absent
        if permission_denied:
            return False
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL if forced else signum)
            elif forced:
                process.kill()
            else:
                process.terminate()
        except ProcessLookupError:
            group_absent = True
        except PermissionError as error:
            denied("sending a signal", error)
        else:
            return True
        return False

    send()
    if os.name == "posix":

        def group_exists() -> bool:
            nonlocal group_absent, permission_denied
            if group_absent:
                return False
            process.poll()  # Reap the launcher too; a zombie keeps its group alive.
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                group_absent = True
                return False
            except PermissionError as error:
                # Keep the lock and defer signals until a later probe succeeds.
                denied("probing the process group", error)
            else:
                permission_denied = False
            return True

        deadline = time.monotonic() + STOP_TIMEOUT
        forced = False
        while group_exists():
            if not forced and time.monotonic() >= deadline:
                forced = send(forced=True)
                if forced:
                    print(
                        "STOPPING  waiting for process group exit; clone lock retained",
                        file=sys.stderr,
                    )
            time.sleep(0.02)
    else:
        try:
            process.wait(timeout=STOP_TIMEOUT)
        except subprocess.TimeoutExpired:
            send(forced=True)
    process.wait()


def python_version() -> str:
    return (ROOT / ".python-version").read_text(encoding="utf-8").strip()


def shared_root(root: Path | None = None) -> Path:
    """Return the main checkout that every worktree of this clone shares."""
    done = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=ROOT if root is None else root,
        capture_output=True,
        text=True,
        check=False,
    )
    common = Path(done.stdout.strip()) if done.returncode == 0 and done.stdout.strip() else None
    if common is not None and common.name == ".git" and common.parent.is_dir():
        return common.parent.resolve()
    if root is not None:
        raise LockBusy("exclusive verification requires the candidate's real git clone")
    return ROOT


def require_exclusive(root: Path, expected: str | None = None) -> str:
    """Verify the current credential against this clone and its live kernel EX lock.

    An independent shared-lock probe succeeds beside another shared lock on POSIX;
    only an exclusive holder can block it. Windows serializes the same single byte.
    No lock is inherited, reacquired or bypassed by this verification.
    """
    token = os.environ.get(EXCLUSIVE_MARKER)
    locks = shared_root(root) / RUNTIME / "locks"
    try:
        if not token or (expected is not None and token != expected):
            raise ValueError("missing or changed marker")
        if (locks / EXCLUSIVE_RECORD).read_text(encoding="ascii") != token:
            raise ValueError("stale marker or wrong clone")
        with (locks / LOCK_NAME).open("r+b") as probe:
            if sys.platform == "win32":
                import msvcrt

                try:
                    msvcrt.locking(probe.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as error:
                    if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                        raise
                else:
                    msvcrt.locking(probe.fileno(), msvcrt.LK_UNLCK, 1)
                    raise ValueError("kernel lock is free")
            else:
                import fcntl

                try:
                    fcntl.flock(probe.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                except BlockingIOError:
                    pass
                else:
                    fcntl.flock(probe.fileno(), fcntl.LOCK_UN)
                    raise ValueError("kernel lock is free or only shared")
        # Reject retirement/replacement during the probe as well.
        if (locks / EXCLUSIVE_RECORD).read_text(encoding="ascii") != token:
            raise ValueError("credential changed during verification")
    except (OSError, ValueError) as error:
        raise LockBusy(
            f"valid clone exclusive lock required ({error}); "
            "start in the candidate clone with dev.py run --exclusive <command>"
        ) from error
    return token


@contextmanager
def exclusive_credential() -> Iterator[str]:
    """Publish only while the caller holds acceptance_lock(EX), then retire before unlock."""
    record = runtime_paths()["locks"] / EXCLUSIVE_RECORD
    token = secrets.token_hex(32)
    try:
        record.write_text(token, encoding="ascii")
        yield token
    finally:
        record.unlink(missing_ok=True)


def runtime_paths() -> dict[str, Path]:
    local = ROOT / RUNTIME
    shared = shared_root() / RUNTIME
    return {
        "python": shared / "python",
        "uv-cache": shared / "uv-cache",
        "locks": shared / "locks",
        "venv": local / "venv",
        "pycache": local / "pycache",
        "ruff-cache": local / "ruff-cache",
        "cache": local / "cache",
        "tmp": local / "tmp",
    }


def environment() -> dict[str, str]:
    paths = runtime_paths()
    env = os.environ.copy()
    for key in (
        "VIRTUAL_ENV",
        "CONDA_PREFIX",
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTEST_ADDOPTS",
        "UV_PROJECT",
        "UV_WORKING_DIR",
        "UV_PYTHON_INSTALL_DIR",
        EXCLUSIVE_MARKER,
    ):
        env.pop(key, None)
    temporary = str(paths["tmp"])
    env.update(
        {
            "UV_PYTHON": python_version(),
            "UV_MANAGED_PYTHON": "1",
            "UV_PYTHON_INSTALL_DIR": str(paths["python"]),
            "UV_PYTHON_INSTALL_BIN": "0",
            "UV_PYTHON_INSTALL_REGISTRY": "0",
            "UV_NO_CONFIG": "1",
            "UV_CACHE_DIR": str(paths["uv-cache"]),
            "UV_PROJECT_ENVIRONMENT": str(paths["venv"]),
            "UV_LINK_MODE": "copy",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": str(paths["pycache"]),
            "RUFF_CACHE_DIR": str(paths["ruff-cache"]),
            "XDG_CACHE_HOME": str(paths["cache"]),
            "MPLCONFIGDIR": str(paths["cache"] / "matplotlib"),
            "PIP_CACHE_DIR": str(paths["cache"] / "pip"),
            "TMPDIR": temporary,
            "TEMP": temporary,
            "TMP": temporary,
        }
    )
    return env


def ensure_runtime() -> None:
    for path in runtime_paths().values():
        if path.name != "venv":
            path.mkdir(parents=True, exist_ok=True)


def run(command: list[str], *, exclusive_token: str | None = None) -> int:
    process = None
    handlers = {}
    interrupted = None

    def interrupt(signum, _frame):
        nonlocal interrupted
        # Only record the request: raising here can interrupt Popen before its
        # child is assigned, or interrupt cleanup on a second signal.
        if interrupted is None:
            interrupted = signum

    try:
        for name in ("SIGINT", "SIGTERM", "SIGHUP"):
            if hasattr(signal, name):
                signum = getattr(signal, name)
                handlers[signum] = signal.signal(signum, interrupt)
        env = environment()
        if exclusive_token is not None:
            env[EXCLUSIVE_MARKER] = exclusive_token
        process = subprocess.Popen(command, cwd=ROOT, env=env, start_new_session=os.name == "posix")
        while interrupted is None:
            try:
                code = process.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                continue
            if interrupted is None:
                if exclusive_token is not None:
                    # A successful launcher may leave children behind. Keep the credential
                    # and lock until our existing supervisor has reaped the whole group.
                    stop_command(process, signal.SIGTERM)
                if interrupted is None:
                    return code
        stop_command(process, interrupted)
        print(f"INTERRUPTED  signal {interrupted}; owned command stopped", file=sys.stderr)
        return 128 + interrupted
    except FileNotFoundError:
        print(f"ERROR: {command[0]} is not on PATH.", file=sys.stderr)
        return 127
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)


def prepare() -> int:
    if shutil.which("uv") is None:
        print("ERROR: uv is not on PATH; install uv first (see CONTRIBUTING.md).", file=sys.stderr)
        return 127
    ensure_runtime()
    installed = run(["uv", "python", "install", "--no-bin", "--no-registry", python_version()])
    if installed:
        return installed
    return run(SYNC)


@contextmanager
def acceptance_lock(*, exclusive: bool) -> Iterator[None]:
    """Hold the clone-wide lock: exclusive for the check, shared for ordinary test runs."""
    path = runtime_paths()["locks"] / LOCK_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if sys.platform == "win32":
            # The Windows standard library has no shared file lock. Serialize local
            # runs there; never silently run an acceptance check without a lock.
            import msvcrt

            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise LockBusy("another test run or check holds the clone lock") from error
            try:
                # A previous owner may have died without retiring its credential.
                (path.parent / EXCLUSIVE_RECORD).unlink(missing_ok=True)
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            try:
                fcntl.flock(stream.fileno(), mode | fcntl.LOCK_NB)
            except BlockingIOError:
                what = (
                    "another test run or acceptance check" if exclusive else "an acceptance check"
                )
                raise LockBusy(f"{what} is running in this clone; wait for it to finish") from None
            try:
                (path.parent / EXCLUSIVE_RECORD).unlink(missing_ok=True)
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def run_locked(command: list[str] | None, *, exclusive: bool) -> int:
    try:
        with acceptance_lock(exclusive=exclusive):
            prepared = prepare()
            if prepared:
                return prepared
            with exclusive_credential() if exclusive else nullcontext(None) as token:
                if exclusive:
                    print("EXCLUSIVE  no other test run or check holds the clone lock", flush=True)
                return run(command, exclusive_token=token) if command is not None else 0
    except LockBusy as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 75


def check() -> int:
    return run_locked(["uv", "run", "--frozen", "python", "-B", CHECK_ALL], exclusive=True)


def pytest(arguments: list[str]) -> int:
    command = ["uv", "run", "--frozen", "python", "-B", "-m", "pytest", *(arguments or ["-q"])]
    return run_locked(command, exclusive=False)


def run_command(arguments: list[str], *, exclusive: bool = False) -> int:
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    if not arguments:
        print(
            "ERROR: run needs a command, for example `run python -B scripts/x.py`.", file=sys.stderr
        )
        return 2
    return run_locked(["uv", "run", "--frozen", *arguments], exclusive=exclusive)


def doctor() -> int:
    print(f"checkout   {ROOT}")
    print(f"python     {python_version()} (project-local uv installation)")
    ensure_runtime()
    for name, path in runtime_paths().items():
        print(f"{name:<10} {path}")
    uv = shutil.which("uv")
    if uv is None:
        print("uv         MISSING: install uv first (see CONTRIBUTING.md)")
        return 127
    print(f"uv         {uv}")
    return run(["uv", "--version"])


def clean(*, shared: bool) -> int:
    paths = runtime_paths()
    # Keep logs and the shared interpreter: sibling worktrees can still use them.
    targets = [paths[name] for name in ("venv", "pycache", "ruff-cache", "cache", "tmp")]
    if shared:
        targets.append(paths["uv-cache"])
    try:
        with acceptance_lock(exclusive=True):
            for path in targets:
                if path.is_symlink():
                    print(f"ERROR: refusing to remove symlink {path}", file=sys.stderr)
                    return 1
                if path.exists():
                    shutil.rmtree(path)
                    print(f"removed    {path}")
        return 0
    except (LockBusy, OSError) as error:
        print(f"ERROR: cleanup failed: {error}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    # pytest owns its flags, including leading -q/-k; argparse must not consume them.
    if arguments[:1] == ["pytest"]:
        rest = arguments[1:]
        return pytest(rest[1:] if rest[:1] == ["--"] else rest)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="show uv, the interpreter and every runtime directory")
    subparsers.add_parser("prepare", help="install the pinned Python and sync the locked env")
    subparsers.add_parser("check", help="run the complete acceptance check (exclusive)")
    pytest_parser = subparsers.add_parser("pytest", help="run pytest with optional arguments")
    pytest_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    run_parser = subparsers.add_parser("run", help="run one command in the project environment")
    run_parser.add_argument("--exclusive", action="store_true", help="hold the clone EX lock")
    run_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    clean_parser = subparsers.add_parser(
        "clean", help="remove this worktree's environment and caches; retain logs"
    )
    clean_parser.add_argument(
        "--shared",
        action="store_true",
        help="also remove the shared uv cache; retain the interpreter",
    )

    args = parser.parse_args(arguments)
    if args.command == "doctor":
        return doctor()
    if args.command == "prepare":
        return run_locked(None, exclusive=False)
    if args.command == "check":
        return check()
    if args.command == "pytest":
        return pytest(args.arguments)
    if args.command == "run":
        return run_command(args.arguments, exclusive=args.exclusive)
    if args.command == "clean":
        return clean(shared=args.shared)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

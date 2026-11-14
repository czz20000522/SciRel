"""The development wrapper keeps every run artifact inside the project directory."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dev.py"
WRITABLE_KEYS = (
    "UV_PYTHON_INSTALL_DIR",
    "UV_CACHE_DIR",
    "UV_PROJECT_ENVIRONMENT",
    "PYTHONPYCACHEPREFIX",
    "RUFF_CACHE_DIR",
    "XDG_CACHE_HOME",
    "MPLCONFIGDIR",
    "PIP_CACHE_DIR",
    "TMPDIR",
    "TEMP",
    "TMP",
)


def _load():
    spec = importlib.util.spec_from_file_location("scirel_dev", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git(cwd, *arguments):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.run(
        ["git", *arguments], cwd=cwd, env=env, check=True, capture_output=True, text=True
    )


def _repository_with_worktree(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "SciRel test")
    _git(repository, "config", "user.email", "scirel-test@example.invalid")
    (repository / ".python-version").write_text("3.14.7\n", encoding="utf-8")
    _git(repository, "add", ".python-version")
    _git(repository, "commit", "-m", "fixture")
    worktree = repository / ".worktrees" / "topic"
    _git(repository, "worktree", "add", "-b", "agent/1-topic", str(worktree), "main")
    return repository.resolve(), worktree.resolve()


def test_every_writable_location_is_inside_the_project_runtime_directory():
    module = _load()
    env = module.environment()
    project = module.shared_root()
    for key in WRITABLE_KEYS:
        path = Path(env[key])
        assert path.is_relative_to(project), key
        assert module.RUNTIME in path.relative_to(project).parts, key


def test_the_interpreter_stays_in_the_project_without_user_bin_links(monkeypatch):
    module = _load()
    monkeypatch.setenv("UV_PYTHON_INSTALL_DIR", "/elsewhere/python")
    env = module.environment()
    assert env["UV_PYTHON"] == (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    assert env["UV_MANAGED_PYTHON"] == "1"
    assert Path(env["UV_PYTHON_INSTALL_DIR"]) == module.shared_root() / ".runtime" / "python"
    assert env["UV_PYTHON_INSTALL_BIN"] == "0"
    assert env["UV_PYTHON_INSTALL_REGISTRY"] == "0"


def test_an_activated_foreign_environment_does_not_leak_in(monkeypatch):
    module = _load()
    monkeypatch.setenv("VIRTUAL_ENV", "/elsewhere/venv")
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", "/elsewhere/venv")
    env = module.environment()
    assert "VIRTUAL_ENV" not in env
    assert Path(env["UV_PROJECT_ENVIRONMENT"]).is_relative_to(module.ROOT)


def test_host_pytest_filters_do_not_reduce_the_full_acceptance_suite(monkeypatch):
    module = _load()
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k test_one_item_only")
    assert "PYTEST_ADDOPTS" not in module.environment()


def test_the_runtime_directory_is_ignored_by_git():
    done = subprocess.run(
        ["git", "check-ignore", "-q", ".runtime/venv/marker"], cwd=ROOT, check=False
    )
    assert done.returncode == 0


def test_a_linked_worktree_shares_the_main_checkouts_cache_and_keeps_its_own_venv(
    tmp_path, monkeypatch
):
    repository, worktree = _repository_with_worktree(tmp_path)
    module = _load()
    monkeypatch.setattr(module, "ROOT", worktree)
    assert module.shared_root() == repository
    paths = module.runtime_paths()
    assert paths["uv-cache"] == repository / ".runtime" / "uv-cache"
    assert paths["locks"] == repository / ".runtime" / "locks"
    assert paths["venv"] == worktree / ".runtime" / "venv"
    assert paths["tmp"] == worktree / ".runtime" / "tmp"


@pytest.mark.skipif(sys.platform == "win32", reason="the clone lock uses POSIX flock")
def test_the_check_and_test_runs_exclude_each_other(tmp_path, monkeypatch):
    repository, _ = _repository_with_worktree(tmp_path)
    module = _load()
    monkeypatch.setattr(module, "ROOT", repository)
    with module.acceptance_lock(exclusive=False), module.acceptance_lock(exclusive=False):
        with pytest.raises(module.LockBusy, match="another test run"):
            with module.acceptance_lock(exclusive=True):
                pass
    with module.acceptance_lock(exclusive=True):
        with pytest.raises(module.LockBusy, match="an acceptance check"):
            with module.acceptance_lock(exclusive=False):
                pass
    with module.acceptance_lock(exclusive=True):
        pass


@pytest.mark.skipif(sys.platform == "win32", reason="the clone lock uses POSIX flock")
def test_a_busy_clone_refuses_the_check_before_preparing_anything(tmp_path, monkeypatch, capsys):
    repository, _ = _repository_with_worktree(tmp_path)
    module = _load()
    monkeypatch.setattr(module, "ROOT", repository)
    monkeypatch.setattr(module, "prepare", lambda: pytest.fail("must not prepare"))
    with module.acceptance_lock(exclusive=False):
        assert module.check() == 75
    assert "is running in this clone" in capsys.readouterr().err


@pytest.mark.skipif(sys.platform == "win32", reason="the clone lock uses POSIX flock")
def test_prepare_cannot_change_the_environment_of_a_running_check(tmp_path, monkeypatch):
    repository, _ = _repository_with_worktree(tmp_path)
    module = _load()
    monkeypatch.setattr(module, "ROOT", repository)
    monkeypatch.setattr(module, "prepare", lambda: pytest.fail("must not resync a running check"))
    with module.acceptance_lock(exclusive=True):
        assert module.main(["prepare"]) == 75


def test_the_cross_device_workflow_is_manual_and_runs_the_same_check():
    workflow = (ROOT / ".github" / "workflows" / "check.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "  push:" not in workflow
    assert "python3 scripts/dev.py check" in workflow


@pytest.mark.parametrize("flags", [["-q", "-k", "example"], ["--", "-q", "tests/tooling"]])
def test_pytest_receives_its_flags_without_argparse_consuming_them(monkeypatch, flags):
    module = _load()
    seen = []
    monkeypatch.setattr(module, "pytest", lambda args: seen.append(args) or 0)
    assert module.main(["pytest", *flags]) == 0
    assert seen == [flags[1:] if flags[:1] == ["--"] else flags]


@pytest.mark.skipif(os.name != "posix", reason="POSIX termination and process groups")
@pytest.mark.parametrize(
    "probe_denial,send_denial,reap_launcher,exit_after,expected_signals",
    [
        pytest.param("always", None, None, 1, ["SIGINT"], id="probe-once"),
        pytest.param("always", None, None, 3, ["SIGINT"], id="probe-repeated"),
        pytest.param("always", None, None, 8, ["SIGINT"], id="probe-past-deadline"),
        pytest.param("once", None, None, 8, ["SIGINT", "SIGKILL"], id="probe-recovers"),
        pytest.param(
            "until-after-deadline", None, None, 8, ["SIGINT", "SIGKILL"], id="probe-recovers-late"
        ),
        pytest.param("never", "SIGINT", None, 8, ["SIGINT", "SIGKILL"], id="initial-send"),
        pytest.param("always", "SIGINT", None, 8, ["SIGINT"], id="send-and-probe"),
        pytest.param(
            "never", "SIGKILL", None, 8, ["SIGINT", "SIGKILL", "SIGKILL"], id="forced-send"
        ),
        pytest.param(
            "after-force",
            "SIGKILL",
            None,
            8,
            ["SIGINT", "SIGKILL"],
            id="forced-send-and-probe",
        ),
        pytest.param("after-force", None, None, 8, ["SIGINT", "SIGKILL"], id="probe-after-force"),
        pytest.param("never", None, "probe", 8, ["SIGINT", "SIGKILL"], id="launcher-reaped"),
        pytest.param("always", None, "probe", 8, ["SIGINT"], id="reaped-and-denied"),
        pytest.param(
            "never", None, "before-send", 8, ["SIGINT", "SIGKILL"], id="launcher-already-reaped"
        ),
        pytest.param("never", None, None, 8, ["SIGINT", "SIGKILL"], id="ordinary-force-once"),
    ],
)
def test_permission_errors_keep_the_lock_until_descendants_stop(
    tmp_path,
    monkeypatch,
    capsys,
    probe_denial,
    send_denial,
    reap_launcher,
    exit_after,
    expected_signals,
):
    """Inject permission errors; this does not reproduce the macOS permission cause."""
    module = _load()
    send_denial = getattr(signal, send_denial) if send_denial is not None else None
    expected_signals = [getattr(signal, name) for name in expected_signals]
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "shared_root", lambda: tmp_path)
    monkeypatch.setattr(module, "prepare", lambda: 0)
    monkeypatch.setattr(module, "environment", lambda: {})
    handlers = {}
    sent = []
    sleeps = 0
    probes = 0
    descendant_alive = True
    reaped = False
    permission_denied = False
    send_denied = False

    class Command:
        pid = 12345
        started = False
        returncode = None

        def wait(self, timeout=None):
            nonlocal reaped
            if not self.started:
                self.started = True
                handlers[signal.SIGINT](signal.SIGINT, None)
                if reap_launcher == "before-send":
                    self.returncode = 0
                    return 0
                raise subprocess.TimeoutExpired("owned command", timeout)
            assert not descendant_alive, "cleanup returned while a descendant was alive"
            self.returncode = 0
            reaped = True
            return 0

        def poll(self):
            if reap_launcher == "probe" or not descendant_alive:
                self.returncode = 0
            return self.returncode

    command = Command()

    def install_handler(signum, handler):
        previous = handlers.get(signum, signal.SIG_DFL)
        handlers[signum] = handler
        return previous

    def assert_locked():
        with pytest.raises(module.LockBusy):
            with module.acceptance_lock(exclusive=True):
                pass

    def killpg(pid, signum):
        nonlocal probes, permission_denied, send_denied
        assert pid == command.pid, "must only address the owned process group"
        assert_locked()
        if signum:
            assert not permission_denied, "must not send signals before a probe confirms recovery"
            if signum == signal.SIGKILL:
                assert sleeps >= module.STOP_TIMEOUT, "must retain the original stop deadline"
            sent.append((pid, signum))
            if signum == send_denial and not send_denied:
                send_denied = True
                permission_denied = True
                raise PermissionError(1, "injected process-group send denial")
            return
        probes += 1
        if not descendant_alive:
            raise ProcessLookupError(3, "the simulated owned group has now exited")
        if (
            probe_denial == "always"
            or (probe_denial == "once" and probes == 1)
            or (probe_denial == "until-after-deadline" and sleeps < module.STOP_TIMEOUT + 1)
            or (probe_denial == "after-force" and (pid, signal.SIGKILL) in sent)
        ):
            permission_denied = True
            raise PermissionError(1, "injected process-group probe denial")
        permission_denied = False

    def sleep(_seconds):
        nonlocal sleeps, descendant_alive
        sleeps += 1
        assert sleeps <= exit_after, "cleanup did not finish after confirmed group exit"
        assert_locked()
        # A second interruption must neither cancel cleanup nor change its result.
        handlers[signal.SIGTERM](signal.SIGTERM, None)
        if sleeps == exit_after:
            descendant_alive = False

    monkeypatch.setattr(module.signal, "signal", install_handler)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: command)
    monkeypatch.setattr(module.os, "killpg", killpg)
    monkeypatch.setattr(module.time, "monotonic", lambda: float(sleeps))
    monkeypatch.setattr(module.time, "sleep", sleep)

    assert module.run_locked(["owned command"], exclusive=True) == 128 + signal.SIGINT
    assert reaped
    assert not descendant_alive
    assert sent == [(command.pid, signum) for signum in expected_signals]
    captured = capsys.readouterr()
    assert "ALL GREEN" not in captured.out + captured.err
    assert "INTERRUPTED" in captured.err
    if probe_denial != "never" or send_denial is not None:
        assert captured.err.count("STOPPING  permission denied") == 1
        assert "clone lock retained" in captured.err
    else:
        assert "permission denied" not in captured.err
    with module.acceptance_lock(exclusive=True):
        pass


@pytest.mark.skipif(os.name != "posix", reason="POSIX termination and process groups")
def test_a_missing_owned_group_is_not_probed_again(monkeypatch):
    module = _load()

    class Command:
        pid = 12345
        returncode = None
        reaped = False

        def poll(self):
            pytest.fail("must not probe a group id after confirmed absence; it can be reused")

        def wait(self):
            self.reaped = True
            return 0

    command = Command()

    def killpg(pid, signum):
        assert (pid, signum) == (command.pid, signal.SIGINT)
        raise ProcessLookupError(3, "the owned group has exited")

    monkeypatch.setattr(module.os, "killpg", killpg)
    module.stop_command(command, signal.SIGINT)
    assert command.reaped


def _wait_for_file(path: Path, timeout: float = 5) -> None:
    deadline = time.monotonic() + timeout
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert path.exists(), f"the owned subprocess did not reach {path.name}"


@pytest.mark.skipif(os.name != "posix", reason="POSIX termination and process groups")
@pytest.mark.parametrize("early_exit", [False, True], ids=["leader-alive", "leader-exited"])
@pytest.mark.parametrize("recovery_delay", [0.1, 0.8], ids=["before-deadline", "after-deadline"])
def test_recovered_permissions_force_persistent_descendants_to_stop(
    tmp_path, early_exit, recovery_delay
):
    """Use real descendants with injected probe denial, not a claim about its macOS cause."""
    module = _load()
    module.ROOT = tmp_path
    module.shared_root = lambda: tmp_path
    ready, leader, denied, recovered, forced = [
        tmp_path / name for name in ("ready", "leader", "denied", "recovered", "forced")
    ]
    grandchild = """
import os, signal, sys, time
from pathlib import Path
for name in ('SIGINT', 'SIGTERM', 'SIGHUP'):
    signal.signal(getattr(signal, name), signal.SIG_IGN)
Path(sys.argv[1]).write_text(str(os.getpid()))
while True:
    time.sleep(0.02)
"""
    child = """
import signal, subprocess, sys
signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(0) if sys.argv[1] == 'True' else None)
process = subprocess.Popen([sys.executable, '-c', sys.argv[2], sys.argv[3]])
raise SystemExit(process.wait())
"""
    wrapper_code = """
import importlib.util, os, signal, sys, time
from pathlib import Path
spec = importlib.util.spec_from_file_location('test_supervisor', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ROOT = Path(sys.argv[2])
module.shared_root = lambda: module.ROOT
module.environment = lambda: dict(os.environ)
module.prepare = lambda: 0
module.STOP_TIMEOUT = 0.4
recovery_delay = float(sys.argv[3])
original_popen, original_killpg = module.subprocess.Popen, module.os.killpg
command = None
denied_at = None
interrupted_at = None
def record_popen(*args, **kwargs):
    global command
    command = original_popen(*args, **kwargs)
    (module.ROOT / 'leader').write_text(str(command.pid))
    return command
def killpg(pid, signum):
    global denied_at, interrupted_at
    assert pid == command.pid
    try:
        with module.acceptance_lock(exclusive=True):
            raise AssertionError('clone lock released while descendants are alive')
    except module.LockBusy:
        pass
    if signum == signal.SIGINT:
        interrupted_at = time.monotonic()
    if signum == 0:
        if denied_at is None:
            denied_at = time.monotonic()
            (module.ROOT / 'denied').touch()
        if (
            not (module.ROOT / 'allow-recovery').exists()
            or time.monotonic() - denied_at < recovery_delay
        ):
            raise PermissionError(1, 'injected temporary process-group probe denial')
        (module.ROOT / 'recovered').touch()
    if signum == signal.SIGKILL:
        assert time.monotonic() - interrupted_at >= module.STOP_TIMEOUT
        assert (module.ROOT / 'recovered').exists()
        (module.ROOT / 'forced').write_text(str(command.poll()))
    return original_killpg(pid, signum)
module.subprocess.Popen, module.os.killpg = record_popen, killpg
raise SystemExit(module.run_locked([sys.executable, '-c', *sys.argv[4:]], exclusive=True))
"""

    def wait_until_absent(pid, *, group=False):
        deadline = time.monotonic() + 5
        while True:
            try:
                if group:
                    os.killpg(pid, 0)
                else:
                    os.kill(pid, 0)
            except ProcessLookupError:
                return
            assert time.monotonic() < deadline, (
                f"owned {'group' if group else 'process'} {pid} survived"
            )
            time.sleep(0.02)

    with (tmp_path / "supervisor.log").open("w") as output:
        wrapper = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-c",
                wrapper_code,
                str(SCRIPT),
                str(tmp_path),
                str(recovery_delay),
                child,
                str(early_exit),
                grandchild,
                str(ready),
            ],
            start_new_session=True,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        group_absent = False
        try:
            _wait_for_file(ready)
            _wait_for_file(leader)
            wrapper.send_signal(signal.SIGINT)
            _wait_for_file(denied)
            with pytest.raises(module.LockBusy):
                with module.acceptance_lock(exclusive=True):
                    pass
            wrapper.send_signal(signal.SIGTERM)
            (tmp_path / "allow-recovery").touch()
            try:
                code = wrapper.wait(timeout=4)
            except subprocess.TimeoutExpired:
                pytest.fail("permission recovered but the persistent descendant was never killed")
            assert code == 128 + signal.SIGINT
            assert recovered.exists()
            assert forced.exists(), "a persistent descendant requires timeout escalation"
            assert forced.read_text() == ("0" if early_exit else "None")
            wait_until_absent(int(leader.read_text()), group=True)
            group_absent = True
            wait_until_absent(int(ready.read_text()))
            with module.acceptance_lock(exclusive=True):
                pass
        finally:
            if leader.exists() and not group_absent:
                try:
                    os.killpg(int(leader.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    group_absent = True
            try:
                wrapper.wait(timeout=5)
            except subprocess.TimeoutExpired:
                wrapper.kill()
                wrapper.wait(timeout=5)
            if leader.exists() and not group_absent:
                wait_until_absent(int(leader.read_text()), group=True)
            if ready.exists():
                wait_until_absent(int(ready.read_text()))
            print(
                f"CLEANUP wrapper={wrapper.pid} exit={wrapper.returncode}; "
                f"group={leader.read_text() if leader.exists() else 'not-started'} absent; "
                f"descendant={ready.read_text() if ready.exists() else 'not-started'} absent"
            )


@pytest.mark.skipif(os.name != "posix", reason="POSIX termination and process groups")
@pytest.mark.parametrize(
    "signal_name,early_exit,during_spawn",
    [
        ("SIGTERM", False, False),
        ("SIGINT", False, False),
        ("SIGHUP", False, False),
        ("SIGTERM", True, False),
        ("SIGTERM", False, True),
    ],
)
def test_termination_stops_descendants_before_releasing_the_clone_lock(
    tmp_path, monkeypatch, signal_name, early_exit, during_spawn
):
    repository, _ = _repository_with_worktree(tmp_path)
    module = _load()
    monkeypatch.setattr(module, "ROOT", repository)
    ready, stopping, release, stopped = [
        tmp_path / name for name in ("ready", "stopping", "release", "stopped")
    ]
    grandchild = """
from pathlib import Path
import os, signal, sys, time
ready, stopping, release, stopped = map(Path, sys.argv[1:])
def stop(signum, frame):
    stopping.touch()
    while not release.exists():
        time.sleep(0.02)
    stopped.touch()
    raise SystemExit(0)
for name in ('SIGTERM', 'SIGINT', 'SIGHUP'):
    signal.signal(getattr(signal, name), stop)
ready.write_text(str(os.getpid()))
while True:
    time.sleep(0.02)
"""
    child = """
import signal, subprocess, sys
process = subprocess.Popen([sys.executable, '-c', sys.argv[1], *sys.argv[2:]])
for name in ('SIGTERM', 'SIGINT', 'SIGHUP'):
    signal.signal(getattr(signal, name), lambda signum, frame: None)
raise SystemExit(process.wait())
"""
    if early_exit:
        child = child.replace("lambda signum, frame: None", "lambda signum, frame: sys.exit(0)")
    wrapper_code = """
import importlib.util, os, signal, sys, time
from pathlib import Path
spec = importlib.util.spec_from_file_location('test_supervisor', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.ROOT = Path(sys.argv[2])
module.prepare = lambda: 0
if sys.argv[3] == 'True':
    module.shared_root = lambda: module.ROOT
    module.environment = lambda: dict(os.environ)
    original_popen = module.subprocess.Popen
    def interrupt_during_spawn(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        while not Path(sys.argv[-4]).exists():
            time.sleep(0.02)
        os.kill(os.getpid(), signal.SIGTERM)
        return child
    module.subprocess.Popen = interrupt_during_spawn
raise SystemExit(module.run_locked([sys.executable, '-c', *sys.argv[4:]], exclusive=True))
"""
    wrapper = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-c",
            wrapper_code,
            str(SCRIPT),
            str(repository),
            str(during_spawn),
            child,
            grandchild,
            *(str(path) for path in (ready, stopping, release, stopped)),
        ],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_file(ready)
        signum = getattr(signal, signal_name)
        if not during_spawn:
            wrapper.send_signal(signum)
        _wait_for_file(stopping)
        wrapper.send_signal(signal.SIGINT if signum != signal.SIGINT else signal.SIGTERM)
        assert wrapper.poll() is None, "the wrapper released its lock while a descendant runs"
        with pytest.raises(module.LockBusy):
            with module.acceptance_lock(exclusive=True):
                pass
        release.touch()
        assert wrapper.wait(timeout=5) == 128 + signum
        assert stopped.exists(), "the descendant must stop before the clone lock is released"
        with module.acceptance_lock(exclusive=True):
            pass
    finally:
        release.touch()
        if ready.exists() and not stopped.exists():
            try:
                os.kill(int(ready.read_text()), signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            os.killpg(wrapper.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        wrapper.wait(timeout=5)

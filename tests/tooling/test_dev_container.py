"""The development wrapper keeps one deterministic, portable container contract."""

from __future__ import annotations

import contextlib
import errno
import importlib.util
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dev_container.py"


def _load():
    spec = importlib.util.spec_from_file_location("dev_container", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_project_name_is_stable_and_checkout_scoped():
    module = _load()
    first = module.project_name()
    assert first == module.project_name()
    assert first.startswith("scirel-dev-")
    assert len(first) == len("scirel-dev-") + 10


def test_uv_cache_is_shared_but_virtualenv_is_checkout_scoped(tmp_path, monkeypatch):
    module = _load()
    roots = [tmp_path / "worktree-a", tmp_path / "worktree-b"]
    environments = []
    for root in roots:
        root.mkdir()
        (root / ".python-version").write_text("3.14.7\n", encoding="utf-8")
        monkeypatch.setattr(module, "ROOT", root)
        environments.append(module.environment())
    assert environments[0]["SCIReL_UV_CACHE_VOLUME"] == environments[1]["SCIReL_UV_CACHE_VOLUME"]
    assert environments[0]["SCIReL_VENV_VOLUME"] != environments[1]["SCIReL_VENV_VOLUME"]


def test_external_uv_cache_volume_is_created(monkeypatch):
    module = _load()
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.ensure_uv_cache_volume() == 0
    assert ["docker", "volume", "create", module.uv_cache_volume()] in [
        command for command, _ in calls
    ]


def test_clean_preserves_the_shared_cache_unless_requested(monkeypatch):
    module = _load()
    calls = []
    monkeypatch.setattr(module, "run", lambda command: calls.append(command) or 0)
    monkeypatch.setattr(module, "container_project_lock", contextlib.nullcontext)
    assert module.clean() == 0
    assert not any(module.uv_cache_volume() in part for command in calls for part in command)
    calls.clear()
    assert module.clean(remove_cache=True, remove_image=True) == 0
    assert any(module.uv_cache_volume() in part for command in calls for part in command)
    assert any("--rmi" in command for command in calls)


def test_pre_push_reuses_only_an_exact_head_tree_receipt(tmp_path, monkeypatch, capsys):
    module = _load()
    repository = tmp_path / "repository"
    repository.mkdir()
    env = {
        key: value for key, value in os.environ.items() if key not in {"GIT_DIR", "GIT_WORK_TREE"}
    }

    def git(*arguments):
        return subprocess.run(
            ["git", *arguments],
            cwd=repository,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "main")
    git("config", "user.name", "SciRel test")
    git("config", "user.email", "scirel-test@example.invalid")
    readme = repository / "README.md"
    readme.write_text("first\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "first")
    monkeypatch.setattr(module, "ROOT", repository)

    runs = []
    monkeypatch.setattr(module, "run_check", lambda: runs.append("check") or 17)
    assert module.pre_push() == 17
    assert runs == ["check"]

    readme.write_text("second\n", encoding="utf-8")
    git("add", "README.md")
    assert module.record_check_receipt()
    valid, reason = module.check_receipt_status()
    assert not valid
    assert "another Git tree" in reason

    git("commit", "-m", "second")
    valid, reason = module.check_receipt_status()
    assert valid
    assert "already passed" in reason
    runs.clear()
    assert module.pre_push() == 0
    assert runs == []

    readme.write_text("third\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "third")
    runs.clear()
    assert module.pre_push() == 17
    assert runs == ["check"]
    capsys.readouterr()


def test_check_receipt_rejects_another_architecture(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    repository.mkdir()
    env = {
        key: value for key, value in os.environ.items() if key not in {"GIT_DIR", "GIT_WORK_TREE"}
    }

    def git(*arguments):
        return subprocess.run(
            ["git", *arguments],
            cwd=repository,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "main")
    git("config", "user.name", "SciRel test")
    git("config", "user.email", "scirel-test@example.invalid")
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "fixture")
    monkeypatch.setattr(module, "ROOT", repository)
    assert module.record_check_receipt()
    path = module.check_receipt_path()
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["architecture"] = "another-architecture"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    valid, reason = module.check_receipt_status()
    assert not valid
    assert "architecture" in reason


def test_loopback_proxy_is_reachable_from_the_container(monkeypatch):
    module = _load()
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:7890")
    monkeypatch.setenv("HTTPS_PROXY", "http://localhost:7890")
    env = module.environment()
    assert env["SCIReL_HTTP_PROXY"] == "http://host.docker.internal:7890"
    assert env["SCIReL_HTTPS_PROXY"] == "http://host.docker.internal:7890"


def test_container_runs_are_serialized_and_clean_their_project(monkeypatch):
    module = _load()
    events = []
    return_codes = [0, 23]

    @contextlib.contextmanager
    def locked():
        events.append("lock-enter")
        try:
            yield
        finally:
            events.append("lock-exit")

    @contextlib.contextmanager
    def no_git_mount():
        yield []

    monkeypatch.setattr(module, "docker_ready", lambda: True)
    monkeypatch.setattr(
        module, "ensure_uv_cache_volume", lambda: events.append("cache-volume") or 0
    )
    monkeypatch.setattr(module, "container_project_lock", locked)
    monkeypatch.setattr(module, "build", lambda: events.append("build") or 0)
    monkeypatch.setattr(module, "container_git_mount", no_git_mount)
    monkeypatch.setattr(module, "cleanup_compose_project", lambda: events.append("cleanup"))
    monkeypatch.setattr(module, "clean_generated_caches", lambda: events.append("cache-clean"))

    def fake_run(command, *, interactive=False):
        events.append(("run", interactive, command))
        return return_codes.pop(0)

    monkeypatch.setattr(module, "run", fake_run)
    assert module.run_in_container(["true"]) == 0
    assert module.run_in_container(["false"], interactive=True) == 23

    assert events.count("lock-enter") == 2
    assert events.count("lock-exit") == 2
    assert events.count("cleanup") == 2
    assert events.count("cache-clean") == 2
    for index, event in enumerate(events):
        if event == "build":
            assert events[index - 1] == "cache-volume"
        if isinstance(event, tuple) and event[0] == "run":
            assert events[index - 1] == "build"
            assert events[index + 1] == "cleanup"
            assert event[2][event[2].index("--project-name") + 1] == module.project_name()
    assert len(events) == 14
    for offset in (0, 7):
        assert events[offset : offset + 3] == ["lock-enter", "cache-volume", "build"]
        assert isinstance(events[offset + 3], tuple) and events[offset + 3][0] == "run"
        assert events[offset + 4 : offset + 7] == ["cleanup", "cache-clean", "lock-exit"]
    runs = [event for event in events if isinstance(event, tuple) and event[0] == "run"]
    assert [event[1] for event in runs] == [False, True]
    assert "--interactive" in runs[1][2]


def test_cleanup_removes_only_the_checkout_project(monkeypatch):
    module = _load()
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.cleanup_compose_project() is True
    assert len(calls) == 2
    down, down_kwargs = calls[0]
    assert down[down.index("--project-name") + 1] == module.project_name()
    assert down[-2:] == ["down", "--remove-orphans"]
    assert down_kwargs["capture_output"] is True
    assert down_kwargs["text"] is True
    assert down_kwargs["check"] is False
    assert calls[1][0] == ["docker", "network", "rm", f"{module.project_name()}_default"]


def test_cleanup_falls_back_to_project_network_removal(monkeypatch):
    module = _load()
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[:2] == ["docker", "compose"]:
            return subprocess.CompletedProcess(command, 37, "", "compose failed")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.cleanup_compose_project() is True
    assert calls[-1] == ["docker", "network", "rm", f"{module.project_name()}_default"]
    assert len(calls) == 2


def test_cleanup_reports_when_all_cleanup_paths_fail(monkeypatch, capsys):
    module = _load()

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, "", "still broken")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.cleanup_compose_project() is False
    warning = capsys.readouterr().err
    assert "Compose cleanup exited 1" in warning
    assert "network removal failed" in warning


def test_cleanup_start_failure_is_reported_without_raising(monkeypatch, capsys):
    module = _load()

    def fail(command, **kwargs):
        raise PermissionError(errno.EACCES, "denied", command[0])

    monkeypatch.setattr(module.subprocess, "run", fail)
    assert module.cleanup_compose_project() is False
    warning = capsys.readouterr().err
    assert "could not start Compose cleanup" in warning
    assert "network removal could not start" in warning


def test_run_result_survives_cleanup_failure(monkeypatch):
    module = _load()

    @contextlib.contextmanager
    def locked():
        yield

    @contextlib.contextmanager
    def no_git_mount():
        yield []

    monkeypatch.setattr(module, "docker_ready", lambda: True)
    monkeypatch.setattr(module, "ensure_uv_cache_volume", lambda: 0)
    monkeypatch.setattr(module, "container_project_lock", locked)
    monkeypatch.setattr(module, "build", lambda: 0)
    monkeypatch.setattr(module, "container_git_mount", no_git_mount)
    monkeypatch.setattr(module, "cleanup_compose_project", lambda: False)
    monkeypatch.setattr(module, "clean_generated_caches", lambda: None)
    monkeypatch.setattr(module, "run", lambda command, interactive=False: 23)
    assert module.run_in_container(["false"]) == 23


def test_generated_cache_cleanup_warns_instead_of_raising(monkeypatch, tmp_path, capsys):
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    cache = tmp_path / "package" / "module.pyc"
    cache.parent.mkdir()
    cache.write_bytes(b"cache")
    original_unlink = Path.unlink

    def fail_unlink(self, *args, **kwargs):
        if self == cache:
            raise PermissionError(errno.EACCES, "denied", str(self))
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    module.clean_generated_caches()
    assert "could not remove generated cache" in capsys.readouterr().err


def test_run_result_survives_generated_cache_cleanup_failure(monkeypatch):
    module = _load()

    @contextlib.contextmanager
    def locked():
        yield

    @contextlib.contextmanager
    def no_git_mount():
        yield []

    monkeypatch.setattr(module, "docker_ready", lambda: True)
    monkeypatch.setattr(module, "ensure_uv_cache_volume", lambda: 0)
    monkeypatch.setattr(module, "container_project_lock", locked)
    monkeypatch.setattr(module, "build", lambda: 0)
    monkeypatch.setattr(module, "container_git_mount", no_git_mount)
    monkeypatch.setattr(module, "cleanup_compose_project", lambda: True)
    monkeypatch.setattr(
        module,
        "clean_generated_caches",
        lambda: (_ for _ in ()).throw(PermissionError(errno.EACCES, "denied")),
    )
    monkeypatch.setattr(module, "run", lambda command, interactive=False: 23)
    assert module.run_in_container(["false"]) == 23


def test_windows_lock_does_not_retry_permanent_errors(monkeypatch, tmp_path):
    module = _load()
    fake_msvcrt = type(
        "FakeMsvcrt",
        (),
        {
            "LK_NBLCK": 1,
            "locking": staticmethod(
                lambda *_args: (_ for _ in ()).throw(OSError(errno.EINVAL, "unsupported"))
            ),
        },
    )
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(module.sys, "platform", "win32")
    path = tmp_path / "lock"
    with path.open("a+b") as stream:
        stream.write(b"\0")
        stream.flush()
        stream.seek(0)
        with pytest.raises(OSError, match="unsupported"):
            module._lock_stream(stream)


def test_container_project_lock_releases_after_exception(tmp_path, monkeypatch):
    module = _load()
    receipt = tmp_path / "receipt.json"
    monkeypatch.setattr(module, "check_receipt_path", lambda: receipt)
    with pytest.raises(RuntimeError):
        with module.container_project_lock():
            raise RuntimeError("stop")
    with module.container_project_lock():
        pass


def test_different_checkouts_use_different_lock_paths(tmp_path, monkeypatch):
    module = _load()
    receipt = tmp_path / "receipt.json"
    monkeypatch.setattr(module, "check_receipt_path", lambda: receipt)
    roots = [tmp_path / "worktree-a", tmp_path / "worktree-b"]
    paths = []
    for root in roots:
        root.mkdir()
        monkeypatch.setattr(module, "ROOT", root)
        paths.append(module.container_lock_path())
    assert len(set(paths)) == 2


def test_container_project_lock_serializes_processes(tmp_path):
    receipt = tmp_path / "receipt.json"
    script = f"""
import importlib.util
import os
from pathlib import Path
import sys
spec = importlib.util.spec_from_file_location('dev_container_worker', {str(SCRIPT)!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.check_receipt_path = lambda: Path(os.environ['LOCK_RECEIPT'])
print('ready', flush=True)
with module.container_project_lock():
    print('locked', flush=True)
    sys.stdin.read()
"""
    env = {**os.environ, "LOCK_RECEIPT": str(receipt)}
    first = subprocess.Popen(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    second = None
    output = queue.Queue()
    reader = None
    try:
        assert first.stdout.readline().strip() == "ready"
        assert first.stdout.readline().strip() == "locked"
        second = subprocess.Popen(
            [sys.executable, "-c", script],
            cwd=ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert second.stdout.readline().strip() == "ready"

        def read_second_line():
            output.put(second.stdout.readline().strip())

        reader = threading.Thread(target=read_second_line, daemon=True)
        reader.start()
        with pytest.raises(queue.Empty):
            output.get(timeout=0.3)
        first.stdin.write("\n")
        first.stdin.flush()
        first.stdin.close()
        assert first.wait(timeout=10) == 0
        assert output.get(timeout=10) == "locked"
        second.stdin.close()
        assert second.wait(timeout=10) == 0
        reader.join(timeout=10)
        assert not reader.is_alive()
    finally:
        for process in (first, second):
            if process is not None and process.poll() is None:
                process.kill()
                process.wait()


def test_wrapper_removes_generated_caches_but_not_git_data(tmp_path, monkeypatch):
    module = _load()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    cache = tmp_path / "src" / "package" / "__pycache__"
    git_cache = tmp_path / ".git" / "objects" / "__pycache__"
    ruff_cache = tmp_path / ".ruff_cache"
    for path in (cache, git_cache, ruff_cache):
        path.mkdir(parents=True)
    (cache / "module.pyc").write_bytes(b"cache")
    (git_cache / "internal.pyc").write_bytes(b"keep")
    module.clean_generated_caches()
    assert not cache.exists()
    assert not ruff_cache.exists()
    assert git_cache.exists()


def test_container_python_matches_the_repository_pin():
    version = (ROOT / ".python-version").read_text(encoding="utf-8").strip()
    dockerfile = (ROOT / "containers" / "dev" / "Dockerfile").read_text(encoding="utf-8")
    assert f"FROM python:{version}-slim-bookworm" in dockerfile


def test_local_container_uses_the_selected_engine_architecture():
    compose = (ROOT / "containers" / "dev" / "compose.yaml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "check.yml").read_text(encoding="utf-8")
    pre_push = (ROOT / ".githooks" / "pre-push").read_text(encoding="utf-8")
    assert "platform: linux/" not in compose
    assert "DOCKER_DEFAULT_PLATFORM: linux/amd64" in workflow
    assert 'docker volume create "$SCIReL_UV_CACHE_VOLUME"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "  push:" not in workflow
    assert "target: /workspace" in compose
    assert "target: /opt/scirel-venv" in compose
    assert "target: /root/.cache/uv" in compose
    assert "name: ${SCIReL_VENV_VOLUME:-scirel-venv-local}" in compose
    assert "name: ${SCIReL_UV_CACHE_VOLUME:-scirel-uv-cache-local}" in compose
    assert "external: true" in compose
    assert "UV_PROJECT_ENVIRONMENT: /opt/scirel-venv" in compose
    assert "PYTHONPYCACHEPREFIX: /tmp/scirel-pycache" in compose
    assert "RUFF_CACHE_DIR: /tmp/scirel-ruff-cache" in compose
    assert 'dev_container.py" pre-push' in pre_push


def test_linked_worktree_git_metadata_is_mounted_portably(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    worktree = tmp_path / "worktree"
    repository.mkdir()

    def git(*arguments):
        env = module.git_discovery_environment()
        return subprocess.run(
            ["git", *arguments],
            cwd=repository,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    git("init", "-b", "main")
    git("config", "user.name", "SciRel test")
    git("config", "user.email", "scirel-test@example.invalid")
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "-m", "fixture")
    git("worktree", "add", "-b", "agent/test", str(worktree), "main")

    monkeypatch.setattr(module, "ROOT", worktree)
    context = module.linked_worktree_git_context()
    assert context is not None
    common_dir, relative_git_dir = context
    assert common_dir == repository / ".git"
    assert relative_git_dir.startswith("worktrees/")
    with module.container_git_mount() as arguments:
        assert arguments[:2] == ["--volume", f"{common_dir}:{module.GIT_COMMON_MOUNT}"]
        pointer = Path(arguments[3].rsplit(":/workspace/.git:ro", 1)[0])
        assert pointer.is_file()
        assert pointer.read_text(encoding="utf-8") == (
            f"gitdir: {module.GIT_COMMON_MOUNT}/{relative_git_dir}\n"
        )
    assert not pointer.exists()

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


def _run_git(cwd, *arguments):
    env = {
        key: value for key, value in os.environ.items() if key not in {"GIT_DIR", "GIT_WORK_TREE"}
    }
    return subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repository(path):
    path.mkdir()
    _run_git(path, "init", "-b", "main")
    _run_git(path, "config", "user.name", "SciRel test")
    _run_git(path, "config", "user.email", "scirel-test@example.invalid")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    _run_git(path, "add", "README.md")
    _run_git(path, "commit", "-m", "fixture")


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
    assert "no local check receipt" in reason

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


@pytest.mark.parametrize("linked_component", ["scirel-acceptance", "receipts"])
def test_receipt_directory_symlink_never_touches_external_files(
    tmp_path, monkeypatch, linked_component
):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    external = tmp_path / "external"
    external.mkdir()
    external_receipts = (
        external / "receipts" if linked_component == "scirel-acceptance" else external
    )
    external_receipts.mkdir(exist_ok=True)
    unrelated = external_receipts / "unrelated.json"
    unrelated.write_text("{damaged", encoding="utf-8")
    receipt_directory = module.check_receipt_directory()
    if linked_component == "scirel-acceptance":
        receipt_directory.parent.symlink_to(external, target_is_directory=True)
    else:
        receipt_directory.parent.mkdir(parents=True)
        receipt_directory.symlink_to(external, target_is_directory=True)

    valid, reason = module.check_receipt_status()
    assert not valid
    assert "unavailable" in reason
    assert not module.record_check_receipt()
    assert not (external_receipts / module.check_receipt_lock_path().name).exists()
    assert unrelated.read_text(encoding="utf-8") == "{damaged"

    runs = []
    monkeypatch.setattr(module, "run_check", lambda: runs.append("check") or 17)
    assert module.pre_push() == 17
    assert runs == ["check"]
    assert unrelated.read_text(encoding="utf-8") == "{damaged"


def test_receipt_lock_symlink_is_not_followed(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    module.validated_receipt_directory(create=True)
    external = tmp_path / "external-lock"
    external.write_text("keep", encoding="utf-8")
    lock_path = module.check_receipt_lock_path()
    lock_path.symlink_to(external)

    valid, reason = module.check_receipt_status()
    assert not valid
    assert "unavailable" in reason
    assert not module.record_check_receipt()
    assert lock_path.is_symlink()
    assert external.read_text(encoding="utf-8") == "keep"


def test_linked_worktrees_keep_receipts_for_distinct_trees(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    worktree_a = tmp_path / "worktree-a"
    worktree_b = tmp_path / "worktree-b"
    _run_git(repository, "worktree", "add", "-b", "agent/receipt-a", str(worktree_a), "main")
    _run_git(repository, "worktree", "add", "-b", "agent/receipt-b", str(worktree_b), "main")

    for worktree, content in ((worktree_a, "a\n"), (worktree_b, "b\n")):
        (worktree / "README.md").write_text(content, encoding="utf-8")
        _run_git(worktree, "add", "README.md")
        _run_git(worktree, "commit", "-m", f"candidate {content.strip()}")

    architecture = "test-architecture"
    monkeypatch.setattr(module.platform, "machine", lambda: architecture)
    tree_a = _run_git(worktree_a, "rev-parse", "HEAD^{tree}").stdout.strip()
    tree_b = _run_git(worktree_b, "rev-parse", "HEAD^{tree}").stdout.strip()
    monkeypatch.setattr(module, "ROOT", worktree_a)
    assert module.record_check_receipt()
    monkeypatch.setattr(module, "ROOT", worktree_b)
    assert module.record_check_receipt()

    path_a = module.check_receipt_path(tree_a, architecture)
    path_b = module.check_receipt_path(tree_b, architecture)
    assert path_a.parent == path_b.parent
    assert path_a.is_file()
    assert path_b.is_file()

    for worktree in (worktree_a, worktree_b):
        monkeypatch.setattr(module, "ROOT", worktree)
        valid, reason = module.check_receipt_status()
        assert valid
        assert "already passed" in reason

    runs = []
    monkeypatch.setattr(module, "run_check", lambda: runs.append("check") or 17)
    monkeypatch.setattr(module, "ROOT", worktree_a)
    assert module.pre_push() == 0
    monkeypatch.setattr(module, "ROOT", worktree_b)
    assert module.pre_push() == 0
    assert runs == []


def test_other_architectures_use_distinct_cache_entries(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)

    monkeypatch.setattr(module.platform, "machine", lambda: "architecture-a")
    assert module.record_check_receipt()
    monkeypatch.setattr(module.platform, "machine", lambda: "architecture-b")
    valid, reason = module.check_receipt_status()
    assert not valid
    assert "no local check receipt" in reason
    assert module.record_check_receipt()

    tree = _run_git(repository, "rev-parse", "HEAD^{tree}").stdout.strip()
    assert module.check_receipt_path(tree, "architecture-a").is_file()
    assert module.check_receipt_path(tree, "architecture-b").is_file()
    valid, _ = module.check_receipt_status()
    assert valid


def test_check_receipt_rejects_a_different_tree(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    assert module.record_check_receipt()
    first_tree = _run_git(repository, "rev-parse", "HEAD^{tree}").stdout.strip()
    first_path = module.check_receipt_path()

    (repository / "README.md").write_text("changed\n", encoding="utf-8")
    _run_git(repository, "add", "README.md")
    _run_git(repository, "commit", "-m", "changed")
    second_tree = _run_git(repository, "rev-parse", "HEAD^{tree}").stdout.strip()

    valid, reason = module.check_receipt_status()
    assert not valid
    assert "no local check receipt" in reason
    assert first_tree != second_tree
    assert first_path.is_file()
    assert module.check_receipt_path() != first_path


def test_check_receipt_rejects_another_schema(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    assert module.record_check_receipt()
    path = module.check_receipt_path()
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["schema"] = module.CHECK_RECEIPT_SCHEMA + 1
    path.write_text(json.dumps(receipt), encoding="utf-8")

    valid, reason = module.check_receipt_status()
    assert not valid
    assert "schema" in reason


def test_corrupt_receipt_and_temporary_file_are_treated_as_misses(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    assert module.record_check_receipt()
    path = module.check_receipt_path()
    path.write_text("{not-json", encoding="utf-8")
    temporary = path.parent / f"{module.CHECK_RECEIPT_TEMP_PREFIX}abandoned.tmp"
    temporary.write_text("partial", encoding="utf-8")

    valid, reason = module.check_receipt_status()
    assert not valid
    assert "unreadable" in reason
    assert not path.exists()
    assert not temporary.exists()

    runs = []
    monkeypatch.setattr(module, "run_check", lambda: runs.append("check") or 17)
    assert module.pre_push() == 17
    assert runs == ["check"]


def test_oversized_receipt_timestamp_is_a_miss_and_pre_push_runs_check(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    assert module.record_check_receipt()
    path = module.check_receipt_path()
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["checked_at_unix"] = 10**1000
    path.write_text(json.dumps(receipt), encoding="utf-8")

    valid, reason = module.check_receipt_status()
    assert not valid
    assert "timestamp" in reason
    assert not path.exists()

    runs = []
    monkeypatch.setattr(module, "run_check", lambda: runs.append("check") or 17)
    assert module.pre_push() == 17
    assert runs == ["check"]


@pytest.mark.parametrize("has_valid_receipt", [False, True])
def test_unrelated_damaged_receipts_are_skipped_with_or_without_a_cache_hit(
    tmp_path, monkeypatch, has_valid_receipt
):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    if has_valid_receipt:
        assert module.record_check_receipt()
    directory = module.validated_receipt_directory(create=True)

    common_fields = {"schema": module.CHECK_RECEIPT_SCHEMA, "architecture": "test"}
    oversized = {**common_fields, "tree": "a" * 40, "checked_at_unix": 10**1000}
    surrogate = {**common_fields, "tree": "\ud800", "checked_at_unix": 1}
    damaged = {
        "oversized.json": json.dumps(oversized),
        "surrogate.json": json.dumps(surrogate),
        "invalid.json": "{not-json",
    }
    for name, content in damaged.items():
        (directory / name).write_text(content, encoding="utf-8")

    valid, _ = module.check_receipt_status()
    assert valid is has_valid_receipt
    for name in damaged:
        assert not (directory / name).exists()

    runs = []
    monkeypatch.setattr(module, "run_check", lambda: runs.append("check") or 17)
    expected = 0 if has_valid_receipt else 17
    assert module.pre_push() == expected
    assert runs == ([] if has_valid_receipt else ["check"])


def test_unrelated_prune_error_does_not_hide_a_valid_receipt(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    assert module.record_check_receipt()
    directory = module.validated_receipt_directory()
    unrelated = directory / "unrelated.json"
    unrelated.write_text("{damaged", encoding="utf-8")
    original_unlink = Path.unlink

    def fail_unrelated(self, *args, **kwargs):
        if self == unrelated:
            raise PermissionError(errno.EACCES, "denied", str(self))
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_unrelated)
    valid, reason = module.check_receipt_status()
    assert valid
    assert "already passed" in reason
    assert unrelated.exists()

    runs = []
    monkeypatch.setattr(module, "run_check", lambda: runs.append("check") or 17)
    assert module.pre_push() == 0
    assert runs == []


def test_receipt_cache_expires_and_prunes_the_current_tree(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    monkeypatch.setattr(module, "CHECK_RECEIPT_MAX_AGE_SECONDS", 30)
    now = [200.0]
    monkeypatch.setattr(module.time, "time", lambda: now[0])
    assert module.record_check_receipt()
    path = module.check_receipt_path()

    now[0] = 229.0
    valid, _ = module.check_receipt_status()
    assert valid
    assert path.is_file()

    now[0] = 230.0
    valid, reason = module.check_receipt_status()
    assert not valid
    assert "expired" in reason
    assert not path.exists()


def test_receipt_cache_prunes_to_the_newest_entries(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    monkeypatch.setattr(module.platform, "machine", lambda: "test-architecture")
    monkeypatch.setattr(module, "CHECK_RECEIPT_MAX_ENTRIES", 2)
    monkeypatch.setattr(module, "CHECK_RECEIPT_MAX_AGE_SECONDS", 1_000)
    now = [100.0]
    monkeypatch.setattr(module.time, "time", lambda: now[0])
    trees = [f"{index:040x}" for index in range(1, 4)]

    for tree in trees:
        assert module.record_check_receipt(tree)
        now[0] += 1

    paths = [module.check_receipt_path(tree, "test-architecture") for tree in trees]
    assert not paths[0].exists()
    assert paths[1].is_file()
    assert paths[2].is_file()
    assert len(list(module.check_receipt_directory().glob("*.json"))) == 2


def test_concurrent_writers_and_pruners_leave_a_valid_bounded_cache(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    architecture = "test-architecture"
    trees = [f"{index:040x}" for index in range(1, 9)]
    worker = f"""
import importlib.util
import os
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location('dev_container_worker', {str(SCRIPT)!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.ROOT = Path(os.environ['RECEIPT_REPO'])
module.platform.machine = lambda: os.environ['RECEIPT_ARCHITECTURE']
module.CHECK_RECEIPT_MAX_ENTRIES = 4
module.CHECK_RECEIPT_MAX_AGE_SECONDS = 1_000
module.time.time = lambda: float(os.environ['RECEIPT_NOW'])
raise SystemExit(0 if module.record_check_receipt(os.environ['RECEIPT_TREE']) else 1)
"""
    processes = []
    for tree in trees:
        env = {
            **os.environ,
            "RECEIPT_REPO": str(repository),
            "RECEIPT_ARCHITECTURE": architecture,
            "RECEIPT_NOW": "1",
            "RECEIPT_TREE": tree,
        }
        processes.append(
            subprocess.Popen(
                [sys.executable, "-c", worker],
                cwd=repository,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )

    for process in processes:
        stdout, stderr = process.communicate(timeout=20)
        assert process.returncode == 0, (stdout, stderr)

    paths = [module.check_receipt_path(tree, architecture) for tree in trees]
    assert sum(path.is_file() for path in paths) == 4
    cached = sorted(module.check_receipt_directory().glob("*.json"))
    assert len(cached) == 4
    for path in cached:
        receipt, error = module._read_check_receipt(path)
        assert error is None
        assert receipt is not None
        assert module._check_receipt_is_fresh(receipt, 1.0)


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
    git_directory = tmp_path / "git-directory"
    git_directory.mkdir()
    monkeypatch.setattr(module, "worktree_git_directory", lambda: git_directory)
    with pytest.raises(RuntimeError):
        with module.container_project_lock():
            raise RuntimeError("stop")
    with module.container_project_lock():
        pass


def test_container_lock_directory_symlink_is_not_followed(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    external = tmp_path / "external"
    external.mkdir()
    lock_directory = module.worktree_git_directory() / "scirel-acceptance"
    lock_directory.symlink_to(external, target_is_directory=True)
    lock_name = module.container_lock_path().name

    with pytest.raises(module.ContainerLockUnavailable):
        with module.container_project_lock():
            pass
    assert not (external / lock_name).exists()


def test_container_lock_file_symlink_is_not_followed(tmp_path, monkeypatch):
    module = _load()
    repository = tmp_path / "repository"
    _init_git_repository(repository)
    monkeypatch.setattr(module, "ROOT", repository)
    external = tmp_path / "external-lock"
    external.write_bytes(b"keep")
    lock_path = module.container_lock_path()
    lock_path.parent.mkdir()
    lock_path.symlink_to(external)

    with pytest.raises(module.ContainerLockUnavailable):
        with module.container_project_lock():
            pass
    assert lock_path.is_symlink()
    assert external.read_bytes() == b"keep"


def test_different_checkouts_use_different_lock_paths(tmp_path, monkeypatch):
    module = _load()
    roots = [tmp_path / "worktree-a", tmp_path / "worktree-b"]
    paths = []
    for root in roots:
        root.mkdir()
        monkeypatch.setattr(module, "ROOT", root)
        monkeypatch.setattr(module, "worktree_git_directory", lambda root=root: root / ".git")
        paths.append(module.container_lock_path())
    assert len(set(paths)) == 2


def test_container_project_lock_serializes_processes(tmp_path):
    git_directory = tmp_path / "git-directory"
    git_directory.mkdir()
    script = f"""
import importlib.util
import os
from pathlib import Path
import sys
spec = importlib.util.spec_from_file_location('dev_container_worker', {str(SCRIPT)!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.worktree_git_directory = lambda: Path(os.environ['WORKTREE_GIT_DIR'])
print('ready', flush=True)
with module.container_project_lock():
    print('locked', flush=True)
    sys.stdin.read()
"""
    env = {**os.environ, "WORKTREE_GIT_DIR": str(git_directory)}
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

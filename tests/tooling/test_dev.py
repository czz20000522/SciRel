"""The development wrapper keeps every run artifact inside the project directory."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

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

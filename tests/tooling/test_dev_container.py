"""The development wrapper keeps one deterministic, portable container contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

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


def test_loopback_proxy_is_reachable_from_the_container(monkeypatch):
    module = _load()
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:7890")
    monkeypatch.setenv("HTTPS_PROXY", "http://localhost:7890")
    env = module.environment()
    assert env["SCIReL_HTTP_PROXY"] == "http://host.docker.internal:7890"
    assert env["SCIReL_HTTPS_PROXY"] == "http://host.docker.internal:7890"


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
    assert "platform: linux/" not in compose
    assert "DOCKER_DEFAULT_PLATFORM: linux/amd64" in workflow
    assert "target: /workspace" in compose
    assert "target: /opt/scirel-venv" in compose
    assert "target: /root/.cache/uv" in compose
    assert "UV_PROJECT_ENVIRONMENT: /opt/scirel-venv" in compose
    assert "PYTHONPYCACHEPREFIX: /tmp/scirel-pycache" in compose
    assert "RUFF_CACHE_DIR: /tmp/scirel-ruff-cache" in compose

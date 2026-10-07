"""Exercise current-document dependency selection without historical scientific assets."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _selector():
    spec = importlib.util.spec_from_file_location("mainline_selector", ROOT / "scripts/select_affected_tests.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _temporary_asset_tree(tmp_path, monkeypatch):
    selector = _selector()
    documents = tmp_path / "catalog/assets"
    documents.mkdir(parents=True)
    tests = tmp_path / "tests"
    tests.mkdir()
    source = tmp_path / "src/scirel/fixture"
    source.mkdir(parents=True)
    base = json.loads((ROOT / "tests/fixtures/contracts/fixture-identity.json").read_text())
    for name, dependencies in (("leaf", []), ("flow", ["leaf"]), ("outer", ["flow"]), ("unrelated", [])):
        document = json.loads(json.dumps(base))
        document["asset_id"] = f"scirel.fixture.{name}"
        document["public_api"]["python"]["module"] = f"scirel.fixture.{name}"
        document["version"]["dependencies"] = [{"asset_id": f"scirel.fixture.{item}"} for item in dependencies]
        document["verification"]["tests"] = [f"tests/test_{name}.py"]
        (documents / f"{name}.json").write_text(json.dumps(document))
        (tests / f"test_{name}.py").touch()
        (source / f"{name}.py").write_text("from .leaf import identity\n" if dependencies else "def identity(x): return x\n")
    monkeypatch.setattr(selector, "ROOT", tmp_path)
    monkeypatch.setattr(selector, "CATALOG", documents)
    return selector


def test_current_scaffold_has_no_historical_assets():
    selector = _selector()
    assert selector._load_assets() == []
    result = selector.select(["src/scirel/__init__.py"])
    assert not result["full_suite_required"]
    assert result["test_paths"] == ["tests/test_asset_documentation.py", "tests/test_public_surface.py"]


def test_current_document_dependencies_select_transitive_consumers_only(tmp_path, monkeypatch):
    selector = _temporary_asset_tree(tmp_path, monkeypatch)
    result = selector.select(["src/scirel/fixture/leaf.py"])
    assert not result["full_suite_required"]
    assert result["test_paths"] == ["tests/test_flow.py", "tests/test_leaf.py", "tests/test_outer.py"]
    assert "tests/test_unrelated.py" not in result["test_paths"]


def test_unmapped_scientific_change_fails_closed_to_current_full_suite():
    result = _selector().select(["src/scirel/new_domain/new_asset.py"])
    assert result["full_suite_required"]
    assert result["test_paths"] == ["tests"]


def test_missing_declared_direct_test_is_rejected(tmp_path, monkeypatch):
    selector = _temporary_asset_tree(tmp_path, monkeypatch)
    (tmp_path / "tests/test_leaf.py").unlink()
    with pytest.raises(ValueError, match="missing direct test"):
        selector.select(["src/scirel/fixture/leaf.py"])


@pytest.mark.parametrize("path, expected", [
    ("src/scirel_workflow/workflow.py", "tests/workflow/test_workflow.py"),
    ("src/scirel_plugin/http_listener.py", "tests/plugin/test_http_listener.py"),
    ("src/scirel_adapter/mcp.py", "tests/test_thin_mcp_adapter.py"),
    ("scripts/build_catalog.py", "tests/test_asset_documentation.py"),
])
def test_retained_tools_select_their_own_contracts(path, expected):
    result = _selector().select([path])
    assert not result["full_suite_required"]
    assert expected in result["test_paths"]


def test_python_selector_cli_remains_usable_without_powershell():
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts/select_affected_tests.py"),
        "--format", "json", "--changed-path", "pyproject.toml",
    ], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["full_suite_required"]

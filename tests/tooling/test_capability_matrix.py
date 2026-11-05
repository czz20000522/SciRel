"""The capability matrix is a derived catalog view used for domain discovery."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_capability_matrix.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_capability_matrix", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _documents():
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((ROOT / "catalog" / "examples").glob("*.json"))
    ]


def _held():
    payload = json.loads((ROOT / "catalog" / "review" / "HOLD.json").read_text())
    return set(payload["assets"])


def test_matrix_covers_every_asset_and_domain():
    tool = _load()
    documents = _documents()
    matrix = tool.build_matrix(documents, revision="test-revision")
    assert matrix["schema"] == "scirel.capability-matrix"
    assert matrix["total_assets"] == len(documents)
    assert matrix["total_domains"] == len(matrix["domains"])
    assert sum(group["count"] for group in matrix["domains"]) == matrix["total_assets"]
    assert sum(matrix["taxonomy_counts"].values()) == sum(
        len(document.get("taxonomy", [])) for document in documents
    )
    assert [asset["asset_id"] for asset in matrix["assets"]] == sorted(
        asset["asset_id"] for asset in matrix["assets"]
    )
    for asset in matrix["assets"]:
        assert asset["ports"].count("->") == 1
        assert asset["symbol"] and asset["domain"]


def test_markdown_and_cli_output(tmp_path):
    tool = _load()
    documents = _documents()
    matrix = tool.build_matrix(documents, revision="test-revision")
    markdown = tool.render_markdown(matrix)
    assert "# SciRel capability matrix" in markdown
    for group in matrix["domains"]:
        assert f"## {group['domain']} (" in markdown
    code = tool.main(["--catalog", str(ROOT / "catalog" / "examples"), "--output", str(tmp_path)])
    assert code == 0
    payload = json.loads((tmp_path / "capability-matrix.json").read_text(encoding="utf-8"))
    assert payload["total_assets"] == len([d for d in documents if d["asset_id"] not in _held()])
    assert (tmp_path / "CAPABILITY_MATRIX.md").is_file()

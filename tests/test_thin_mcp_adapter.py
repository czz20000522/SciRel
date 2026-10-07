"""Verify thin adapter boundaries using synthetic catalog records only."""

import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_catalog import build_catalog
from scirel_adapter import ThinMcpAdapter, ThinMcpAdapterError


@pytest.fixture
def catalog(tmp_path):
    output = tmp_path / "catalog"
    result = build_catalog(ROOT / "tests/fixtures/contracts", output,
                           catalog_id="synthetic-fixture", release_version="0.1.0.dev5",
                           coverage_status="complete", declared_total=2)
    return output, result["root_digest"]


def test_discovery_and_reads_do_not_import_scientific_code(catalog):
    with patch("scirel_adapter.mcp.importlib.import_module", side_effect=AssertionError("unexpected import")):
        adapter = ThinMcpAdapter(catalog[0], expected_root_digest=catalog[1])
        page = adapter.discover(limit=1)
        assert len(page["items"]) == 1 and not page["exhausted"]
        asset_id = page["items"][0]["asset_id"]
        document = adapter.read_assets([asset_id], detail="document")["items"][0]
        assert document["asset_id"] == asset_id
        assert "Synthetic" in document["summary"]


def test_release_digest_mismatch_is_rejected(catalog):
    with pytest.raises(ThinMcpAdapterError):
        ThinMcpAdapter(catalog[0], expected_root_digest="sha256:" + "0" * 64)


def test_changed_catalog_bytes_are_rejected(catalog):
    release = json.loads((catalog[0] / "release.json").read_text())
    partition = catalog[0] / release["partitions"][0]["path"]
    partition.write_bytes(partition.read_bytes() + b"changed")
    with pytest.raises(ThinMcpAdapterError):
        ThinMcpAdapter(catalog[0])


def test_unknown_assets_cannot_resolve_to_a_guessed_callable(catalog):
    with pytest.raises(ThinMcpAdapterError) as error:
        ThinMcpAdapter(catalog[0]).read_assets(["scirel.fixture.absent"])
    assert error.value.code == "asset_not_found"


def test_callable_version_mismatch_blocks_execution(catalog):
    with patch("scirel_adapter.mcp.metadata.version", return_value="different"):
        with pytest.raises(ThinMcpAdapterError) as error:
            ThinMcpAdapter(catalog[0]).resolve_callable("scirel.fixture.identity")
    assert error.value.code == "callable_mismatch"


def test_invocation_uses_only_the_exact_selected_binding(catalog):
    def identity(x, scale=1.0):
        return {"value": x * scale}
    with patch("scirel_adapter.mcp.metadata.version", return_value="0.1.0.dev5"), \
         patch("scirel_adapter.mcp.importlib.import_module", return_value=SimpleNamespace(identity=identity)) as imported:
        response = ThinMcpAdapter(catalog[0]).invoke("scirel.fixture.identity", {"x": 3.0, "scale": 2.0})
    imported.assert_called_once_with("scirel.fixture.identity")
    assert response["result"] == {"value": 6.0}

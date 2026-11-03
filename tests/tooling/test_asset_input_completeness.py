"""Runtime signatures distinguish no-input assets from incomplete port lists."""

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_asset_documents import (  # noqa: E402
    AssetDocumentError,
    validate_document,
    validate_runtime,
)


def _document(asset_id):
    return json.loads((ROOT / "catalog/examples" / f"{asset_id}.json").read_bytes())


@pytest.mark.parametrize("asset_id", [
    "scirel.electromagnetism.wham",
    "scirel.electromagnetism.brb",
    "scirel.kinetic.multifluid-deck",
    "scirel.kinetic.rational-jpole-grid-coordinates",
])
def test_zero_argument_callable_accepts_an_explicit_empty_input_list(asset_id):
    document = _document(asset_id)
    assert document["inputs"] == []
    assert validate_document(document) is document
    validate_runtime(document)


@pytest.mark.parametrize("omitted", ["all", "r0", "angle_deg"])
def test_parameterized_callable_rejects_undocumented_explicit_inputs(omitted):
    document = _document("scirel.field.rectangular-coil-filaments")
    document["inputs"] = [
        port for port in document["inputs"]
        if omitted != "all" and port["name"] != omitted
    ]
    # An empty list is structurally valid; the runtime binding establishes
    # whether explicit scientific parameters are missing.
    assert validate_document(document) is document
    expected = "angle_deg" if omitted == "angle_deg" else "r0"
    with pytest.raises(AssetDocumentError, match=f"undocumented.*{expected}"):
        validate_runtime(document)

"""The current SciRel document closure used by development tests.

The closure is canonicalized under ``catalog/examples``. External project
source catalogs and D0-D3 work are not test inputs for the SciRel package.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "catalog/examples"
EXAMPLE_CLOSURE_COUNT = 141


def example_document_sources():
    sources = {}
    for path in EXAMPLES.glob("*.json"):
        document = json.loads(path.read_bytes())
        sources[document["asset_id"]] = path
    assert len(sources) == EXAMPLE_CLOSURE_COUNT
    return sources


def copy_example_closure(target):
    target.mkdir()
    for asset, source in example_document_sources().items():
        (target / f"{asset}.json").write_bytes(source.read_bytes())
    return target

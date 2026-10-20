"""The current SciRel document closure used by development tests.

The closure is canonicalized under ``catalog/examples``. External project
source catalogs and D0-D3 work are not test inputs for the SciRel package.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "catalog/examples"
# Keep the fixture denominator tied to the current working-tree document set.
# Release selections carry their own frozen counts; development tests must not
# turn one historical manifest into a permanent project gate.
EXAMPLE_CLOSURE_COUNT = sum(1 for path in EXAMPLES.glob("*.json") if path.is_file())


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

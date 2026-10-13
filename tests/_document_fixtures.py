"""Dependency-closed copies for development tests, never canonical documents.

The historical examples are a bounded fixture, not a self-contained catalog:
their maintained field implementations now use three canonical Green assets.
Resolve only declared dependencies from the explicit maintained family. This
does not widen the validator or project scientific fields from implementation.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "catalog/examples"
MAINTAINED = ROOT / "catalog/pleiades-maintained"
EXAMPLE_CLOSURE_COUNT = 136


def example_document_sources():
    sources = {}
    for path in EXAMPLES.glob("*.json"):
        document = json.loads(path.read_bytes())
        sources[document["asset_id"]] = path
    assert len(sources) == 133
    dependencies = {}
    for path in MAINTAINED.glob("*.json"):
        document = json.loads(path.read_bytes())
        asset = document["asset_id"]
        assert asset not in dependencies
        dependencies[asset] = path
    pending = list(sources)
    while pending:
        document = json.loads(sources[pending.pop()].read_bytes())
        for dependency in document["version"]["dependencies"]:
            asset = dependency["asset_id"]
            if asset not in sources:
                sources[asset] = dependencies[asset]
                pending.append(asset)
    assert set(sources) - {json.loads(p.read_bytes())["asset_id"] for p in EXAMPLES.glob("*.json")} == {
        "scirel.electromagnetism.circular-filament-green",
        "scirel.electromagnetism.loop-flux-matrix",
        "scirel.electromagnetism.green-response-matrices",
    }
    assert len(sources) == EXAMPLE_CLOSURE_COUNT
    return sources


def copy_example_closure(target):
    target.mkdir()
    for asset, source in example_document_sources().items():
        (target / f"{asset}.json").write_bytes(source.read_bytes())
    return target

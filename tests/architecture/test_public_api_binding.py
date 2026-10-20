import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from build_catalog import build_catalog  # noqa: E402
from public_api_binding import implementation_module  # noqa: E402
from validate_asset_documents import (  # noqa: E402
    AssetDocumentError,
    validate_document,
    validate_runtime,
)


def _document(name: str) -> dict:
    return json.loads((ROOT / "catalog/examples" / name).read_text(encoding="utf-8"))


def test_legacy_package_root_documents_resolve_to_child_implementations():
    package_root_documents = []
    for path in sorted((ROOT / "catalog/examples").glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        api = document["public_api"]["python"]
        module_path = ROOT / "src" / Path(*api["module"].split("."))
        if (module_path / "__init__.py").is_file() and not module_path.with_suffix(".py").is_file():
            package_root_documents.append((api["module"], api["symbol"]))

    assert len(package_root_documents) == 11
    for module, symbol in package_root_documents:
        implementation = implementation_module(ROOT, module, symbol)
        assert implementation.startswith(module + ".")
        assert (ROOT / "src" / Path(*implementation.split("."))).with_suffix(".py").is_file()


def test_canonical_binding_requires_a_pair_and_preserves_runtime_identity():
    document = _document("scirel.geometry.spherical-r-chord.json")
    python_api = document["public_api"]["python"]
    python_api.update(
        {"canonical_module": "scirel.geometry", "canonical_symbol": "SphericalRChord"}
    )
    assert validate_document(document) is document
    validate_runtime(document)

    missing_pair = json.loads(json.dumps(document))
    del missing_pair["public_api"]["python"]["canonical_symbol"]
    with pytest.raises(AssetDocumentError, match="provided together"):
        validate_document(missing_pair)

    mismatched = json.loads(json.dumps(document))
    mismatched["public_api"]["python"]["canonical_symbol"] = "Mesh"
    with pytest.raises(AssetDocumentError, match="canonical Python callable differs"):
        validate_runtime(mismatched)


def test_runtime_requires_the_implementation_symbol_in_module_all(monkeypatch):
    document = _document("scirel.field.multi-coil-vacuum-field.json")
    import importlib

    module = importlib.import_module(document["public_api"]["python"]["module"])
    symbol = document["public_api"]["python"]["symbol"]
    monkeypatch.setattr(
        module,
        "__all__",
        [name for name in module.__all__ if name != symbol],
    )
    with pytest.raises(AssetDocumentError, match="implementation module __all__"):
        validate_runtime(document)


def test_runtime_requires_the_canonical_symbol_in_package_all(monkeypatch):
    document = _document("scirel.geometry.spherical-r-chord.json")
    document["public_api"]["python"].update(
        {
            "module": "scirel.geometry.mesh",
            "canonical_module": "scirel.geometry",
            "canonical_symbol": "SphericalRChord",
        }
    )
    import importlib

    canonical = importlib.import_module("scirel.geometry")
    monkeypatch.setattr(
        canonical,
        "__all__",
        [name for name in canonical.__all__ if name != "SphericalRChord"],
    )
    with pytest.raises(AssetDocumentError, match="canonical module __all__"):
        validate_runtime(document)


def test_package_export_wins_over_same_named_child_module():
    import importlib

    package = importlib.import_module("scirel.collisions")
    importlib.import_module("scirel.collisions.relativistic_maxwellian_bessel")

    exported = getattr(package, "relativistic_maxwellian_bessel")
    implementation = importlib.import_module(
        "scirel.collisions.relativistic_maxwellian_bessel"
    ).relativistic_maxwellian_bessel
    assert exported is implementation
    assert callable(exported)


def test_catalog_summary_keeps_canonical_and_implementation_bindings_separate(tmp_path):
    document = _document("scirel.geometry.spherical-r-chord.json")
    document["public_api"]["python"].update(
        {
            "module": "scirel.geometry.mesh",
            "canonical_module": "scirel.geometry",
            "canonical_symbol": "SphericalRChord",
        }
    )
    documents = tmp_path / "documents"
    documents.mkdir()
    (documents / "asset.json").write_text(json.dumps(document), encoding="utf-8")
    output = tmp_path / "catalog"
    build_catalog(
        documents,
        output,
        catalog_id="canonical-binding-test",
        release_version=document["version"]["implementation_version"],
        coverage_status="complete",
        declared_total=1,
    )
    summary = json.loads((output / "summaries/all.jsonl").read_text(encoding="utf-8"))
    assert summary["public_callable"] == "scirel.geometry.SphericalRChord"
    assert summary["implementation_callable"] == "scirel.geometry.mesh.SphericalRChord"

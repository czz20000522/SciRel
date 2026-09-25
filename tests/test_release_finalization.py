"""Catalog integrity checks reused by review-version freezing."""

import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_catalog import build_catalog  # noqa: E402
from finalize_release import _validate_catalog  # noqa: E402


def _catalog(tmp_path: Path) -> Path:
    documents = tmp_path / "documents"
    documents.mkdir()
    source = ROOT / "catalog/examples/scirel.field.circular-filament-green.json"
    (documents / source.name).write_bytes(source.read_bytes())
    version = json.loads(source.read_text(encoding="utf-8"))["version"][
        "implementation_version"
    ]
    output = tmp_path / "catalog"
    build_catalog(
        documents,
        output,
        catalog_id="scirel-catalog-integrity-test",
        release_version=version,
        coverage_status="complete",
        declared_total=1,
    )
    return output


def test_review_version_catalog_integrity_accepts_built_catalog(tmp_path):
    catalog = _catalog(tmp_path)
    assert _validate_catalog(catalog)["schema"] == "scirel.catalog-release.v1"


def test_review_version_catalog_integrity_rejects_partition_mutation(tmp_path):
    catalog = _catalog(tmp_path)
    partition = next((catalog / "records").rglob("*.json"))
    partition.write_bytes(partition.read_bytes() + b" ")
    with pytest.raises(ValueError, match="partition byte count differs"):
        _validate_catalog(catalog)


def test_review_version_catalog_integrity_rejects_root_mutation(tmp_path):
    catalog = _catalog(tmp_path)
    path = catalog / "release.json"
    release = json.loads(path.read_text(encoding="utf-8"))
    release["catalog_id"] = "changed-without-rebinding"
    path.write_text(json.dumps(release), encoding="utf-8")
    with pytest.raises(ValueError, match="root digest does not match"):
        _validate_catalog(catalog)

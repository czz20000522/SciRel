from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from package_catalog_snapshot import package_catalog_snapshot  # noqa: E402


def _digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _catalog(root: Path) -> None:
    (root / "routes").mkdir(parents=True, exist_ok=True)
    partition = b'{"asset_id":"test"}\n'
    (root / "routes" / "all.jsonl").write_bytes(partition)
    release = {
        "schema": "scirel.catalog-release.v1",
        "catalog_id": "test",
        "release_version": "0.0.0",
        "coverage": {"status": "complete", "included_asset_count": 1, "declared_total_asset_count": 1},
        "progressive_disclosure": ["routes", "summaries", "exact_records"],
        "partitions": [{"path": "routes/all.jsonl", "bytes": len(partition), "sha256": _digest(partition)}],
    }
    canonical = json.dumps(release, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    release["root_digest"] = _digest(canonical)
    (root / "release.json").write_text(json.dumps(release), encoding="utf-8")


def test_package_is_deterministic_and_contains_exact_release_files(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    _catalog(catalog)
    first = package_catalog_snapshot(catalog, tmp_path / "first.zip")
    second = package_catalog_snapshot(catalog, tmp_path / "second.zip")

    assert first["sha256"] == second["sha256"]
    assert first["file_count"] == 2
    with zipfile.ZipFile(first["output"]) as archive:
        assert archive.namelist() == ["release.json", "routes/all.jsonl"]
        for name in archive.namelist():
            assert archive.read(name) == (catalog / name).read_bytes()


def test_package_rejects_changed_or_extra_files(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    _catalog(catalog)
    (catalog / "routes" / "all.jsonl").write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="digest or size mismatch"):
        package_catalog_snapshot(catalog, tmp_path / "changed.zip")
    assert not (tmp_path / "changed.zip").exists()

    _catalog(catalog)
    (catalog / "extra.txt").write_text("unbound", encoding="utf-8")
    with pytest.raises(ValueError, match="files differ"):
        package_catalog_snapshot(catalog, tmp_path / "extra.zip")


def test_package_rejects_unsafe_partition_path(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    _catalog(catalog)
    release_path = catalog / "release.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    release["partitions"][0]["path"] = "../outside.jsonl"
    unsigned = {key: value for key, value in release.items() if key != "root_digest"}
    release["root_digest"] = _digest(json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode())
    release_path.write_text(json.dumps(release), encoding="utf-8")

    with pytest.raises(ValueError, match="invalid catalog partition path"):
        package_catalog_snapshot(catalog, tmp_path / "unsafe.zip")
    assert not (tmp_path / "unsafe.zip").exists()

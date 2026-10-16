from __future__ import annotations

import json
from pathlib import Path
import sys
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_release_alignment import (
    _validate_platform_receipts,
    validate_alignment,
)  # noqa: E402


def test_current_release_alignment_is_exact() -> None:
    result = validate_alignment(ROOT)
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert result["wheel_version"] == project["project"]["version"]
    assert result["documentation_selection"] == "scientific-core-current"
    assert result["source_revision"] == "9733bfc6e9f91a8526f5c72843b9203aa8ebbf04"
    assert result["capability_counts"] == {
        "operators": 230,
        "task_graphs": 30,
        "document_closure": 260,
    }


def test_current_release_version_is_the_pyproject_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    current = json.loads((ROOT / "release/CURRENT.json").read_text(encoding="utf-8"))
    assert current["version"] == project["project"]["version"]


def test_alignment_rejects_a_pyproject_version_drift(tmp_path: Path) -> None:
    import shutil

    for relative in ("release", "catalog", "provenance", "tools"):
        source = ROOT / relative
        target = tmp_path / relative
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        project.replace('version = "0.1.0.dev9"', 'version = "0.1.0.dev10"'),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="pyproject.toml project.version"):
        validate_alignment(tmp_path)


def test_alignment_can_require_an_exact_git_source_revision() -> None:
    with pytest.raises(ValueError, match="expected Git revision"):
        validate_alignment(ROOT, expected_source_revision="0" * 40)


def test_legacy_current_files_are_thin_compatibility_pointers() -> None:
    for line in ("wheel", "docs"):
        path = ROOT / "release" / line / "CURRENT.json"
        pointer = json.loads(path.read_text())
        assert pointer["schema"] == "scirel.release-compat-pointer.v1"
        assert pointer["canonical"] == "../CURRENT.json"
        assert pointer["deprecated"] is True


def test_version_history_is_kept_in_git_and_short_release_notes() -> None:
    assert not list((ROOT / "release/wheel/versions").glob("*.json"))
    assert not list((ROOT / "release/docs/versions").glob("*.json"))
    assert (ROOT / "docs/release/0.1.0.dev8-notes.md").is_file()
    assert not list((ROOT / "tools/docs/handbooks").glob("*.json"))
    assert json.loads((ROOT / "release/CURRENT.json").read_text())["documentation"]["handbook"] == "tools/docs/handbook.json"


def test_alignment_rejects_a_document_added_outside_the_wheel(tmp_path: Path) -> None:
    for relative in ("release", "catalog", "provenance", "tools"):
        source = ROOT / relative
        target = tmp_path / relative
        if source.is_dir():
            import shutil

            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    (tmp_path / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
    (tmp_path / "uv.lock").write_bytes((ROOT / "uv.lock").read_bytes())
    current_path = tmp_path / "release/CURRENT.json"
    current = json.loads(current_path.read_text())
    current["documentation"]["capability_counts"]["document_closure"] += 1
    current_path.write_text(json.dumps(current), encoding="utf-8")
    with pytest.raises(ValueError, match="capability_counts"):
        validate_alignment(tmp_path)


def test_alignment_rejects_a_built_catalog_from_a_different_source_revision(
    tmp_path: Path,
) -> None:
    import shutil

    for relative in ("release", "catalog", "provenance", "tools"):
        source = ROOT / relative
        target = tmp_path / relative
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    (tmp_path / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
    (tmp_path / "uv.lock").write_bytes((ROOT / "uv.lock").read_bytes())
    catalog_root = tmp_path / "built-catalog"
    catalog_root.mkdir()
    (catalog_root / "release.json").write_text(
        json.dumps({
            "schema": "scirel.catalog-release.v1",
            "source_revision": "0" * 40,
        }),
        encoding="utf-8",
    )
    current_path = tmp_path / "release/CURRENT.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["documentation"]["catalog_root"] = "built-catalog"
    current_path.write_text(json.dumps(current), encoding="utf-8")
    with pytest.raises(ValueError, match="documentation catalog source_revision"):
        validate_alignment(tmp_path)


def test_alignment_accepts_wrapped_platform_receipt_and_checks_source_revision(
    tmp_path: Path,
) -> None:
    import hashlib

    source_revision = "a" * 40
    artifact_sha = "b" * 64
    inner = {
        "schema": "scirel.installed-wheel-validation.v1",
        "status": "PASS",
        "package": {"version": "0.1.0.dev9"},
        "artifact": {"sha256": artifact_sha, "bytes": 123},
        "runtime": {"expected_platform": "linux-x86_64-cp314"},
    }
    receipt = {
        "schema": "scirel.dev9-linux-acceptance.v1",
        "status": "PASS",
        "source": {"revision": source_revision},
        "validation": inner,
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    wheel = {
        "version": "0.1.0.dev9",
        "artifact": {"sha256": artifact_sha, "bytes": 123},
        "platform_receipts": [
            {
                "platform": "linux-x86_64-cp314",
                "path": "receipt.json",
                "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            }
        ],
    }

    _validate_platform_receipts(
        tmp_path, wheel, expected_source_revision=source_revision
    )
    with pytest.raises(ValueError, match="source revision differs"):
        _validate_platform_receipts(
            tmp_path, wheel, expected_source_revision="c" * 40
        )

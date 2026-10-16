from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_release_alignment import validate_alignment  # noqa: E402


def test_current_release_alignment_is_exact() -> None:
    result = validate_alignment(ROOT)
    assert result["wheel_version"] == "0.1.0.dev9"
    assert result["documentation_version"] == "scientific-core-r18"
    assert result["source_revision"] is None
    assert result["capability_counts"] == {
        "operators": 230,
        "task_graphs": 30,
        "document_closure": 260,
    }


def test_legacy_current_files_are_thin_compatibility_pointers() -> None:
    for line in ("wheel", "docs"):
        path = ROOT / "release" / line / "CURRENT.json"
        pointer = json.loads(path.read_text())
        assert pointer["schema"] == "scirel.release-compat-pointer.v1"
        assert pointer["canonical"] == "../CURRENT.json"
        assert pointer["deprecated"] is True


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
    current_path = tmp_path / "release/CURRENT.json"
    current = json.loads(current_path.read_text())
    current["documentation"]["capability_counts"]["document_closure"] += 1
    current_path.write_text(json.dumps(current), encoding="utf-8")
    with pytest.raises(ValueError, match="capability_counts"):
        validate_alignment(tmp_path)

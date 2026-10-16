from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_platform_support import validate_matrix  # noqa: E402


def test_platform_matrix_is_explicit_and_fail_closed() -> None:
    result = validate_matrix(ROOT)
    assert result["platforms"]["linux-x86_64-cp314"] == "PARTIAL"
    assert result["platforms"]["windows-amd64-cp314"] == "NOT_RUN"
    assert result["capabilities"]["fluidbw-native-octave"] == "PASS"
    assert result["capabilities"]["pdrk-native-octave"] == "PARTIAL"


def test_missing_evidence_is_rejected(tmp_path: Path) -> None:
    import json
    import shutil

    shutil.copytree(ROOT / "release", tmp_path / "release")
    matrix_path = tmp_path / "release/platform-support-matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    matrix["platforms"][0]["evidence"] = ["missing.json"]
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(ValueError, match="evidence is missing"):
        validate_matrix(tmp_path)

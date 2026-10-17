from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.validate_platform_support import validate_matrix  # noqa: E402


def _isolated_matrix_root(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    import json
    import shutil

    shutil.copytree(ROOT / "release", tmp_path / "release")
    (tmp_path / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
    matrix_path = tmp_path / "release/platform-support-matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    for index, row in enumerate(matrix["platforms"]):
        evidence = f"evidence-{index}.json"
        row["evidence"] = [evidence]
        (tmp_path / evidence).write_text("{}\n", encoding="utf-8")
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    return matrix_path, matrix


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
    (tmp_path / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
    matrix_path = tmp_path / "release/platform-support-matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    matrix["platforms"][0]["evidence"] = ["missing.json"]
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(ValueError, match="evidence is missing"):
        validate_matrix(tmp_path)


def test_platform_id_and_python_metadata_must_agree(tmp_path: Path) -> None:
    import json

    matrix_path, matrix = _isolated_matrix_root(tmp_path)
    matrix["platforms"][0]["architecture"] = "aarch64"
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(ValueError, match="canonical id"):
        validate_matrix(tmp_path)


def test_platform_python_line_must_be_covered_by_project_metadata(tmp_path: Path) -> None:
    import json

    matrix_path, matrix = _isolated_matrix_root(tmp_path)
    project_path = tmp_path / "pyproject.toml"
    project = project_path.read_text(encoding="utf-8")
    project_path.write_text(project.replace(">=3.14,<3.15", ">=3.13,<3.14"), encoding="utf-8")
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(ValueError, match="outside project.requires-python"):
        validate_matrix(tmp_path)


def test_platform_matrix_rejects_version_drift(tmp_path: Path) -> None:
    import json
    import shutil

    shutil.copytree(ROOT / "release", tmp_path / "release")
    (tmp_path / "pyproject.toml").write_bytes((ROOT / "pyproject.toml").read_bytes())
    matrix_path = tmp_path / "release/platform-support-matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    matrix["package_version"] = "0.1.0.dev999"
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(ValueError, match="package_version"):
        validate_matrix(tmp_path)

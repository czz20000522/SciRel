from __future__ import annotations

import json
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


def _bind_pass_capability(tmp_path: Path, matrix: dict[str, object]) -> Path:
    current = json.loads((tmp_path / "release/CURRENT.json").read_text(encoding="utf-8"))
    artifact = current["wheel"]["artifact"]
    receipt_path = tmp_path / "capability-receipt.json"
    receipt_path.write_text(
        json.dumps(
            {
                "schema": "scirel.capability-validation.v1",
                "status": "PASS",
                "source_revision": current["source_revision"],
                "package": {"version": current["version"]},
                "artifact": {
                    "sha256": artifact["sha256"],
                    "bytes": artifact["bytes"],
                },
            }
        ),
        encoding="utf-8",
    )
    for row in matrix["capabilities"]:
        if row["status"] == "PASS":
            row["evidence"] = ["capability-receipt.json"]
            break
    return receipt_path


def test_platform_matrix_is_explicit_and_fail_closed() -> None:
    result = validate_matrix(ROOT)
    assert result["platforms"]["linux-x86_64-cp314"] == "PARTIAL"
    assert result["platforms"]["windows-amd64-cp314"] == "NOT_RUN"
    assert result["platforms"]["macos-arm64-cp314"] == "PARTIAL"
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


def test_pass_capability_requires_current_release_bound_receipt(tmp_path: Path) -> None:
    matrix_path, matrix = _isolated_matrix_root(tmp_path)
    for row in matrix["capabilities"]:
        if row["status"] == "PASS":
            row.pop("evidence", None)
            break
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(ValueError, match="requires bound evidence"):
        validate_matrix(tmp_path)


def test_pass_capability_accepts_receipt_bound_to_current_wheel(tmp_path: Path) -> None:
    matrix_path, matrix = _isolated_matrix_root(tmp_path)
    _bind_pass_capability(tmp_path, matrix)
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    result = validate_matrix(tmp_path)
    assert result["capabilities"]["fluidbw-native-octave"] == "PASS"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("source_revision", "0" * 40, "source revision differs"),
        ("package_version", "0.1.0.dev8", "package version differs"),
        ("sha256", "0" * 64, "wheel sha256 differs"),
        ("bytes", 1, "wheel bytes differs"),
    ],
)
def test_pass_capability_rejects_stale_receipt_binding(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    import json

    matrix_path, matrix = _isolated_matrix_root(tmp_path)
    receipt_path = _bind_pass_capability(tmp_path, matrix)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if field == "package_version":
        receipt["package"]["version"] = value
    elif field in {"sha256", "bytes"}:
        receipt["artifact"][field] = value
    else:
        receipt[field] = value
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        validate_matrix(tmp_path)


def test_non_pass_capability_keeps_optional_historical_evidence_boundary(
    tmp_path: Path,
) -> None:
    matrix_path, matrix = _isolated_matrix_root(tmp_path)
    _bind_pass_capability(tmp_path, matrix)
    (tmp_path / "historical.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "wheel": {
                    "version": "0.1.0.dev8",
                    "sha256": "0" * 64,
                },
            }
        ),
        encoding="utf-8",
    )
    for row in matrix["capabilities"]:
        if row["status"] == "PARTIAL":
            row["evidence"] = ["historical.json"]
            break
    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
    validate_matrix(tmp_path)

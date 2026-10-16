from __future__ import annotations

import subprocess
from pathlib import Path
import tomllib
import json
import re
import hashlib
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


ROOT = Path(__file__).resolve().parents[1]


def test_git_release_structure_has_one_version_source() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    current = json.loads((ROOT / "release/CURRENT.json").read_text(encoding="utf-8"))
    assert current["version"] == version
    assert current["wheel"]["version"] == version
    assert current["documentation"]["compatible_wheel"] == version
    assert (ROOT / f"docs/release/{version}-notes.md").is_file()


def test_historical_release_data_is_not_parallel_wheel_or_doc_copies() -> None:
    assert not list((ROOT / "release/wheel/versions").glob("*"))
    assert not list((ROOT / "release/docs/versions").glob("*"))
    versioned_release_files = [
        path
        for line in ("wheel", "docs")
        for path in (ROOT / "release" / line).rglob("*")
        if path.is_file() and re.search(r"\d+\.\d+\.\d+", path.name)
    ]
    assert versioned_release_files == []
    tracked = subprocess.check_output(
        ["git", "ls-files", "*.whl", "dist", "build"],
        cwd=ROOT,
        text=True,
    )
    assert tracked.strip() == ""
    assert not list((ROOT / "tools/docs/handbooks").glob("*.json"))
    assert (ROOT / "tools/docs/handbook.json").is_file()


def test_current_release_receipt_is_not_the_version_source() -> None:
    text = (ROOT / "release/README.md").read_text(encoding="utf-8")
    assert "not a second version" in text
    assert "pyproject.toml" in text


def test_ref_bound_build_helper_is_documented_and_keeps_artifacts_external() -> None:
    helper = ROOT / "scripts/build_scirel_from_ref.py"
    docs_helper = ROOT / "scripts/build_scirel_docs_from_ref.py"
    text = helper.read_text(encoding="utf-8")
    readme = (ROOT / "release/wheel/README.md").read_text(encoding="utf-8")
    assert "git archive" in text
    assert "output-dir must be outside" in text
    assert "build_scirel_from_ref.py" in readme
    assert "git archive" in docs_helper.read_text(encoding="utf-8")
    assert "build_scirel_docs_from_ref.py" in (ROOT / "release/docs/README.md").read_text(encoding="utf-8")


def test_document_selection_materializes_only_digest_bound_records(tmp_path: Path) -> None:
    from build_scirel_docs_from_ref import _materialize_selection, _materialize_translations

    source = tmp_path / "source"
    document = source / "catalog/examples/scirel.test.example.json"
    document.parent.mkdir(parents=True)
    document.write_text('{"asset_id":"scirel.test.example"}\n', encoding="utf-8")
    selection = source / "provenance/selections/current.json"
    selection.parent.mkdir(parents=True)
    digest = hashlib.sha256(document.read_bytes()).hexdigest()
    selection.write_text(
        json.dumps(
            {
                "schema": "scirel.selected-document-set.v1",
                "records": [
                    {
                        "asset_id": "scirel.test.example",
                        "path": "catalog/examples/scirel.test.example.json",
                        "sha256": digest,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = _materialize_selection(source, "provenance/selections/current.json", tmp_path / "staging")

    assert result["asset_count"] == 1
    assert (tmp_path / "staging/selected-documents/scirel.test.example.json").read_bytes() == document.read_bytes()


def test_document_selection_filters_reader_bundle_to_exact_assets(tmp_path: Path) -> None:
    from build_scirel_docs_from_ref import _materialize_translations

    source = tmp_path / "source"
    reader_root = source / "tools/docs/zh"
    reader_root.mkdir(parents=True)
    reader_root.joinpath("domain.json").write_text(
        json.dumps(
            {
                "schema": "scirel.reader-translation.v1",
                "language": "zh-CN",
                "records": [
                    {"asset_id": "scirel.selected"},
                    {"asset_id": "scirel.unselected"},
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "staging").mkdir()

    result = _materialize_translations(source, {"scirel.selected"}, tmp_path / "staging")

    bundle = json.loads((tmp_path / "staging/selected-reader-bundle.json").read_text(encoding="utf-8"))
    assert result["asset_count"] == 1
    assert [record["asset_id"] for record in bundle["records"]] == ["scirel.selected"]

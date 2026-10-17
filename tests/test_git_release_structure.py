from __future__ import annotations

import subprocess
from pathlib import Path
import tomllib
import json
import re
import hashlib
import sys
import stat

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


ROOT = Path(__file__).resolve().parents[1]


def test_git_release_structure_has_one_version_source() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    current = json.loads((ROOT / "release/CURRENT.json").read_text(encoding="utf-8"))
    assert current["schema"] == "scirel.release-current.v2"
    assert current["version"] == version
    assert current["wheel"]["version"] == version
    assert current["documentation"]["compatible_wheel"] == version
    assert "asset_implementation_baselines" not in current["documentation"]
    assert "path" not in current["wheel"]["artifact"]
    assert current["wheel"]["artifact"]["manifest_ref"].endswith("/wheel/build-manifest.json")
    assert current["documentation"]["artifact"]["manifest_ref"].endswith("/docs/build-manifest.json")
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
    assert "build/releases" not in (ROOT / "release/CURRENT.json").read_text(encoding="utf-8")
    assert not list((ROOT / "tools/docs/handbooks").glob("*.json"))
    assert (ROOT / "tools/docs/handbook.json").is_file()
    chapter_dirs = sorted(
        path.name for path in (ROOT / "tools/docs").glob("magnetostatics*") if path.is_dir()
    )
    assert chapter_dirs == ["magnetostatics"]
    selection = json.loads((ROOT / "tools/docs/chapter-selection.json").read_text(encoding="utf-8"))
    assert selection["chapters"]["magnetostatics"]["directory"] == "tools/docs/magnetostatics"


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
    assert "normalizes regular-file and directory modes" in readme


def test_ref_bound_build_input_binding_covers_project_lock_license_and_helper() -> None:
    from build_scirel_from_ref import build_input_binding

    binding = build_input_binding(
        ROOT,
        helper_paths=("scripts/build_scirel_from_ref.py",),
    )

    assert binding["schema"] == "scirel.build-inputs.v1"
    files = binding["files"]
    assert set(("pyproject.toml", "uv.lock")) <= set(files)
    assert binding["license_files"]
    assert binding["helper"]["files"]["scripts/build_scirel_from_ref.py"]["bytes"] > 0
    for summary in files.values():
        assert len(summary["sha256"]) == 64
        assert summary["bytes"] > 0


def test_ref_bound_archive_normalizes_umask_dependent_modes(tmp_path: Path) -> None:
    from build_scirel_from_ref import _normalize_archive_modes

    source = tmp_path / "source"
    source.mkdir(mode=0o775)
    data = source / "package-data.m"
    executable = source / "tool.sh"
    nested = source / "nested"
    nested.mkdir(mode=0o775)
    data.write_text("data\n", encoding="utf-8")
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    (nested / "metadata.json").write_text("{}\n", encoding="utf-8")
    data.chmod(0o664)
    executable.chmod(0o775)
    (nested / "metadata.json").chmod(0o664)

    _normalize_archive_modes(source)

    assert stat.S_IMODE(data.stat().st_mode) == 0o644
    assert stat.S_IMODE((nested / "metadata.json").stat().st_mode) == 0o644
    assert stat.S_IMODE(executable.stat().st_mode) == 0o755
    assert stat.S_IMODE(source.stat().st_mode) == 0o755
    assert stat.S_IMODE(nested.stat().st_mode) == 0o755


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


def test_current_document_selection_matches_project_version() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    expected = project["project"]["version"]
    selection = json.loads(
        (ROOT / "provenance/selections/scientific-core-documents-20261017-dev9.json")
        .read_text(encoding="utf-8")
    )
    for record in selection["records"]:
        document = json.loads((ROOT / record["path"]).read_text(encoding="utf-8"))
        assert document["version"]["implementation_version"] == expected


def test_current_document_tuple_has_one_implementation_version() -> None:
    current = json.loads((ROOT / "release/CURRENT.json").read_text(encoding="utf-8"))
    documentation = current["documentation"]
    assert set(documentation).isdisjoint({"asset_implementation_baselines", "versions"})
    assert documentation["compatible_wheel"] == current["version"]


def test_ref_bound_document_builder_requires_selection(tmp_path: Path) -> None:
    from build_scirel_docs_from_ref import build_from_ref

    try:
        build_from_ref("HEAD", tmp_path / "selection-required")
    except ValueError as error:
        assert "requires --selection" in str(error)
    else:
        raise AssertionError("unbound ref documentation build unexpectedly succeeded")


def test_release_notes_do_not_duplicate_dynamic_artifact_identity() -> None:
    current = json.loads((ROOT / "release/CURRENT.json").read_text(encoding="utf-8"))
    note_paths = sorted((ROOT / "docs/release").glob("*-notes.md"))
    assert note_paths
    for path in note_paths:
        notes = path.read_text(encoding="utf-8")
        assert "release/CURRENT.json" in notes
        assert not re.search(r"scirel-[^`\s]+\.whl", notes)
        assert not re.search(r"(?i)sha-?256", notes)
        assert not re.search(r"(?i)source[_ ]revision", notes)
        assert not re.search(r"(?i)\b[0-9a-f]{40}\b", notes)
        assert not re.search(r"(?i)\b[0-9a-f]{64}\b", notes)
    current_note = (ROOT / "docs/release/0.1.0.dev9-notes.md").read_text(encoding="utf-8")
    assert current["source_revision"] not in current_note
    assert current["wheel"]["artifact"]["sha256"] not in current_note


def test_release_design_docs_do_not_copy_candidate_versions() -> None:
    version_literal = re.compile(r"\b\d+\.\d+\.\d+\.dev\d+\b")
    wheel_filename = re.compile(r"\bscirel-[^`\s]+\.whl\b")
    for path in (
        ROOT / "docs/design/scirel-git-release-model.md",
        ROOT / "docs/design/scirel-wheel-packaging-strategy.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert not version_literal.search(text), path
        assert not wheel_filename.search(text), path


def test_scipy_style_git_release_model_is_explicit() -> None:
    design = (ROOT / "docs/design/scirel-git-release-model.md").read_text(encoding="utf-8")
    required_phrases = (
        "pyproject.toml",
        "短小的",
        "外部输出",
        "release/CURRENT.json",
        "release/wheel/versions/",
        "release/docs/versions/",
        "tools/building/gitversion.py",
        "doc/source/release/",
        "git_revision",
        "scipy-release",
        "SOURCE_REF_TO_BUILD",
        "SCIREL_SOURCE_REF_TO_BUILD",
    )
    for phrase in required_phrases:
        assert phrase in design
    assert not list((ROOT / "release/wheel/versions").glob("*"))
    assert not list((ROOT / "release/docs/versions").glob("*"))
    tracked_artifacts = subprocess.check_output(
        ["git", "ls-files", "*.whl"],
        cwd=ROOT,
        text=True,
        shell=False,
    )
    assert tracked_artifacts.strip() == ""
    tracked_html = subprocess.check_output(
        ["git", "ls-files", "*.html"],
        cwd=ROOT,
        text=True,
        shell=False,
    ).splitlines()
    assert all(path.startswith("tools/docs/") for path in tracked_html)

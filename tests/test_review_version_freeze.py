import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import freeze_review_version as freeze_module  # noqa: E402
from build_catalog import build_catalog  # noqa: E402


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    repo = tmp_path / "repo"
    documents = repo / "catalog" / "examples"
    documents.mkdir(parents=True)
    shutil.copy2(
        ROOT / "catalog/examples/scirel.geometry.planar-wavevector-projection.json",
        documents,
    )
    dossier = repo / "review.md"
    dossier.write_text("Initial whole-version review scope.\n", encoding="utf-8")
    material = repo / "docs" / "domains" / "field.md"
    material.parent.mkdir(parents=True)
    material.write_text("# Field review\nBounded development evidence.\n", encoding="utf-8")
    package = repo / "src" / "scirel"
    package.mkdir(parents=True)
    (package / "__init__.py").write_bytes(b"VERSION = 'current'\n")
    _git(repo, "init")
    _git(repo, "add", ".")
    _git(
        repo, "-c", "user.name=SciRel Test", "-c", "user.email=test@example.invalid",
        "commit", "-m", "review fixture",
    )
    monkeypatch.setattr(freeze_module, "ROOT", repo)

    catalog = tmp_path / "catalog"
    build_catalog(
        documents,
        catalog,
        catalog_id="test-development",
        release_version="0.1.0.dev15",
        coverage_status="partial",
        declared_total=63,
    )
    wheel = tmp_path / "scirel-0.1.0.dev15-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "scirel-0.1.0.dev15.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: scirel\nVersion: 0.1.0.dev15\n",
        )
        archive.writestr("scirel/__init__.py", "VERSION = 'current'\n")
    evidence = tmp_path / "tests.md"
    evidence.write_text("Focused test passed.\n", encoding="utf-8")
    return {
        "documents_dir": documents,
        "catalog_dir": catalog,
        "wheel": wheel,
        "review_dossier": dossier,
        "test_evidence": evidence,
        "output_dir": tmp_path / "review-version",
    }


def test_freeze_binds_clean_commit_documents_catalog_and_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)

    manifest = freeze_module.freeze_review_version(**inputs)

    saved = json.loads((inputs["output_dir"] / "manifest.json").read_text(encoding="utf-8"))
    assert saved == manifest
    assert manifest["review_status"] == "pending_unapproved"
    assert manifest["trusted_baseline"] is None
    assert manifest["catalog"]["coverage"]["included_asset_count"] == 1
    assert len(manifest["exact_documents"]) == 1
    for entry in [manifest["review_dossier"], *manifest["exact_documents"]]:
        saved_path = inputs["output_dir"] / entry["snapshot_path"]
        assert saved_path.is_file()
        assert entry["sha256"] == "sha256:" + hashlib.sha256(saved_path.read_bytes()).hexdigest()
    assert (inputs["output_dir"] / manifest["wheel"]["path"]).is_file()
    assert (inputs["output_dir"] / "test-evidence.md").is_file()
    with pytest.raises(FileExistsError, match="already exists"):
        freeze_module.freeze_review_version(**inputs)


def test_freeze_preserves_worktree_line_endings_outside_source_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    repo = inputs["review_dossier"].parent
    document = next(inputs["documents_dir"].glob("*.json"))
    package_module = repo / "src/scirel/__init__.py"
    _git(repo, "config", "core.autocrlf", "true")
    for path in (document, inputs["review_dossier"], package_module):
        data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        path.write_bytes(data)
    _git(repo, "add", ".")
    assert not subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, check=True, capture_output=True
    ).stdout
    blob = subprocess.run(
        ["git", "show", "HEAD:catalog/examples/" + document.name],
        cwd=repo, check=True, capture_output=True,
    ).stdout
    assert blob != document.read_bytes()
    package_blob = subprocess.run(
        ["git", "show", "HEAD:src/scirel/__init__.py"],
        cwd=repo, check=True, capture_output=True,
    ).stdout
    assert package_blob != package_module.read_bytes()

    manifest = freeze_module.freeze_review_version(**inputs)
    archived = tmp_path / "detached-review"
    inputs["output_dir"].rename(archived)
    repo.rename(tmp_path / "source-away")
    for entry in [manifest["review_dossier"], *manifest["exact_documents"]]:
        saved = archived / entry["snapshot_path"]
        assert entry["sha256"] == "sha256:" + hashlib.sha256(saved.read_bytes()).hexdigest()
    assert (archived / "catalog/release.json").is_file()


def test_freeze_copies_explicit_review_material_for_detached_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    repo = inputs["review_dossier"].parent
    material = repo / "docs/domains/field.md"
    inputs["review_materials"] = [material]

    manifest = freeze_module.freeze_review_version(**inputs)
    archived = tmp_path / "detached-review"
    inputs["output_dir"].rename(archived)
    repo.rename(tmp_path / "source-away")

    assert len(manifest["review_materials"]) == 1
    entry = manifest["review_materials"][0]
    assert entry["path"] == "docs/domains/field.md"
    assert (archived / entry["snapshot_path"]).read_text(encoding="utf-8").startswith("# Field review")
    assert entry["sha256"] == "sha256:" + hashlib.sha256(
        (archived / entry["snapshot_path"]).read_bytes()
    ).hexdigest()


def test_freeze_rejects_untracked_or_repeated_review_material(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    repo = inputs["review_dossier"].parent
    material = repo / "docs/domains/field.md"
    with pytest.raises(ValueError, match="repeated"):
        freeze_module.freeze_review_version(**inputs, review_materials=[material, material])

    untracked = repo / "docs/domains/untracked.md"
    untracked.write_text("draft", encoding="utf-8")
    with pytest.raises(ValueError, match="clean Git worktree"):
        freeze_module.freeze_review_version(**inputs, review_materials=[untracked])


def test_freeze_rejects_review_material_changed_while_copying(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    material = inputs["review_dossier"].parent / "docs/domains/field.md"
    original_copy = freeze_module.shutil.copy2

    def changed_copy(src, dst, *args, **kwargs):
        result = original_copy(src, dst, *args, **kwargs)
        if Path(src) == material:
            Path(dst).write_text("changed", encoding="utf-8")
        return result

    monkeypatch.setattr(freeze_module.shutil, "copy2", changed_copy)
    with pytest.raises(ValueError, match="review material changed during freeze"):
        freeze_module.freeze_review_version(**inputs, review_materials=[material])


def test_freeze_rejects_committed_document_change_without_rebuilt_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    document = next(inputs["documents_dir"].glob("*.json"))
    payload = json.loads(document.read_text(encoding="utf-8"))
    payload["summary"] += " Revised contract."
    document.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _git(document.parents[2], "add", ".")
    _git(
        document.parents[2], "-c", "user.name=SciRel Test",
        "-c", "user.email=test@example.invalid", "commit", "-m", "revise document",
    )

    with pytest.raises(ValueError, match="catalog records differ"):
        freeze_module.freeze_review_version(**inputs)


def test_freeze_rejects_wheel_with_stale_scientific_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    with zipfile.ZipFile(inputs["wheel"], "w") as archive:
        archive.writestr(
            "scirel-0.1.0.dev15.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: scirel\nVersion: 0.1.0.dev15\n",
        )
        archive.writestr("scirel/__init__.py", "VERSION = 'stale'\n")

    with pytest.raises(ValueError, match="wheel package differs from committed source"):
        freeze_module.freeze_review_version(**inputs)


def test_freeze_accepts_wheel_with_windows_source_line_endings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    with zipfile.ZipFile(inputs["wheel"], "w") as archive:
        archive.writestr(
            "scirel-0.1.0.dev15.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: scirel\nVersion: 0.1.0.dev15\n",
        )
        archive.writestr("scirel/__init__.py", b"VERSION = 'current'\r\n")

    manifest = freeze_module.freeze_review_version(**inputs)
    assert manifest["review_status"] == "pending_unapproved"


def test_freeze_allows_snapshot_beside_tracked_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    inputs["output_dir"] = inputs["review_dossier"].parent / "review-version"

    manifest = freeze_module.freeze_review_version(**inputs)

    assert (inputs["output_dir"] / manifest["exact_documents"][0]["snapshot_path"]).is_file()


@pytest.mark.parametrize("artifact,expected", [
    ("wheel", "wheel changed during freeze"),
    ("test_evidence", "test evidence changed during freeze"),
])
def test_freeze_rejects_changed_copied_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, artifact: str, expected: str
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    original_copy = freeze_module.shutil.copy2
    source = inputs[artifact]

    def changed_copy(src, dst, *args, **kwargs):
        result = original_copy(src, dst, *args, **kwargs)
        if Path(src) == source:
            Path(dst).write_bytes(b"changed after validation")
        return result

    monkeypatch.setattr(freeze_module.shutil, "copy2", changed_copy)
    with pytest.raises(ValueError, match=expected):
        freeze_module.freeze_review_version(**inputs)


def test_freeze_rejects_dirty_source_or_mismatched_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    inputs["review_dossier"].write_text("Changed after commit.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="clean Git worktree"):
        freeze_module.freeze_review_version(**inputs)

    _git(inputs["review_dossier"].parent, "restore", "review.md")
    with zipfile.ZipFile(inputs["wheel"], "w") as archive:
        archive.writestr(
            "scirel-0.2.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: scirel\nVersion: 0.2.0\n",
        )
    with pytest.raises(ValueError, match="versions differ"):
        freeze_module.freeze_review_version(**inputs)


def test_freeze_rejects_output_nested_in_input_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _inputs(tmp_path, monkeypatch)
    inputs["output_dir"] = inputs["catalog_dir"] / "review-version"
    with pytest.raises(ValueError, match="inside its input catalog"):
        freeze_module.freeze_review_version(**inputs)

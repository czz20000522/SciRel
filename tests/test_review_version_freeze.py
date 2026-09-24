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
        release_version="0.1.0.dev6",
        coverage_status="partial",
        declared_total=63,
    )
    wheel = tmp_path / "scirel-0.1.0.dev6-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "scirel-0.1.0.dev6.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: scirel\nVersion: 0.1.0.dev6\n",
        )
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
    assert (inputs["output_dir"] / manifest["wheel"]["path"]).is_file()
    assert (inputs["output_dir"] / "test-evidence.md").is_file()
    with pytest.raises(FileExistsError, match="already exists"):
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

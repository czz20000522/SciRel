from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = _load("build_extraction_skill_bundle")
installer = _load("install_extraction_skill_bundle")


def _source_tree(root: Path) -> Path:
    source = root / "skills"
    for index, name in enumerate(builder.SKILL_NAMES):
        skill = source / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"---\nname: {name}\n---\nbody {index}\n", encoding="utf-8")
        (skill / "references").mkdir()
        (skill / "references" / "contract.md").write_text(f"contract {index}\n", encoding="utf-8")
    return source


def test_bundle_is_deterministic_and_contains_exact_five_skills(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    first_manifest = builder.build_bundle(source, first)
    second_manifest = builder.build_bundle(source, second)

    assert first.read_bytes() == second.read_bytes()
    assert first_manifest == second_manifest
    assert first_manifest["skill_names"] == list(builder.SKILL_NAMES)
    with zipfile.ZipFile(first) as archive:
        stored = json.loads(archive.read(builder.MANIFEST_PATH))
    assert stored == first_manifest


def test_builder_rejects_missing_skill_entrypoint(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    (source / builder.SKILL_NAMES[-1] / "SKILL.md").unlink()

    with pytest.raises(ValueError, match="missing required skill entrypoint"):
        builder.build_bundle(source, tmp_path / "bundle.zip")


def test_installer_rejects_tampered_payload(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    bundle = tmp_path / "bundle.zip"
    builder.build_bundle(source, bundle)
    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(bundle) as original, zipfile.ZipFile(tampered, "w") as output:
        for info in original.infolist():
            content = original.read(info.filename)
            if info.filename.endswith("/SKILL.md"):
                content += b"tampered\n"
            output.writestr(info, content)

    with pytest.raises(ValueError, match="digest mismatch"):
        installer.install_bundle(tampered, tmp_path / "target", dry_run=True)


def test_dry_run_validates_without_writing(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    bundle = tmp_path / "bundle.zip"
    builder.build_bundle(source, bundle)
    target = tmp_path / "target"

    plan = installer.install_bundle(bundle, target, dry_run=True)

    assert plan["schema"] == "scirel.extraction-skill-install-plan.v1"
    assert not target.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="runtime installation uses POSIX directory symlinks")
def test_install_switches_all_entrypoints_and_removes_previous_bundle(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    first = tmp_path / "first.zip"
    first_manifest = builder.build_bundle(source, first)
    target = tmp_path / "target"
    first_receipt = installer.install_bundle(first, target)
    assert first_receipt["bundle_digest"] == first_manifest["bundle_digest"]
    for name in builder.SKILL_NAMES:
        assert (target / name / "SKILL.md").is_file()
    installed = next((target / installer.BUNDLE_DIR).iterdir())
    assert installed.stat().st_mode & 0o222 == 0
    assert (installed / builder.SKILL_NAMES[0] / "SKILL.md").stat().st_mode & 0o222 == 0

    (source / builder.SKILL_NAMES[0] / "SKILL.md").write_text("changed\n", encoding="utf-8")
    second = tmp_path / "second.zip"
    second_manifest = builder.build_bundle(source, second)
    second_receipt = installer.install_bundle(second, target)

    assert second_receipt["bundle_digest"] == second_manifest["bundle_digest"]
    bundle_dirs = list((target / installer.BUNDLE_DIR).iterdir())
    assert [path.name for path in bundle_dirs] == [
        "sha256-" + str(second_manifest["bundle_digest"]).removeprefix("sha256:")
    ]
    assert (target / builder.SKILL_NAMES[0] / "SKILL.md").read_text(encoding="utf-8") == "changed\n"


def test_installer_refuses_foreign_skill_directory(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    bundle = tmp_path / "bundle.zip"
    builder.build_bundle(source, bundle)
    target = tmp_path / "target"
    foreign = target / builder.SKILL_NAMES[0]
    foreign.mkdir(parents=True)

    with pytest.raises(ValueError, match="non-SciRel skill directories"):
        installer.install_bundle(bundle, target, dry_run=True)


def test_installer_refuses_foreign_active_bundle_path(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    bundle = tmp_path / "bundle.zip"
    builder.build_bundle(source, bundle)
    target = tmp_path / "target"
    (target / installer.ACTIVE_LINK).mkdir(parents=True)

    with pytest.raises(ValueError, match="foreign active bundle path"):
        installer.install_bundle(bundle, target, dry_run=True)


@pytest.mark.skipif(sys.platform == "win32", reason="runtime installation uses POSIX directory symlinks")
def test_installer_refuses_foreign_skill_symlink(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    bundle = tmp_path / "bundle.zip"
    builder.build_bundle(source, bundle)
    target = tmp_path / "target"
    target.mkdir()
    (target / builder.SKILL_NAMES[0]).symlink_to(tmp_path, target_is_directory=True)

    with pytest.raises(ValueError, match="non-SciRel skill directories"):
        installer.install_bundle(bundle, target, dry_run=True)


@pytest.mark.skipif(sys.platform == "win32", reason="runtime installation uses POSIX directory symlinks")
def test_installer_rejects_tampered_existing_content_addressed_bundle(tmp_path: Path) -> None:
    source = _source_tree(tmp_path)
    bundle = tmp_path / "bundle.zip"
    manifest = builder.build_bundle(source, bundle)
    target = tmp_path / "target"
    digest = str(manifest["bundle_digest"]).removeprefix("sha256:")
    existing = target / installer.BUNDLE_DIR / f"sha256-{digest}"
    existing.mkdir(parents=True)
    (existing / builder.MANIFEST_PATH).write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="file set does not match"):
        installer.install_bundle(bundle, target)


def test_failed_publish_removes_read_only_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source_tree(tmp_path)
    bundle = tmp_path / "bundle.zip"
    builder.build_bundle(source, bundle)
    target = tmp_path / "target"
    real_replace = installer.os.replace

    def reject_stage_publish(source_path: Path, destination_path: Path) -> None:
        source_path = Path(source_path)
        destination_path = Path(destination_path)
        if (
            source_path.name.startswith(".stage-")
            and destination_path.parent.name == installer.BUNDLE_DIR
        ):
            raise PermissionError("simulated publish failure")
        real_replace(source_path, destination_path)

    monkeypatch.setattr(installer.os, "replace", reject_stage_publish)

    with pytest.raises(PermissionError, match="simulated publish failure"):
        installer.install_bundle(bundle, target)

    bundle_root = target / installer.BUNDLE_DIR
    assert bundle_root.is_dir()
    assert list(bundle_root.iterdir()) == []

"""Verify that release staging contains only explicitly admitted SciRel assets."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_admitted_distribution.py"


def _build(staging: Path) -> subprocess.CompletedProcess[str]:
    return _build_from(ROOT, staging)


def _build_from(source_root: Path, staging: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--source-root",
            str(source_root),
            "--staging-dir",
            str(staging),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def _build_with_wheel(source_root: Path, staging: Path, wheel: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--source-root",
            str(source_root),
            "--staging-dir",
            str(staging),
            "--wheel-dir",
            str(wheel),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def _copy_builder_input(destination: Path) -> None:
    (destination / "provenance").mkdir(parents=True)
    shutil.copyfile(ROOT / "pyproject.toml", destination / "pyproject.toml")
    shutil.copyfile(
        ROOT / "provenance" / "admitted-assets.json",
        destination / "provenance" / "admitted-assets.json",
    )
    records = json.loads(
        (ROOT / "provenance" / "admitted-assets.json").read_text(encoding="utf-8")
    )
    for entry in records["integrations"]:
        module = Path("src", *entry["public_callable"].split(".")[:-1]).with_suffix(".py")
        target = destination / module
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / module, target)


def test_staging_contains_only_hash_locked_admitted_modules(tmp_path):
    staging = tmp_path / "staging"
    result = _build(staging)
    assert result.returncode == 0, result.stderr

    records = json.loads(
        (ROOT / "provenance" / "admitted-assets.json").read_text(encoding="utf-8")
    )
    expected_modules = {
        Path("src", *entry["public_callable"].split(".")[:-1]).with_suffix(".py")
        for entry in records["integrations"]
    }
    actual_modules = {
        path.relative_to(staging)
        for path in (staging / "src" / "scirel").rglob("*.py")
        if path.name != "__init__.py"
    }
    assert actual_modules == expected_modules
    assert all(b"\r\n" not in (staging / path).read_bytes() for path in actual_modules)
    assert not (staging / "src/scirel/equilibrium/anisotropic_force_balance.py").exists()

    manifest = json.loads(
        (staging / "src/scirel/_admitted_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["schema"] == "scirel.admitted-wheel-manifest.v1"
    assert manifest["distribution_version"] == "0.1.0.dev3"
    assert {item["public_callable"] for item in manifest["assets"]} == {
        entry["public_callable"] for entry in records["integrations"]
    }
    expected_admissions = {
        entry["admitted_input"]["admission"]["admission_ref"]
        for entry in records["integrations"]
    }
    expected_admissions.update(
        equivalent["admitted_input"]["admission"]["admission_ref"]
        for entry in records["integrations"]
        for equivalent in entry.get("equivalent_admitted_inputs", [])
    )
    assert set(manifest["admission_refs"]) == expected_admissions

    digest = manifest.pop("manifest_digest")
    canonical = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert digest == "sha256:" + hashlib.sha256(canonical).hexdigest()

    content_lock = json.loads(
        (staging / "scirel-content-lock.json").read_text(encoding="utf-8")
    )
    assert content_lock["schema"] == "scirel.distribution-content-lock.v1"
    for item in content_lock["files"]:
        payload = (staging / item["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]


def test_staged_public_surface_imports_without_the_development_tree(tmp_path):
    staging = tmp_path / "staging"
    result = _build(staging)
    assert result.returncode == 0, result.stderr

    probe = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            (
                "import json,sys;"
                f"sys.path.insert(0,{str(staging / 'src')!r});"
                "import scirel;"
                "from scirel.kinetic import assemble_mirror_total_pressure;"
                "assert callable(assemble_mirror_total_pressure);"
                "assert set(scirel.__all__)=={'closures','diagnostics','field','kinetic'};"
                "import importlib.util;"
                "assert importlib.util.find_spec('scirel.equilibrium') is None;"
                "print(json.dumps(sorted(scirel.__all__)))"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert probe.returncode == 0, probe.stderr


def test_builder_refuses_to_overwrite_an_existing_staging_directory(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    marker = staging / "keep.txt"
    marker.write_text("keep", encoding="utf-8")

    result = _build(staging)

    assert result.returncode != 0
    assert marker.read_text(encoding="utf-8") == "keep"
    assert "already exists" in result.stderr


def test_builder_rejects_source_drift_without_creating_output(tmp_path):
    source_root = tmp_path / "source"
    _copy_builder_input(source_root)
    records = json.loads(
        (source_root / "provenance/admitted-assets.json").read_text(encoding="utf-8")
    )
    module = Path("src", *records["integrations"][0]["public_callable"].split(".")[:-1]).with_suffix(".py")
    with (source_root / module).open("a", encoding="utf-8") as stream:
        stream.write("\n# unreviewed drift\n")
    staging = tmp_path / "staging"

    result = _build_from(source_root, staging)

    assert result.returncode != 0
    assert "source digest differs" in result.stderr
    assert not staging.exists()


def test_builder_rejects_incomplete_admission_provenance(tmp_path):
    source_root = tmp_path / "source"
    _copy_builder_input(source_root)
    provenance = source_root / "provenance/admitted-assets.json"
    records = json.loads(provenance.read_text(encoding="utf-8"))
    records["integrations"][0]["admitted_input"]["admission"]["decision_ref"] = None
    provenance.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    staging = tmp_path / "staging"

    result = _build_from(source_root, staging)

    assert result.returncode != 0
    assert "missing decision_ref" in result.stderr
    assert not staging.exists()


def test_wheel_build_is_reproducible(tmp_path):
    first = _build_with_wheel(ROOT, tmp_path / "stage-one", tmp_path / "wheel-one")
    second = _build_with_wheel(ROOT, tmp_path / "stage-two", tmp_path / "wheel-two")
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr

    first_result = json.loads(first.stdout)
    second_result = json.loads(second.stdout)
    assert first_result["wheel_sha256"] == second_result["wheel_sha256"]
    assert Path(first_result["wheel"]).read_bytes() == Path(second_result["wheel"]).read_bytes()

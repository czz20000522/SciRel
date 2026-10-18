"""Verify that release staging contains only explicitly admitted SciRel assets."""

import hashlib
import importlib.util
import json
import os
import pytest
import shutil
import subprocess
import sys
import tomllib
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts" / "build_admitted_distribution.py"
_BUILDER_SPEC = importlib.util.spec_from_file_location("scirel_admitted_builder", BUILDER)
assert _BUILDER_SPEC is not None and _BUILDER_SPEC.loader is not None
_BUILDER = importlib.util.module_from_spec(_BUILDER_SPEC)
_BUILDER_SPEC.loader.exec_module(_BUILDER)


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
    for entry in records.get("support_modules", []):
        module = Path("src", *entry["module"].split(".")).with_suffix(".py")
        target = destination / module
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / module, target)


def _write_module(source_root: Path, module_name: str, source: str) -> str:
    path = source_root / "src" / Path(*module_name.split(".")).with_suffix(".py")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = source.replace("\r\n", "\n").encode("utf-8")
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _set_support_modules(source_root: Path, modules: dict[str, str]) -> None:
    provenance = source_root / "provenance" / "admitted-assets.json"
    records = json.loads(provenance.read_text(encoding="utf-8"))
    records.setdefault("support_modules", []).extend([
        {
            "module": module_name,
            "library_source_lf_sha256": _write_module(source_root, module_name, source),
        }
        for module_name, source in modules.items()
    ])
    provenance.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")


def _add_support_import_to_selected_module(source_root: Path, import_statement: str) -> None:
    provenance = source_root / "provenance" / "admitted-assets.json"
    records = json.loads(provenance.read_text(encoding="utf-8"))
    entry = records["integrations"][0]
    module_name = entry["public_callable"].rsplit(".", 1)[0]
    source_path = source_root / "src" / Path(*module_name.split(".")).with_suffix(".py")
    digest = _write_module(
        source_root,
        module_name,
        source_path.read_text(encoding="utf-8") + "\n" + import_statement + "\n",
    )
    entry["library_source_lf_sha256"] = digest
    provenance.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")


def test_builder_reads_canonical_build_and_runtime_metadata(tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "pyproject.toml").write_text(
        """
[build-system]
requires = ["setuptools==84.0.0"]
build-backend = "setuptools.build_meta"

[project]
name = "scirel"
version = "9.8.7"
description = "Canonical test metadata"
requires-python = ">=3.14,<3.15"
dependencies = ["numpy==2.5.4", "scipy==1.18.1", "mpmath==1.4.1"]

[project.optional-dependencies]
plot = ["matplotlib==3.11.2"]
""".lstrip(),
        encoding="utf-8",
    )

    metadata = _BUILDER._read_project_metadata(source_root)
    rendered = tomllib.loads(_BUILDER._render_admitted_pyproject(metadata))

    assert rendered["build-system"] == {
        "requires": ["setuptools==84.0.0"],
        "build-backend": "setuptools.build_meta",
    }
    assert rendered["project"] == {
        "name": "scirel",
        "version": "9.8.7",
        "description": "Canonical test metadata",
        "requires-python": ">=3.14,<3.15",
        "dependencies": ["numpy==2.5.4", "scipy==1.18.1", "mpmath==1.4.1"],
        "optional-dependencies": {"plot": ["matplotlib==3.11.2"]},
    }


def test_builder_rejects_a_canonical_project_name_that_cannot_match_the_package_tree(tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "pyproject.toml").write_text(
        """
[build-system]
requires = ["setuptools==84.0.0"]
build-backend = "setuptools.build_meta"

[project]
name = "other-name"
version = "9.8.7"
requires-python = ">=3.14,<3.15"
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="project.name = 'scirel'"):
        _BUILDER._read_project_metadata(source_root)


def test_builder_staging_uses_canonical_runtime_metadata(tmp_path):
    source_root = tmp_path / "source"
    (source_root / "provenance").mkdir(parents=True)
    shutil.copyfile(ROOT / "pyproject.toml", source_root / "pyproject.toml")
    records = json.loads(
        (ROOT / "provenance" / "admitted-assets.json").read_text(encoding="utf-8")
    )
    entry = next(
        item
        for item in records["integrations"]
        if item["public_callable"].endswith("close_hall_two_fluid_pressure")
    )
    module = Path("src", *entry["public_callable"].split(".")[:-1]).with_suffix(".py")
    target = source_root / module
    target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / module, target)
    entry["library_source_lf_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    records["integrations"] = [entry]
    records["support_modules"] = []
    (source_root / "provenance" / "admitted-assets.json").write_text(
        json.dumps(records, ensure_ascii=False), encoding="utf-8"
    )

    staging = tmp_path / "staging"
    result = _build_from(source_root, staging)

    assert result.returncode == 0, result.stderr
    rendered = tomllib.loads((staging / "pyproject.toml").read_text(encoding="utf-8"))
    canonical = tomllib.loads((source_root / "pyproject.toml").read_text(encoding="utf-8"))
    assert rendered["build-system"] == {
        key: canonical["build-system"][key] for key in ("requires", "build-backend")
    }
    for key in ("name", "version", "description", "requires-python", "dependencies"):
        assert rendered["project"][key] == canonical["project"][key]
    assert rendered["project"]["optional-dependencies"] == canonical["project"]["optional-dependencies"]


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
    expected_modules.update(
        Path("src", *entry["module"].split(".")).with_suffix(".py")
        for entry in records.get("support_modules", [])
    )
    actual_modules = {
        path.relative_to(staging)
        for path in (staging / "src" / "scirel").rglob("*.py")
        if path.name != "__init__.py"
    }
    assert actual_modules == expected_modules
    assert all(b"\r\n" not in (staging / path).read_bytes() for path in actual_modules)
    assert (staging / "src/scirel/equilibrium/anisotropic_force_balance.py").exists()

    manifest = json.loads(
        (staging / "src/scirel/_admitted_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["schema"] == "scirel.admitted-wheel-manifest.v1"
    assert manifest["distribution_version"] == "0.1.0.dev5"
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
                "assert set(scirel.__all__)=={'closures','diagnostics','equilibrium','field','geometry','inference','kinetic'};"
                "import importlib.util;"
                "assert importlib.util.find_spec('scirel.equilibrium') is not None;"
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


def test_admitted_wheel_runs_a_source_free_scientific_relation(tmp_path):
    result = _build_with_wheel(ROOT, tmp_path / "staging", tmp_path / "wheel")
    assert result.returncode == 0, result.stderr
    wheel = Path(json.loads(result.stdout)["wheel"])

    environment = tmp_path / "environment"
    venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment)
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

    # A nested venv does not inherit packages installed in its parent venv.
    dependency_roots = []
    for module_name in ("numpy", "scipy"):
        spec = importlib.util.find_spec(module_name)
        assert spec is not None and spec.origin is not None
        dependency_roots.append(Path(spec.origin).resolve().parent.parent)
    site_packages = subprocess.run(
        [str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (Path(site_packages) / "scirel-test-dependencies.pth").write_text(
        "".join(f"{path}\n" for path in dict.fromkeys(dependency_roots)),
        encoding="utf-8",
    )

    install = subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--force-reinstall",
            str(wheel),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, install.stderr

    clean_environment = os.environ.copy()
    clean_environment["PYTHONPATH"] = site_packages
    probe = subprocess.run(
        [
            str(python),
            "-c",
            """
import importlib.metadata
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
from scirel.field.circular_filament_green import circular_filament_green_response

distribution = importlib.metadata.distribution("scirel")
package_root = Path(distribution.locate_file("scirel")).resolve()
assert package_root.is_relative_to(Path(sys.prefix).resolve())
with zipfile.ZipFile(sys.argv[1]) as archive:
    members = [name for name in archive.namelist() if name.startswith("scirel/") and name.endswith(".py")]
    assert members
    for member in members:
        assert distribution.locate_file(member).read_bytes() == archive.read(member), member

response = circular_filament_green_response([[0.35, 0.0, 1.0]], [[0.0, 0.2]])
expected_bz = 4.0 * np.pi * 1.0e-7 * 0.35**2 / (2.0 * (0.35**2 + 0.2**2) ** 1.5)
np.testing.assert_allclose(response["gBZ"], [expected_bz], rtol=1.0e-13, atol=0.0)
np.testing.assert_array_equal(response["gBR"], [0.0])
np.testing.assert_array_equal(response["gpsi"], [0.0])
print(json.dumps({"version": distribution.version, "module_root": str(package_root), "verified_python_files": len(members)}))
""",
            str(wheel),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=clean_environment,
    )
    assert probe.returncode == 0, probe.stderr

    report = json.loads(probe.stdout)
    assert report["version"] == "0.1.0.dev5"
    assert report["verified_python_files"] > 0
    assert Path(report["module_root"]).is_relative_to(environment)


def test_builder_stages_a_hash_locked_relative_support_module_closure(tmp_path):
    source_root = tmp_path / "source"
    _copy_builder_input(source_root)
    _add_support_import_to_selected_module(
        source_root,
        "from .._admitted_support import SUPPORT_VALUE",
    )
    _set_support_modules(
        source_root,
        {
            "scirel._admitted_support": (
                "from ._admitted_support_leaf import SUPPORT_VALUE\n"
            ),
            "scirel._admitted_support_leaf": "SUPPORT_VALUE = 1\n",
        },
    )
    staging = tmp_path / "staging"

    result = _build_from(source_root, staging)

    assert result.returncode == 0, result.stderr
    assert (staging / "src/scirel/_admitted_support.py").is_file()
    assert (staging / "src/scirel/_admitted_support_leaf.py").is_file()
    manifest = json.loads(
        (staging / "src/scirel/_admitted_manifest.json").read_text(encoding="utf-8")
    )
    assert all(
        not item["public_callable"].startswith("scirel._admitted_support")
        for item in manifest["assets"]
    )
    root_initializer = (staging / "src/scirel/__init__.py").read_text(encoding="utf-8")
    assert "_admitted_support" not in root_initializer
    content_lock = json.loads(
        (staging / "scirel-content-lock.json").read_text(encoding="utf-8")
    )
    assert {
        "src/scirel/_admitted_support.py",
        "src/scirel/_admitted_support_leaf.py",
    } <= {item["path"] for item in content_lock["files"]}


def test_builder_rejects_a_support_module_with_an_unbound_internal_import(tmp_path):
    source_root = tmp_path / "source"
    _copy_builder_input(source_root)
    _add_support_import_to_selected_module(
        source_root,
        "from .._admitted_support import SUPPORT_VALUE",
    )
    _set_support_modules(
        source_root,
        {"scirel._admitted_support": "from ._not_admitted import SUPPORT_VALUE\n"},
    )

    result = _build_from(source_root, tmp_path / "staging")

    assert result.returncode != 0
    assert "unbound internal import" in result.stderr
    assert not (tmp_path / "staging").exists()


def test_builder_rejects_invalid_support_module_provenance(tmp_path):
    source_root = tmp_path / "source"
    _copy_builder_input(source_root)
    provenance = source_root / "provenance" / "admitted-assets.json"
    records = json.loads(provenance.read_text(encoding="utf-8"))
    records["support_modules"] = [
        {
            "module": "scirel._admitted_support",
            "library_source_lf_sha256": "not-a-sha256-digest",
        }
    ]
    provenance.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

    result = _build_from(source_root, tmp_path / "staging")

    assert result.returncode != 0
    assert "invalid source digest for support module" in result.stderr
    assert not (tmp_path / "staging").exists()

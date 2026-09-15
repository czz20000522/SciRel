"""Verify that release staging contains only explicitly admitted SciRel assets."""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import venv
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


def test_admitted_wheel_runs_the_source_free_user_acceptance(tmp_path):
    result = _build_with_wheel(ROOT, tmp_path / "staging", tmp_path / "wheel")
    assert result.returncode == 0, result.stderr
    wheel = Path(json.loads(result.stdout)["wheel"])

    environment = tmp_path / "environment"
    venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment)
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

    # A nested venv does not inherit packages installed in its parent venv.
    dependency_roots = []
    for module_name in ("numpy", "scipy"):
        spec = importlib.util.find_spec(module_name)
        assert spec is not None and spec.origin is not None
        dependency_roots.append(Path(spec.origin).resolve().parent.parent)
    site_packages = subprocess.run(
        [str(python), "-c", "import site; print(site.getsitepackages()[0])"],
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

    output = tmp_path / "acceptance"
    clean_environment = os.environ.copy()
    clean_environment.pop("PYTHONPATH", None)
    acceptance = subprocess.run(
        [
            str(python),
            str(ROOT / "examples" / "user_acceptance.py"),
            "--wheel",
            str(wheel),
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=clean_environment,
    )
    assert acceptance.returncode == 0, acceptance.stderr

    report = json.loads((output / "acceptance.json").read_text(encoding="utf-8"))
    assert report["installation"]["version"] == "0.1.0.dev5"
    assert set(report["tasks"]) == {
        "green_field_synthesis",
        "pressure_state_and_residual",
        "quasineutral_profile",
    }
    assert all(task["passed"] for task in report["tasks"].values())
    assert Path(report["installation"]["module_root"]).is_relative_to(environment)


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

"""New builds share one maintained dependency baseline, including old selections."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
from email.parser import Parser

from packaging.specifiers import SpecifierSet

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from scientific_runtime import baseline, baseline_receipt, pin_dependencies
from prepare_reviewed_distribution import _project_for_release


def test_old_compatible_selection_gets_exact_current_pins():
    requested = ["numpy>=1.24", "scipy>=1.10", "matplotlib>=3.7"]
    # Selected builders declare the requested compatible subset, rather than
    # importing every dependency used by another selected scientific reader.
    expected = ["numpy==2.5.4", "scipy==1.18.1", "matplotlib==3.11.2"]
    assert pin_dependencies(requested) == expected
    with pytest.raises(ValueError, match="outside the scientific baseline"):
        pin_dependencies(["netCDF4>=1.7"])
    assert baseline()["project"]["dependencies"] == [
        "numpy==2.5.4", "scipy==1.18.1", "mpmath==1.4.1"
    ]
    assert baseline()["project"]["optional-dependencies"]["plot"] == ["matplotlib==3.11.2"]
    assert "netcdf" not in baseline()["project"]["optional-dependencies"]
    assert baseline_receipt()["pyproject_sha256"] == hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest()


@pytest.mark.parametrize("dependency", ["numpy<2", "numpy==1.26.4", "unknown-science", "scipy[extra]", "numpy; python_version<'3.14'", "numpy @ https://example.invalid/numpy.whl"])
def test_conflicting_or_unqualified_dependency_is_not_silently_replaced(dependency):
    with pytest.raises(ValueError):
        pin_dependencies([dependency])


def test_reviewed_project_keeps_pyproject_as_the_version_source(tmp_path):
    project = (ROOT / "pyproject.toml").read_text()
    (tmp_path / "pyproject.toml").write_text(project)
    current_version = next(
        line.split('"', 2)[1]
        for line in project.splitlines()
        if line.startswith("version = ")
    )
    selected = {"a": {"version": {"implementation_version": current_version}}}
    result = _project_for_release(tmp_path, selected)
    assert result == project
    assert (tmp_path / "pyproject.toml").read_text() == project
    selected["b"] = {"version": {"implementation_version": "0.0.0"}}
    with pytest.raises(ValueError, match="share one implementation_version"):
        _project_for_release(tmp_path, selected)


def test_reviewed_project_rejects_document_version_drift(tmp_path):
    project = (ROOT / "pyproject.toml").read_text()
    (tmp_path / "pyproject.toml").write_text(project)
    selected = {"a": {"version": {"implementation_version": "0.2.0+historical"}}}
    with pytest.raises(ValueError, match="match pyproject.toml project.version"):
        _project_for_release(tmp_path, selected)
    assert (tmp_path / "pyproject.toml").read_text() == project


def test_reviewed_historical_runtime_requires_explicit_requalification(tmp_path):
    project = (ROOT / "pyproject.toml").read_text().replace("numpy==2.5.4", "numpy>=1.24")
    (tmp_path / "pyproject.toml").write_text(project)
    import tomllib

    version = tomllib.loads(project)["project"]["version"]
    with pytest.raises(ValueError, match="maintained scientific runtime"):
        _project_for_release(tmp_path, {"a": {"version": {"implementation_version": version}}})


def test_selected_wheel_binds_baseline_and_preserves_exact_science(tmp_path):
    source = "src/scirel/field/circular_filament_on_axis.py"
    # A small isolated builder fixture exercises actual wheel metadata/bytes;
    # its synthetic notice is never a production license qualification.
    fixture = tmp_path / "source"
    scientific = fixture / source
    scientific.parent.mkdir(parents=True)
    body = b"def field(x):\n    return 2 * x\n"
    scientific.write_bytes(body)
    license_file = fixture / "licenses/TEST.txt"
    license_file.parent.mkdir()
    license_file.write_text("Synthetic build fixture only.\n")
    profile = {"schema": "scirel.selected-scientific-wheel.v1", "version": "0.0.0+runtimefixture",
               "dependencies": ["numpy>=1.24", "scipy>=1.10"],
               "files": [{"path": source, "sha256": hashlib.sha256(body).hexdigest()}],
               "licenses": [{"path": "licenses/TEST.txt", "sha256": hashlib.sha256(license_file.read_bytes()).hexdigest()}],
               "initializers": {"src/scirel/__init__.py": "__all__ = ['field']\n", "src/scirel/field/__init__.py": "from .circular_filament_on_axis import field\n"}}
    profile_path = tmp_path / "selection.json"
    profile_path.write_text(json.dumps(profile))
    # A carried initializer must never report a different release identity.
    profile["initializers"]["src/scirel/__init__.py"] += "__version__ = '0.0.0+stale'\n"
    profile_path.write_text(json.dumps(profile))
    rejected = tmp_path / "rejected"
    bad = subprocess.run([sys.executable, str(ROOT / "scripts/build_pleiades_selected.py"), str(profile_path), str(rejected), "--source-root", str(fixture)], capture_output=True, text=True)
    assert bad.returncode != 0 and not rejected.exists()
    assert "initializer version" in bad.stderr
    profile["initializers"]["src/scirel/__init__.py"] = "__all__ = ['field']\n__version__ = " + repr(profile["version"]) + "\n"
    profile_path.write_text(json.dumps(profile))
    output = tmp_path / "build"
    result = subprocess.run([sys.executable, str(ROOT / "scripts/build_pleiades_selected.py"), str(profile_path), str(output), "--source-root", str(fixture)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    with zipfile.ZipFile(next((output / "wheel").glob("*.whl"))) as wheel:
        metadata = Parser().parsestr(wheel.read(next(p for p in wheel.namelist() if p.endswith("/METADATA"))).decode())
        assert SpecifierSet(metadata["Requires-Python"]) == SpecifierSet(baseline()["project"]["requires-python"])
        assert set(metadata.get_all("Requires-Dist")) == set(pin_dependencies(profile["dependencies"]))
        assert wheel.read(source.removeprefix("src/")) == body
    receipt = json.loads((output / "BUILD_RECEIPT.json").read_text())
    assert receipt["scientific_runtime_baseline"] == baseline_receipt()
    assert json.loads(profile_path.read_text()) == profile

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
    assert pin_dependencies(["numpy>=1.24", "scipy>=1.10", "matplotlib>=3.7"]) == baseline()["project"]["dependencies"]
    assert baseline_receipt()["pyproject_sha256"] == hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest()


@pytest.mark.parametrize("dependency", ["numpy<2", "numpy==1.26.4", "unknown-science", "scipy[extra]", "numpy; python_version<'3.14'", "numpy @ https://example.invalid/numpy.whl"])
def test_conflicting_or_unqualified_dependency_is_not_silently_replaced(dependency):
    with pytest.raises(ValueError):
        pin_dependencies([dependency])


def test_reviewed_project_only_changes_selected_version(tmp_path):
    project = (ROOT / "pyproject.toml").read_text()
    (tmp_path / "pyproject.toml").write_text(project)
    selected = {"a": {"version": {"implementation_version": "0.2.0.dev4+bound"}}}
    result = _project_for_release(tmp_path, selected)
    assert result == project.replace('version = "0.1.0.dev5"', 'version = "0.2.0.dev4+bound"')
    assert (tmp_path / "pyproject.toml").read_text() == project
    selected["b"] = {"version": {"implementation_version": "0.1.0.dev5"}}
    with pytest.raises(ValueError, match="share one implementation_version"):
        _project_for_release(tmp_path, selected)


def test_reviewed_historical_runtime_requires_explicit_requalification(tmp_path):
    project = (ROOT / "pyproject.toml").read_text().replace("numpy==2.5.4", "numpy>=1.24")
    (tmp_path / "pyproject.toml").write_text(project)
    with pytest.raises(ValueError, match="maintained scientific runtime"):
        _project_for_release(tmp_path, {"a": {"version": {"implementation_version": "0.2.0"}}})


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
    profile = {"schema": "scirel.selected-scientific-wheel.v1", "version": "0.0.0.dev0+runtimefixture",
               "dependencies": ["numpy>=1.24", "scipy>=1.10"],
               "files": [{"path": source, "sha256": hashlib.sha256(body).hexdigest()}],
               "licenses": [{"path": "licenses/TEST.txt", "sha256": hashlib.sha256(license_file.read_bytes()).hexdigest()}],
               "initializers": {"src/scirel/__init__.py": "__all__ = ['field']\n", "src/scirel/field/__init__.py": "from .circular_filament_on_axis import field\n"}}
    profile_path = tmp_path / "selection.json"
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

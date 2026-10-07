"""Runtime validation follows the actual wheel metadata, independent of old science deps."""

from importlib import metadata
from pathlib import Path
import sys
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from runtime_dependency_roots import runtime_dependency_roots


def _wheel(tmp_path, requirements):
    path = tmp_path / "scirel-fixture.whl"
    text = "Metadata-Version: 2.1\nName: scirel\nVersion: 0.0.0\n"
    text += "".join(f"Requires-Dist: {value}\n" for value in requirements)
    with ZipFile(path, "w") as archive:
        archive.writestr("scirel-0.0.0.dist-info/METADATA", text)
    return path


def test_no_scientific_dependencies_requires_only_the_test_tool(tmp_path):
    expected = str(Path(metadata.distribution("pytest").locate_file("")).resolve())
    assert runtime_dependency_roots(_wheel(tmp_path, [])) == [expected]


def test_optional_test_extra_is_not_a_scientific_runtime_dependency(tmp_path):
    assert runtime_dependency_roots(_wheel(tmp_path, ['absent-fixture-package; extra == "test"']))


def test_missing_declared_runtime_dependency_is_rejected(tmp_path):
    with pytest.raises(metadata.PackageNotFoundError):
        runtime_dependency_roots(_wheel(tmp_path, ["absent-fixture-package"]))


def test_incompatible_installed_dependency_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="does not satisfy"):
        runtime_dependency_roots(_wheel(tmp_path, ["pytest<1"]))

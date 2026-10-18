from __future__ import annotations

import json
from pathlib import Path
import sys
import tomllib
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_native_resource_closure import (  # noqa: E402
    _validate_pyproject_package_data,
    validate,
)


def test_native_resource_closure_covers_source_and_declared_package_data() -> None:
    result = validate(ROOT)
    assert result["resource_count"] == 117
    assert result["groups"] == {
        "fluidbw-octave": 36,
        "pdrk-current-core": 37,
        "pdrk-current-fixtures": 18,
        "pdrk-rational-legacy": 15,
        "pdrk-examples": 8,
        "pdrk-finiteN": 2,
        "pdrk-shared-plot-helper": 1,
    }
    manifest = json.loads((ROOT / "release/wheel/native-resource-closure.json").read_text())
    pdrk_binding = next(
        binding
        for binding in manifest["package_data_bindings"]
        if binding["package"] == "scirel.kinetic.pdrk"
    )
    assert pdrk_binding["patterns"] == [
        "_native/scirel_prepare_plot.m",
        "_native/current/**/*",
        "_native/examples/*",
        "_native/finiteN/*",
        "_native/legacy/*",
    ]
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["tool"]["setuptools"]["include-package-data"] is False


def test_native_resource_closure_rejects_unlisted_resource(tmp_path: Path) -> None:
    manifest = json.loads((ROOT / "release/wheel/native-resource-closure.json").read_text())
    manifest["groups"][0]["files"].pop()
    manifest_path = tmp_path / "native-resource-closure.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="file_digests differ from files"):
        validate(ROOT, manifest_path=manifest_path)


def test_native_resource_closure_checks_exact_wheel_members(tmp_path: Path) -> None:
    manifest = json.loads((ROOT / "release/wheel/native-resource-closure.json").read_text())
    expected = {
        "scirel/kinetic/" + name
        for group in manifest["groups"]
        for name in group["files"]
    }
    wheel = tmp_path / "scirel.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for name in sorted(expected):
            source = ROOT / "src/scirel/kinetic" / name.removeprefix("scirel/kinetic/")
            archive.writestr(name, source.read_bytes())
    assert validate(ROOT, wheel=wheel)["wheel_checked"] is True

    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr("scirel/kinetic/pdrk/_native/extra.m", b"unexpected")
    with pytest.raises(ValueError, match="wheel native resource members differ"):
        validate(ROOT, wheel=wheel)


def test_native_resource_closure_rejects_source_digest_drift(tmp_path: Path) -> None:
    manifest = json.loads((ROOT / "release/wheel/native-resource-closure.json").read_text())
    first = manifest["groups"][0]["files"][0]
    manifest["groups"][0]["file_digests"][first]["sha256"] = "0" * 64
    manifest_path = tmp_path / "native-resource-closure.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="digest differs from source resource"):
        validate(ROOT, manifest_path=manifest_path)


def test_native_resource_closure_rejects_package_data_drift(tmp_path: Path) -> None:
    manifest = json.loads((ROOT / "release/wheel/native-resource-closure.json").read_text())
    (tmp_path / "pyproject.toml").write_text(
        """[tool.setuptools.package-data]\n"""
        """\"scirel.kinetic\" = [\"_fluidbw_native/*.m\"]\n"""
        """\"scirel.kinetic.pdrk\" = [\"_native/incorrect/**/*\"]\n""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="package-data differs"):
        _validate_pyproject_package_data(tmp_path, manifest)

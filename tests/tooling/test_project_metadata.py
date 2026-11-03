from __future__ import annotations

from pathlib import Path
import tomllib

from setuptools import find_packages


ROOT = Path(__file__).resolve().parents[2]


def test_project_metadata_exposes_standard_discovery_fields() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert project["name"] == "scirel"
    assert project["readme"] == "README.md"
    assert project["keywords"] == [
        "scientific computing",
        "numerical methods",
        "plasma physics",
    ]
    assert "Intended Audience :: Science/Research" in project["classifiers"]
    assert "Topic :: Scientific/Engineering :: Physics" in project["classifiers"]

    urls = project["urls"]
    assert urls["Homepage"] == "https://github.com/czz20000522/SciRel"
    assert urls["Repository"] == urls["Homepage"]
    assert urls["Issues"].endswith("/issues")


def test_package_discovery_excludes_private_development_compositions() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    discovery = config["tool"]["setuptools"]["packages"]["find"]
    packages = find_packages(
        where=str(ROOT / discovery["where"][0]),
        include=discovery["include"],
        exclude=discovery["exclude"],
    )

    assert "scirel.equilibrium" in packages
    assert "scirel._framework_compositions" not in packages
    assert not any(
        package.startswith("scirel._framework_compositions.") for package in packages
    )

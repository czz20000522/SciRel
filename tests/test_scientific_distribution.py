"""Verify the actual developer wheel keeps project tools outside the science package."""

from pathlib import Path
from email.parser import Parser
import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
from zipfile import ZipFile

from setuptools import find_packages
from packaging.specifiers import SpecifierSet


ROOT = Path(__file__).resolve().parents[1]


def test_built_scientific_wheel_excludes_project_tool_packages(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    shutil.copy2(ROOT / "pyproject.toml", source / "pyproject.toml")
    shutil.copytree(ROOT / "licenses", source / "licenses")
    shutil.copytree(
        ROOT / "src", source / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
    )
    wheels = tmp_path / "wheel"
    wheels.mkdir()
    built = subprocess.run(
        [
            sys.executable, "-I", "-c",
            "from setuptools.build_meta import build_wheel; "
            "import sys; build_wheel(sys.argv[1])",
            str(wheels),
        ],
        cwd=source, capture_output=True, text=True,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    artifacts = list(wheels.glob("scirel-*.whl"))
    assert len(artifacts) == 1
    with ZipFile(artifacts[0]) as archive:
        files = set(archive.namelist())
        metadata_name = next(
            name for name in files
            if name.endswith('.dist-info/METADATA')
        )
        metadata = Parser().parsestr(archive.read(metadata_name).decode('utf-8'))
        config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project = config["project"]
        assert SpecifierSet(metadata["Requires-Python"]) == SpecifierSet(
            project["requires-python"]
        )
        requires_dist = set(metadata.get_all("Requires-Dist") or [])
        assert set(project["dependencies"]) <= requires_dist
        unconditional = {
            requirement.split(";", 1)[0].strip()
            for requirement in requires_dist
            if ";" not in requirement
        }
        assert "scipy==1.18.1" not in unconditional
        assert "matplotlib==3.11.2" not in unconditional
        assert f'{project["optional-dependencies"]["plot"][0]}; extra == "plot"' in requires_dist
        assert f'{project["optional-dependencies"]["scipy"][0]}; extra == "scipy"' in requires_dist
        accepted = json.loads((ROOT / 'provenance/selections/scientific-core-20261014-r7.json').read_text())
        for resource in accepted['data_files']:
            name = resource['path'].removeprefix('src/')
            assert name in files, f'accepted runtime resource missing: {name}'
            assert hashlib.sha256(archive.read(name)).hexdigest() == resource['sha256']
        for notice in ('licenses/Pleiades-MIT.txt',
                       'licenses/gpdf/full-core/SCIREL-GPDF-CORE-NOTICE.txt',
                       'licenses/pdrk/Faddeeva-Ikuma-BSD-2-Clause.txt'):
            packaged = [n for n in files if n.endswith('.dist-info/licenses/' + notice)]
            assert len(packaged) == 1, f'distribution notice missing: {notice}'
            assert archive.read(packaged[0]) == (ROOT / notice).read_bytes()
    assert "scirel/__init__.py" in files
    assert all(
        path.startswith("scirel/") or path.split("/", 1)[0].endswith(".dist-info")
        for path in files
    ), sorted(files)
    discovery = config["tool"]["setuptools"]["packages"]["find"]
    packages = find_packages(
        where=str(ROOT / discovery["where"][0]),
        include=discovery["include"],
        exclude=discovery["exclude"],
    )
    expected_scientific_source = {
        path.relative_to(ROOT / "src").as_posix()
        for package in packages
        for path in (ROOT / "src" / package.replace(".", "/")).glob("*.py")
    }
    assert expected_scientific_source <= files
    assert not any(
        path.startswith("scirel/_framework_compositions/") for path in files
    )

    installed = tmp_path / 'installed'
    subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '--no-deps', '--no-index',
         '--target', str(installed), str(artifacts[0])],
        cwd=tmp_path, check=True, capture_output=True, text=True,
    )
    checked = subprocess.run(
        [sys.executable, '-I', '-S', '-c',
         'import sys; sys.path.insert(0, sys.argv[1]); import scirel; '
         'assert scirel.__file__.startswith(sys.argv[1]); '
         'assert not any(n.startswith("scirel.") for n in sys.modules); '
         'assert "numpy" not in sys.modules; '
         'assert not hasattr(scirel, "solve_multi_coil_vacuum_field")', str(installed)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr

"""Build the bounded kinetic development wheel from an explicit runtime closure.

This is a D2 development builder. It grants no license, scientific approval or
release authority. Dependency notices must come from the bound installed runtime.
"""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys

from scientific_runtime import baseline_receipt, build_requirements, pin_dependencies, python_requirement

RUNTIME = ("cauchy_transform.py", "maxwellian_electrostatic.py", "plasma_dispersion.py")
EXPORTS = ("evaluate_cauchy_transform", "evaluate_maxwellian_electrostatic",
           "solve_maxwellian_electrostatic_mode", "evaluate_plasma_dispersion")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--notices", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=False)
    stage = args.output / "source"
    kinetic = stage / "src/scirel/kinetic"
    kinetic.mkdir(parents=True)
    for name in RUNTIME:
        shutil.copyfile(repo / "src/scirel/kinetic" / name, kinetic / name)
    (kinetic.parent / "__init__.py").write_text(
        '"""SciRel selected kinetic development candidate."""\n'
        '__version__ = "0.1.0.dev7"\n__all__ = ["kinetic"]\n', encoding="utf-8")
    (kinetic / "__init__.py").write_text(
        '"""Selected kinetic operators with explicit numerical contracts."""\n'
        'from .cauchy_transform import evaluate_cauchy_transform\n'
        'from .maxwellian_electrostatic import evaluate_maxwellian_electrostatic, solve_maxwellian_electrostatic_mode\n'
        'from .plasma_dispersion import evaluate_plasma_dispersion\n'
        f'__all__ = {list(EXPORTS)!r}\n', encoding="utf-8")
    notices = stage / "licenses"
    notices.mkdir()
    for name in ("NUMPY-LICENSE.txt", "SCIPY-LICENSE.txt", "SCIREL-GPDF-D2-NOTICE.txt"):
        shutil.copyfile(args.notices / name, notices / name)
    (stage / "pyproject.toml").write_text(f'''[build-system]
requires = {json.dumps(build_requirements())}
build-backend = "setuptools.build_meta"
[project]
name = "scirel"
version = "0.1.0.dev7"
description = "SciRel bounded kinetic D2 development candidate"
requires-python = {json.dumps(python_requirement())}
dependencies = {json.dumps(pin_dependencies(["numpy", "scipy"]))}
license-files = ["licenses/*"]
[tool.setuptools.packages.find]
where = ["src"]
include = ["scirel", "scirel.kinetic"]
''', encoding="utf-8")
    wheels = args.output / "wheel"
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-index",
                    "--no-build-isolation", "--no-deps", "--wheel-dir", str(wheels),
                    str(stage)], check=True)
    print(json.dumps({"scientific_runtime_baseline": baseline_receipt(), "runtime": RUNTIME, "exports": EXPORTS,
                      "wheel": str(next(wheels.glob("*.whl")))}))


if __name__ == "__main__":
    main()

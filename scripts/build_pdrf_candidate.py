"""Build the selected PDRF D2 local candidate; never copy the whole SciRel tree.

The four exact documents and scientific module define this isolated increment.
Existing provisional SciRel modules, D1 native code, papers, workflow tooling
and evidence are excluded from the wheel. This is a local evaluation artifact,
not a license determination or release authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0.dev20261013"
SYMBOLS = ("initialize_pdrf_plasma", "assemble_pdrf_matrix",
           "solve_pdrf_spectrum", "evaluate_pdrf_dispersion")
DOCUMENTS = ("pdrf-plasma-state", "pdrf-temporal-matrix",
             "pdrf-temporal-spectrum", "pdrf-dispersion-scan")


def build(output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    stage = output / "staging"
    (stage / "scirel" / "kinetic").mkdir(parents=True)
    import_line = ", ".join(SYMBOLS)
    (stage / "scirel" / "__init__.py").write_text(
        '"""Selected local D2 scientific candidate; public redistribution not established."""\n'
        f"from .kinetic import {import_line}\n__all__ = {list(SYMBOLS)!r}\n")
    (stage / "scirel" / "kinetic" / "__init__.py").write_text(
        f"from .pdrf import {import_line}\n__all__ = {list(SYMBOLS)!r}\n")
    shutil.copy2(ROOT / "src/scirel/kinetic/pdrf.py", stage / "scirel/kinetic/pdrf.py")
    (output / "exact-documents").mkdir()
    for name in DOCUMENTS:
        shutil.copy2(ROOT / f"catalog/examples/scirel.kinetic.{name}.json", output / "exact-documents")
    setup = {
        "name": "scirel", "version": VERSION,
        "description": "PDRF effective multi-fluid local D2 evaluation candidate",
        "packages": ["scirel", "scirel.kinetic"],
        "python_requires": ">=3.10",
        "install_requires": ["numpy==2.5.3", "scipy==1.18.1", "matplotlib>=3.7", "mpmath==1.3.0"],
        "license": "NOT_ESTABLISHED; local authorized D2 evaluation only",
        "classifiers": ["Development Status :: 2 - Pre-Alpha"],
    }
    (stage / "setup.py").write_text("from setuptools import setup\nsetup(**" + repr(setup) + ")\n")
    process = subprocess.run([sys.executable, "setup.py", "bdist_wheel", "--dist-dir", str(output / "wheel")],
                             cwd=stage, text=True, capture_output=True)
    (output / "build.stdout").write_text(process.stdout)
    (output / "build.stderr").write_text(process.stderr)
    if process.returncode:
        raise RuntimeError(f"wheel build failed ({process.returncode})")
    subprocess.run([sys.executable, str(ROOT / "scripts/validate_asset_documents.py"),
                    str(output / "exact-documents"), "--check-runtime", "--execute-examples"], check=True)
    subprocess.run([sys.executable, str(ROOT / "scripts/build_catalog.py"), str(output / "exact-documents"),
                    "--output-dir", str(output / "catalog"), "--catalog-id", "scirel-pdrf-d2-local",
                    "--release-version", VERSION, "--coverage-status", "complete", "--declared-total", "4"], check=True)
    wheel, = (output / "wheel").glob("*.whl")
    record = {"schema": "scirel.pdrf.d2.selected-build.v1", "version": VERSION,
              "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "git_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
              "git_status": subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True),
              "wheel": str(wheel.relative_to(output)), "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
              "scientific_source_sha256": hashlib.sha256((ROOT / "src/scirel/kinetic/pdrf.py").read_bytes()).hexdigest(),
              "selected_public_api": list(SYMBOLS), "selected_assets": ["scirel.kinetic."+n for n in DOCUMENTS],
              "public_distribution": False, "source_license": "NOT_ESTABLISHED", "paper_license": "NOT_ESTABLISHED"}
    (output / "BUILD.json").write_text(json.dumps(record, indent=2)+"\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(json.dumps(build(parser.parse_args().output.resolve()), indent=2))

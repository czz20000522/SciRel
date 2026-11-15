"""The six mathematical basis relations have one public numerical owner."""

import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
RELATIONS = (
    ("basis-matrix", "BasisMatrix"),
    ("build-basis", "build_basis"),
    ("clamped-cubic-spline", "ClampedCubicSpline"),
    ("first-clamped-cubic-spline", "FirstClampedCubicSpline"),
    ("natural-cubic-spline", "NaturalCubicSpline"),
    ("second-clamped-cubic-spline", "SecondClampedCubicSpline"),
)


@pytest.mark.parametrize("child_first", [False, True])
def test_basis_module_and_facade_keep_identity_in_either_import_order(child_first):
    script = f"""
import importlib
import scirel
names = {[symbol for _, symbol in RELATIONS]!r}
if {child_first!r}:
    child = importlib.import_module('scirel.numerics.basis')
facade = scirel.numerics
first = {{name: getattr(facade, name) for name in names}}
child = importlib.import_module('scirel.numerics.basis')
assert facade.basis is child
assert set(child.__all__) == set(names)
for name in names:
    assert first[name] is getattr(child, name) is getattr(facade, name)
    assert getattr(child, name).__module__ == 'scirel.numerics.basis'
    assert name in facade.__all__ and name in dir(facade)
"""
    done = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.parametrize("name", ["basis", *(symbol for _, symbol in RELATIONS)])
def test_geometry_has_no_legacy_basis_entry(name):
    geometry = importlib.import_module("scirel.geometry")
    assert name not in geometry.__all__
    assert name not in dir(geometry)
    with pytest.raises(AttributeError):
        getattr(geometry, name)
    with pytest.raises(ImportError):
        exec(f"from scirel.geometry import {name}", {})
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("scirel.geometry.basis")


@pytest.mark.parametrize(("suffix", "symbol"), RELATIONS)
def test_basis_contract_ids_bind_numerics_without_a_legacy_copy(suffix, symbol):
    asset_id = f"scirel.numerics.{suffix}"
    catalog = ROOT / "catalog/examples"
    document = json.loads((catalog / f"{asset_id}.json").read_text())
    assert document["asset_id"] == asset_id
    api = document["public_api"]["python"]
    assert api["module"] == "scirel.numerics.basis"
    assert api["canonical_module"] == "scirel.numerics"
    assert api["symbol"] == api["canonical_symbol"] == symbol
    assert not (catalog / f"scirel.basis.{suffix}.json").exists()
    expected = [{"asset_id": "scirel.numerics.build-basis"}] if suffix == "basis-matrix" else []
    assert document["version"]["dependencies"] == expected
    exec(compile(document["example"]["code"], asset_id, "exec"), {})


def test_basis_namespace_discovery_stays_lazy():
    script = """
import sys
from scirel import numerics
assert 'basis' in dir(numerics)
assert 'BasisMatrix' in dir(numerics)
assert 'numpy' not in sys.modules
assert 'scipy' not in sys.modules
assert 'scirel.numerics.basis' not in sys.modules
"""
    done = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr

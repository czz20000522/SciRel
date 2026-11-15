"""Canonical numerical interpolation ownership and removal of geometry aliases."""

from __future__ import annotations

import importlib
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
CASES = (
    ("bilinear_grid_sampling", "sample_rectilinear_field"),
    ("complex_rectilinear_interpolation", "interpolate_complex_rectilinear_field"),
)


@pytest.mark.parametrize(("module_name", "symbol"), CASES)
def test_interpolation_subpackage_and_root_share_only_the_new_owner(module_name, symbol):
    from scirel import geometry, numerics
    from scirel.numerics import interpolate

    module = importlib.import_module("scirel.numerics.interpolate." + module_name)
    function = getattr(module, symbol)
    assert getattr(interpolate, symbol) is function
    assert getattr(numerics, symbol) is function
    assert symbol in interpolate.__all__ and symbol in numerics.__all__
    assert symbol not in geometry.__all__ and symbol not in dir(geometry)
    assert not hasattr(geometry, symbol)
    assert not hasattr(geometry, module_name)
    old_module = "scirel.geometry." + module_name
    with pytest.raises(ModuleNotFoundError) as error:
        importlib.import_module(old_module)
    assert error.value.name == old_module


def test_interpolation_namespace_keeps_face_export_and_defers_dependencies():
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-c",
            """
import sys
sys.path.insert(0, sys.argv[1])
import scirel.numerics as numerics
from scirel.numerics import interpolate
assert {"face_to_cell", "sample_rectilinear_field", "interpolate_complex_rectilinear_field"} <= set(interpolate.__all__)
assert set(interpolate.__all__) <= set(dir(interpolate))
assert {"face_to_cell", "sample_rectilinear_field", "interpolate_complex_rectilinear_field"} <= set(numerics.__all__)
assert not any(name in sys.modules for name in ("numpy", "scipy", "matplotlib"))
assert "scirel.geometry" not in sys.modules
assert "scirel.numerics.interpolate.midpoint" not in sys.modules
assert "scirel.numerics.interpolate.bilinear_grid_sampling" not in sys.modules
assert "scirel.numerics.interpolate.complex_rectilinear_interpolation" not in sys.modules
""",
            str(ROOT / "src"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

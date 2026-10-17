"""PDRK module discovery stays explicit and lazy."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pdrk_package_discovers_modules_without_importing_backends() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            r'''
import sys
from types import ModuleType

sys.path.insert(0, sys.argv[1])
import scirel.kinetic.pdrk as pdrk

expected = [
    "magnetized", "multifluid", "parallel", "plotting",
    "rational", "reference", "special", "workflows",
]
assert pdrk.__all__ == expected
assert sorted(name for name in pdrk.__all__ if name in dir(pdrk)) == expected
assert not any(
    name.startswith("scirel.kinetic.pdrk.") for name in sys.modules
)

namespace = {}
exec("from scirel.kinetic.pdrk import *", namespace)
assert all(isinstance(namespace[name], ModuleType) for name in expected)
''',
            str(ROOT / "src"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_pdrk_catalog_modules_have_explicit_callable_exports() -> None:
    from scirel.kinetic.pdrk import magnetized, rational, workflows

    expected = {
        "magnetized": {
            "initialize_equilibrium", "electromagnetic_matrix",
            "electrostatic_matrix", "eigensolve", "reconstruct_point_fields",
            "select_modes", "pole_coefficients", "loss_cone_partition",
            "render_spectrum", "select_preset", "interpolate_selected_dispersion",
            "source_output", "wavevector_coordinates", "render_selected_modes",
        },
        "rational": {
            "default_deck", "equilibrium", "pole_table", "point_matrix",
            "solve_matrix", "em_coordinates", "jpole_grid_coordinates",
            "jpole_evaluate", "jpole_coefficients",
        },
        "workflows": {
            "solve_dispersion", "scan_spectrum", "reconstruct_polarization",
            "original_program", "selected_fields", "rendered_output",
            "preset_output", "ordered_rational_spectrum", "regenerate_jpole",
            "reassemble_rational_program",
        },
    }
    modules = {
        "magnetized": magnetized,
        "rational": rational,
        "workflows": workflows,
    }
    for name, module in modules.items():
        assert set(module.__all__) == expected[name]
        assert all(callable(getattr(module, symbol)) for symbol in module.__all__)


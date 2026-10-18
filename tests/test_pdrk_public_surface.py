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


def test_pdrk_presentation_modules_do_not_import_scipy_until_called() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            r'''
import sys
sys.path.insert(0, sys.argv[1])
from scirel.kinetic.pdrk import plotting, reference, special
assert "scipy" not in sys.modules
assert "scipy.io" not in sys.modules
assert "scipy.sparse" not in sys.modules
assert callable(plotting.fluid_plot_scan)
assert callable(reference.whamp_reference)
assert callable(special.evaluate_faddeeva_finite_order)
''',
            str(ROOT / "src"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_pdrk_transport_defers_scipy_until_state_validation() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            r'''
import sys
import numpy as np
sys.path.insert(0, sys.argv[1])
import scirel.kinetic.pdrk._transport as transport

assert "scipy" not in sys.modules
assert "scipy.io" not in sys.modules
assert "scipy.sparse" not in sys.modules

value = transport._state_value(np.ones(2))
assert value.shape == (2,)
assert "scipy.sparse" in sys.modules
assert "scipy.io" not in sys.modules
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


def test_pdrk_numeric_modules_defer_scipy_until_valid_backend() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            r'''
import sys
import numpy as np
sys.path.insert(0, sys.argv[1])

from scirel.kinetic.pdrk import (
    _fluid_parallel,
    _perpendicular_em,
    _rational_frequency,
    magnetized,
    rational,
)

assert "scipy" not in sys.modules

for call in (
    lambda: _fluid_parallel.solve_frequency_pencil(np.empty((0, 0)), np.empty((0, 0))),
    lambda: _fluid_parallel.continue_em1d({}, k_grid=[0.0]),
    lambda: _perpendicular_em.perpendicular_maxwell_pencil(
        components=[], kx=np.nan, N=0, c2=1.0
    ),
    lambda: _rational_frequency.solve_rational_frequency(
        constant=0.0, poles=[], residues=[]
    ),
    lambda: magnetized.initialize_equilibrium(controls={"B0": 0.0}),
    lambda: rational.solve_matrix(np.eye(1), model="unknown"),
    lambda: rational.solve_matrix(np.empty((0, 0)), model="es1d"),
):
    try:
        call()
    except (ValueError, TypeError):
        pass
    else:
        raise AssertionError("invalid PDRK input unexpectedly succeeded")
    assert "scipy" not in sys.modules

output = _rational_frequency.solve_rational_frequency(
    constant=1.0, poles=[1.0], residues=[1.0]
)
assert output["omega"].shape == (1,)
assert "scipy" in sys.modules
''',
            str(ROOT / "src"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


"""Import-boundary regression for the Maxwellian electrostatic solver."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_maxwellian_solver_defers_scipy_optimize_until_valid_solve() -> None:
    source = """
import sys
from scirel.kinetic import (
    evaluate_maxwellian_electrostatic,
    solve_maxwellian_electrostatic_mode,
)
from scirel.kinetic.maxwellian_electrostatic import (
    evaluate_maxwellian_electrostatic as direct_evaluate,
    solve_maxwellian_electrostatic_mode as direct_solve,
)

assert evaluate_maxwellian_electrostatic is direct_evaluate
assert solve_maxwellian_electrostatic_mode is direct_solve
assert "scipy" not in sys.modules
try:
    evaluate_maxwellian_electrostatic([], 0.4)
except ValueError as error:
    assert str(error) == "omega must contain finite numeric values"
else:
    raise AssertionError("invalid Maxwellian response input unexpectedly succeeded")
assert "scipy" not in sys.modules
try:
    solve_maxwellian_electrostatic_mode(0.4, [], max_evaluations=1)
except ValueError as error:
    assert str(error) == "initial_omega must contain finite numeric values"
else:
    raise AssertionError("invalid Maxwellian solve input unexpectedly succeeded")
assert "scipy" not in sys.modules
try:
    solve_maxwellian_electrostatic_mode(1e-3, 2.0, max_evaluations=1)
except RuntimeError as error:
    assert "Maxwellian mode solve failed" in str(error)
else:
    raise AssertionError("budget-limited Maxwellian solve unexpectedly succeeded")
assert "scipy" in sys.modules
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-c", source],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

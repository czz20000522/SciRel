"""Fresh-process import boundaries for the cross-mesh distribution operator."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def _run(source: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-c", source],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_module_import_and_rejected_call_do_not_load_scipy() -> None:
    result = _run(
        """
import sys
import scirel.kinetic.cross_mesh_distribution_interpolation as module

assert "scipy" not in sys.modules
try:
    module.interp_distribution_across_mesh(
        [[1.0]], [0.5, 1.0], [-1.0, 1.0], [0.0, 1.0],
        float("nan"), [0.5, 1.0], [-1.0, 1.0], [0.0, 1.0], 1.0,
    )
except ValueError as error:
    assert str(error) == "Tnorm_a and Tnorm_b must be positive and finite"
else:
    raise AssertionError("invalid normalization unexpectedly succeeded")
assert "scipy" not in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_valid_backends_load_only_at_their_numeric_boundaries() -> None:
    result = _run(
        """
import sys
import numpy as np
from scirel.kinetic.cross_mesh_distribution_interpolation import (
    interp_distribution_across_mesh,
)

assert "scipy" not in sys.modules
vr = np.array([0.5, 1.0])
vx = np.array([-1.0, 1.0])
x = np.array([0.0, 1.0])
fa = np.ones((2, 2, 2))

interp_distribution_across_mesh(
    fa, vr, vx, x, 1.0, vr, vx, x, 1.0, correct=0,
)
assert "scipy.interpolate" in sys.modules

for name in tuple(sys.modules):
    if name == "scipy" or name.startswith("scipy."):
        del sys.modules[name]

vr_b = np.array([0.4, 0.8, 1.2])
vx_b = np.array([-1.2, 0.0, 1.2])
interp_distribution_across_mesh(
    fa, vr, vx, x, 1.0, vr_b, vx_b, x, 1.0, correct=1,
)
assert "scipy.special" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr

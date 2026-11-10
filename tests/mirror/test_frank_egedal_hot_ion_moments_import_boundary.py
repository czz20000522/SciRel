"""Fresh-process import boundaries for Frank--Egedal hot-ion moments."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_hot_ion_moments_defers_scipy_until_valid_quadrature_call() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
import numpy as np
from scirel.mirror import evaluate_frank_egedal_hot_ion_moments
from scirel.mirror.frank_egedal_hot_ion_moments import (
    evaluate_frank_egedal_hot_ion_moments as direct,
)

assert evaluate_frank_egedal_hot_ion_moments is direct
assert "scipy" not in sys.modules

try:
    evaluate_frank_egedal_hot_ion_moments(
        [[1.0]],
        {"B0": 1.0, "mirror_ratio": 1.0},
        [0.0],
        [1.0],
        2,
        lambda degree, xi, terms: np.ones_like(xi),
    )
except ValueError as error:
    assert str(error) == "mirror_ratio must be finite and greater than one"
else:
    raise AssertionError("invalid hot-ion input unexpectedly succeeded")
assert "scipy" not in sys.modules

output = evaluate_frank_egedal_hot_ion_moments(
    [[1.0]],
    {
        "B0": 1.0,
        "mirror_ratio": 2.0,
        "vc_over_v0": 0.8,
        "velocity_nodes": 4,
        "pitch_nodes": 4,
    },
    [0.0],
    [1.0],
    2,
    lambda degree, xi, terms: np.ones_like(xi),
)
assert output["hot_density_shape"].shape == (1, 1)
assert "scipy.special" in sys.modules
""",
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

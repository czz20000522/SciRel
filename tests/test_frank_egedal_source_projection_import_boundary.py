"""Fresh-process import boundaries for the Frank--Egedal source projection."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_source_projection_defers_scipy_until_quadrature_is_needed() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from scirel.kinetic import project_frank_egedal_source_modes
from scirel.kinetic.frank_egedal_source_projection import (
    project_frank_egedal_source_modes as direct,
)

assert project_frank_egedal_source_modes is direct
assert "scipy" not in sys.modules
try:
    project_frank_egedal_source_modes({})
except ValueError as error:
    assert str(error) == "spectrum_operator is required when legendre_degrees is absent"
else:
    raise AssertionError("incomplete source state unexpectedly succeeded")
assert "scipy" not in sys.modules

# Explicit coefficients do not need the quadrature backend and remain light.
project_frank_egedal_source_modes(
    {
        "mirror_ratio": 2.0,
        "legendre_degrees": [0.0],
        "source_coefficients": [1.0],
    }
)
assert "scipy" not in sys.modules

# Omitting coefficients enters the numerical normalization path, where the
# delayed roots_legendre import is required.
output = project_frank_egedal_source_modes(
    {
        "mirror_ratio": 2.0,
        "legendre_degrees": [0.0],
        "legendre_terms": 2,
    }
)
assert output["source_coefficients"].shape == (1,)
assert "scipy.special" in sys.modules
""",
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

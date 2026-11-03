"""Fresh-process import boundary for the Cauchy transform operator."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_cauchy_transform_defers_scipy_until_valid_call() -> None:
    source = """
import sys
from scirel.kinetic import evaluate_cauchy_transform
from scirel.kinetic.cauchy_transform import (
    evaluate_cauchy_transform as direct,
)

assert evaluate_cauchy_transform is direct
assert "scipy" not in sys.modules
try:
    evaluate_cauchy_transform(1j, lambda v: 1.0, bounds=(1.0, 1.0))
except ValueError as error:
    assert str(error) == "bounds must be an ordered finite pair"
else:
    raise AssertionError("invalid Cauchy bounds unexpectedly succeeded")
assert "scipy" not in sys.modules

output = evaluate_cauchy_transform(1j, lambda v: 1.0, bounds=(-1.0, 1.0))
assert output["G"].shape == ()
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

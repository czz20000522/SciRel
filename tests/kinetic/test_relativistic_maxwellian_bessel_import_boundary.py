"""Fresh-process import boundary for the relativistic Maxwellian Bessel closure."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_relativistic_maxwellian_bessel_defers_scipy_until_valid_call() -> None:
    source = """
import importlib
import sys

module = importlib.import_module(
    "scirel.collisions.relativistic_maxwellian_bessel"
)
assert "scipy" not in sys.modules
try:
    module.relativistic_maxwellian_bessel(0.0)
except module.InvalidBesselArgumentError as error:
    assert str(error) == "x must be positive and finite"
else:
    raise AssertionError("invalid Bessel argument unexpectedly succeeded")
assert "scipy" not in sys.modules

result = module.relativistic_maxwellian_bessel(1.5)
assert set(result) == {"bk0", "bk1", "bk2"}
assert all(type(value) is float for value in result.values())
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

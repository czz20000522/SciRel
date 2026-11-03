"""Fresh-process import boundary for the retained Faddeeva variants."""

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


def test_faddeeva_variants_defer_scipy_until_axis_stabilization() -> None:
    result = _run(
        """
import sys
from scirel.kinetic import evaluate_faddeeva_gpdf
from scirel.kinetic.faddeeva_variants import (
    evaluate_faddeeva_gpdf as direct,
)

assert evaluate_faddeeva_gpdf is direct
assert "scipy" not in sys.modules
try:
    evaluate_faddeeva_gpdf([])
except ValueError as error:
    assert str(error) == "z must be finite and nonempty"
else:
    raise AssertionError("empty Faddeeva input unexpectedly succeeded")
assert "scipy" not in sys.modules
try:
    evaluate_faddeeva_gpdf(1j, order=0)
except ValueError as error:
    assert str(error) == "order must be a positive integer"
else:
    raise AssertionError("invalid Faddeeva order unexpectedly succeeded")
assert "scipy" not in sys.modules
result = evaluate_faddeeva_gpdf(0.3 + 0.2j)
assert result["w"].shape == ()
assert "scipy" not in sys.modules
result = evaluate_faddeeva_gpdf(1j)
assert result["w"].shape == ()
assert "scipy" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr

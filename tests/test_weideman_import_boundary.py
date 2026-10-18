"""Fresh-process import boundary for the Weideman kinetic operator."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_weideman_defers_scipy_until_valid_call() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from scirel.kinetic import evaluate_plasma_dispersion_weideman
from scirel.kinetic.plasma_dispersion_weideman import (
    evaluate_plasma_dispersion_weideman as direct,
)

assert evaluate_plasma_dispersion_weideman is direct
assert "scipy" not in sys.modules
try:
    evaluate_plasma_dispersion_weideman([])
except ValueError as error:
    assert str(error) == "z must be nonempty and finite"
else:
    raise AssertionError("empty Weideman input unexpectedly succeeded")
assert "scipy" not in sys.modules
output = evaluate_plasma_dispersion_weideman(0j)
assert output["method"].tolist() == "erfc"
assert output["w"].tolist() == 1.0 + 0.0j
assert "scipy" in sys.modules
""",
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

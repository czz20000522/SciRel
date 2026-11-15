"""Fresh-process import boundary for the Weideman kinetic operator."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_weideman_defers_scipy_until_valid_call() -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from scirel.kinetic import evaluate_plasma_dispersion
from scirel.kinetic.plasma_dispersion import evaluate_plasma_dispersion as direct

assert evaluate_plasma_dispersion is direct
assert "scipy" not in sys.modules
try:
    evaluate_plasma_dispersion([], method="weideman")
except ValueError as error:
    assert "z" in str(error) and "scirel.kinetic.plasma-dispersion-function" in str(error)
else:
    raise AssertionError("empty Weideman input unexpectedly succeeded")
assert "scipy" not in sys.modules
output = evaluate_plasma_dispersion(0j, method="weideman")
assert set(output) == {"w", "Z"}
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

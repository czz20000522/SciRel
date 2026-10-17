"""Optional capability boundaries report the extra that enables them."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


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


_BLOCK_MATPLOTLIB = """
import importlib.abc
import sys

class BlockMatplotlib(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "matplotlib" or fullname.startswith("matplotlib."):
            raise ModuleNotFoundError("blocked optional dependency", name=fullname)
        return None

sys.meta_path.insert(0, BlockMatplotlib())
"""


@pytest.mark.parametrize(
    "operation",
    (
        """
from scirel.io.eqdsk import write_pleiades_eqdsk_legacy_raw
import numpy as np

R, Z = np.meshgrid(np.linspace(0.0, 1.0, 2), np.linspace(-0.5, 0.5, 2))
try:
    write_pleiades_eqdsk_legacy_raw(R, Z, np.ones_like(R), np.zeros_like(R),
                                    "/tmp/scirel-optional-eqdsk", "test")
except ModuleNotFoundError as error:
    assert error.name == "matplotlib"
    assert "pip install scirel[plot]" in str(error)
else:
    raise AssertionError("the legacy writer unexpectedly ran without Matplotlib")
""",
        """
from scirel.kinetic.pdrf import _plot
import numpy as np

try:
    _plot(
        {"method": 2, "unit": "normalized", "kk": np.array([0.1]),
         "ww1": np.array([[1.0j]]), "ww2": np.array([[1.0j]]),
         "state": {"s": 0}},
        None,
    )
except ModuleNotFoundError as error:
    assert error.name == "matplotlib"
    assert "pip install scirel[plot]" in str(error)
else:
    raise AssertionError("PDRF plotting unexpectedly ran without Matplotlib")
""",
        """
from scirel.kinetic.pdrk._presentation import save_program
import numpy as np

try:
    save_program(
        "generator",
        {"x": np.array([0.0]), "y": np.array([0.0]),
         "ZJ": np.array([[0.0j]]), "bzj": np.array([0.0]),
         "czj": np.array([0.0])},
        "/tmp/scirel-optional-pdrk",
    )
except ModuleNotFoundError as error:
    assert error.name == "matplotlib"
    assert "pip install scirel[plot]" in str(error)
else:
    raise AssertionError("PDRK presentation unexpectedly ran without Matplotlib")
""",
    ),
)
def test_plot_capabilities_report_the_scirel_extra(operation: str) -> None:
    result = _run(_BLOCK_MATPLOTLIB + operation)
    assert result.returncode == 0, result.stdout + result.stderr

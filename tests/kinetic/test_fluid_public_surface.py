"""Keep the fluid-dispersion catalog bindings explicit at implementation modules."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CATALOG_DOCUMENTS = (
    "scirel.kinetic.fluid-dispersion-matrix.json",
    "scirel.kinetic.fluid-wavevector-eigensolve.json",
    "scirel.kinetic.fluid-wavevector-scan.json",
    "scirel.kinetic.gamma-lpole-coefficients.json",
    "scirel.kinetic.z-pole-coefficients.json",
)


@pytest.mark.parametrize("document_name", CATALOG_DOCUMENTS)
def test_catalog_callable_is_an_explicit_module_export(document_name: str) -> None:
    document = json.loads((ROOT / "catalog" / "examples" / document_name).read_text())
    python_api = document["public_api"]["python"]
    module = importlib.import_module(python_api["module"])

    exports = getattr(module, "__all__", None)
    assert isinstance(exports, (list, tuple))
    assert set(exports) == {python_api["symbol"]}
    assert all(isinstance(name, str) and not name.startswith("_") for name in exports)
    assert callable(getattr(module, python_api["symbol"]))

    namespace: dict[str, object] = {}
    exec(f"from {python_api['module']} import *", namespace)
    assert namespace[python_api["symbol"]] is getattr(module, python_api["symbol"])


def test_fluidbw_direct_import_does_not_preload_scipy_io() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            r'''
import sys
sys.path.insert(0, sys.argv[1])
import scirel.kinetic.fluid_spectrum
assert "scipy.io" not in sys.modules
''',
            str(ROOT / "src"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

"""Keep the neutral-transport formulation neutral-generation catalog bindings explicit."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CATALOG_DOCUMENTS = (
    "scirel.neutrals.neutral-boltzmann-rhs.json",
    "scirel.neutrals.neutral-generation-propagation.json",
    "scirel.neutrals.neutral-generation-stopping.json",
    "scirel.neutrals.generation-accumulation-update.json",
    "scirel.neutrals.neutral-total-collision-frequency.json",
    "scirel.neutrals.outer-seed-convergence.json",
    "scirel.neutrals.neutral-upwind-transport-coefficients.json",
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

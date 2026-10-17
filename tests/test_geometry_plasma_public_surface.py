"""Keep small numerical families discoverable through explicit module exports."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


CASES = (
    (
        "scirel.numerics.nonuniform-derivatives.json",
        {"NumericalContractError", "diff_12_central"},
    ),
    (
        "scirel.plasma.fast-ion-heating.json",
        {"fast_ion_fractional_heating"},
    ),
)


@pytest.mark.parametrize(("document_name", "expected_exports"), CASES)
def test_catalog_callable_matches_explicit_module_exports(
    document_name: str, expected_exports: set[str]
) -> None:
    document = json.loads(
        (ROOT / "catalog" / "examples" / document_name).read_text(encoding="utf-8")
    )
    python_api = document["public_api"]["python"]
    module = importlib.import_module(python_api["module"])

    exports = getattr(module, "__all__", None)
    assert isinstance(exports, (list, tuple))
    assert set(exports) == expected_exports
    assert python_api["symbol"] in exports
    assert all(isinstance(name, str) and not name.startswith("_") for name in exports)
    assert callable(getattr(module, python_api["symbol"]))

    namespace: dict[str, object] = {}
    exec(f"from {python_api['module']} import *", namespace)
    assert {name for name in namespace if not name.startswith("__")} == expected_exports
    for name in expected_exports:
        assert namespace[name] is getattr(module, name)


def test_geometry_numerics_contract_error_remains_a_value_error() -> None:
    module = importlib.import_module("scirel.geometry.numerics")
    assert issubclass(module.NumericalContractError, ValueError)

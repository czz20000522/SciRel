"""Check exact module-level exports for stable domain APIs."""

from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_fvm_modules_expose_only_their_public_operators() -> None:
    expected = {
        "scirel.fvm.cell_variable": {"CellVariable"},
        "scirel.fvm.convection": {"make_convection_terms"},
        "scirel.fvm.diffusion": {"TriDiagonal", "make_diffusion_terms"},
        "scirel.fvm.implicit": {"theta_step"},
    }

    import scirel.fvm as fvm

    for module_name, names in expected.items():
        module = importlib.import_module(module_name)
        assert set(module.__all__) == names
        namespace: dict[str, object] = {}
        exec(f"from {module_name} import *", namespace)
        assert {key for key in namespace if not key.startswith("__")} == names
        for name in names:
            assert namespace[name] is getattr(module, name)
            assert getattr(fvm, name) is getattr(module, name)


def test_eqdsk_catalog_callables_are_explicit_module_exports() -> None:
    """Catalog records must resolve through the implementation module's API."""

    module = importlib.import_module("scirel.io.eqdsk")
    catalog_dir = Path(__file__).resolve().parents[1] / "catalog" / "examples"
    records = sorted(catalog_dir.glob("scirel.io.*.json"))
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in records]
    expected = {
        document["public_api"]["python"]["symbol"]
        for document in documents
        if document["public_api"]["python"]["module"] == "scirel.io.eqdsk"
    }

    assert expected == {
        "EQDSK",
        "read_eqdsk",
        "write_eqdsk",
    }
    assert expected <= set(module.__all__)
    namespace: dict[str, object] = {}
    exec("from scirel.io.eqdsk import *", namespace)
    assert all(namespace[name] is getattr(module, name) for name in module.__all__)


def test_public_operator_modules_do_not_leak_support_names() -> None:
    expected = {
        "scirel.equilibrium.equilibrium_state": {"EquilibriumResult", "compute_equilibrium"},
        "scirel.physics.thermal_energy": {"calculate_stored_thermal_energy"},
        "scirel.source.gaussian": {"gaussian_profile"},
        "scirel.source.exponential": {"exponential_profile"},
    }

    for module_name, names in expected.items():
        module = importlib.import_module(module_name)
        assert set(module.__all__) == names
        namespace: dict[str, object] = {}
        exec(f"from {module_name} import *", namespace)
        assert {key for key in namespace if not key.startswith("__")} == names
        for name in names:
            assert namespace[name] is getattr(module, name)

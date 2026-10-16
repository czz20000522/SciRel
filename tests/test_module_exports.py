"""Check exact module-level exports for stable domain APIs."""

from __future__ import annotations

import importlib


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

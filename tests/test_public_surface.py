"""Check the current package exposes its scaffold without historical scientific APIs."""

import importlib.util

import scirel


def test_scaffold_has_no_scientific_exports_or_legacy_domains():
    assert scirel.__version__ == "0.2.0.dev0"
    assert scirel.__all__ == []
    for name in ("field", "kinetic", "collisions", "geometry", "equilibrium"):
        assert importlib.util.find_spec(f"scirel.{name}") is None

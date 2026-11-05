"""Keep the remaining kinetic catalog bindings explicit at implementation modules."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


CASES = (
    (
        "scirel.kinetic.atomic-alpha-contraction.json",
        {"contract_atomic_hydrogen_alpha_frequencies"},
    ),
    ("scirel.kinetic.atomic-scattered-sources-reduction.json", {"reduce_atomic_scattered_sources"}),
    (
        "scirel.kinetic.cross-mesh-distribution-interpolation.json",
        {
            "InfeasibleMomentsError",
            "MomentCorrectionConvergenceError",
            "interp_distribution_across_mesh",
        },
    ),
    ("scirel.kinetic.elastic-frequency-channels.json", {"sum_elastic_frequency_channels"}),
    (
        "scirel.kinetic.elastic-regeneration-aggregation.json",
        {"aggregate_elastic_regeneration_source"},
    ),
    (
        "scirel.kinetic.kinetic-dispersion-relation.json",
        {"evaluate_kinetic_dispersion_relation"},
    ),
    (
        "scirel.kinetic.kinetic-dispersion-ronnmark.json",
        {"evaluate_kinetic_dispersion_ronnmark"},
    ),
    (
        "scirel.kinetic.kinetic-dispersion-sum-fluid.json",
        {"evaluate_fluid_kinetic_dispersion_sum"},
    ),
    ("scirel.kinetic.kinetic-wavevector-scan.json", {"scan_kinetic_wavevectors"}),
    ("scirel.kinetic.outer-convergence.json", {"evaluate_outer_convergence"}),
    (
        "scirel.kinetic.molecular-alpha-contraction.json",
        {"contract_molecular_hydrogen_alpha_frequencies"},
    ),
    (
        "scirel.kinetic.molecular-scattered-sources-reduction.json",
        {"reduce_molecular_scattered_sources"},
    ),
    (
        "scirel.kinetic.simple-charge-exchange-source.json",
        {"assemble_simple_charge_exchange_source"},
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


def test_cross_mesh_error_exports_remain_value_error_subclasses() -> None:
    module = importlib.import_module("scirel.kinetic.cross_mesh_distribution_interpolation")
    assert issubclass(module.InfeasibleMomentsError, ValueError)
    assert issubclass(module.MomentCorrectionConvergenceError, ValueError)

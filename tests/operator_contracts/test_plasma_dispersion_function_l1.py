"""Bounded comparisons with fluidBW D1 and the withdrawn historical PDRK input."""

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import evaluate_plasma_dispersion


SOURCE_HASHES = {
    "PDRK": "b951764f0f4829874444c198dba94006aef000d69b94403915da57d933f2b131",
    "fluidBW": "d16799ad771a5eb16dda2b3d41b40e49564c0fb1435bf086f71aa67d6b54ca16",
}


def _source_operator(project):
    root = os.environ.get("SCIREL_L1_ROOT")
    if not root:
        pytest.skip("SCIREL_L1_ROOT is not set; source-free contract tests remain active")
    historical_pdrk = os.environ.get("SCIREL_HISTORICAL_PDRK_ROOT") if project == "PDRK" else None
    project_root = Path(historical_pdrk) if historical_pdrk else Path(root) / project
    path = project_root / "operators/plasma_dispersion_function/scientific_operator.py"
    assert path.is_file()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SOURCE_HASHES[project]
    spec = importlib.util.spec_from_file_location(f"{project}_plasma_dispersion", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.scientific_operator


def test_pdrk_order_32_matches_canonical_relation_on_bounded_domain():
    source = _source_operator("PDRK")
    z = np.array([0j, 1.5j, -2j, 0.5 + 0.5j, 2.0 - 0.8j, -3.0 + 0j])
    candidate = evaluate_plasma_dispersion(z)
    retained = source(z=z, N=32)
    np.testing.assert_allclose(candidate["w"], retained["w"], rtol=0, atol=1e-12)
    np.testing.assert_allclose(candidate["Z"], retained["Z"], rtol=0, atol=2e-12)


def test_pdrk_default_order_is_a_numerical_variant_not_exact_equivalence():
    source = _source_operator("PDRK")
    canonical = evaluate_plasma_dispersion(0.5)["w"]
    approximate = source(z=0.5)["w"]
    assert 1e-8 < abs(canonical - approximate) < 2e-7


def test_fluidbw_order_64_matches_canonical_relation_on_bounded_domain():
    source = _source_operator("fluidBW")
    z = np.array([0j, 1.5j, -2j, 0.5 + 0.5j, 2.0 - 0.8j, -3.0 + 0j, 8.0])
    candidate = evaluate_plasma_dispersion(z)
    retained = source(z)
    np.testing.assert_allclose(candidate["w"], retained["w"], rtol=0, atol=1e-13)
    np.testing.assert_allclose(candidate["Z"], retained["Z"], rtol=0, atol=2e-13)

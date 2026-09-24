"""Saved fluidBW oracle and implementation comparisons without L1 writes."""

import ast
import hashlib
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic.bessel_gamma import evaluate_bessel_gamma


SOURCE_SHA256 = "2aa8a7079c0d248b25832dc15a09e5c2e019244afd62a721581c9e032c1e080c"
TEST_SHA256 = "8d98d3deb98e859ac66ce21188c8c015f60956cdd1c5b7b879fd4c12bd36432d"
ABS_TOL = 1e-15
REL_TOL = 1e-13


def _source_and_oracle():
    historical = os.environ.get("SCIREL_HISTORICAL_FLUIDBW_ROOT")
    delivery = os.environ.get("SCIREL_L1_ROOT")
    project_root = Path(historical) if historical else Path(delivery) / "fluidBW" if delivery else None
    if project_root is None or not project_root.is_dir():
        pytest.skip("fluidBW L1 input is not configured; scientific contract tests remain active")
    operator_dir = project_root / "operators/bessel_gamma_functions"
    source_path = operator_dir / "scientific_operator.py"
    test_path = operator_dir / "test_scientific_operator.py"
    source = source_path.read_bytes()
    test_source = test_path.read_bytes()
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA256
    assert hashlib.sha256(test_source).hexdigest() == TEST_SHA256
    namespace = {"__name__": "fluidbw_bessel_gamma"}
    exec(compile(source, str(source_path), "exec"), namespace)
    tree = ast.parse(test_source, filename=str(test_path))
    reference = next(
        ast.literal_eval(statement.value)
        for statement in tree.body
        if isinstance(statement, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "REFERENCE" for target in statement.targets)
    )
    return namespace["scientific_operator"], reference


def test_saved_source_oracle_grid_and_parity():
    source, reference = _source_and_oracle()
    assert len(reference) == 98
    order = np.array([row[0] for row in reference])
    argument = np.array([row[1] for row in reference])
    candidate = evaluate_bessel_gamma(order, argument)
    retained = source(order, argument)
    for key, column in (("Gamma_n", 2), ("Gamma_prime_n", 3)):
        golden = np.asarray([row[column] for row in reference])
        difference = np.abs(candidate[key] - golden)
        assert float(np.max(difference)) <= ABS_TOL
        assert float(np.max(difference / np.maximum(np.abs(golden), 1e-300))) <= REL_TOL
        np.testing.assert_allclose(candidate[key], retained[key], rtol=0, atol=ABS_TOL)

"""Bounded replay of the saved fluidBW L1 kinetic dispersion relation."""

import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from scirel.kinetic import evaluate_kinetic_dispersion_sum

SOURCE_HASH = "06c1cb9c6c3c61288afe3438ccea90c48d31fb72c6591af1b71f31a8580f075e"
KB = 1.38064852e-23
QE = 1.60217662e-19
ME = 9.1094e-31
MP = 1.6726219e-27
CASE_SINGLE = dict(
    B0=1.0, qs=np.array([-QE]), ms=np.array([ME]), ns0=np.array([6.075e19]),
    Ts0=np.array([1e3 * 1.6022e-19 / KB]), kz=1326.1942478795652,
)
CASE_PAIR = dict(
    B0=6.0, qs=np.array([-QE, QE]), ms=np.array([ME, 2 * MP]),
    ns0=np.array([2e20, 2e20]), Ts0=np.array([4e3 * 1.6022e-19 / KB] * 2),
    kz=65.65372832698084,
)


def _source_operator():
    historical = os.environ.get("SCIREL_HISTORICAL_FLUIDBW_ROOT")
    delivery = os.environ.get("SCIREL_L1_ROOT")
    project_root = Path(historical) if historical else Path(delivery) / "fluidBW" if delivery else None
    if project_root is None or not project_root.is_dir():
        pytest.skip("fluidBW L1 input is not configured; saved-oracle tests remain active")
    path = project_root / "operators/kinetic_dispersion_sum_n/scientific_operator.py"
    assert path.is_file()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SOURCE_HASH
    spec = importlib.util.spec_from_file_location("fluidbw_kinetic_dispersion_sum_n", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.scientific_operator


@pytest.mark.parametrize(
    "case,omega,kx,lmx",
    [
        (CASE_SINGLE, 175881684853.009, 13261.94247879565, 5),
        (CASE_SINGLE, 175881684853.009, 13261.94247879565, 15),
        (CASE_PAIR, 718412490.59336126, 656.53728326980831, 5),
    ],
)
def test_scirel_matches_frozen_l1_on_bounded_inputs(case, omega, kx, lmx):
    source = _source_operator()
    inputs = dict(case, f=omega / (2 * np.pi), kx=kx, lmx=lmx)
    actual = evaluate_kinetic_dispersion_sum(**inputs)
    original = source(**inputs)
    np.testing.assert_allclose(actual["K"], original["K"], rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(actual["D"], original["D"], rtol=1e-12, atol=1e-12)
    assert abs(actual["determinant"] - original["determinant"]) <= 1e-12 * abs(original["determinant"])

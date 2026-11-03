"""Ronnmark, tensor diagnostic, and signed complex-root source cases."""

import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from scirel.kinetic import (
    evaluate_kinetic_dielectric_tensor,
    evaluate_kinetic_dispersion_ronnmark,
    evaluate_ronnmark_r,
    solve_kinetic_wavevector_roots,
)


CASE = dict(
    B0=1.0, qs=[-1.60217662e-19], ms=[9.1094e-31], ns0=[6.075e19],
    Ts0=[1000.0 * 1.6022e-19 / 1.38064852e-23],
)
WN = 175881684853.009
KN = 13261.94247879565

ROOT = Path(__file__).resolve().parents[2]


def _run_import_probe(source: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-c", source],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("x,lam,branch", [
    (0.5, 0.25, "RTAY(AL<4)"),
    (5.5, 4.0, "RINT"),
    (0.05, 100.0, "RASY"),
])
def test_ronnmark_selector_source_branches(x, lam, branch):
    assert evaluate_ronnmark_r(x, lam)["branch"] == branch


@pytest.mark.parametrize("x,lam", [(np.nan, 1.0), (1.0, np.inf)])
def test_ronnmark_selector_rejects_nonfinite_inputs(x, lam):
    with pytest.raises(ValueError):
        evaluate_ronnmark_r(x, lam)


def test_ronnmark_complex_wavepoint_and_zero_kz():
    out = evaluate_kinetic_dispersion_ronnmark(
        **CASE, f=WN / (2 * np.pi), kz=1326.1942478795652,
        kx=KN + 663.0971239397826j,
    )
    assert out["determinant"] == pytest.approx(
        651060.3902992245 + 4501393.276005662j, rel=1e-11
    )
    zero = evaluate_kinetic_dispersion_ronnmark(
        **CASE, omega=0.11 * WN, kz=0.0,
        kx=-0.17247987402764309 - 0.12372615593987332j,
    )
    assert zero["nz"] == 0
    assert zero["determinant"] == pytest.approx(
        1677715.8370950853 + 0.071368484095235246j, rel=1e-9
    )


@pytest.mark.parametrize("omega_frac,kx,expected", [
    (0.5, 328.26864163490416 + 32.82686416349042j,
     2072381829944473 + 682075474436386.1j),
    (1.0, 656.5372832698083 + 32.82686416349042j,
     638013122809463.6 + 853704298255882.2j),
    (1.5, 1313.0745665396166 + 32.82686416349042j,
     475033329182035 + 126259624643246.12j),
])
def test_two_species_complex_kx_matches_frozen_source(omega_frac, kx, expected):
    out = evaluate_kinetic_dispersion_ronnmark(
        B0=6.0,
        qs=[-1.60217662e-19, 1.60217662e-19],
        ms=[9.1094e-31, 2 * 1.6726219e-27],
        ns0=[2e20, 2e20],
        Ts0=[4000 * 1.6022e-19 / 1.38064852e-23] * 2,
        f=omega_frac * 287364996.2373445 / (2 * np.pi),
        kz=65.65372832698084,
        kx=kx,
    )
    assert out["determinant"] == pytest.approx(expected, rel=1e-11)


@pytest.mark.parametrize("change", [
    {"B0": np.nan}, {"kz": np.inf}, {"kx": complex(np.nan, 0)},
    {"qs": [0.0]}, {"f": WN / (2 * np.pi), "omega": WN},
])
def test_ronnmark_invalid_controls_fail_closed(change):
    args = dict(CASE, f=WN / (2 * np.pi), kz=0.0, kx=KN)
    args.update(change)
    with pytest.raises(ValueError):
        evaluate_kinetic_dispersion_ronnmark(**args)


def test_full_tensor_diagnostic_keeps_15_harmonics_and_six_term_det():
    out = evaluate_kinetic_dielectric_tensor(
        **CASE, f=WN / (2 * np.pi), kz=1326.1942478795652, kx=KN
    )
    assert out["lmx"] == 15
    assert out["det_D"] == pytest.approx(
        1184259.0392493994 + 4322544.5590004744j, rel=1e-11
    )
    assert out["K"][0, 0] == pytest.approx(1.323438756569723 + 16.286340462141965j)


@pytest.mark.parametrize("change", [{"B0": 1.0 + 0.1j}, {"qs": [0.0]}])
def test_full_tensor_diagnostic_rejects_invalid_species_controls(change):
    args = dict(CASE, f=WN / (2 * np.pi), kz=1326.1942478795652, kx=KN)
    args.update(change)
    with pytest.raises(ValueError):
        evaluate_kinetic_dielectric_tensor(**args)


def test_diagnostic_module_star_import_exports_public_callable():
    namespace = {}
    exec("from scirel.kinetic.dielectric_tensor_diagnostic import *", namespace)
    assert namespace["evaluate_kinetic_dielectric_tensor"] is evaluate_kinetic_dielectric_tensor


def test_full_tensor_diagnostic_import_and_rejected_call_defer_scipy():
    result = _run_import_probe(
        """
import sys
from scirel.kinetic import evaluate_kinetic_dielectric_tensor
from scirel.kinetic.dielectric_tensor_diagnostic import (
    evaluate_kinetic_dielectric_tensor as direct,
)

assert evaluate_kinetic_dielectric_tensor is direct
assert "scipy" not in sys.modules
try:
    evaluate_kinetic_dielectric_tensor(
        0.0, [-1.0], [1.0], [1.0], [1.0], 1.0, 1.0, 1.0,
    )
except ValueError as error:
    assert str(error) == "B0 must be non-zero: wcs and rhocs degenerate at B0=0"
else:
    raise AssertionError("invalid dielectric-tensor input unexpectedly succeeded")
assert "scipy" not in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_full_tensor_diagnostic_valid_call_loads_special_backend():
    result = _run_import_probe(
        """
import sys
from scirel.kinetic import evaluate_kinetic_dielectric_tensor

assert "scipy" not in sys.modules
output = evaluate_kinetic_dielectric_tensor(
    1.0, [-1.0], [1.0], [1.0], [1.0], 1.0, 1.0, 1.0, lmx=0,
)
assert output["K"].shape == (3, 3)
assert "scipy.special" in sys.modules
"""
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_complex_root_preserves_source_sign_and_exit_flag():
    out = solve_kinetic_wavevector_roots(
        **CASE, omegas=[0.11 * WN], kz=0.0, kx_start=0.6 * KN
    )
    assert out["roots"][0] == pytest.approx(
        -0.1724798740276431 - 0.12372615593987332j, rel=1e-9, abs=1e-9
    )
    assert out["exit_flags"][0] == 0
    assert out["converged"][0] == False


@pytest.mark.parametrize("change", [
    {"B0": np.nan}, {"qs": [0.0]}, {"max_iterations": 2.5},
])
def test_root_scan_rejects_invalid_controls(change):
    args = dict(CASE, omegas=[0.11 * WN], kz=0.0, kx_start=0.6 * KN)
    args.update(change)
    with pytest.raises(ValueError):
        solve_kinetic_wavevector_roots(**args)

"""Signed-kz reflection regressions for the homogeneous Maxwellian leaves."""

import numpy as np
import pytest

from scirel.kinetic import evaluate_dielectric_response, evaluate_dielectric_diagnostics

Q = -1.60217662e-19
M = 9.1094e-31
N = 6.075e19
T = 1000.0 * 1.6022e-19 / 1.38064852e-23
ARGS = dict(
    B0=1.0,
    qs=[Q],
    ms=[M],
    ns0=[N],
    Ts0=[T],
    omega=2.0 * np.pi * float(175881684853.009 / (2 * np.pi)),
    kx=13261.94247879565,
)
P = np.diag([1.0, 1.0, -1.0])


@pytest.mark.parametrize(
    "call, kwargs",
    [
        (evaluate_dielectric_diagnostics, {"harmonics": 15}),
        (evaluate_dielectric_response, {"method": "harmonic", "harmonics": 5}),
        (evaluate_dielectric_response, {"method": "harmonic_weideman", "harmonics": 5}),
        (evaluate_dielectric_response, {"method": "ronnmark"}),
    ],
)
def test_signed_kz_reflects_full_tensor_and_preserves_determinant(call, kwargs):
    plus = call(**ARGS, kz=1326.1942478795652, **kwargs)
    minus = call(**ARGS, kz=-1326.1942478795652, **kwargs)
    diagnostic = call is evaluate_dielectric_diagnostics
    k_key, d_key = ("K_raw", "D_raw") if diagnostic else ("K", "D")
    np.testing.assert_allclose(minus[k_key], P @ plus[k_key] @ P, rtol=2e-12, atol=2e-12)
    np.testing.assert_allclose(minus[d_key], P @ plus[d_key] @ P, rtol=2e-12, atol=2e-12)
    key = "determinant_raw" if diagnostic else "determinant"
    assert minus[key] == pytest.approx(plus[key], rel=2e-12, abs=2e-12)
    assert minus["nz"] == -plus["nz"]


@pytest.mark.parametrize(
    "kz", [1e-12, np.nextafter(1e-10, 0.0), 1e-10, np.nextafter(1e-10, np.inf)]
)
def test_fluid_near_zero_uses_actual_kz_and_signed_reflection(kz):
    plus = evaluate_dielectric_response(method="harmonic_weideman", **ARGS, kz=kz, harmonics=5)
    minus = evaluate_dielectric_response(method="harmonic_weideman", **ARGS, kz=-kz, harmonics=5)
    for key in ("K", "D"):
        np.testing.assert_allclose(minus[key], P @ plus[key] @ P, rtol=2e-12, atol=2e-12)
    assert minus["determinant"] == pytest.approx(plus["determinant"], rel=2e-12, abs=2e-12)
    assert plus["nz"] == np.sqrt((2.99792458e8) ** 2) * kz / ARGS["omega"]
    assert minus["nz"] == -plus["nz"]

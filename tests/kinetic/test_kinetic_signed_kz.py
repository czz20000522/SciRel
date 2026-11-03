"""Signed-kz reflection regressions for the homogeneous Maxwellian leaves."""
import numpy as np
import pytest

from scirel.kinetic import (
    evaluate_fluid_kinetic_dispersion_sum,
    evaluate_kinetic_dispersion_ronnmark,
    evaluate_kinetic_dispersion_sum,
    evaluate_kinetic_dielectric_tensor,
)

Q = -1.60217662e-19
M = 9.1094e-31
N = 6.075e19
T = 1000.0 * 1.6022e-19 / 1.38064852e-23
ARGS = dict(B0=1.0, qs=[Q], ms=[M], ns0=[N], Ts0=[T], f=175881684853.009 / (2*np.pi), kx=13261.94247879565)
P = np.diag([1.0, 1.0, -1.0])

@pytest.mark.parametrize("call, kwargs", [
    (evaluate_kinetic_dielectric_tensor, {"lmx": 15}),
    (evaluate_kinetic_dispersion_sum, {"lmx": 5}),
    (evaluate_fluid_kinetic_dispersion_sum, {"lmx": 5}),
    (evaluate_kinetic_dispersion_ronnmark, {}),
])
def test_signed_kz_reflects_full_tensor_and_preserves_determinant(call, kwargs):
    plus = call(**ARGS, kz=1326.1942478795652, **kwargs)
    minus = call(**ARGS, kz=-1326.1942478795652, **kwargs)
    np.testing.assert_allclose(minus["K"], P @ plus["K"] @ P, rtol=2e-12, atol=2e-12)
    np.testing.assert_allclose(minus["D"], P @ plus["D"] @ P, rtol=2e-12, atol=2e-12)
    key = "det_D" if "det_D" in plus else "determinant"
    assert minus[key] == pytest.approx(plus[key], rel=2e-12, abs=2e-12)
    assert minus["nz"] == -plus["nz"]


def test_fluid_negative_near_zero_keeps_the_positive_clamp():
    plus = evaluate_fluid_kinetic_dispersion_sum(**ARGS, kz=1e-12, lmx=5)
    minus = evaluate_fluid_kinetic_dispersion_sum(**ARGS, kz=-1e-12, lmx=5)
    endpoint = evaluate_fluid_kinetic_dispersion_sum(**ARGS, kz=1e-10, lmx=5)
    np.testing.assert_array_equal(plus["D"], endpoint["D"])
    np.testing.assert_array_equal(minus["D"], endpoint["D"])
    assert plus["nz"] == minus["nz"] == endpoint["nz"]

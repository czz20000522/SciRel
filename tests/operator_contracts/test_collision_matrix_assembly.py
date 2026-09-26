"""Direct contract tests for the r67 collision-matrix assembly family:
``assemble_atomic_hydrogen_collision_matrices`` and
``assemble_molecular_hydrogen_collision_matrices``.

The oracle below is an independent broadcasting-geometry recomputation of the
saved KN1DPy source mapping (kinetic_h.py:888-1018 / kinetic_h2.py:1036-1125)
with the source's own embedded cross-section formulas, including the source's
``np.e **`` charge-exchange evaluation.  The integrated ports reuse the
standardized ``scirel.collisions`` leaves, so the charge-exchange families are
compared to the oracle with the saved packages' rtol=1e-12 budget, which also
covers the sampled ~2.2e-15 ``np.exp`` vs ``np.e **`` deviation.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import (
    assemble_atomic_hydrogen_collision_matrices,
    assemble_molecular_hydrogen_collision_matrices,
    contract_atomic_hydrogen_alpha_frequencies,
    contract_molecular_hydrogen_alpha_frequencies,
)

H_MASS = 1.6726231e-27
Q = 1.602177e-19
NTHETA = 5
D_THETA = np.ones(NTHETA) / NTHETA
THETA = np.pi * (np.arange(NTHETA) / NTHETA + 0.5 / NTHETA)
COS_THETA = np.cos(THETA)


def _poly(x, coefficients):
    x = np.asarray(x)
    n = len(coefficients) - 1
    y = coefficients[n] * np.ones_like(x, dtype=float)
    for i in range(n - 1, -1, -1):
        y = y * x + coefficients[i]
    return y


# Source-embedded cross-section formulas (independent oracle copies of the
# saved KN1DPy sigma/ slices, including the source's np.e ** evaluation).
_JANEV_CX_COEFFICIENTS = np.array([
    -3.274123792568e1, -8.916456579806e-2, -3.016990732025e-2,
    9.205482406462e-3, 2.400266568315e-3, -1.927122311323e-3,
    3.654750340106e-4, -2.788866460622e-5, 7.422296363524e-7,
])
_H_H_VISCOSITY_COEFFICIENTS = np.array([
    -3.344860e1, -4.238982e-1, -7.477873e-2, -7.915053e-3, -2.686129e-4,
])
_H_H2_COEFFICIENTS = np.array([
    -3.495671e1, -4.062257e-1, -3.820531e-2, -9.404486e-3, 3.963723e-4,
])
_H_P_LOW_COEFFICIENTS = np.array([
    -3.233966e1, -1.126918e-1, 5.287706e-3, -2.445017e-3,
    -1.044156e-3, 8.419691e-5, 3.824773e-5,
])
_H_P_HIGH_COEFFICIENTS = np.array([-3.231141e1, -1.386002e-1])
_CX_HH_COEFFICIENTS = np.array([
    -3.427958758517e1, -7.121484125189e-2, 4.690466187943e-2,
    -8.033946660540e-3, -2.265090924593e-3, -2.102414848737e-4,
    1.948869487515e-4, -2.208124950005e-5, 7.262446915488e-7,
])
_H2_P_COEFFICIENTS = np.array([
    -3.355719e1, -5.696568e-1, -4.089556e-2, -1.143513e-2, 5.926596e-4,
])
_H2_H2_COEFFICIENTS = np.array([
    -3.430345e1, -2.960406e-1, -6.382532e-2, -7.557519e-3, 2.606259e-4,
])


def _sigma_cx_h0(e):
    return np.e ** (_poly(np.log(np.minimum(np.maximum(e, 0.1), 2.01e4)), _JANEV_CX_COEFFICIENTS)) * 1.0e-4


def _sigma_el_h_h(e):
    return np.exp(_poly(np.log(np.minimum(np.maximum(e, 0.03), 1.01e4)), _H_H_VISCOSITY_COEFFICIENTS)) * 1.0e-4


def _sigma_el_h_hh(e):
    return np.exp(_poly(np.log(np.minimum(np.maximum(e, 0.03), 1.01e4)), _H_H2_COEFFICIENTS)) * 1.0e-4


def _sigma_el_p_h(e):
    e = np.minimum(np.maximum(e, 0.001), 1.01e5)
    result = np.zeros(np.shape(e), dtype=float)
    result = np.where(e < 10.0, np.exp(_poly(np.log(e), _H_P_LOW_COEFFICIENTS)) * 1.0e-4, result)
    result = np.where(e > 10.0, np.exp(_poly(np.log(e), _H_P_HIGH_COEFFICIENTS)) * 1.0e-4, result)
    return result


def _sigma_cx_hh(e):
    return np.e ** (_poly(np.log(np.minimum(np.maximum(e, 0.1), 2.01e4)), _CX_HH_COEFFICIENTS)) * 1.0e-4


def _sigma_el_p_hh(e):
    return np.exp(_poly(np.log(np.minimum(np.maximum(e, 0.03), 1.01e4)), _H2_P_COEFFICIENTS)) * 1.0e-4


def _sigma_el_hh_hh(e):
    return np.exp(_poly(np.log(np.minimum(np.maximum(e, 0.03), 1.01e4)), _H2_H2_COEFFICIENTS)) * 1.0e-4


def _geometry(vr, vx):
    """Broadcasting-geometry predecessor state, independent of the port loops."""
    nvr, nvx = vr.size, vx.size
    i = np.arange(nvr)[:, None, None, None, None]
    k = np.arange(nvr)[None, None, :, None, None]
    l = np.arange(nvx)[None, None, None, :, None]
    j = np.arange(nvx)[None, :, None, None, None]
    m = np.arange(NTHETA)[None, None, None, None, :]
    v_starter = vr[i] ** 2 + vr[k] ** 2 - 2 * vr[i] * vr[k] * COS_THETA[m]
    v_v2 = v_starter + (vx[None, :, None, None, None] - vx[l]) ** 2
    vr2_vx2 = v_starter - 2 * (vx[None, :, None, None, None] - vx[l]) ** 2
    v_v = np.sqrt(v_v2)
    j_axis = np.arange(nvx)[None, :, None, None]
    l_axis = np.arange(nvx)[None, None, None, :]
    vx_vx = np.broadcast_to(vx[j_axis] - vx[l_axis], (nvr, nvx, nvr, nvx)).copy()
    return v_v2, v_v, vr2_vx2, vx_vx


def _atomic_oracle(vr, vx, Vr2pidVr, dVx, Tnorm, mu=1.0):
    vr = np.asarray(vr, float)
    vx = np.asarray(vx, float)
    nvr, nvx = vr.size, vx.size
    Vth = np.sqrt((2 * Q * Tnorm) / (mu * H_MASS))
    Vth2 = Vth * Vth
    ecx = 0.5 * H_MASS * Vth2 / Q
    ehh = 0.5 * H_MASS * mu * Vth2 / Q
    v_v2, v_v, vr2_vx2, vx_vx = _geometry(vr, vx)
    Vr2pidVrdVx = Vr2pidVr[None, None, :, None] * dVx[None, None, None, :]
    Vr2pidVrdVx = np.broadcast_to(Vr2pidVrdVx, (nvr, nvx, nvr, nvx)).copy()
    f_v = Vr2pidVrdVx.reshape((nvr * nvx * nvr * nvx,), order="F")
    f_vxvx = vx_vx.reshape((nvr * nvx * nvr * nvx,), order="F")

    def contract(integrand_5d, with_vx_vx=False):
        flat = integrand_5d.reshape((nvr * nvx * nvr * nvx, NTHETA), order="F")
        base = f_v * (flat @ D_THETA)
        if with_vx_vx:
            base = base * f_vxvx
        return base.reshape((nvr * nvx, nvr * nvx), order="F")

    return {
        "SIG_CX": contract(v_v * _sigma_cx_h0(v_v2 * ecx)),
        "SIG_H_H": contract(vr2_vx2 * v_v * _sigma_el_h_h(v_v2 * ehh) / 8),
        "SIG_H_H2": contract(v_v * _sigma_el_h_hh(v_v2 * ecx), with_vx_vx=True),
        "SIG_H_P": contract(v_v * _sigma_el_p_h(v_v2 * ecx), with_vx_vx=True),
        "v_v2": v_v2,
        "v_v": v_v,
        "vr2_vx2": vr2_vx2,
        "vx_vx": vx_vx,
        "Vr2pidVrdVx": Vr2pidVrdVx,
    }


def _molecular_oracle(vr, vx, Vr2pidVr, dVx, Tnorm, mu=1.0):
    vr = np.asarray(vr, float)
    vx = np.asarray(vx, float)
    nvr, nvx = vr.size, vx.size
    Vth = np.sqrt((2 * Q * Tnorm) / (mu * H_MASS))
    Vth2 = Vth * Vth
    ecx = H_MASS * Vth2 / Q
    e_half = 0.5 * H_MASS * Vth2 / Q
    eh2 = H_MASS * mu * Vth2 / Q
    v_v2, v_v, vr2_vx2, vx_vx = _geometry(vr, vx)
    Vr2pidVrdVx = Vr2pidVr[None, None, :, None] * dVx[None, None, None, :]
    Vr2pidVrdVx = np.broadcast_to(Vr2pidVrdVx, (nvr, nvx, nvr, nvx)).copy()
    f_v = Vr2pidVrdVx.reshape((nvr * nvx * nvr * nvx,), order="F")
    f_vxvx = vx_vx.reshape((nvr * nvx * nvr * nvx,), order="F")

    def contract(integrand_5d, with_vx_vx=False):
        flat = integrand_5d.reshape((nvr * nvx * nvr * nvx, NTHETA), order="F")
        base = f_v * (flat @ D_THETA)
        if with_vx_vx:
            base = base * f_vxvx
        return base.reshape((nvr * nvx, nvr * nvx), order="F")

    return {
        "SIG_CX": contract(v_v * _sigma_cx_hh(v_v2 * ecx)),
        "SIG_H2_H": contract(v_v * _sigma_el_h_hh(v_v2 * e_half), with_vx_vx=True),
        "SIG_H2_P": contract(v_v * _sigma_el_p_hh(v_v2 * e_half), with_vx_vx=True),
        "SIG_H2_H2": contract(vr2_vx2 * v_v * _sigma_el_hh_hh(v_v2 * eh2) / 8.0),
        "v_v2": v_v2,
        "v_v": v_v,
        "vr2_vx2": vr2_vx2,
        "vx_vx": vx_vx,
        "Vr2pidVrdVx": Vr2pidVrdVx,
    }


CANONICAL = dict(vr=np.array([0.5, 1.0]), vx=np.array([-1.0, 1.0]),
                 Vr2pidVr=np.array([1.7671458676442586, 3.141592653589793]),
                 dVx=np.array([2.0, 2.0]), Tnorm=1.0, mu=1.0)

HOLDOUT = dict(vr=np.array([0.4, 0.8, 1.5]), vx=np.array([-2.0, -1.0, 1.0, 2.0]),
               Vr2pidVr=np.array([1.1309733552923258, 3.0237829290801748, 6.597344572538567]),
               dVx=np.array([1.0, 1.5, 1.5, 1.0]), Tnorm=5.0, mu=1.0)


@pytest.mark.parametrize("case", [CANONICAL, HOLDOUT])
def test_atomic_matches_independent_oracle(case):
    result = assemble_atomic_hydrogen_collision_matrices(**case)
    expected = _atomic_oracle(**case)
    for name in ("SIG_CX", "SIG_H_H", "SIG_H_H2", "SIG_H_P"):
        np.testing.assert_allclose(result[name], expected[name], rtol=1e-12, atol=0.0)
        assert result[name].shape == (case["vr"].size * case["vx"].size,) * 2


@pytest.mark.parametrize("case", [CANONICAL, HOLDOUT])
def test_molecular_matches_independent_oracle(case):
    result = assemble_molecular_hydrogen_collision_matrices(**case)
    expected = _molecular_oracle(**case)
    for name in ("SIG_CX", "SIG_H2_H", "SIG_H2_P", "SIG_H2_H2"):
        np.testing.assert_allclose(result[name], expected[name], rtol=1e-12, atol=0.0)
        assert result[name].shape == (case["vr"].size * case["vx"].size,) * 2


@pytest.mark.parametrize("case", [CANONICAL, HOLDOUT])
@pytest.mark.parametrize("assemble,oracle,prefix", [
    (assemble_atomic_hydrogen_collision_matrices, _atomic_oracle, ("v_v2", "v_v", "vr2_vx2", "vx_vx", "Vr2pidVrdVx")),
    (assemble_molecular_hydrogen_collision_matrices, _molecular_oracle, ("v_v2", "v_v", "vr2_vx2", "vx_vx", "Vr2pidVrdVx")),
])
def test_predecessor_state_and_thermal_normalization(assemble, oracle, prefix, case):
    result = assemble(**case)
    expected = oracle(**case)
    for name in prefix:
        np.testing.assert_allclose(result[name], expected[name], rtol=1e-12, atol=0.0)
    vth2 = np.sqrt((2 * Q * case["Tnorm"]) / (case["mu"] * H_MASS))
    assert result["Vth2"][0] == vth2 * vth2
    assert result["Vth2"].shape == (1,)


@pytest.mark.parametrize("assemble,families", [
    (assemble_atomic_hydrogen_collision_matrices, ("SIG_H_H", "SIG_H_H2", "SIG_H_P")),
    (assemble_molecular_hydrogen_collision_matrices, ("SIG_H2_H", "SIG_H2_P", "SIG_H2_H2")),
])
def test_sig_cx_nonnegative_and_elastic_negative_cells_bounded(assemble, families):
    for case in (CANONICAL, HOLDOUT):
        result = assemble(**case)
        assert np.all(result["SIG_CX"] >= 0.0)
        for name in families:
            matrix = result[name]
            negatives = matrix[matrix < 0.0]
            assert negatives.size > 0
            assert np.all(np.isfinite(matrix))
            assert np.max(np.abs(negatives)) <= np.max(np.abs(matrix))
    # Deterministic negative-cell counts on the canonical fixture, asserted
    # against the actual recomputation (atomic 8/4/4 matches the saved
    # operator.md note; the saved molecular operator.md claims 2/2/4, which
    # CONFLICTS with this reproducible canonical computation 4/4/8 -- the
    # saved document is kept verbatim and the cause is left to expert review).
    atomic = assemble_atomic_hydrogen_collision_matrices(**CANONICAL)
    assert int((atomic["SIG_H_H"] < 0).sum()) == 8
    assert int((atomic["SIG_H_H2"] < 0).sum()) == 4
    assert int((atomic["SIG_H_P"] < 0).sum()) == 4
    molecular = assemble_molecular_hydrogen_collision_matrices(**CANONICAL)
    assert int((molecular["SIG_H2_H"] < 0).sum()) == 4
    assert int((molecular["SIG_H2_P"] < 0).sum()) == 4
    assert int((molecular["SIG_H2_H2"] < 0).sum()) == 8


def test_molecular_sig_cx_energy_factor_differs_from_atomic():
    """The molecular CX energy factor is H_MASS*Vth2/Q (no 0.5, no mu)."""
    atomic = assemble_atomic_hydrogen_collision_matrices(**CANONICAL)
    molecular = assemble_molecular_hydrogen_collision_matrices(**CANONICAL)
    assert not np.allclose(molecular["SIG_CX"], atomic["SIG_CX"], rtol=1e-12, atol=0.0)
    oracle = _molecular_oracle(**CANONICAL)
    np.testing.assert_allclose(molecular["SIG_CX"], oracle["SIG_CX"], rtol=1e-12, atol=0.0)


def test_invalid_carrier_fails_closed():
    good = dict(vr=np.array([0.5, 1.0]), vx=np.array([-1.0, 1.0]),
                Vr2pidVr=np.array([1.0, 2.0]), dVx=np.array([2.0, 2.0]),
                Tnorm=1.0, mu=1.0)
    bad_cases = [
        dict(good, Vr2pidVr=np.array([1.0])),                    # length mismatch
        dict(good, Vr2pidVr=np.array([-1.0, 2.0])),              # negative weight
        dict(good, Tnorm=-1.0),                                  # non-positive Tnorm
        dict(good, vx=np.array([1.0, 2.0])),                     # no negative side
        dict(good, dVx=np.array([0.0, 2.0])),                    # non-positive dVx
        dict(good, vr=np.array([0.0, 1.0])),                     # non-positive vr
        dict(good, Tnorm=np.nan),                                # non-finite
        dict(good, mu=0.0),                                      # non-positive mu
        dict(good, Tnorm=np.array([1.0])),                       # non-scalar Tnorm
        dict(good, mu=np.array([1.0])),                          # non-scalar mu
        dict(good, Tnorm=np.array([])),                          # empty Tnorm
    ]
    for assemble in (assemble_atomic_hydrogen_collision_matrices,
                     assemble_molecular_hydrogen_collision_matrices):
        for case in bad_cases:
            with pytest.raises(ValueError):
                assemble(**case)


def test_carrier_inputs_are_not_modified():
    vr = np.array([0.5, 1.0])
    vx = np.array([-1.0, 1.0])
    weights = np.array([1.7671458676442586, 3.141592653589793])
    dvx = np.array([2.0, 2.0])
    vr_before, vx_before = vr.copy(), vx.copy()
    weights_before, dvx_before = weights.copy(), dvx.copy()
    assemble_atomic_hydrogen_collision_matrices(vr, vx, weights, dvx, 1.0, 1.0)
    assemble_molecular_hydrogen_collision_matrices(vr, vx, weights, dvx, 1.0, 1.0)
    np.testing.assert_array_equal(vr, vr_before)
    np.testing.assert_array_equal(vx, vx_before)
    np.testing.assert_array_equal(weights, weights_before)
    np.testing.assert_array_equal(dvx, dvx_before)


def test_composition_with_r66_alpha_contraction():
    """The assembled SIG matrices feed the r66 contraction ports unchanged."""
    sig_a = assemble_atomic_hydrogen_collision_matrices(**CANONICAL)
    nvr, nvx = 2, 2
    nx = 1
    fi_hat = np.ones((nvr, nvx, nx))
    fH2 = np.full((nvr, nvx, nx), 0.5)
    fH = np.full((nvr, nvx, nx), 0.25)
    ni = np.full(nx, 1e18)
    alpha = contract_atomic_hydrogen_alpha_frequencies(
        sig_a["SIG_CX"], sig_a["SIG_H_H"], sig_a["SIG_H_H2"], sig_a["SIG_H_P"],
        fi_hat, ni, fH2, fH,
    )
    assert set(alpha) == {"Alpha_CX", "Alpha_H_H2", "Alpha_H_P", "Alpha_H_H"}
    for key in alpha:
        assert alpha[key].shape == fi_hat.shape
        assert np.all(np.isfinite(alpha[key]))
    assert np.all(alpha["Alpha_CX"] >= 0.0)

    sig_m = assemble_molecular_hydrogen_collision_matrices(**CANONICAL)
    fHp_hat = np.full((nvr, nvx, nx), 0.75)
    n = np.full(nx, 1e18)
    nHP = np.full(nx, 5e17)
    alpha_m = contract_molecular_hydrogen_alpha_frequencies(
        sig_m["SIG_CX"], sig_m["SIG_H2_H"], sig_m["SIG_H2_P"],
        fH2, fHp_hat, fi_hat, n, nHP,
    )
    assert set(alpha_m) == {"Alpha_CX", "Alpha_H2_H", "Alpha_H2_P"}
    for key in alpha_m:
        assert alpha_m[key].shape == fi_hat.shape
        assert np.all(np.isfinite(alpha_m[key]))
    assert np.all(alpha_m["Alpha_CX"] >= 0.0)

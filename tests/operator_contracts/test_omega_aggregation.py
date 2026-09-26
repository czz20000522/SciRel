"""Direct contract tests for the r68 Omega aggregation family:
``assemble_atomic_hydrogen_omega_frequencies`` and
``assemble_molecular_hydrogen_omega_frequencies``.

Oracle style follows the saved packages' own closed-form reduction tests:
every declared output is re-derived independently over manufactured inputs,
including the branch-time SIG re-contraction on the Fortran-order carrier.
The registered divergence regressions (scalar Vth/tol gates, non-finite
output gate) discriminate the documented fail-closed hardenings against the
saved arm, which returns NaN/Inf silently on those boundaries.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import (
    assemble_atomic_hydrogen_omega_frequencies,
    assemble_molecular_hydrogen_omega_frequencies,
)

VR = np.linspace(0.5, 4.5, 9)
VX = np.linspace(-6.0, 6.0, 13)
NX = 3
NVR, NVX = VR.size, VX.size

_R = np.linspace(0.0, 1.0, NVR + 1)
VR2PIDVR = np.pi * (_R[1:] ** 2 - _R[:-1] ** 2)
_X = np.linspace(-6.5, 6.5, NVX + 1)
DVX = np.diff(_X)
KERNEL = VR[:, None] ** 2 - 2.0 * VX[None, :] ** 2

VTH = 1000.0
VXI = np.array([900.0, 800.0, 1200.0])
VXH2 = np.array([700.0, 750.0, 1100.0])
VXH = VXH2
NH = np.array([0.7, 1.9, 1.1])
NH2 = np.array([1.4, 0.9, 2.1])
DELTA_TOL = 0.01
WPP_TOL = 0.001

_RNG_SEED = 44
_SHIFT = 1.5
_SHAPE = np.exp(-(VR[:, None] ** 2 + (VX[None, :] - _SHIFT) ** 2) / 9.0)


def _fixture(weight_sum, seed=_RNG_SEED):
    """Every call draws from a freshly seeded generator so a single affected
    test and the whole-file run see byte-identical carriers."""
    rng = np.random.default_rng(seed)
    amps = rng.uniform(0.7, 1.3, size=NX)
    fh = np.repeat(_SHAPE[:, :, None], NX, axis=2) * amps[None, None, :]
    a1 = rng.uniform(0.1, 0.9, size=(NVR, NVX, NX))
    a2 = rng.uniform(0.1, 0.9, size=(NVR, NVX, NX))
    sig = -rng.uniform(0.1, 0.9, size=(NVR * NVX, NVR * NVX))
    return fh, a1, a2, sig, fh * weight_sum


def _call_atomic(fh, a_p, a_h2, sig, weight, vth=VTH, **overrides):
    kwargs = dict(H_P_EL=True, H_H2_EL=True, H_H_EL=True,
                  DeltaVx_tol=DELTA_TOL, Wpp_tol=WPP_TOL)
    kwargs.update(overrides)
    return assemble_atomic_hydrogen_omega_frequencies(
        fh, NH, a_p, a_h2, sig, VR2PIDVR, DVX, VR, VX, vth, VXI, VXH2,
        weight, KERNEL, **kwargs)


def _call_molecular(fh2, a_p, a_h, sig, weight, vth=VTH, **overrides):
    kwargs = dict(H2_P_EL=True, H2_H_EL=True, H2_H2_EL=True,
                  DeltaVx_tol=DELTA_TOL, Wpp_tol=WPP_TOL)
    kwargs.update(overrides)
    return assemble_molecular_hydrogen_omega_frequencies(
        fh2, NH2, a_p, a_h, sig, VR2PIDVR, DVX, VR, VX, vth, VXI, VXH,
        weight, KERNEL, **kwargs)


def _floored(value, tol):
    return np.sign(value) * max(abs(value), tol)


@pytest.mark.parametrize("weight_sum", [0.5, -0.5])
def test_atomic_channels_match_the_closed_form_reductions(weight_sum):
    fh, a_p, a_h2, sig, w = _fixture(weight_sum)
    out = _call_atomic(fh, a_p, a_h2, sig, w)
    # VxH
    for k in range(NX):
        expected = VTH * np.sum(VR2PIDVR * (fh[:, :, k] @ (VX * DVX))) / NH[k]
        assert out["VxH"][k] == expected
    # Wperp_paraH: atomic branch test is sum(w) <= 0
    for k in range(NX):
        if float(np.sum(w)) <= 0.0:
            profile = VR[:, None] ** 2 - 2.0 * (VX[None, :] - out["VxH"][k] / VTH) ** 2
            expected = np.sum(VR2PIDVR * ((profile * fh[:, :, k]) @ DVX)) / NH[k]
        else:
            momentum = w[:, :, k] - fh[:, :, k]
            expected = -np.sum(VR2PIDVR * ((KERNEL * momentum) @ DVX)) / NH[k]
        np.testing.assert_allclose(out["Wperp_paraH"][k], expected, rtol=1e-13, atol=1e-12)
    # Alpha channels (P against vxi, H2 against vxH2)
    for key, alpha, target in (("Omega_H_P", a_p, VXI), ("Omega_H_H2", a_h2, VXH2)):
        for k in range(NX):
            delta = _floored((out["VxH"][k] - target[k]) / VTH, DELTA_TOL)
            value = np.sum(VR2PIDVR * ((alpha[:, :, k] * fh[:, :, k]) @ DVX))
            np.testing.assert_allclose(
                out[key][k], max(value / (NH[k] * delta), 0.0), rtol=1e-12, atol=1e-9)
    # H-H channel with branch-time SIG re-contraction on the F-order carrier
    for k in range(NX):
        carrier = fh[:, :, k].reshape(NVR * NVX, order="F")
        alpha = np.array((sig @ carrier).reshape((NVR, NVX), order="F"), order="C", copy=True)
        wpp = _floored(out["Wperp_paraH"][k], WPP_TOL)
        value = np.sum(VR2PIDVR * ((alpha * carrier.reshape((NVR, NVX), order="F")) @ DVX))
        np.testing.assert_allclose(
            out["Omega_H_H"][k], max(value / (NH[k] * wpp), 0.0), rtol=1e-12, atol=1e-9)
    # Omega_EL exact sum; outputs nonnegative
    assert np.array_equal(out["Omega_EL"],
                          out["Omega_H_P"] + out["Omega_H_H2"] + out["Omega_H_H"])
    for key in ("Omega_H_P", "Omega_H_H2", "Omega_H_H", "Omega_EL"):
        assert np.all(out[key] >= 0.0)


@pytest.mark.parametrize("weight_sum", [0.5, -0.5])
def test_molecular_channels_match_the_closed_form_reductions(weight_sum):
    fh2, a_p, a_h, sig, w = _fixture(weight_sum)
    out = _call_molecular(fh2, a_p, a_h, sig, w)
    for k in range(NX):
        expected = VTH * np.sum(VR2PIDVR * (fh2[:, :, k] @ (VX * DVX))) / NH2[k]
        assert out["VxH2"][k] == expected
    # Wperp_paraH2: molecular branch test is sum(w) < 0 (zero takes the else path)
    for k in range(NX):
        if float(np.sum(w)) < 0.0:
            profile = VR[:, None] ** 2 - 2.0 * (VX[None, :] - out["VxH2"][k] / VTH) ** 2
            expected = np.sum(VR2PIDVR * ((profile * fh2[:, :, k]) @ DVX)) / NH2[k]
        else:
            momentum = w[:, :, k] - fh2[:, :, k]
            expected = -np.sum(VR2PIDVR * ((KERNEL * momentum) @ DVX)) / NH2[k]
        np.testing.assert_allclose(out["Wperp_paraH2"][k], expected, rtol=1e-13, atol=1e-12)
    # P divides (nH2*DeltaVx) outside the sum; H divides inside it (source-exact order)
    for key, alpha, target in (("Omega_H2_P", a_p, VXI), ("Omega_H2_H", a_h, VXH)):
        for k in range(NX):
            delta = _floored((out["VxH2"][k] - target[k]) / VTH, DELTA_TOL)
            if key == "Omega_H2_P":
                value = np.sum(VR2PIDVR * ((alpha[:, :, k] * fh2[:, :, k]) @ DVX))
                expected = value / (NH2[k] * delta)
            else:
                expected = np.sum(
                    VR2PIDVR * ((alpha[:, :, k] * fh2[:, :, k]) @ DVX) / (NH2[k] * delta))
            np.testing.assert_allclose(out[key][k], max(expected, 0.0), rtol=1e-12, atol=1e-9)
    # H2-H2 channel with branch-time SIG re-contraction
    for k in range(NX):
        carrier = fh2[:, :, k].reshape(NVR * NVX, order="F")
        alpha = (sig @ carrier).reshape((NVR, NVX), order="F")
        wpp = _floored(out["Wperp_paraH2"][k], WPP_TOL)
        value = np.sum(VR2PIDVR * ((alpha * carrier.reshape((NVR, NVX), order="F")) @ DVX))
        np.testing.assert_allclose(
            out["Omega_H2_H2"][k], max(value / (NH2[k] * wpp), 0.0), rtol=1e-12, atol=1e-9)
    assert np.array_equal(out["Omega_EL"],
                          out["Omega_H2_P"] + out["Omega_H2_H"] + out["Omega_H2_H2"])
    for key in ("Omega_H2_P", "Omega_H2_H", "Omega_H2_H2", "Omega_EL"):
        assert np.all(out[key] >= 0.0)


def test_branch_selectors_are_genuinely_different_between_arms():
    """A zero accumulated moment takes the vr2 branch on the atomic side
    (sum <= 0) and the M-fH2 branch on the molecular side (sum < 0)."""
    fh, a_p, a_h2, sig, _ = _fixture(0.5)
    zero = np.zeros_like(fh)
    atomic = _call_atomic(fh, a_p, a_h2, sig, zero)
    molecular = _call_molecular(fh, a_p, a_h2, sig, zero)
    # atomic zero-sum path: direct vr2 projection with VxH
    expected_atomic = np.zeros(NX)
    vxh = atomic["VxH"]
    for k in range(NX):
        profile = VR[:, None] ** 2 - 2.0 * (VX[None, :] - vxh[k] / VTH) ** 2
        expected_atomic[k] = np.sum(VR2PIDVR * ((profile * fh[:, :, k]) @ DVX)) / NH[k]
    np.testing.assert_allclose(atomic["Wperp_paraH"], expected_atomic, rtol=1e-13, atol=1e-12)
    # molecular zero-sum path: -(kernel*(0-fH2)) reduction
    expected_molecular = np.zeros(NX)
    vxh2 = molecular["VxH2"]
    for k in range(NX):
        expected_molecular[k] = -np.sum(
            VR2PIDVR * ((KERNEL * (zero[:, :, k] - fh[:, :, k])) @ DVX)) / NH2[k]
    assert not np.allclose(atomic["Wperp_paraH"], molecular["Wperp_paraH2"],
                           rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(molecular["Wperp_paraH2"], expected_molecular,
                               rtol=1e-13, atol=1e-12)


def test_sig_matrix_acts_on_the_fortran_order_carrier():
    fh, a_p, a_h2, _, w = _fixture(0.5)
    rng = np.random.default_rng(78)
    sig = -rng.uniform(0.1, 0.9, size=(NVR * NVX, NVR * NVX))
    out = _call_atomic(fh, a_p, a_h2, sig, w)
    expected = np.zeros(NX)
    wrong = np.zeros(NX)
    for k in range(NX):
        wpp = _floored(out["Wperp_paraH"][k], WPP_TOL)
        carrier_f = fh[:, :, k].reshape(NVR * NVX, order="F")
        alpha_f = np.array((sig @ carrier_f).reshape((NVR, NVX), order="F"), order="C", copy=True)
        expected[k] = np.sum(VR2PIDVR * ((alpha_f * carrier_f.reshape((NVR, NVX), order="F")) @ DVX)) / (NH[k] * wpp)
        carrier_c = fh[:, :, k].reshape(NVR * NVX, order="C")
        alpha_c = np.array((sig @ carrier_c).reshape((NVR, NVX), order="C"), order="C", copy=True)
        wrong[k] = np.sum(VR2PIDVR * ((alpha_c * carrier_c.reshape((NVR, NVX), order="C")) @ DVX)) / (NH[k] * wpp)
    assert np.all(expected > 0.0) and np.all(wrong > 0.0)
    np.testing.assert_allclose(out["Omega_H_H"], expected, rtol=1e-12, atol=1e-9)
    assert not np.allclose(out["Omega_H_H"], wrong, rtol=1e-9, atol=1e-12)


def test_disabled_channels_contribute_nothing():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    off = _call_atomic(fh, a_p, a_h2, sig, w, H_P_EL=False, H_H2_EL=False, H_H_EL=False)
    for key in ("VxH", "Omega_H_P", "Omega_H_H2", "Omega_H_H", "Omega_EL"):
        assert np.array_equal(off[key], np.zeros(NX))
    zero_density = assemble_atomic_hydrogen_omega_frequencies(
        fh, np.zeros(NX), a_p, a_h2, sig, VR2PIDVR, DVX, VR, VX, VTH, VXI, VXH2,
        w, KERNEL, H_P_EL=False, H_H2_EL=False, H_H_EL=False)
    assert np.array_equal(zero_density["Omega_EL"], np.zeros(NX))
    off_m = _call_molecular(fh, a_p, a_h2, sig, w, H2_P_EL=False, H2_H_EL=False, H2_H2_EL=False)
    for key in ("VxH2", "Omega_H2_P", "Omega_H2_H", "Omega_H2_H2", "Omega_EL"):
        assert np.array_equal(off_m[key], np.zeros(NX))


def test_inputs_are_not_mutated():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    snapshot = (fh.copy(), a_p.copy(), a_h2.copy(), sig.copy(), w.copy(),
                VXI.copy(), VXH2.copy(), NH.copy())
    _call_atomic(fh, a_p, a_h2, sig, w)
    _call_molecular(fh, a_p, a_h2, sig, w)
    assert all(np.array_equal(a, b) for a, b in zip(
        snapshot, (fh, a_p, a_h2, sig, w, VXI, VXH2, NH)))


@pytest.mark.parametrize("bad_vth", [0.0, -1.0, np.nan, np.inf, np.array([1000.0])])
def test_non_positive_or_non_scalar_vth_fails_closed(bad_vth):
    """Registered hardening: the saved arm accepts a zero/NaN Vth silently."""
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    with pytest.raises(ValueError):
        _call_atomic(fh, a_p, a_h2, sig, w, vth=bad_vth)
    with pytest.raises(ValueError):
        _call_molecular(fh, a_p, a_h2, sig, w, vth=bad_vth)


@pytest.mark.parametrize("bad_tol", [np.nan, np.array([0.01])])
@pytest.mark.parametrize("which", ["DeltaVx_tol", "Wpp_tol"])
def test_nan_or_non_scalar_tolerances_fail_closed(bad_tol, which):
    """Registered hardening: NaN bypasses the saved arm's `tol <= 0` check."""
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    with pytest.raises(ValueError):
        _call_atomic(fh, a_p, a_h2, sig, w, **{which: bad_tol})
    with pytest.raises(ValueError):
        _call_molecular(fh, a_p, a_h2, sig, w, **{which: bad_tol})
    for value in (0.0, -1.0):
        with pytest.raises(ValueError):
            _call_atomic(fh, a_p, a_h2, sig, w, **{which: value})


def test_non_finite_aggregation_output_fails_closed():
    """A finite but extreme Vth overflows the bulk-velocity product; the port
    raises instead of returning Inf (the saved arm returns it silently)."""
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    with pytest.raises(ValueError, match="non-finite"):
        _call_atomic(fh, a_p, a_h2, sig, w, vth=1e308)
    with pytest.raises(ValueError, match="non-finite"):
        _call_molecular(fh, a_p, a_h2, sig, w, vth=1e308)


def test_fail_closed_shape_boundaries():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    bad_calls = [
        lambda: _call_atomic(fh, a_p, a_h2, np.zeros((NVR * NVX, NVX)), w),
        lambda: _call_atomic(fh, a_p, a_h2, np.zeros((NVR, NVR)), w),
        lambda: _call_atomic(fh, np.ones(NX + 1), a_h2, sig, w),
        lambda: _call_atomic(fh, a_p, a_h2, sig, w, H_P_EL=True).__class__ and
                assemble_atomic_hydrogen_omega_frequencies(
                    fh, np.zeros(NX), a_p, a_h2, sig, VR2PIDVR, DVX, VR, VX,
                    VTH, VXI, VXH2, w, KERNEL),
        lambda: _call_atomic(np.full_like(fh, np.nan), a_p, a_h2, sig, w),
        lambda: _call_atomic(fh, a_p, a_h2, sig, w[:-1]),
        lambda: _call_atomic(fh, a_p, a_h2, sig, np.zeros((NVR, NX))),
        lambda: _call_atomic(fh, a_p, a_h2, sig, w, DeltaVx_tol=0.0),
        lambda: _call_atomic(fh, a_p, a_h2, sig, w, Wpp_tol=-1.0),
    ]
    for call in bad_calls:
        with pytest.raises(ValueError):
            call()
    molecular_bad = [
        lambda: _call_molecular(fh, a_p, a_h2, np.zeros((NVR * NVX, NVX)), w),
        lambda: _call_molecular(fh, np.ones(NX + 1), a_h2, sig, w),
        lambda: _call_molecular(np.full_like(fh, np.nan), a_p, a_h2, sig, w),
        lambda: _call_molecular(fh, a_p, a_h2, sig, w[:-1]),
    ]
    for call in molecular_bad:
        with pytest.raises(ValueError):
            call()

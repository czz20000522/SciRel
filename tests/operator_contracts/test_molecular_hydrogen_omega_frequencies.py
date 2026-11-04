# 测试结果：formal package bounded contract checks
# 工作目录：当前 operator/task_graph package
# 命令：pytest -q
# 环境变量：PYTHONDONTWRITEBYTECODE=1
# 结果：由验证命令在当前环境重新确认
# 对照依据：operator.md 的显式端口、适用域与边界
# 源码对照状态：source_free: formal contract replay; source runtime unavailable
# 证据来源：当前 package 内的独立闭式归约 oracle 与不变量，不读取包外证据目录
# 数值差异：闭式归约 oracle 逐位或 1e-15 相对相等；分支/开关选择精确
# 运行环境：asset runtime NumPy
"""Tests for the molecular H2 elastic-frequency Omega aggregation operator.

Package-local oracle.  Every declared output is a closed-form quadrature
reduction over the manufactured inputs, so the whole relation is re-derived
independently here (the oracle builds its own quadrature and does not import the
operator's helpers):

- ``VxH2`` = ``Vth * sum(Vr2pidVr * (fH2 @ (vx*dVx))) / nH2``;
- ``Omega_H2_P`` / ``Omega_H2_H`` divide the ``Alpha*fH2`` reduction by
  ``nH2*DeltaVx`` with the source's ``sign*max(|DeltaVx|, DeltaVx_tol)`` floor;
  the H channel places the denominator **inside** the sum, the P channel
  outside (an ordering difference that is asserted explicitly);
- ``Wperp_paraH2`` is selected by the sign of ``sum(MH2_H2_sum)``: the
  ``vr^2-2*vx^2`` projection branch when negative, and the
  ``-(vr^2-2*vx^2)*(MH2_H2_sum-fH2)`` branch otherwise;
- ``Omega_H2_H2`` is the ``SIG_H2_H2`` matrix reduction divided by
  ``nH2*Wpp`` with the ``sign*max(|Wpp|,Wpp_tol)`` floor;
- every ``Omega_*`` is clamped at zero, and ``Omega_EL`` is their exact sum.

Invariants checked: closed-form reduction equality, branch selector on the sign
of the ``MH2_H2_sum`` total, tensor-order (Fortran) semantics through the
explicit ``reshape(..., order='F')``, the zero-floor clamps, channel-switch
gating, input immutability and fail-closed boundaries.

Claim ceiling: bounded molecular H2 elastic-frequency aggregation on the
declared port.  ``KH2.Internal`` cache lifecycle, cross-PFM composition and
external physical correctness are outside this package and are not claimed.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions.molecular_hydrogen_omega_frequencies import assemble_molecular_hydrogen_omega_frequencies as OP

VR = np.linspace(0.5, 4.5, 9)
VX = np.linspace(-6.0, 6.0, 13)
NX = 3
NVR, NVX = VR.size, VX.size

# independent quadrature: radial shell weights and axial cell widths
_R = np.linspace(0.0, 1.0, NVR + 1)
VR2PIDVR = np.pi * (_R[1:] ** 2 - _R[:-1] ** 2)
_X = np.linspace(-6.5, 6.5, NVX + 1)
DVX = np.diff(_X)
KERNEL = VR[:, None] ** 2 - 2.0 * VX[None, :] ** 2

VTH = 1000.0
VXI = np.array([900.0, 800.0, 1200.0])
VXH = np.array([700.0, 750.0, 1100.0])
NH2 = np.array([1.4, 0.9, 2.1])
DELTA_TOL = 0.01
WPP_TOL = 0.001

_RNG = np.random.default_rng(31)
_SHIFT = 1.5
_SHAPE = np.exp(-(VR[:, None] ** 2 + (VX[None, :] - _SHIFT) ** 2) / 9.0)


def _fixture(weight_sum, amplitudes=None):
    amps = np.array([1.0, 1.0, 1.0]) if amplitudes is None else amplitudes
    fh2 = np.repeat(_SHAPE[:, :, None], NX, axis=2) * amps[None, None, :]
    ap = _RNG.uniform(0.1, 0.9, size=(NVR, NVX, NX))
    ah = _RNG.uniform(0.1, 0.9, size=(NVR, NVX, NX))
    # negative-dominant SIG keeps the h2-h2 channel strictly positive, so the
    # documented zero clamp stays inactive and the reduction is observable
    sig = -_RNG.uniform(0.1, 0.9, size=(NVR * NVX, NVR * NVX))
    return fh2, ap, ah, sig, fh2 * weight_sum


def _call(fh2, ap, ah, sig, weight, **overrides):
    kwargs = dict(
        H2_P_EL=True, H2_H_EL=True, H2_H2_EL=True,
        DeltaVx_tol=DELTA_TOL, Wpp_tol=WPP_TOL,
    )
    kwargs.update(overrides)
    return OP(fh2, NH2, ap, ah, sig, VR2PIDVR, DVX, VR, VX, VTH, VXI, VXH,
              weight, KERNEL, **kwargs)


def _independent_vxh2(fh2):
    return np.array([
        VTH * np.sum(VR2PIDVR * (fh2[:, :, k] @ (VX * DVX))) / NH2[k]
        for k in range(NX)
    ])


def _floored(value, tol):
    return np.sign(value) * max(abs(value), tol)


def test_bulk_velocity_matches_its_quadrature_definition():
    fh2, ap, ah, sig, w = _fixture(0.5)
    out = _call(fh2, ap, ah, sig, w)
    np.testing.assert_allclose(out["VxH2"], _independent_vxh2(fh2), rtol=0.0, atol=0.0)


@pytest.mark.parametrize("channel", ["Omega_H2_P", "Omega_H2_H"])
def test_alpha_channels_reproduce_the_declared_reduction(channel):
    """P places the ``nH2*DeltaVx`` denominator outside the sum, H inside it."""
    fh2, ap, ah, sig, w = _fixture(0.5)
    out = _call(fh2, ap, ah, sig, w)
    vxh2 = _independent_vxh2(fh2)
    expected = np.zeros(NX)
    for k in range(NX):
        if channel == "Omega_H2_P":
            delta = _floored((vxh2[k] - VXI[k]) / VTH, DELTA_TOL)
            value = np.sum(VR2PIDVR * ((ap[:, :, k] * fh2[:, :, k]) @ DVX))
            expected[k] = value / (NH2[k] * delta)
        else:
            delta = _floored((vxh2[k] - VXH[k]) / VTH, DELTA_TOL)
            expected[k] = np.sum(
                VR2PIDVR * ((ah[:, :, k] * fh2[:, :, k]) @ DVX) / (NH2[k] * delta)
            )
    np.testing.assert_allclose(out[channel], np.maximum(expected, 0.0),
                               rtol=0.0, atol=1e-9)


def test_alpha_channels_collapse_when_their_inputs_coincide():
    """With the same alpha field and the same velocity target the P and H
    reductions must agree to round-off; the H channel differs only by placing
    the ``nH2*DeltaVx`` denominator inside the sum."""
    fh2, _, ah, sig, w = _fixture(0.5)
    same = OP(fh2, NH2, ah, ah, sig, VR2PIDVR, DVX, VR, VX, VTH, VXI, VXI,
              w, KERNEL, DeltaVx_tol=DELTA_TOL, Wpp_tol=WPP_TOL)
    np.testing.assert_allclose(same["Omega_H2_P"], same["Omega_H2_H"],
                               rtol=1e-13, atol=1e-15)
    # distinct alpha fields / distinct targets yield distinct channels
    distinct = _call(fh2, ah, ah * 1.7 + 0.05, sig, w)
    assert not np.allclose(distinct["Omega_H2_P"], distinct["Omega_H2_H"],
                           rtol=1e-9, atol=1e-12)


@pytest.mark.parametrize("weight_sum", [0.5, -0.5])
def test_wperp_branch_is_selected_by_the_weight_total(weight_sum):
    fh2, ap, ah, sig, w = _fixture(weight_sum)
    out = _call(fh2, ap, ah, sig, w)
    expected = np.zeros(NX)
    for k in range(NX):
        if float(np.sum(w)) < 0.0:
            profile = VR[:, None] ** 2 - 2.0 * (VX[None, :] - out["VxH2"][k] / VTH) ** 2
            expected[k] = np.sum(
                VR2PIDVR * ((profile * fh2[:, :, k]) @ DVX)
            ) / NH2[k]
        else:
            momentum = w[:, :, k] - fh2[:, :, k]
            expected[k] = -np.sum(
                VR2PIDVR * ((KERNEL * momentum) @ DVX)
            ) / NH2[k]
    np.testing.assert_allclose(out["Wperp_paraH2"], expected, rtol=1e-13, atol=1e-12)
    # the two branches must genuinely differ, so the selector is observable
    other = _call(fh2, ap, ah, sig, -w)
    assert not np.allclose(out["Wperp_paraH2"], other["Wperp_paraH2"])


def test_h2_h2_channel_reproduces_the_matrix_reduction():
    fh2, ap, ah, sig, w = _fixture(0.5)
    out = _call(fh2, ap, ah, sig, w)
    expected = np.zeros(NX)
    for k in range(NX):
        carrier = fh2[:, :, k].reshape(NVR * NVX, order="F")
        alpha = (sig @ carrier).reshape((NVR, NVX), order="F")
        wpp = _floored(out["Wperp_paraH2"][k], WPP_TOL)
        value = np.sum(
            VR2PIDVR * ((alpha * carrier.reshape((NVR, NVX), order="F")) @ DVX)
        )
        expected[k] = max(value / (NH2[k] * wpp), 0.0)
    np.testing.assert_allclose(out["Omega_H2_H2"], expected, rtol=1e-12, atol=1e-9)
    assert np.all(expected > 0.0), "fixture must keep the zero clamp inactive"


def test_sig_matrix_acts_on_the_forth_order_carrier():
    """Asymmetric SIG matrices distinguish the Fortran-order carrier from a
    C-order one; the reduction must track the declared (column-major) layout."""
    fh2, ap, ah, _, w = _fixture(0.5)
    rng = np.random.default_rng(77)
    # negative-dominant SIG keeps the h2-h2 channel positive so the zero clamp
    # does not mask the layout difference
    sig = -rng.uniform(0.1, 0.9, size=(NVR * NVX, NVR * NVX))
    out = _call(fh2, ap, ah, sig, w)

    expected = np.zeros(NX)
    wrong = np.zeros(NX)
    for k in range(NX):
        wpp = _floored(out["Wperp_paraH2"][k], WPP_TOL)
        carrier_f = fh2[:, :, k].reshape(NVR * NVX, order="F")
        alpha_f = (sig @ carrier_f).reshape((NVR, NVX), order="F")
        expected[k] = np.sum(VR2PIDVR * ((alpha_f * carrier_f.reshape((NVR, NVX), order="F")) @ DVX)) / (NH2[k] * wpp)

        carrier_c = fh2[:, :, k].reshape(NVR * NVX, order="C")
        alpha_c = (sig @ carrier_c).reshape((NVR, NVX), order="C")
        wrong[k] = np.sum(VR2PIDVR * ((alpha_c * carrier_c.reshape((NVR, NVX), order="C")) @ DVX)) / (NH2[k] * wpp)

    assert np.all(expected > 0.0) and np.all(wrong > 0.0)
    np.testing.assert_allclose(out["Omega_H2_H2"], expected, rtol=1e-12, atol=1e-9)
    assert not np.allclose(out["Omega_H2_H2"], wrong, rtol=1e-9, atol=1e-12)


def test_omegas_are_clamped_at_zero():
    fh2, ap, ah, _, w = _fixture(0.5)
    negative_sig = -np.abs(_RNG.uniform(0.1, 0.9, size=(NVR * NVX, NVR * NVX)))
    out = _call(fh2, ap, ah, negative_sig, w)
    for key in ("Omega_H2_P", "Omega_H2_H", "Omega_H2_H2", "Omega_EL"):
        assert np.all(out[key] >= 0.0)


def test_omega_el_is_the_exact_channel_sum():
    fh2, ap, ah, sig, w = _fixture(0.5)
    out = _call(fh2, ap, ah, sig, w)
    assert np.array_equal(
        out["Omega_EL"],
        out["Omega_H2_P"] + out["Omega_H2_H"] + out["Omega_H2_H2"],
    )


def test_disabled_channels_contribute_nothing():
    fh2, ap, ah, sig, w = _fixture(0.5)
    off = _call(fh2, ap, ah, sig, w, H2_P_EL=False, H2_H_EL=False, H2_H2_EL=False)
    for key in ("VxH2", "Omega_H2_P", "Omega_H2_H", "Omega_H2_H2", "Omega_EL"):
        assert np.array_equal(off[key], np.zeros(NX))
    # with everything disabled a non-positive density is admissible
    zero_density = OP(fh2, np.zeros(NX), ap, ah, sig, VR2PIDVR, DVX, VR, VX, VTH,
                      VXI, VXH, w, KERNEL,
                      H2_P_EL=False, H2_H_EL=False, H2_H2_EL=False)
    assert np.array_equal(zero_density["Omega_EL"], np.zeros(NX))


def test_inputs_are_not_mutated():
    fh2, ap, ah, sig, w = _fixture(0.5)
    snapshot = (fh2.copy(), ap.copy(), ah.copy(), sig.copy(), w.copy(),
                VXI.copy(), VXH.copy())
    _call(fh2, ap, ah, sig, w)
    assert all(np.array_equal(a, b) for a, b in zip(
        snapshot, (fh2, ap, ah, sig, w, VXI, VXH)))


def test_fail_closed_boundaries():
    fh2, ap, ah, sig, w = _fixture(0.5)
    base = dict(fh2=fh2, ap=ap, ah=ah, sig=sig, w=w, nh2=NH2,
                vr2pidvr=VR2PIDVR, dvx=DVX, vr=VR, vx=VX, kernel=KERNEL)
    bad = [
        (dict(sig=np.zeros((NVR * NVX, NVX))), "non-square SIG"),
        (dict(sig=np.zeros((NVR, NVR))), "SIG dimension mismatch"),
        (dict(nh2=np.ones(NX + 1)), "nH2 length mismatch"),
        (dict(nh2=np.zeros(NX)), "non-positive density with elastic enabled"),
        (dict(ap=np.zeros((NVR, NVX, NX + 1))), "Alpha_H2_P shape mismatch"),
        (dict(dvx=DVX[:-1]), "dVx length mismatch"),
        (dict(fh2=np.full_like(fh2, np.nan)), "non-finite fH2"),
        (dict(kernel=np.zeros((NVR, NX))), "kernel shape mismatch"),
    ]
    for overrides, _name in bad:
        kwargs = dict(base)
        kwargs.update(overrides)
        with pytest.raises(Exception):
            OP(kwargs["fh2"], kwargs["nh2"], kwargs["ap"], kwargs["ah"],
               kwargs["sig"], kwargs["vr2pidvr"], kwargs["dvx"],
               kwargs["vr"], kwargs["vx"], VTH, VXI, VXH, kwargs["w"],
               kwargs["kernel"], DeltaVx_tol=DELTA_TOL, Wpp_tol=WPP_TOL)

    for tol_kwargs in (dict(DeltaVx_tol=0.0), dict(Wpp_tol=-1.0)):
        with pytest.raises(Exception):
            _call(fh2, ap, ah, sig, w, **tol_kwargs)


def test_carrier_and_mesh_axes_must_match_the_declared_shapes():
    fh2, ap, ah, sig, w = _fixture(0.5)
    with pytest.raises(ValueError, match="fH2.*3-D"):
        _call(fh2[:, :, 0], ap, ah, sig, w)
    with pytest.raises(ValueError, match="Vr2pidVr.*1-D"):
        OP(fh2, NH2, ap, ah, sig, VR2PIDVR[:, None], DVX, VR, VX,
           VTH, VXI, VXH, w, KERNEL)


def test_zero_target_velocity_difference_fails_closed():
    fh2, ap, ah, sig, w = _fixture(0.5)
    flow = _call(fh2, ap, ah, sig, w, H2_H_EL=False, H2_H2_EL=False)["VxH2"]
    with pytest.raises(ValueError, match="zero velocity difference"):
        OP(fh2, NH2, ap, ah, sig, VR2PIDVR, DVX, VR, VX, VTH,
           flow, VXH, w, KERNEL, H2_H_EL=False, H2_H2_EL=False)


def test_zero_perpendicular_moment_fails_closed():
    fh2, ap, ah, sig, w = _fixture(0.5)
    with pytest.raises(ValueError, match="zero perpendicular moment"):
        _call(np.zeros_like(fh2), ap, ah, sig, np.zeros_like(w),
              H2_P_EL=False, H2_H_EL=False)


@pytest.mark.parametrize("control", [
    {"Vth": 0.0},
    {"DeltaVx_tol": float("nan")},
    {"Wpp_tol": float("inf")},
])
def test_thermal_speed_and_floors_must_be_finite_positive_scalars(control):
    fh2, ap, ah, sig, w = _fixture(0.5)
    args = dict(Vth=VTH, DeltaVx_tol=DELTA_TOL, Wpp_tol=WPP_TOL)
    args.update(control)
    with pytest.raises(ValueError, match="finite positive real scalar"):
        OP(fh2, NH2, ap, ah, sig, VR2PIDVR, DVX, VR, VX, args["Vth"],
           VXI, VXH, w, KERNEL, DeltaVx_tol=args["DeltaVx_tol"],
           Wpp_tol=args["Wpp_tol"])

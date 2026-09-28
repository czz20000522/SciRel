# 测试结果：formal package bounded contract checks
# 工作目录：当前 operator/task_graph package
# 命令：pytest -q
# 环境变量：PYTHONDONTWRITEBYTECODE=1
# 结果：由验证命令在当前环境重新确认
# 对照依据：operator.md 的显式端口、适用域与边界
# 源码对照状态：source_free: formal contract replay; source runtime unavailable
# 证据来源：当前 package 内的独立闭式归约 oracle 与不变量，不读取包外证据目录
# 数值差异：闭式归约 oracle 1e-9 绝对/1e-12 相对相等；分支与开关选择精确
# 运行环境：asset runtime NumPy
"""Tests for the atomic H elastic-scattering frequency Omega aggregation.

Package-local oracle.  Every declared output is a closed-form quadrature
reduction over the manufactured inputs, re-derived independently here (the
oracle builds its own quadrature and does not import the operator's helpers):

- ``VxH`` = ``Vth * sum(Vr2pidVr * (fH @ (vx*dVx))) / nH``;
- ``Omega_H_P`` and ``Omega_H_H2`` reduce ``Alpha*fH`` over the mesh divided by
  ``nH*DeltaVx``, where ``DeltaVx`` is the source's
  ``sign*max(|DeltaVx|, DeltaVx_tol)``-floored bulk-velocity difference against
  the proton and H2 targets respectively;
- ``Wperp_paraH`` is selected by the sign of ``sum(MH_H_sum)``: the direct
  ``vr^2-2*(vx-VxH/Vth)^2`` projection when the total is ``<= 0``, and the
  ``-(vr^2-2*vx^2)*(MH_H_sum-fH)`` branch otherwise;
- ``Omega_H_H`` is the ``SIG_H_H`` matrix reduction divided by ``nH*Wpp`` with
  the ``sign*max(|Wpp|,Wpp_tol)`` floor, and the source writes the product into
  a preallocated C-order buffer;
- every ``Omega_*`` is clamped at zero and ``Omega_EL`` is their exact sum.

Invariants checked: closed-form reduction equality for all three channels, the
``MH_H_sum`` sign branch selector, the Fortran-order carrier layout, the
zero-floor clamps, channel-switch gating, input immutability and fail-closed
boundaries.

Claim ceiling: bounded atomic H elastic-scattering frequency aggregation on the
declared port.  ``KH.Internal`` cache lifecycle, cross-PFM composition and
external physical correctness are outside this package and are not claimed.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions.atomic_hydrogen_omega_frequencies import assemble_atomic_hydrogen_omega_frequencies as OP

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
NH = np.array([0.7, 1.9, 1.1])
DELTA_TOL = 0.01
WPP_TOL = 0.001

_RNG = np.random.default_rng(33)
_SHIFT = 1.5
_SHAPE = np.exp(-(VR[:, None] ** 2 + (VX[None, :] - _SHIFT) ** 2) / 9.0)


def _fixture(weight_sum):
    amps = _RNG.uniform(0.7, 1.3, size=NX)
    fh = np.repeat(_SHAPE[:, :, None], NX, axis=2) * amps[None, None, :]
    a_p = _RNG.uniform(0.1, 0.9, size=(NVR, NVX, NX))
    a_h2 = _RNG.uniform(0.1, 0.9, size=(NVR, NVX, NX))
    sig = -_RNG.uniform(0.1, 0.9, size=(NVR * NVX, NVR * NVX))
    return fh, a_p, a_h2, sig, fh * weight_sum


def _call(fh, a_p, a_h2, sig, weight, **overrides):
    kwargs = dict(
        H_P_EL=True, H_H2_EL=True, H_H_EL=True,
        DeltaVx_tol=DELTA_TOL, Wpp_tol=WPP_TOL,
    )
    kwargs.update(overrides)
    return OP(fh, NH, a_p, a_h2, sig, VR2PIDVR, DVX, VR, VX, VTH, VXI, VXH2,
              weight, KERNEL, **kwargs)


def _independent_vxh(fh):
    return np.array([
        VTH * np.sum(VR2PIDVR * (fh[:, :, k] @ (VX * DVX))) / NH[k]
        for k in range(NX)
    ])


def _floored(value, tol):
    return np.sign(value) * max(abs(value), tol)


def test_bulk_velocity_matches_its_quadrature_definition():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    out = _call(fh, a_p, a_h2, sig, w)
    np.testing.assert_allclose(out["VxH"], _independent_vxh(fh), rtol=0.0, atol=0.0)


@pytest.mark.parametrize("channel", ["Omega_H_P", "Omega_H_H2"])
def test_alpha_channels_reproduce_the_declared_reduction(channel):
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    out = _call(fh, a_p, a_h2, sig, w)
    vxh = _independent_vxh(fh)
    expected = np.zeros(NX)
    for k in range(NX):
        if channel == "Omega_H_P":
            delta = _floored((vxh[k] - VXI[k]) / VTH, DELTA_TOL)
            alpha = a_p[:, :, k]
        else:
            delta = _floored((vxh[k] - VXH2[k]) / VTH, DELTA_TOL)
            alpha = a_h2[:, :, k]
        value = np.sum(VR2PIDVR * ((alpha * fh[:, :, k]) @ DVX))
        expected[k] = max(value / (NH[k] * delta), 0.0)
    assert np.all(expected > 0.0), "fixture must keep the zero clamp inactive"
    np.testing.assert_allclose(out[channel], expected, rtol=1e-12, atol=1e-9)


def test_alpha_channels_are_distinct_for_distinct_targets():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    out = _call(fh, a_p, a_h2, sig, w)
    assert not np.allclose(out["Omega_H_P"], out["Omega_H_H2"], rtol=1e-9, atol=1e-12)
    same = OP(fh, NH, a_p, a_p, sig, VR2PIDVR, DVX, VR, VX, VTH, VXI, VXI,
              w, KERNEL, DeltaVx_tol=DELTA_TOL, Wpp_tol=WPP_TOL)
    np.testing.assert_allclose(same["Omega_H_P"], same["Omega_H_H2"],
                               rtol=1e-13, atol=1e-15)


@pytest.mark.parametrize("weight_sum", [0.5, -0.5])
def test_wperp_branch_is_selected_by_the_weight_total(weight_sum):
    fh, a_p, a_h2, sig, w = _fixture(weight_sum)
    out = _call(fh, a_p, a_h2, sig, w)
    expected = np.zeros(NX)
    for k in range(NX):
        if float(np.sum(w)) <= 0.0:
            profile = VR[:, None] ** 2 - 2.0 * (VX[None, :] - out["VxH"][k] / VTH) ** 2
            expected[k] = np.sum(VR2PIDVR * ((profile * fh[:, :, k]) @ DVX)) / NH[k]
        else:
            momentum = w[:, :, k] - fh[:, :, k]
            expected[k] = -np.sum(VR2PIDVR * ((KERNEL * momentum) @ DVX)) / NH[k]
    np.testing.assert_allclose(out["Wperp_paraH"], expected, rtol=1e-13, atol=1e-12)
    other = _call(fh, a_p, a_h2, sig, -w)
    assert not np.allclose(out["Wperp_paraH"], other["Wperp_paraH"])


def test_h_h_channel_reproduces_the_matrix_reduction():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    out = _call(fh, a_p, a_h2, sig, w)
    expected = np.zeros(NX)
    for k in range(NX):
        carrier = fh[:, :, k].reshape(NVR * NVX, order="F")
        alpha = np.array(
            (sig @ carrier).reshape((NVR, NVX), order="F"), order="C", copy=True
        )
        wpp = _floored(out["Wperp_paraH"][k], WPP_TOL)
        value = np.sum(
            VR2PIDVR * ((alpha * carrier.reshape((NVR, NVX), order="F")) @ DVX)
        )
        expected[k] = max(value / (NH[k] * wpp), 0.0)
    assert np.all(expected > 0.0)
    np.testing.assert_allclose(out["Omega_H_H"], expected, rtol=1e-12, atol=1e-9)


def test_sig_matrix_acts_on_the_fortran_order_carrier():
    fh, a_p, a_h2, _, w = _fixture(0.5)
    rng = np.random.default_rng(78)
    sig = -rng.uniform(0.1, 0.9, size=(NVR * NVX, NVR * NVX))
    out = _call(fh, a_p, a_h2, sig, w)

    expected = np.zeros(NX)
    wrong = np.zeros(NX)
    for k in range(NX):
        wpp = _floored(out["Wperp_paraH"][k], WPP_TOL)
        carrier_f = fh[:, :, k].reshape(NVR * NVX, order="F")
        alpha_f = np.array((sig @ carrier_f).reshape((NVR, NVX), order="F"),
                           order="C", copy=True)
        expected[k] = np.sum(
            VR2PIDVR * ((alpha_f * carrier_f.reshape((NVR, NVX), order="F")) @ DVX)
        ) / (NH[k] * wpp)

        carrier_c = fh[:, :, k].reshape(NVR * NVX, order="C")
        alpha_c = np.array((sig @ carrier_c).reshape((NVR, NVX), order="C"),
                           order="C", copy=True)
        wrong[k] = np.sum(
            VR2PIDVR * ((alpha_c * carrier_c.reshape((NVR, NVX), order="C")) @ DVX)
        ) / (NH[k] * wpp)

    assert np.all(expected > 0.0) and np.all(wrong > 0.0)
    np.testing.assert_allclose(out["Omega_H_H"], expected, rtol=1e-12, atol=1e-9)
    assert not np.allclose(out["Omega_H_H"], wrong, rtol=1e-9, atol=1e-12)


def test_omegas_are_clamped_at_zero():
    fh, a_p, a_h2, _, w = _fixture(0.5)
    positive_sig = _RNG.uniform(0.1, 0.9, size=(NVR * NVX, NVR * NVX))
    out = _call(fh, a_p, a_h2, positive_sig, w)
    for key in ("Omega_H_P", "Omega_H_H2", "Omega_H_H", "Omega_EL"):
        assert np.all(out[key] >= 0.0)


def test_omega_el_is_the_exact_channel_sum():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    out = _call(fh, a_p, a_h2, sig, w)
    assert np.array_equal(
        out["Omega_EL"],
        out["Omega_H_P"] + out["Omega_H_H2"] + out["Omega_H_H"],
    )


def test_disabled_channels_contribute_nothing():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    off = _call(fh, a_p, a_h2, sig, w, H_P_EL=False, H_H2_EL=False, H_H_EL=False)
    for key in ("VxH", "Omega_H_P", "Omega_H_H2", "Omega_H_H", "Omega_EL"):
        assert np.array_equal(off[key], np.zeros(NX))
    zero_density = OP(fh, np.zeros(NX), a_p, a_h2, sig, VR2PIDVR, DVX, VR, VX,
                      VTH, VXI, VXH2, w, KERNEL,
                      H_P_EL=False, H_H2_EL=False, H_H_EL=False)
    assert np.array_equal(zero_density["Omega_EL"], np.zeros(NX))


def test_inputs_are_not_mutated():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    snapshot = (fh.copy(), a_p.copy(), a_h2.copy(), sig.copy(), w.copy(),
                VXI.copy(), VXH2.copy())
    _call(fh, a_p, a_h2, sig, w)
    assert all(np.array_equal(a, b) for a, b in zip(
        snapshot, (fh, a_p, a_h2, sig, w, VXI, VXH2)))


def test_fail_closed_boundaries():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    bad = [
        (dict(sig=np.zeros((NVR * NVX, NVX))), "non-square SIG"),
        (dict(sig=np.zeros((NVR, NVR))), "SIG dimension mismatch"),
        (dict(nh=np.ones(NX + 1)), "nH length mismatch"),
        (dict(nh=np.zeros(NX)), "non-positive density with elastic enabled"),
        (dict(a_p=np.zeros((NVR, NVX, NX + 1))), "Alpha_H_P shape mismatch"),
        (dict(dvx=DVX[:-1]), "dVx length mismatch"),
        (dict(fh=np.full_like(fh, np.nan)), "non-finite fH"),
        (dict(kernel=np.zeros((NVR, NX))), "kernel shape mismatch"),
    ]
    for overrides, _name in bad:
        kwargs = dict(fh=fh, nh=NH, a_p=a_p, a_h2=a_h2, sig=sig,
                      vr2pidvr=VR2PIDVR, dvx=DVX, vr=VR, vx=VX, kernel=KERNEL)
        kwargs.update(overrides)
        with pytest.raises(Exception):
            OP(kwargs["fh"], kwargs["nh"], kwargs["a_p"], kwargs["a_h2"],
               kwargs["sig"], kwargs["vr2pidvr"], kwargs["dvx"],
               kwargs["vr"], kwargs["vx"], VTH, VXI, VXH2, w,
               kwargs["kernel"], DeltaVx_tol=DELTA_TOL, Wpp_tol=WPP_TOL)

    for tol_kwargs in (dict(DeltaVx_tol=0.0), dict(Wpp_tol=-1.0)):
        with pytest.raises(Exception):
            _call(fh, a_p, a_h2, sig, w, **tol_kwargs)


def test_carrier_and_mesh_axes_must_match_the_declared_shapes():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    with pytest.raises(ValueError, match="fH.*3-D"):
        _call(fh[:, :, 0], a_p, a_h2, sig, w)
    with pytest.raises(ValueError, match="Vr2pidVr.*1-D"):
        OP(fh, NH, a_p, a_h2, sig, VR2PIDVR[:, None], DVX, VR, VX,
           VTH, VXI, VXH2, w, KERNEL)


def test_zero_target_velocity_difference_fails_closed():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    flow = _call(fh, a_p, a_h2, sig, w, H_H2_EL=False, H_H_EL=False)["VxH"]
    with pytest.raises(ValueError, match="zero velocity difference"):
        OP(fh, NH, a_p, a_h2, sig, VR2PIDVR, DVX, VR, VX, VTH,
           flow, VXH2, w, KERNEL, H_H2_EL=False, H_H_EL=False)


def test_zero_perpendicular_moment_fails_closed():
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    with pytest.raises(ValueError, match="zero perpendicular moment"):
        _call(np.zeros_like(fh), a_p, a_h2, sig, np.zeros_like(w),
              H_P_EL=False, H_H2_EL=False)


@pytest.mark.parametrize("control", [
    {"Vth": 0.0},
    {"DeltaVx_tol": float("nan")},
    {"Wpp_tol": float("inf")},
])
def test_thermal_speed_and_floors_must_be_finite_positive_scalars(control):
    fh, a_p, a_h2, sig, w = _fixture(0.5)
    args = dict(Vth=VTH, DeltaVx_tol=DELTA_TOL, Wpp_tol=WPP_TOL)
    args.update(control)
    with pytest.raises(ValueError, match="finite positive real scalar"):
        OP(fh, NH, a_p, a_h2, sig, VR2PIDVR, DVX, VR, VX, args["Vth"],
           VXI, VXH2, w, KERNEL, DeltaVx_tol=args["DeltaVx_tol"],
           Wpp_tol=args["Wpp_tol"])

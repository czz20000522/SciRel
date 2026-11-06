# 测试结果：本文件由包级定向测试执行确认。
# 工作目录：当前算子或任务图包目录。
# 命令：python -m pytest -q -p no:cacheprovider test_scientific_function.py。
# 环境变量：PYTHONDONTWRITEBYTECODE=1。
# 结果：以本次固定 asset_runtime pytest 输出为准。
# 对照依据：独立公式、不变量、边界行为或源码派生 fixture。
# 源码对照状态：source_unavailable: source runtime is isolated。
# 证据来源：test_scientific_function.py 的断言与同包 scientific_function.py。
# 数值差异：以测试断言中的指标和容差为准。
# 运行环境：固定 asset_runtime（Python、NumPy/SciPy；无源码挂载）。

"""Validation: source-free atomic four-family SIG collision-matrix assembly.

The operator assembles ``SIG_CX / SIG_H_H / SIG_H_H2 / SIG_H_P`` from an
explicit velocity-space carrier (``vr, vx, Vr2pidVr, dVx, Tnorm, mu``) with
Fortran-order reshapes and an embedded theta quadrature.  The tests below use
an independent (broadcasting-geometry) oracle for the double-velocity-space
geometry and check shape, nonnegativity of ``SIG_CX``, the intrinsic bounded
negative cells of the elastic families, and fail-closed boundaries.
"""

from __future__ import annotations

import numpy as np
import pytest

from scirel._result import Result
from scirel.collisions.atomic_hydrogen_collision_matrices import (
    assemble_atomic_hydrogen_collision_matrices,
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


_JANEV_CX_COEFFICIENTS = np.array(
    [
        -3.274123792568e1,
        -8.916456579806e-2,
        -3.016990732025e-2,
        9.205482406462e-3,
        2.400266568315e-3,
        -1.927122311323e-3,
        3.654750340106e-4,
        -2.788866460622e-5,
        7.422296363524e-7,
    ]
)
_H_H_VISCOSITY_COEFFICIENTS = np.array(
    [
        -3.344860e1,
        -4.238982e-1,
        -7.477873e-2,
        -7.915053e-3,
        -2.686129e-4,
    ]
)
_H_H2_COEFFICIENTS = np.array(
    [
        -3.495671e1,
        -4.062257e-1,
        -3.820531e-2,
        -9.404486e-3,
        3.963723e-4,
    ]
)
_H_P_LOW_COEFFICIENTS = np.array(
    [
        -3.233966e1,
        -1.126918e-1,
        5.287706e-3,
        -2.445017e-3,
        -1.044156e-3,
        8.419691e-5,
        3.824773e-5,
    ]
)
_H_P_HIGH_COEFFICIENTS = np.array([-3.231141e1, -1.386002e-1])


def _sigma_cx(e):
    return (
        np.e ** (_poly(np.log(np.minimum(np.maximum(e, 0.1), 2.01e4)), _JANEV_CX_COEFFICIENTS))
        * 1.0e-4
    )


def _sigma_h_h(e):
    return (
        np.exp(_poly(np.log(np.minimum(np.maximum(e, 0.03), 1.01e4)), _H_H_VISCOSITY_COEFFICIENTS))
        * 1.0e-4
    )


def _sigma_h_hh(e):
    return (
        np.exp(_poly(np.log(np.minimum(np.maximum(e, 0.03), 1.01e4)), _H_H2_COEFFICIENTS)) * 1.0e-4
    )


def _sigma_p_h(e):
    e = np.minimum(np.maximum(e, 0.001), 1.01e5)
    result = np.zeros(np.shape(e), dtype=float)
    result = np.where(e <= 10.0, np.exp(_poly(np.log(e), _H_P_LOW_COEFFICIENTS)) * 1.0e-4, result)
    result = np.where(e > 10.0, np.exp(_poly(np.log(e), _H_P_HIGH_COEFFICIENTS)) * 1.0e-4, result)
    return result


def _independent_oracle(vr, vx, Vr2pidVr, dVx, Tnorm, mu=1.0):
    """Independent replay: broadcasting geometry + einsum theta quadrature."""
    vr = np.asarray(vr, float)
    vx = np.asarray(vx, float)
    nvr, nvx = vr.size, vx.size
    Vth = np.sqrt((2 * Q * Tnorm) / (mu * H_MASS))
    Vth2 = Vth * Vth
    ecx = 0.5 * H_MASS * Vth2 / Q
    ehh = 0.5 * H_MASS * mu * Vth2 / Q

    # Broadcasting over the (nvr, nvx, nvr, nvx, ntheta) layout.
    i = np.arange(nvr)[:, None, None, None, None]
    k = np.arange(nvr)[None, None, :, None, None]
    l = np.arange(nvx)[None, None, None, :, None]
    m = np.arange(NTHETA)[None, None, None, None, :]
    v_starter = vr[i] ** 2 + vr[k] ** 2 - 2 * vr[i] * vr[k] * COS_THETA[m]
    v_v2 = v_starter + (vx[None, :, None, None, None] - vx[l]) ** 2
    vr2_vx2 = v_starter - 2 * (vx[None, :, None, None, None] - vx[l]) ** 2
    v_v = np.sqrt(v_v2)
    # vx_vx[j-axis, l-axis] = vx[j] - vx[l]; broadcast to (nvr, nvx, nvr, nvx).
    j_axis = np.arange(nvx)[None, :, None, None]
    l_axis = np.arange(nvx)[None, None, None, :]
    vx_vx = np.broadcast_to(vx[j_axis] - vx[l_axis], (nvr, nvx, nvr, nvx)).copy()

    Vr2pidVrdVx = Vr2pidVr[None, None, :, None] * dVx[None, None, None, :]
    Vr2pidVrdVx = np.broadcast_to(Vr2pidVrdVx, (nvr, nvx, nvr, nvx)).copy()

    # Fortran-order flatten of the (nvr,nvx,nvr,nvx) -> (N,N) index map.
    # Element (ii, jj) = (i,j,k,l) with ii = i + nvr*j, jj = k + nvr*l.
    f_v = Vr2pidVrdVx.reshape((nvr * nvx * nvr * nvx,), order="F")
    f_vxvx = vx_vx.reshape((nvr * nvx * nvr * nvx,), order="F")

    def contract(integrand_5d, weight_vector, with_vx_vx=False):
        flat = integrand_5d.reshape((nvr * nvx * nvr * nvx, NTHETA), order="F")
        theta_int = flat @ D_THETA
        base = f_v * theta_int
        if with_vx_vx:
            base = base * f_vxvx
        return base.reshape((nvr * nvx, nvr * nvx), order="F")

    return {
        "SIG_CX": contract(v_v * _sigma_cx(v_v2 * ecx), None),
        "SIG_H_H": contract(vr2_vx2 * v_v * _sigma_h_h(v_v2 * ehh) * 3.0 / 8.0, None),
        "SIG_H_H2": contract(v_v * _sigma_h_hh(v_v2 * ecx), None, with_vx_vx=True),
        "SIG_H_P": contract(v_v * _sigma_p_h(v_v2 * ecx), None, with_vx_vx=True),
        "v_v2": v_v2,
        "v_v": v_v,
        "vr2_vx2": vr2_vx2,
        "vx_vx": vx_vx,
        "Vr2pidVrdVx": Vr2pidVrdVx,
    }


CANONICAL = dict(
    vr=np.array([0.5, 1.0]),
    vx=np.array([-1.0, 1.0]),
    Vr2pidVr=np.array([1.7671458676442586, 3.141592653589793]),
    dVx=np.array([2.0, 2.0]),
    Tnorm=1.0,
    mu=1.0,
)

HOLDOUT = dict(
    vr=np.array([0.4, 0.8, 1.5]),
    vx=np.array([-2.0, -1.0, 1.0, 2.0]),
    Vr2pidVr=np.array([1.1309733552923258, 3.0237829290801748, 6.597344572538567]),
    dVx=np.array([1.0, 1.5, 1.5, 1.0]),
    Tnorm=5.0,
    mu=1.0,
)


@pytest.mark.parametrize("case", [CANONICAL, HOLDOUT])
def test_matches_independent_oracle_for_all_four_families(case):
    result = assemble_atomic_hydrogen_collision_matrices(**case)
    expected = _independent_oracle(**case)
    assert isinstance(result, Result)
    assert list(result) == [
        "SIG_CX",
        "SIG_H_H",
        "SIG_H_H2",
        "SIG_H_P",
        "v_v2",
        "v_v",
        "vr2_vx2",
        "vx_vx",
        "Vr2pidVrdVx",
        "Vth2",
    ]
    assert result.SIG_CX is result["SIG_CX"]
    assert result.Vth2 is result["Vth2"]
    assert all(isinstance(value, np.ndarray) for value in result.values())
    for name in ("SIG_CX", "SIG_H_H", "SIG_H_H2", "SIG_H_P"):
        # Structurally-independent oracle: tolerance covers last-ULP round-off.
        np.testing.assert_allclose(result[name], expected[name], rtol=1e-12, atol=0.0)
        assert result[name].shape == (case["vr"].size * case["vx"].size,) * 2


@pytest.mark.parametrize("case", [CANONICAL, HOLDOUT])
def test_predecessor_state_and_thermal_normalization(case):
    result = assemble_atomic_hydrogen_collision_matrices(**case)
    expected = _independent_oracle(**case)
    for name in ("v_v2", "v_v", "vr2_vx2", "vx_vx", "Vr2pidVrdVx"):
        np.testing.assert_allclose(result[name], expected[name], rtol=1e-12, atol=0.0)
    assert result["Vth2"][0] > 0.0


@pytest.mark.parametrize("case", [CANONICAL, HOLDOUT])
def test_sig_cx_is_nonnegative_and_elastic_families_have_bounded_negative_cells(case):
    result = assemble_atomic_hydrogen_collision_matrices(**case)
    assert np.all(result["SIG_CX"] >= 0.0)
    for name in ("SIG_H_H", "SIG_H_H2", "SIG_H_P"):
        matrix = result[name]
        negatives = matrix[matrix < 0.0]
        # Negative cells are intrinsic (signed vr2_vx2 / vx_vx); reproduce as-is, never clamp.
        assert negatives.size > 0
        assert np.all(np.isfinite(matrix))
        assert np.max(np.abs(negatives)) <= np.max(np.abs(matrix))


def test_invalid_carrier_fails_closed():
    # Vr2pidVr length must match vr.
    with pytest.raises(ValueError):
        assemble_atomic_hydrogen_collision_matrices(
            np.array([0.5, 1.0]), np.array([-1.0, 1.0]), np.array([1.0]), np.array([2.0, 2.0]), 1.0
        )
    # Negative radial weight.
    with pytest.raises(ValueError):
        assemble_atomic_hydrogen_collision_matrices(
            np.array([0.5, 1.0]),
            np.array([-1.0, 1.0]),
            np.array([-1.0, 2.0]),
            np.array([2.0, 2.0]),
            1.0,
        )
    # Non-positive Tnorm.
    with pytest.raises(ValueError):
        assemble_atomic_hydrogen_collision_matrices(
            np.array([0.5, 1.0]),
            np.array([-1.0, 1.0]),
            np.array([1.0, 2.0]),
            np.array([2.0, 2.0]),
            -1.0,
        )
    # Non-increasing vx; crossing zero is not a physical requirement.
    with pytest.raises(ValueError):
        assemble_atomic_hydrogen_collision_matrices(
            np.array([0.5, 1.0]),
            np.array([1.0, 1.0]),
            np.array([1.0, 2.0]),
            np.array([2.0, 2.0]),
            1.0,
        )
    # Non-positive dVx.
    with pytest.raises(ValueError):
        assemble_atomic_hydrogen_collision_matrices(
            np.array([0.5, 1.0]),
            np.array([-1.0, 1.0]),
            np.array([1.0, 2.0]),
            np.array([0.0, 2.0]),
            1.0,
        )


def test_radial_axis_must_be_strictly_increasing():
    case = dict(CANONICAL)
    case["vr"] = np.array([1.0, 0.5])
    with pytest.raises(ValueError, match="velocity-space carrier"):
        assemble_atomic_hydrogen_collision_matrices(**case)


@pytest.mark.parametrize("parameter", ["Tnorm", "mu"])
def test_normalization_parameters_must_be_scalars(parameter):
    case = dict(CANONICAL)
    case[parameter] = np.array([1.0])
    with pytest.raises(ValueError, match="velocity-space carrier"):
        assemble_atomic_hydrogen_collision_matrices(**case)


@pytest.mark.parametrize(
    "parameter,value",
    [
        ("dVx", np.array([True, True])),
        ("dVx", np.array(["2.0", "2.0"])),
        ("dVx", [True, 2.0]),
    ],
)
def test_velocity_carrier_requires_real_numeric_arrays(parameter, value):
    case = dict(CANONICAL)
    case[parameter] = value
    with pytest.raises(ValueError, match="velocity-space carrier"):
        assemble_atomic_hydrogen_collision_matrices(**case)


def test_underflowed_thermal_normalization_is_rejected():
    case = dict(CANONICAL, Tnorm=np.nextafter(0.0, 1.0))
    with pytest.raises(ValueError, match="thermal normalization"):
        assemble_atomic_hydrogen_collision_matrices(**case)


def test_underflowed_mass_denominator_is_rejected():
    case = dict(CANONICAL, mu=np.nextafter(0.0, 1.0))
    with pytest.raises(ValueError, match="thermal normalization"):
        assemble_atomic_hydrogen_collision_matrices(**case)

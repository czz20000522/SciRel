from scirel.equilibrium.free_boundary_anisotropic_picard import (
    solve_free_boundary_anisotropic_picard,
)
from pathlib import Path
import inspect

import numpy as np
import pytest


def _run(values):
    return solve_free_boundary_anisotropic_picard(values)


def test_public_solver_docstring_declares_contract():
    doc = inspect.getdoc(solve_free_boundary_anisotropic_picard)
    assert doc is not None
    for section in ("Parameters", "Returns", "Raises", "Notes"):
        assert section in doc
    for field in ("fixed-point", "maxiter=0", "minimum_field"):
        assert field in doc


# 验证：YAML 的 N6 映射、显式 N4 closure port 和反馈边必须与可调用图同步。
def test_yaml_declares_picard_feedback_contract():
    contract = Path(__file__).with_name("composition.yaml").read_text(encoding="utf-8")
    assert "primary_pfm_node: N6" in contract
    assert "pressure_closure" in contract
    assert "scirel.kinetic.compositions.frank_egedal_pressure_closure" not in contract
    assert "to_input: psi_state" in contract


def _pressure_closure(state):
    psi = np.asarray(state["psi"], dtype=float)
    return {
        "p_parallel": 2.0 + psi,
        "p_perp": 1.0 + 0.5 * psi,
        "density": None,
        "electron_temperature": None,
    }


def _isotropic_limit_closure(state):
    psi = np.asarray(state["psi"], dtype=float)
    pressure = np.full_like(psi, 2.0)
    return {
        "p_parallel": pressure,
        "p_perp": pressure.copy(),
        "density": None,
        "electron_temperature": None,
    }


def _inputs(**overrides):
    r_grid, z_grid = np.meshgrid(np.array([0.2, 0.4, 0.6]), np.array([-0.1, 0.0, 0.1]))
    n_points = r_grid.size
    values = {
        "r_grid": r_grid,
        "z_grid": z_grid,
        "psi_vac": r_grid.copy(),
        "br_vac": np.zeros_like(r_grid),
        "bz_vac": np.ones_like(r_grid),
        "g_psi": np.zeros((n_points, n_points)),
        "pressure_closure": _pressure_closure,
        "params": {
            "hot_pressure_scale": 1.0,
            "psi_axis": 0.0,
            "psi_edge": 1.0,
            "B0": 1.0,
            "mirror_ratio": 2.0,
            "legendre_degrees": [0.5],
            "source_coefficients": [1.0],
            "velocity_nodes": 4,
            "pitch_nodes": 4,
        },
        "tol": 1.0e-12,
        "maxiter": 1,
        "relax": 0.0,
    }
    values.update(overrides)
    return values


# 验证：零 Green 响应时仍执行一轮真实 pressure-current 状态链，但磁通保持真空值并收敛。
def test_zero_green_performs_one_iteration_without_changing_vacuum_flux():
    values = _inputs()
    result = _run(values)
    assert result["iterations"] == 1
    assert result["converged"]
    assert result["failure_reason"] is None
    np.testing.assert_allclose(result["psi"], values["psi_vac"])
    assert result["picard_current_state"].shape == (9,)
    assert result["profiles"]["p_parallel"].shape == (3, 3)


def test_isotropic_limit_has_zero_anisotropic_source_and_preserves_vacuum():
    values = _inputs(
        pressure_closure=_isotropic_limit_closure,
        g_psi=1.0e-2 * np.eye(9),
    )
    result = _run(values)
    np.testing.assert_allclose(result["profiles"]["p_parallel"], result["profiles"]["p_perp"])
    np.testing.assert_allclose(result["picard_current_state"], 0.0, atol=1.0e-12)
    np.testing.assert_allclose(result["psi"], values["psi_vac"])


# 验证：plasma Green 矩阵不是任意 array；field/source 轴都必须等于 N_Z*N_R。
def test_rejects_non_square_or_wrong_size_green_matrix():
    with pytest.raises(ValueError, match="g_psi must have shape"):
        _run(_inputs(g_psi=np.eye(3)))


# 验证：第 2 步消费第 1 步的真实 psi/current 输出；若没有反馈，psi 不会偏离真空状态。
def test_nonzero_green_requires_sequential_state_feedback():
    r = _inputs()["r_grid"]
    green = 0.5 * r.ravel()[:, None] * r.ravel()[:, None] * np.ones((1, r.size))

    def closure(state):
        p = 3.0 + r**2
        return {"p_parallel": p, "p_perp": p.copy(), "density": None, "electron_temperature": None}

    values = _inputs(
        psi_vac=0.5 * r**2, pressure_closure=closure, g_psi=green, maxiter=2, tol=1.0e-30
    )
    result = _run(values)
    assert result["iterations"] == 2
    assert result["residual_history"].shape == (2,)
    # I0=integral(2R)dR dZ=K; BZ1=1+I0; I1=K/(1+K).
    # Differentiating the same psi increment is necessary for this transition.
    k = (0.6**2 - 0.2**2) * 0.2
    second = k / (1.0 + k)
    np.testing.assert_allclose(result["psi"], 0.5 * r**2 * (1.0 + second))
    np.testing.assert_allclose(result["BZ"], 1.0 + second)
    assert not result["converged"]
    assert result["failure_reason"] == "maxiter_reached"
    final = _run({**values, "maxiter": 50, "tol": 1e-12})
    fixed = 2 * k / (1.0 + np.sqrt(1.0 + 4 * k))
    assert final["converged"]
    np.testing.assert_allclose(final["BZ"], 1.0 + fixed, rtol=2e-12, atol=2e-12)
    np.testing.assert_allclose(np.sum(final["plasma_currents"]), fixed, rtol=2e-12, atol=2e-12)


# 验证：自洽 BR/BZ Green 响应是成对合同，单独提供一个会改变 B 的物理含义，必须拒绝。
def test_iteration_bound_returns_last_state_without_convergence():
    result = _run(_inputs(g_psi=1.0e-2 * np.eye(9), maxiter=1, tol=1.0e-30))
    assert result["iterations"] == 1
    assert not result["converged"]
    assert result["failure_reason"] == "maxiter_reached"
    assert result["residual"] == result["residual_history"][0] > 0.0
    np.testing.assert_allclose(result["profiles"]["p_parallel"], 2.0 + result["psi"])


def test_rejects_unpaired_magnetic_field_green_matrices():
    with pytest.raises(ValueError, match="g_br and g_bz must be provided together"):
        _run(_inputs(g_br=np.eye(9)))


# 验证：墙磁通修正必须同步其磁场导数；保留历史节点名以核对原失败。
def test_boundary_branch_corrects_flux_only_and_keeps_vacuum_poloidal_field():
    # Historical node ID: a wall flux correction must change its magnetic
    # derivatives. A rank-one wall constraint preserves a nonzero physical B.
    r, z = _inputs()["r_grid"], _inputs()["z_grid"]
    sample = np.zeros((1, r.size))
    sample[0, 0] = 1.0
    response = (r**2).ravel()[:, None]
    values = _inputs(
        psi_vac=r**2 * (0.5 + 0.1 * z),
        br_vac=-0.1 * r,
        bz_vac=1 + 0.2 * z,
        pressure_closure=_isotropic_limit_closure,
        boundary_correction={
            "boundary_sample_matrix": sample,
            "green_boundary_to_boundary": sample @ response,
            "green_boundary_to_field": response,
        },
    )
    result = _run(values)
    np.testing.assert_allclose(result["psi"], 0.1 * r**2 * (z + 0.1), atol=1e-15)
    np.testing.assert_allclose(result["BR"], -0.1 * r)
    np.testing.assert_allclose(result["BZ"], 0.2 * (z + 0.1), atol=2e-15)
    assert result["boundary_currents"].shape == (1,)
    # A complete identity wall removes all psi AND B, hitting the declared
    # nonzero-field domain instead of returning a fictitious vacuum field.
    with pytest.raises(FloatingPointError, match="minimum_field"):
        _run(
            _inputs(
                psi_vac=0.5 * r**2,
                pressure_closure=_isotropic_limit_closure,
                boundary_correction={
                    "boundary_sample_matrix": np.eye(r.size),
                    "green_boundary_to_boundary": np.eye(r.size),
                    "green_boundary_to_field": np.eye(r.size),
                },
            )
        )


def test_requires_explicit_n4_pressure_closure_port():
    values = _inputs()
    values.pop("pressure_closure")
    with pytest.raises(ValueError, match="pressure_closure"):
        _run(values)


def test_requires_all_yaml_required_picard_controls():
    for name in ("params", "tol", "maxiter", "relax"):
        values = _inputs()
        values.pop(name)
        with pytest.raises(ValueError, match=f"{name} is required"):
            _run(values)


def test_zero_step_returns_declared_zero_feedback_state():
    result = _run(_inputs(maxiter=0))
    assert result["failure_reason"] == "maxiter_reached"
    assert result["iterations"] == 0
    assert np.isinf(result["residual"])
    assert result["residual_history"].size == 0
    np.testing.assert_allclose(result["picard_current_state"], 0.0)


def test_current_grid_validation_precedes_required_port_validation():
    values = _inputs(r_grid=np.ones((2, 2)))
    values.pop("pressure_closure")
    with pytest.raises(ValueError, match="equal-shape 2-D grids"):
        _run(values)


def test_review_gate_rejects_invalid_closure_fields_and_mask_shape():
    values = _inputs()

    def invalid_closure(state):
        shape = np.asarray(state["psi"]).shape
        return {
            "p_parallel": np.ones(shape),
            "p_perp": np.ones(shape),
            "density": -np.ones(shape),
            "electron_temperature": np.full(shape, np.nan),
        }

    with pytest.raises(ValueError, match="density.*finite nonnegative"):
        _run({**values, "pressure_closure": invalid_closure})

    values = _inputs()
    with pytest.raises(ValueError, match="plasma_mask.*same shape"):
        _run({**values, "plasma_mask": np.ones((2, 2), dtype=bool)})
    with pytest.raises(ValueError, match="plasma_mask.*boolean array"):
        _run({**values, "plasma_mask": np.ones(values["r_grid"].shape, dtype=int)})


def test_review_gate_terminal_outputs_share_the_returned_state():
    values = _inputs()
    result = _run(values)
    weights = np.outer([0.05, 0.1, 0.05], [0.1, 0.2, 0.1])
    np.testing.assert_allclose(result["plasma_currents"], result["j_phi"] * weights)
    np.testing.assert_allclose(result["profiles"]["p_parallel"], 2.0 + result["psi"])


def test_review_gate_rejects_nonuniform_rz_axes_before_iteration():
    r_grid, z_grid = np.meshgrid(np.array([0.2, 0.4, 0.7]), np.array([-0.1, 0.0, 0.1]))
    # Historical node ID: monotone nonuniform coordinates are now supported
    # with explicit per-node weights, rather than rejected or first-spaced.
    result = _run(_inputs(r_grid=r_grid, z_grid=z_grid))
    weights = np.outer([0.05, 0.1, 0.05], [0.1, 0.25, 0.15])
    np.testing.assert_allclose(result["plasma_currents"], result["j_phi"] * weights)
    np.testing.assert_allclose(np.sum(weights), 0.5 * 0.2)


def test_review_gate_rejects_fractional_picard_iteration_count():
    with pytest.raises(ValueError, match="maxiter must be an integer"):
        _run(_inputs(maxiter=1.2))


def test_small_relaxed_step_does_not_terminate_unconverged_feedback_early():
    r = _inputs()["r_grid"]
    p = 3.0 + r**2
    values = _inputs(
        psi_vac=0.5 * r**2,
        pressure_closure=lambda state: {
            "p_parallel": p,
            "p_perp": p.copy(),
            "density": None,
            "electron_temperature": None,
        },
        g_psi=0.5 * (r**2).ravel()[:, None] * np.ones((1, r.size)),
        maxiter=3,
        tol=1e-9,
        relax=1 - 1e-12,
    )
    result = _run(values)
    assert result["iterations"] == 3
    assert len(result["residual_history"]) == 3
    assert result["residual"] < values["tol"]
    assert result["fixed_point_residual"] > values["tol"]
    assert not result["converged"]


def test_unchanged_flux_does_not_hide_changing_field_and_current_feedback():
    r = _inputs()["r_grid"]
    p = 3.0 + r**2
    values = _inputs(
        psi_vac=0.5 * r**2,
        pressure_closure=lambda state: {
            "p_parallel": p,
            "p_perp": p.copy(),
            "density": None,
            "electron_temperature": None,
        },
        g_br=np.zeros((r.size, r.size)),
        g_bz=0.5 * np.ones((r.size, r.size)),
        maxiter=1,
        tol=1e-12,
    )
    result = _run(values)
    np.testing.assert_array_equal(result["psi"], values["psi_vac"])
    assert not result["converged"]
    assert result["field_fixed_point_residual"] > values["tol"]
    assert result["current_fixed_point_residual"] > values["tol"]
    final = _run({**values, "maxiter": 50})
    k = (0.6**2 - 0.2**2) * 0.2
    expected = (1.0 + np.sqrt(1.0 + 2 * k)) / 2.0
    assert final["converged"]
    np.testing.assert_allclose(final["BZ"], expected, rtol=2e-12, atol=2e-12)


def test_null_intermediate_field_fails_before_pressure_current_evaluation():
    calls = []

    def closure(state):
        calls.append(state)
        return _isotropic_limit_closure(state)

    with pytest.raises(FloatingPointError, match="minimum_field"):
        _run(
            _inputs(
                br_vac=np.zeros((3, 3)),
                bz_vac=np.zeros((3, 3)),
                params={"B0": 1.0},
                pressure_closure=closure,
            )
        )
    assert not calls

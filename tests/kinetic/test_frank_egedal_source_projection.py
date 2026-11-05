import pytest
from scirel.kinetic.frank_egedal_source_projection import (
    project_frank_egedal_source_modes,
    project_frank_egedal_source_modes as scientific_function,
)


def test_rejects_incomplete_source_state():
    with pytest.raises((KeyError, ValueError, TypeError)):
        scientific_function({})


def test_reviewed_relation_example():
    import math
    import numpy as np
    from scipy.integrate import quad
    from scipy.special import hyp2f1

    # 显式 degree、无显式系数：用独立自适应积分复算 NBI 投影系数。
    angle_deg = 60.0
    projected = project_frank_egedal_source_modes(
        {
            "mirror_ratio": 2.0,
            "legendre_degrees": [0.5],
            "nbi_pitch_angle_deg": angle_deg,
            "legendre_terms": 24,
            "legendre_backend": "hypergeometric",
        }
    )
    mode = projected["fractional_mode"]
    degree = 0.5

    def independent_mode(xi):
        # 独立重建 P/Q 组合和零点导数边界，不调用返回的 fractional_mode。
        def p(value):
            return hyp2f1(-degree, degree + 1.0, 1.0, (1.0 - value) / 2.0)

        def q(value):
            return (
                0.5
                * math.pi
                / math.sin(math.pi * degree)
                * (math.cos(math.pi * degree) * p(value) - p(-value))
            )

        step = 1.0e-5
        matrix = np.array(
            [
                [p(0.0), q(0.0)],
                [(p(step) - p(-step)) / (2.0 * step), (q(step) - q(-step)) / (2.0 * step)],
            ]
        )
        a_coeff, b_coeff = np.linalg.solve(matrix, np.array([1.0, 0.0]))
        return a_coeff * p(xi) + b_coeff * q(xi)

    xi_tp = projected["xi_tp_mid"]
    xi_nbi = min(max(math.cos(math.radians(angle_deg)), 0.0), xi_tp)
    normalization = (
        4.0
        * math.pi
        * quad(
            lambda xi: float(independent_mode(xi)) ** 2,
            0.0,
            xi_tp,
            epsabs=1e-12,
        )[0]
    )
    expected = float(independent_mode(xi_nbi)) / normalization
    assert projected["degree_source"] == "caller_supplied"
    assert np.allclose(projected["degrees"], [0.5])
    assert abs(projected["source_coefficients"][0] - expected) < 2e-11
    assert abs(float(mode(0.5, 0.0, 24)) - 1.0) < 1e-10
    assert abs(float(mode(0.5, 0.2, 24)) - independent_mode(0.2)) < 2e-12
    step = 1.0e-5
    assert abs(float(mode(0.5, step, 24) - mode(0.5, -step, 24)) / (2.0 * step)) < 1e-8

    # 无显式 degree 时必须调用谱端口，并原样使用它给出的 degree。
    calls = []

    def spectrum(xi_tp_arg, mode_count, grid_points, backend):
        calls.append((xi_tp_arg, mode_count, grid_points, backend))
        return {"degrees": np.array([0.25, 0.75])}

    generated = project_frank_egedal_source_modes(
        {
            "mirror_ratio": 3.0,
            "legendre_mode_count": 2,
            "legendre_spectrum_grid_points": 80,
            "legendre_backend": "truncated",
            "source_coefficients": [1.0, -0.5],
        },
        spectrum_operator=spectrum,
    )
    assert len(calls) == 1 and calls[0][1:] == (2, 80, "truncated")
    assert np.allclose(generated["degrees"], [0.25, 0.75])
    assert np.allclose(generated["source_coefficients"], [1.0, -0.5])
    assert generated["degree_source"] == "scirel.kinetic.loss_cone_spectrum"

    inactive = project_frank_egedal_source_modes({"mirror_ratio": 1.0})
    assert inactive["degrees"].size == 0
    assert inactive["degree_source"] == "inactive_loss_cone"
    assert "legendre_backend" not in inactive

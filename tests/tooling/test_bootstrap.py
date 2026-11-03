import numpy as np
import pytest

from scirel.neoclassical.bootstrap import (
    calculate_bootstrap_current,
    calculate_redl_coefficients,
    calculate_sauter_coefficients,
)


def test_sauter_alpha_finite_large_collisionality():
    l31, l32, l34, alpha = calculate_sauter_coefficients(
        [0.5, 0.5], [1.0, 1.0], [2.0, 2.0], [1e300, 1e300]
    )
    assert np.isfinite(alpha[0])
    np.testing.assert_allclose(alpha, [2.1, 2.1], rtol=0, atol=1e-14)


def test_redl_alpha_and_l34_caller_convention():
    l31, l32, l34, alpha = calculate_redl_coefficients(
        [0.4, 0.4], [0.2, 0.2], [2.0, 2.0], [1e200, 1e200]
    )
    np.testing.assert_array_equal(l34, l31)
    np.testing.assert_allclose(alpha, [-0.5, -0.5], rtol=0, atol=1e-14)


def test_coefficients_match_source_for_ordinary_case():
    got = calculate_sauter_coefficients(
        np.array([0.2, 0.5]), np.array([0.01, 10.0]), np.array([1.5, 2.0]), np.array([0.03, 2.0])
    )
    f = np.array([0.2, 0.5])
    nui = np.array([0.03, 2.0])
    t = np.sqrt(nui)
    a0 = -1.17 * (1 - f) / (1 - 0.22 * f - 0.19 * f * f)
    y = nui**2 * f**6
    expected = (a0 + 0.25 * (1 - f * f) * t) / (1 + 0.5 * t)
    expected = (expected + 0.315 * y) / (1 + 0.15 * y)
    np.testing.assert_allclose(got[3], expected, rtol=2e-15, atol=1e-15)


def test_current_axis_sign_and_midpoint():
    one = np.ones(3)
    zero = np.zeros(3)
    out = calculate_bootstrap_current(
        rho_face=[0.0, 0.5, 1.0],
        F_face=one,
        B0=2.0,
        dpsi_drho_face=one,
        p_e_face=one,
        p_i_face=one,
        dlnne_drho_face=one,
        dlnni_drho_face=zero,
        dlnte_drho_face=zero,
        dlnti_drho_face=zero,
        L31=one,
        L32=zero,
        L34=one,
        alpha=one,
    )
    np.testing.assert_allclose(out["j_parallel_bootstrap_face"], [0, -np.pi, -np.pi])
    np.testing.assert_allclose(out["j_parallel_bootstrap"], [-np.pi / 2, -np.pi])


def test_current_requires_nonzero_interior_flux_gradient():
    with pytest.raises(ValueError, match="nonzero away"):
        calculate_bootstrap_current(
            rho_face=[0.0, 0.5, 1.0],
            F_face=[1, 1, 1],
            B0=1,
            dpsi_drho_face=[0, 0, 1],
            p_e_face=[1, 1, 1],
            p_i_face=[1, 1, 1],
            dlnne_drho_face=[0, 0, 0],
            dlnni_drho_face=[0, 0, 0],
            dlnte_drho_face=[0, 0, 0],
            dlnti_drho_face=[0, 0, 0],
            L31=[1, 1, 1],
            L32=[1, 1, 1],
            L34=[1, 1, 1],
            alpha=[1, 1, 1],
        )


def test_alpha_binary_exponent_cancellation():
    sa = calculate_sauter_coefficients([1e-100] * 2, [1.0] * 2, [2.0] * 2, [1e300] * 2)[3]
    # Exact decimal relation y=nu_i^2*f^6=1; B tends to .5.
    np.testing.assert_allclose(sa, (0.5 + 0.315) / (1 + 0.15), rtol=2e-14, atol=3e-15)


def test_current_finite_extreme_midpoints():
    one = np.ones(3)
    zero = np.zeros(3)
    x = calculate_bootstrap_current(
        rho_face=[0.0, 0.5, 1.0],
        F_face=one,
        B0=2.0,
        dpsi_drho_face=np.full(3, np.pi / 1e308),
        p_e_face=one,
        p_i_face=zero,
        dlnne_drho_face=one,
        dlnni_drho_face=zero,
        dlnte_drho_face=zero,
        dlnti_drho_face=zero,
        L31=one,
        L32=zero,
        L34=zero,
        alpha=zero,
    )
    assert np.all(np.isfinite(x["j_parallel_bootstrap"]))
    np.testing.assert_allclose(x["j_parallel_bootstrap"], [-5e307, -1e308], rtol=2e-15)


def test_scalar_and_mixed_boolean_input_contract():
    with pytest.raises(ValueError):
        calculate_sauter_coefficients([True, 0.5], [1.0, 1.0], [2.0, 2.0], [1.0, 1.0])
    one = np.ones(3)
    zero = np.zeros(3)
    for invalid in ("2.0", True, [2.0], 2j, np.ma.array(2.0, mask=True)):
        with pytest.raises(ValueError):
            calculate_bootstrap_current(
                rho_face=[0.0, 0.5, 1.0],
                F_face=one,
                B0=invalid,
                dpsi_drho_face=one,
                p_e_face=one,
                p_i_face=one,
                dlnne_drho_face=zero,
                dlnni_drho_face=zero,
                dlnte_drho_face=zero,
                dlnti_drho_face=zero,
                L31=one,
                L32=zero,
                L34=one,
                alpha=one,
            )


def _current_inputs(**overrides):
    one, zero = np.ones(3), np.zeros(3)
    values = dict(
        rho_face=[0.0, 0.5, 1.0],
        F_face=one,
        B0=2.0,
        p_e_face=one,
        p_i_face=one,
        dlnne_drho_face=one,
        dlnni_drho_face=zero,
        dlnte_drho_face=zero,
        dlnti_drho_face=zero,
        L31=one,
        L32=zero,
        L34=one,
        alpha=one,
    )
    values.update(overrides)
    return values


def test_per_radian_flux_derivative_equals_total_flux_divided_by_two_pi():
    total = calculate_bootstrap_current(
        **_current_inputs(dpsi_drho_face=2 * np.pi * np.array([0.0, 0.3, 0.7]))
    )
    per_radian = calculate_bootstrap_current(
        **_current_inputs(dpsi_per_radian_drho_face=[0.0, 0.3, 0.7])
    )
    np.testing.assert_allclose(
        per_radian["j_parallel_bootstrap_face"], total["j_parallel_bootstrap_face"], rtol=1e-15
    )
    np.testing.assert_allclose(
        per_radian["j_parallel_bootstrap_face"], [0.0, -1 / (2 * 0.3), -1 / (2 * 0.7)]
    )


@pytest.mark.parametrize(
    "flux", [{}, {"dpsi_drho_face": np.ones(3), "dpsi_per_radian_drho_face": np.ones(3)}]
)
def test_flux_derivative_must_be_given_in_exactly_one_convention(flux):
    with pytest.raises(ValueError, match="exactly one of dpsi_drho_face"):
        calculate_bootstrap_current(**_current_inputs(**flux))


def test_only_a_face_at_rho_zero_is_treated_as_the_axis():
    off_axis = calculate_bootstrap_current(
        **_current_inputs(rho_face=[0.1, 0.5, 1.0], dpsi_per_radian_drho_face=np.ones(3))
    )
    np.testing.assert_allclose(off_axis["j_parallel_bootstrap_face"], [-0.5, -0.5, -0.5])
    with pytest.raises(ValueError, match="nonzero away from the axis"):
        calculate_bootstrap_current(
            **_current_inputs(rho_face=[0.1, 0.5, 1.0], dpsi_per_radian_drho_face=[0.0, 1.0, 1.0])
        )


@pytest.mark.parametrize("rho", [[0.0, 0.5, 0.5], [0.5, 0.2, 1.0], [-0.1, 0.5, 1.0]])
def test_rho_face_must_be_nonnegative_and_increasing(rho):
    with pytest.raises(ValueError, match="rho_face"):
        calculate_bootstrap_current(**_current_inputs(rho_face=rho, dpsi_drho_face=np.ones(3)))

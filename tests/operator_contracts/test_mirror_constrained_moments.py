# 覆盖：无损失锥解析极限、端塞损失锥、单侧端塞拒绝、caller profile(psi) 与显式数组等价。
import numpy as np
import pytest

from scirel.kinetic.mirror_constrained_moments import evaluate_mirror_constrained_moments, evaluate_mirror_constrained_moments as scientific_operator


E = 1.602176634e-19
M = 1.67262192595e-27


def test_untruncated_moments_match_closed_form():
    b = np.array([1.0, 1.5, 2.0])
    result = scientific_operator(b, np.zeros(3), 0.0, M, E, 2e18, 1200 * E, 2400 * E, 1.0)
    t_perp = b / ((b - 1.0) / (1200 * E) + 1.0 / (2400 * E))
    density = 2e18 * t_perp / (2400 * E)
    np.testing.assert_allclose(result['density_m3'], density)
    np.testing.assert_allclose(result['p_parallel_pa'], density * 1200 * E)
    np.testing.assert_allclose(result['p_perpendicular_pa'], density * t_perp)


def test_plugged_loss_cone_reduces_moments_without_negative_values():
    result = scientific_operator(np.array([1.0, 2.0]), np.zeros(2), 0.0, M, E, 2e18, 1200 * E, 2400 * E, 1.0, b_plug_left_t=4.0, b_plug_right_t=5.0, phi_plug_left_v=800.0, phi_plug_right_v=1000.0, loss_cone_refill=0.0, quadrature_order=40)
    assert np.all(result['density_pitch_integral'] < 1.0)
    assert np.all(result['density_m3'] > 0.0)
    assert np.all(result['p_parallel_pa'] >= 0.0)


def test_plugged_default_is_the_source_empty_loss_cone_default():
    kwargs = dict(b_plug_left_t=4.0, b_plug_right_t=5.0, phi_plug_left_v=800.0, phi_plug_right_v=1000.0)
    default = scientific_operator(np.array([1.0]), np.zeros(1), 0.0, M, E, 2e18, 1200*E, 2400*E, 1.0, **kwargs)
    explicit = scientific_operator(np.array([1.0]), np.zeros(1), 0.0, M, E, 2e18, 1200*E, 2400*E, 1.0, loss_cone_refill=0.0, **kwargs)
    np.testing.assert_allclose(default['density_m3'], explicit['density_m3'])


def test_single_plug_field_is_rejected():
    try:
        scientific_operator(1.0, 0.0, 0.0, M, E, 1e18, E, E, 1.0, b_plug_left_t=4.0)
    except ValueError:
        return
    raise AssertionError('expected invalid one-sided plug contract to fail')


def test_refill_one_skips_plug_profiles_but_still_validates_quadrature_control():
    args = (1.25, 0.0, 0.0, M, E, 2e18, 1200 * E, 2400 * E, 1.0)

    def unexpected_profile(_psi):
        raise AssertionError('refill-one branch must not evaluate plug profiles')

    baseline = scientific_operator(*args)
    restored = scientific_operator(
        *args, b_plug_left_t=unexpected_profile,
        b_plug_right_t=unexpected_profile,
        phi_plug_left_v=unexpected_profile,
        phi_plug_right_v=unexpected_profile,
        loss_cone_refill=1.0,
    )
    np.testing.assert_allclose(restored['density_m3'], baseline['density_m3'])
    np.testing.assert_allclose(restored['p_parallel_pa'], baseline['p_parallel_pa'])
    np.testing.assert_allclose(restored['p_perpendicular_pa'], baseline['p_perpendicular_pa'])
    with pytest.raises(ValueError, match='quadrature_order'):
        scientific_operator(*args, quadrature_order=7.9)


def test_fractional_quadrature_order_uses_its_integer_part():
    args = (1.25, 0.0, 0.0, M, E, 2e18, 1200 * E, 2400 * E, 1.0)
    plugs = dict(b_plug_left_t=4.0, b_plug_right_t=5.0,
                 phi_plug_left_v=800.0, phi_plug_right_v=-800.0)
    integer = scientific_operator(*args, quadrature_order=16, **plugs)
    fractional = scientific_operator(*args, quadrature_order=16.9, **plugs)
    for field in ('density_pitch_integral', 'parallel_pitch_integral',
                  'perpendicular_pitch_integral'):
        np.testing.assert_array_equal(fractional[field], integer[field])


def test_signed_negative_charge_is_supported_by_the_leaf():
    result = scientific_operator(1.0, 0.0, 1.0, M, -E, 1e18, E, E, 1.0)
    np.testing.assert_allclose(result['density_m3'], 1e18 * np.e)


def test_vectorized_psi_profile_matches_its_explicit_array_values():
    psi = np.array([0.0, 0.25, 0.5])
    density = lambda value: 2e18 * (1.0 + 0.2 * value)
    callable_result = scientific_operator(np.ones(3), psi, 0.0, M, E, density, 1200 * E, 2400 * E, 1.0)
    array_result = scientific_operator(np.ones(3), psi, 0.0, M, E, density(psi), 1200 * E, 2400 * E, 1.0)
    np.testing.assert_allclose(callable_result['density_m3'], array_result['density_m3'])


def test_reviewed_relation_example():
    import math
    import numpy as np
    from scipy.integrate import quad
    from scirel.kinetic.mirror_constrained_moments import evaluate_mirror_constrained_moments

    ELEMENTARY_CHARGE = 1.602176634e-19
    PROTON_MASS = 1.67262192595e-27
    b = np.array([1.0, 1.5, 2.0])
    result = evaluate_mirror_constrained_moments(
        b,
        np.zeros(3),
        0.0,
        PROTON_MASS,
        ELEMENTARY_CHARGE,
        2.0e18,
        1200.0 * ELEMENTARY_CHARGE,
        2400.0 * ELEMENTARY_CHARGE,
        1.0,
    )
    t_perp = b / ((b - 1.0) / (1200.0 * ELEMENTARY_CHARGE) + 1.0 / (2400.0 * ELEMENTARY_CHARGE))
    density = 2.0e18 * t_perp / (2400.0 * ELEMENTARY_CHARGE)
    assert np.allclose(result["density_m3"], density)
    assert np.allclose(result["p_parallel_pa"] / result["density_m3"], 1200.0 * ELEMENTARY_CHARGE)
    assert np.allclose(result["p_perpendicular_pa"] / result["density_m3"], t_perp)
    assert np.allclose(result["density_pitch_integral"], 1.0)
    restored = evaluate_mirror_constrained_moments(
        b,
        np.zeros(3),
        0.0,
        PROTON_MASS,
        ELEMENTARY_CHARGE,
        2.0e18,
        1200.0 * ELEMENTARY_CHARGE,
        2400.0 * ELEMENTARY_CHARGE,
        1.0,
        b_plug_left_t=4.0,
        b_plug_right_t=5.0,
        loss_cone_refill=1.0,
    )
    assert np.allclose(restored["density_m3"], result["density_m3"])

    # 端塞分支用独立自适应积分复算三个俯仰积分；不调用实现的求积节点或内部函数。
    b_plug_left = 4.0
    b_plug_right = 5.0
    phi_plug_left = 800.0
    phi_plug_right = -800.0
    plugged = evaluate_mirror_constrained_moments(
        np.array([1.25, 1.75]),
        np.zeros(2),
        0.0,
        PROTON_MASS,
        ELEMENTARY_CHARGE,
        2.0e18,
        1200.0 * ELEMENTARY_CHARGE,
        2400.0 * ELEMENTARY_CHARGE,
        1.0,
        b_plug_left_t=b_plug_left,
        b_plug_right_t=b_plug_right,
        phi_plug_left_v=phi_plug_left,
        phi_plug_right_v=phi_plug_right,
        loss_cone_refill=0.0,
        quadrature_order=256,
    )
    def independent_pitch_integrals(local_b):
        coefficient = (local_b - 1.0) / (1200.0 * ELEMENTARY_CHARGE) + 1.0 / (2400.0 * ELEMENTARY_CHARGE)
        alpha_left = (b_plug_left - local_b) / (coefficient * 1200.0 * ELEMENTARY_CHARGE)
        alpha_right = (b_plug_right - local_b) / (coefficient * 1200.0 * ELEMENTARY_CHARGE)
        beta_left = ELEMENTARY_CHARGE * phi_plug_left / (1200.0 * ELEMENTARY_CHARGE)
        beta_right = ELEMENTARY_CHARGE * phi_plug_right / (1200.0 * ELEMENTARY_CHARGE)
        roots = [0.0, 40.0]
        for alpha, beta in ((alpha_left, beta_left), (alpha_right, beta_right)):
            if abs(alpha) > np.finfo(float).eps:
                roots.append(min(max(-beta / alpha, 0.0), 40.0))
        if abs(alpha_left - alpha_right) > np.finfo(float).eps:
            roots.append(min(max(-(beta_left - beta_right) / (alpha_left - alpha_right), 0.0), 40.0))
        roots = sorted(set(roots))
        def factors(x):
            y = max(min(alpha_left * x + beta_left, alpha_right * x + beta_right), 0.0)
            root_y = math.sqrt(y)
            density_factor = math.erf(root_y)
            parallel_factor = density_factor - 2.0 / math.sqrt(math.pi) * root_y * math.exp(-y)
            return density_factor, parallel_factor
        values = []
        for index in range(3):
            total = 0.0
            for lower, upper in zip(roots[:-1], roots[1:]):
                if upper == lower:
                    continue
                total += quad(
                    lambda x: math.exp(-x) * (factors(x)[index] if index < 2 else x * factors(x)[0]),
                    lower,
                    upper,
                    epsabs=1.0e-13,
                    points=None,
                )[0]
            values.append(total)
        return values
    expected_plug = np.asarray([independent_pitch_integrals(value) for value in (1.25, 1.75)])
    # The square-root onset at a loss-cone root is integrable but not smooth;
    # this tolerance is the observed 256-point Gauss--Legendre discretization error.
    np.testing.assert_allclose(plugged["density_pitch_integral"], expected_plug[:, 0], rtol=3.0e-8, atol=1.0e-10)
    np.testing.assert_allclose(plugged["parallel_pitch_integral"], expected_plug[:, 1], rtol=3.0e-8, atol=1.0e-10)
    np.testing.assert_allclose(plugged["perpendicular_pitch_integral"], expected_plug[:, 2], rtol=3.0e-8, atol=1.0e-10)


def test_review_gate_rejects_nonfinite_species_and_refill_controls():
    import pytest

    values = dict(
        b_t=np.ones(2), psi=np.zeros(2), potential_v=np.zeros(2), mass_kg=1.0,
        charge_c=1.0, density_ref_m3=1.0, temperature_parallel_j=1.0,
        temperature_perpendicular_ref_j=1.0, b_ref_t=1.0,
    )
    with pytest.raises(ValueError, match="mass_kg"):
        evaluate_mirror_constrained_moments(**{**values, "mass_kg": np.nan})
    with pytest.raises(ValueError, match="loss_cone_refill"):
        evaluate_mirror_constrained_moments(**{**values, "loss_cone_refill": np.nan})

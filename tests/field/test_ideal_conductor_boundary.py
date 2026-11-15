from fractions import Fraction

import numpy as np
import pytest

from scirel.field.ideal_conductor_boundary import (
    correct_ideal_conductor_boundary_flux,
    correct_ideal_conductor_boundary_flux as scientific_function,
)


def _inputs():
    return {
        "uncorrected_field_flux": np.array([3.0, -1.0, 2.0]),
        "boundary_sample_matrix": np.array([[1.0, 0.0, 0.0], [0.0, 0.5, 0.5]]),
        "green_boundary_to_boundary": np.array([[2.0, 0.0], [0.0, 4.0]]),
        # S @ G_BF equals G_BB, so the field correction is physically
        # consistent with the sampled boundary response.
        "green_boundary_to_field": np.array([[2.0, 0.0], [-1.0, 3.0], [1.0, 5.0]]),
    }


# 验证：满秩墙 Green 矩阵时，采样边界磁通应由墙电流严格抵消。
def test_cancels_boundary_flux_and_reports_rank():
    result = scientific_function(**_inputs())
    assert np.allclose(result["residual"], 0.0)
    assert result["residual_norm"] == pytest.approx(0.0)
    assert result["effective_rank"] == 2
    assert np.allclose(result["corrected_field_flux"], np.array([0.0, 0.125, -0.125]))
    assert np.allclose(_inputs()["boundary_sample_matrix"] @ result["corrected_field_flux"], 0.0)


# 验证：相对奇异值截断必须改变有效秩，而非法 rcond 必须 fail closed。
def test_honors_relative_svd_cutoff_and_rejects_invalid_cutoff():
    data = _inputs()
    data["green_boundary_to_boundary"] = np.diag([2.0, 1.0e-6])
    result = scientific_function(**data, rcond=1.0e-4)
    assert result["effective_rank"] == 1
    with pytest.raises(ValueError):
        scientific_function(**_inputs(), rcond=-1.0)


def test_consistent_flux_rescaling_preserves_boundary_currents():
    data = _inputs()
    per_radian = scientific_function(**data)
    full_flux = scientific_function(
        uncorrected_field_flux=2 * np.pi * data["uncorrected_field_flux"],
        boundary_sample_matrix=data["boundary_sample_matrix"],
        green_boundary_to_boundary=2 * np.pi * data["green_boundary_to_boundary"],
        green_boundary_to_field=2 * np.pi * data["green_boundary_to_field"],
    )
    np.testing.assert_allclose(full_flux["boundary_currents"], per_radian["boundary_currents"])
    for name in (
        "corrected_field_flux",
        "boundary_flux_correction",
        "field_flux_correction",
        "residual",
    ):
        np.testing.assert_allclose(full_flux[name], 2 * np.pi * per_radian[name])


def test_reviewed_relation_example():
    import numpy as np

    field_flux = np.array([3.0, -1.0, 2.0])
    sample = np.array([[1.0, 0.0, 0.0], [0.0, 0.5, 0.5]])
    g_boundary = np.array([[2.0, 0.0], [0.0, 4.0]])
    g_field = np.array([[2.0, 0.0], [-1.0, 3.0], [1.0, 5.0]])
    assert np.allclose(sample @ g_field, g_boundary)
    result = correct_ideal_conductor_boundary_flux(field_flux, sample, g_boundary, g_field)
    np.testing.assert_allclose(result["residual"], 0.0)
    np.testing.assert_allclose(sample @ result["corrected_field_flux"], result["residual"])
    np.testing.assert_allclose(result["corrected_field_flux"], [0.0, 0.125, -0.125])
    assert result["effective_rank"] == 2
    assert result["residual_norm"] == 0.0


@pytest.mark.parametrize(
    "scale", [np.nextafter(0.0, 1.0), 1e-310, np.ldexp(1.0, -900), 1.0, np.ldexp(1.0, 996)]
)
def test_representable_scalar_solution_does_not_require_a_representable_inverse(scale):
    # The exact equation is scale * I = -scale, even for a subnormal scale.
    with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
        result = scientific_function([scale], [[1.0]], [[scale]], [[scale]])
    np.testing.assert_array_equal(result.boundary_currents, [-1.0])
    np.testing.assert_array_equal(result.corrected_field_flux, [0.0])
    np.testing.assert_array_equal(result.boundary_flux_correction, [-scale])
    np.testing.assert_array_equal(result.field_flux_correction, [-scale])
    np.testing.assert_array_equal(result.residual, [0.0])
    np.testing.assert_array_equal(result.singular_values, [scale])
    assert result.residual_norm == 0.0
    assert result.effective_rank == 1


def _exact_two_by_two_currents(matrix, flux):
    # Independent Cramer's-rule oracle on the actual binary64 inputs, no SVD.
    a, b, c, d = [Fraction(float(x)) for x in np.asarray(matrix).flat]
    p, q = [Fraction(float(x)) for x in flux]
    determinant = a * d - b * c
    return np.array([float((b * q - d * p) / determinant), float((c * p - a * q) / determinant)])


@pytest.mark.parametrize(
    "scale", [np.ldexp(1.0, e) for e in (-1027, -500, 0, 500, 1000)] + [1e-300, 1e300]
)
def test_nondiagonal_common_scale_matches_exact_rational_equations(scale):
    green = scale * np.array([[2.0, 1.0], [1.0, 2.0]])
    flux = scale * np.array([1.0, -2.0])
    expected = _exact_two_by_two_currents(green, flux)
    with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
        result = scientific_function(flux, np.eye(2), green, green)
    # At 2**-1027 one subnormal ulp is 2**-47 of the smaller singular value.
    # This fixed bound also covers the ordinary and large-scale cases.
    np.testing.assert_allclose(result.boundary_currents, expected, rtol=5e-14, atol=0.0)
    np.testing.assert_allclose(result.boundary_flux_correction / scale, [-1.0, 2.0], rtol=5e-14)
    np.testing.assert_allclose(result.corrected_field_flux / scale, 0.0, rtol=0.0, atol=5e-14)
    np.testing.assert_allclose(result.residual / scale, 0.0, rtol=0.0, atol=5e-14)
    np.testing.assert_allclose(result.singular_values / scale, [3.0, 1.0], rtol=5e-14)
    assert np.isfinite(result.residual_norm)
    assert result.effective_rank == 2


@pytest.mark.parametrize("scale", [np.ldexp(1.0, -1027), 1.0, np.ldexp(1.0, 1000)])
def test_underdetermined_solution_retains_the_minimum_norm_and_nullspace(scale):
    # a=(scale,scale): the exact minimum-norm solution is -b*a/(a.a).
    a, b = Fraction(float(scale)), Fraction(float(scale))
    expected = float(-b * a / (2 * a * a))
    green = np.array([[scale, scale]])
    result = scientific_function([scale], [[1.0]], green, green)
    np.testing.assert_allclose(result.boundary_currents, [expected, expected], rtol=5e-14)
    assert result.boundary_currents[0] - result.boundary_currents[1] == pytest.approx(0.0)
    np.testing.assert_allclose(result.residual / scale, 0.0, rtol=0.0, atol=5e-14)
    assert result.effective_rank == 1


@pytest.mark.parametrize("scale", [np.ldexp(1.0, -1027), 1.0, np.ldexp(1.0, 1000)])
@pytest.mark.parametrize(
    "rcond,rank",
    [
        (0.0, 2),
        (0.25 - 2.0**-48, 2),
        (np.nextafter(0.25, 0.0), 2),
        (0.25, 1),
        (np.nextafter(0.25, 1.0), 1),
        (1.0, 0),
        (2.0, 0),
    ],
)
def test_cutoff_equality_and_adjacent_values_keep_the_original_strict_rule(scale, rcond, rank):
    green = np.diag([4.0 * scale, scale])
    flux = np.array([4.0 * scale, scale])
    # Preserve the *rounded product* cutoff, not an idealized real ratio.
    # In the subnormal case the immediately lower rcond still rounds to s_min.
    if scale == np.ldexp(1.0, -1027) and rcond == np.nextafter(0.25, 0.0):
        rank = 1
    result = scientific_function(flux, np.eye(2), green, green, rcond=rcond)
    expected = [-1.0, -1.0] if rank == 2 else ([-1.0, 0.0] if rank == 1 else [0.0, 0.0])
    np.testing.assert_array_equal(result.boundary_currents, expected)
    np.testing.assert_array_equal(result.residual, flux + green @ np.array(expected))
    assert result.effective_rank == rank
    assert result.residual_norm == pytest.approx(
        float(np.hypot(*result.residual)), rel=2e-15, abs=0.0
    )


@pytest.mark.parametrize("scale", [np.ldexp(1.0, -1027), 1.0, np.ldexp(1.0, 1000)])
def test_rank_deficiency_keeps_left_nullspace_residual_and_its_finite_norm(scale):
    green = np.diag([scale, 0.0])
    result = scientific_function([scale, 2.0 * scale], np.eye(2), green, green, rcond=0.0)
    np.testing.assert_array_equal(result.boundary_currents, [-1.0, 0.0])
    np.testing.assert_array_equal(result.residual, [0.0, 2.0 * scale])
    assert result.residual_norm == 2.0 * scale
    assert result.effective_rank == 1


@pytest.mark.parametrize("scale", [np.ldexp(1.0, -1027), 1.0, np.ldexp(1.0, 1000)])
def test_zero_green_keeps_all_flux_and_a_scaled_three_four_five_norm(scale):
    green = np.zeros((2, 2))
    flux = np.array([3.0 * scale, 4.0 * scale])
    result = scientific_function(flux, np.eye(2), green, green, rcond=0.0)
    np.testing.assert_array_equal(result.boundary_currents, [0.0, 0.0])
    np.testing.assert_array_equal(result.corrected_field_flux, flux)
    np.testing.assert_array_equal(result.residual, flux)
    assert result.residual_norm == 5.0 * scale
    assert result.effective_rank == 0


def test_overflowing_nonnegative_cutoff_still_discards_all_directions():
    # A finite rcond above one may produce an infinite product cutoff.
    result = scientific_function([1.0], [[1.0]], [[1e308]], [[1e308]], rcond=1e308)
    np.testing.assert_array_equal(result.boundary_currents, [0.0])
    np.testing.assert_array_equal(result.residual, [1.0])
    assert result.residual_norm == 1.0
    assert result.effective_rank == 0


@pytest.mark.parametrize(
    "failure",
    [
        "currents",
        "field_correction",
        "corrected_flux",
        "sampled_flux",
        "singular_values",
        "residual_norm",
    ],
)
def test_truly_nonfinite_arithmetic_raises_without_returning_a_partial_result(failure):
    largest = np.finfo(float).max
    if failure == "currents":
        args = ([1.0], [[1.0]], [[1e-310]], [[1e-310]])
    elif failure == "field_correction":
        args = ([2.0], [[1.0]], [[1.0]], [[largest]])
    elif failure == "corrected_flux":
        args = ([1e308], [[1e-308]], [[-1.0]], [[1e308]])
    elif failure == "sampled_flux":
        args = ([largest], [[2.0]], [[1.0]], [[1.0]])
    elif failure == "singular_values":
        args = ([0.0], [[1.0]], [[largest, largest]], [[0.0, 0.0]])
    else:
        args = ([largest, largest], np.eye(2), np.zeros((2, 2)), np.zeros((2, 2)))
    # A caller's warning policy must not turn an unrepresentable result green.
    with np.errstate(all="ignore"), pytest.raises(FloatingPointError):
        scientific_function(*args)


@pytest.mark.parametrize("exponent", [-1060, -1050, -1020, 0, 1000])
def test_conditioned_binary_equations_do_not_quantize_the_internal_solve(exponent):
    scale = np.ldexp(1.0, exponent)
    green = scale * np.array([[3.0, 1.0], [2.0, 4.0]])
    flux = scale * np.array([2.0, -5.0])
    expected = _exact_two_by_two_currents(green, flux)
    result = scientific_function(flux, np.eye(2), green, green)
    np.testing.assert_allclose(
        result.boundary_currents, expected, rtol=64 * np.finfo(float).eps, atol=0.0
    )
    assert result.effective_rank == 2


def test_finite_tall_solution_allows_an_unrepresentable_internal_projection():
    scale = np.ldexp(1.0, 1023)
    green = np.full((2, 1), scale)
    flux = np.full(2, 1.5 * scale)
    # Exact equation a*I=-3*a/2, without projecting onto the SVD basis.
    expected = float(-Fraction(float(flux[0])) / Fraction(float(scale)))
    result = scientific_function(flux, np.eye(2), green, green)
    np.testing.assert_allclose(result.boundary_currents, [expected], rtol=5e-14, atol=0.0)
    np.testing.assert_allclose(result.residual / scale, 0.0, rtol=0.0, atol=5e-14)
    np.testing.assert_allclose(result.corrected_field_flux / scale, 0.0, rtol=0.0, atol=5e-14)


def test_finite_wide_solution_allows_an_unrepresentable_internal_mode():
    scale = np.ldexp(1.0, -1023)
    green = np.full((1, 2), scale)
    # Minimum norm for a*(I1+I2)=-3 is I1=I2=-3/(2*a).
    expected = float(-Fraction(3) / (2 * Fraction(float(scale))))
    result = scientific_function([3.0], [[1.0]], green, green)
    np.testing.assert_allclose(result.boundary_currents, [expected, expected], rtol=5e-14, atol=0.0)
    np.testing.assert_allclose(result.residual, 0.0, rtol=0.0, atol=5e-14)
    np.testing.assert_allclose(result.corrected_field_flux, 0.0, rtol=0.0, atol=5e-14)


def test_compensated_sampling_retains_a_current_below_the_flux_rounding_floor():
    scale = np.nextafter(0.0, 1.0)
    # Exact S*Gbf=Gbb; sampled flux=t/4 is internal, whereas I=-1/4 is finite.
    result = scientific_function([scale], [[0.25]], [[scale]], [[4.0 * scale]])
    np.testing.assert_array_equal(result.boundary_currents, [-0.25])
    np.testing.assert_array_equal(result.field_flux_correction, [-scale])
    np.testing.assert_array_equal(result.corrected_field_flux, [0.0])
    np.testing.assert_array_equal(result.residual, [0.0])
    assert result.residual_norm == 0.0
    assert result.effective_rank == 1


def test_zero_field_axis_remains_a_valid_empty_field_result():
    result = scientific_function([], np.zeros((1, 0)), [[1.0]], np.zeros((0, 1)))
    np.testing.assert_array_equal(result.corrected_field_flux, [])
    np.testing.assert_array_equal(result.field_flux_correction, [])
    np.testing.assert_array_equal(result.boundary_currents, [0.0])
    np.testing.assert_array_equal(result.residual, [0.0])
    assert result.residual_norm == 0.0
    assert result.effective_rank == 1


def test_exact_sampling_cancellation_does_not_overflow_partial_products():
    largest = np.finfo(float).max
    # S @ Gbf = Gbb = 2, but each of the two sampling products overflows.
    result = scientific_function([largest, largest], [[2.0, -2.0]], [[2.0]], [[1.0], [0.0]])
    np.testing.assert_array_equal(result.corrected_field_flux, [largest, largest])
    np.testing.assert_array_equal(result.boundary_currents, [0.0])
    np.testing.assert_array_equal(result.residual, [0.0])
    assert result.residual_norm == 0.0


def test_residual_norm_is_formed_before_rounding_each_subnormal_component():
    scale = np.nextafter(0.0, 1.0)
    # Sixteen residual components t/4 have Euclidean norm t, not zero.
    result = scientific_function([scale], np.full((16, 1), 0.25), np.zeros((16, 1)), [[0.0]])
    np.testing.assert_array_equal(result.residual, np.zeros(16))
    np.testing.assert_array_equal(result.boundary_currents, [0.0])
    assert result.residual_norm == scale
    assert result.effective_rank == 0


@pytest.mark.parametrize("policy", ["ignore", "warn", "raise"])
def test_nonzero_current_lost_at_output_is_an_explicit_failure(policy):
    exact_current = -Fraction(1e-20) / Fraction(1e308)
    assert exact_current and float(exact_current) == 0.0
    with np.errstate(all=policy), pytest.raises(FloatingPointError):
        scientific_function([1e-20], [[1.0]], [[1e308]], [[1e308]])


@pytest.mark.parametrize("current", [np.ldexp(1.0, -1000), np.nextafter(0.0, 1.0)])
def test_representable_tiny_current_is_not_rejected(current):
    result = scientific_function([current], [[1.0]], [[1.0]], [[1.0]])
    np.testing.assert_array_equal(result.boundary_currents, [-current])
    np.testing.assert_array_equal(result.field_flux_correction, [-current])
    np.testing.assert_array_equal(result.residual, [0.0])


def test_true_final_field_underflow_does_not_reject_a_reusable_current():
    tiny = np.nextafter(0.0, 1.0)
    result = scientific_function([tiny], [[0.25]], [[tiny]], [[tiny]])
    np.testing.assert_array_equal(result.boundary_currents, [-0.25])
    np.testing.assert_array_equal(result.field_flux_correction, [0.0])
    np.testing.assert_array_equal(result.corrected_field_flux, [tiny])


def test_exact_zero_current_is_not_an_underflow_failure():
    result = scientific_function([0.0], [[1.0]], [[1e308]], [[1e308]])
    np.testing.assert_array_equal(result.boundary_currents, [0.0])
    assert result.residual_norm == 0.0


def test_subnormal_current_corrections_use_the_returned_current():
    flux, green = 1e-15, 1e308
    current = float(-Fraction(flux) / Fraction(green))
    assert current != 0.0 and abs(current) < np.finfo(float).tiny
    expected_correction = float(Fraction(green) * Fraction(current))
    expected_residual = float(Fraction(flux) + Fraction(expected_correction))
    result = scientific_function([flux], [[1.0]], [[green]], [[green]])
    np.testing.assert_array_equal(result.boundary_currents, [current])
    np.testing.assert_array_equal(result.field_flux_correction, [expected_correction])
    np.testing.assert_array_equal(result.boundary_flux_correction, [expected_correction])
    np.testing.assert_array_equal(result.residual, [expected_residual])


def test_ordinary_coupled_problem_does_not_use_integer_dot_products(monkeypatch):
    import scirel.field.ideal_conductor_boundary as implementation

    def unexpected_integer_sum(*args):
        raise AssertionError("ordinary coupled arithmetic must use the vectorized path")

    monkeypatch.setattr(implementation, "_scaled_sum", unexpected_integer_sum)
    green = np.eye(16)
    field = np.tile(green, (16, 1))
    sample = np.zeros((16, 256))
    sample[:, :16] = green
    result = scientific_function(np.ones(256), sample, green, field)
    np.testing.assert_array_equal(result.boundary_currents, -np.ones(16))
    np.testing.assert_array_equal(result.corrected_field_flux, np.zeros(256))


@pytest.mark.parametrize("bits", [27, 52])
def test_cancelling_rounded_products_retain_the_exact_sampled_equation(bits):
    a = 1.0 + 2.0**-bits
    b = 1.0 + 2.0 ** (1 - bits)
    # a*a-b = 2**(-2*bits), even when each rounded product erases that term.
    sampled = Fraction(a) * Fraction(a) - Fraction(b)
    assert sampled == Fraction(2) ** (-2 * bits)
    expected = float(-sampled / Fraction(a))
    result = scientific_function([a, b], [[a, -1.0]], [[a]], [[1.0], [0.0]])
    np.testing.assert_allclose(
        result.boundary_currents, [expected], rtol=64 * np.finfo(float).eps, atol=0.0
    )

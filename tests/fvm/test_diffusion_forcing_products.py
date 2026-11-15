"""Keep boundary products scaled until the complete diffusion forcing exists."""

from fractions import Fraction
from math import ldexp

import numpy as np
import pytest

from scirel.fvm import CellVariable, make_diffusion_terms, theta_step


def _endpoint(width, side, kind, boundary):
    kwargs = {f"{side}_face_constraint": boundary, f"{side}_face_grad_constraint": None}
    if kind == "N":
        kwargs = {f"{side}_face_grad_constraint": boundary}
    return CellVariable([0.0, 0.0], [0.0, width, 2 * width], **kwargs)


def _exact_endpoint(width, diffusivity, boundary, kind, side):
    h, d, g = map(Fraction, (width, diffusivity, boundary))
    # A Dirichlet half-cell flux is +/-D*g/(h/2), then divided by h.
    # A Neumann flux is D*g; divergence reverses only the left-end sign.
    return 2 * d * g / h**2 if kind == "D" else (-1 if side == "left" else 1) * d * g / h


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("diffusion_sign", [-1, 0, 1])
@pytest.mark.parametrize("boundary_sign", [-1, 1])
@pytest.mark.parametrize(
    "h_exp,d_exp,g_exp",
    [
        pytest.param(500, 0, 100, id="normal-coefficient-control"),
        pytest.param(530, 0, 100, id="subnormal-coefficient"),
        pytest.param(540, 0, 100, id="coefficient-rounded-to-zero"),
        pytest.param(540, 0, 10, id="subnormal-complete-forcing"),
        pytest.param(-530, -1000, -1070, id="subnormal-boundary-control"),
        pytest.param(540, -20, 1020, id="large-boundary-small-coefficient"),
    ],
)
def test_complete_dirichlet_forcing_from_raw_fraction(
    side, diffusion_sign, boundary_sign, h_exp, d_exp, g_exp
):
    h = ldexp(1.0, h_exp)
    d = diffusion_sign * ldexp(1.0, d_exp)
    g = boundary_sign * ldexp(1.0, g_exp)
    var = _endpoint(h, side, "D", g)
    diffusion = np.zeros(3)
    index = 0 if side == "left" else -1
    diffusion[index] = d
    matrix, forcing = make_diffusion_terms(diffusion, var)
    expected = np.zeros(2)
    expected[index] = float(_exact_endpoint(h, d, g, "D", side))
    np.testing.assert_array_equal(forcing, expected)
    diagonal = np.zeros(2)
    diagonal[index] = -float(2 * Fraction(d) / Fraction(h) ** 2)
    np.testing.assert_array_equal(matrix.diagonal, diagonal)
    np.testing.assert_array_equal(matrix.above, [0.0])
    np.testing.assert_array_equal(matrix.below, [0.0])
    np.testing.assert_array_equal(var.value, [0.0, 0.0])


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("sign", [-1.0, 1.0])
@pytest.mark.parametrize("h_exp", [530, 540])
def test_nondyadic_quotient_forcing_keeps_the_strict_ulp_budget(side, sign, h_exp):
    h, d, g = ldexp(1.25, h_exp), sign * 1.5, ldexp(0.75, 100)
    diffusion = np.zeros(3)
    index = 0 if side == "left" else -1
    diffusion[index] = d
    matrix, forcing = make_diffusion_terms(diffusion, _endpoint(h, side, "D", g))
    expected = np.zeros(2)
    expected[index] = float(_exact_endpoint(h, d, g, "D", side))
    np.testing.assert_array_max_ulp(forcing, expected, maxulp=4)
    expected_diagonal = np.zeros(2)
    expected_diagonal[index] = -float(2 * Fraction(d) / Fraction(h) ** 2)
    np.testing.assert_array_max_ulp(matrix.diagonal, expected_diagonal, maxulp=4)


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("diffusion_sign", [-1, 1])
@pytest.mark.parametrize("gradient_sign", [-1, 1])
@pytest.mark.parametrize(
    "h_exp,d_exp,g_exp", [(500, 300, 300), (540, 600, 600), (-540, -600, -600)]
)
def test_complete_neumann_forcing_preserves_product_range(
    side, diffusion_sign, gradient_sign, h_exp, d_exp, g_exp
):
    h = ldexp(1.0, h_exp)
    d, g = diffusion_sign * ldexp(1.0, d_exp), gradient_sign * ldexp(1.0, g_exp)
    diffusion = np.zeros(3)
    index = 0 if side == "left" else -1
    diffusion[index] = d
    matrix, forcing = make_diffusion_terms(diffusion, _endpoint(h, side, "N", g))
    expected = np.zeros(2)
    expected[index] = float(_exact_endpoint(h, d, g, "N", side))
    np.testing.assert_array_equal(forcing, expected)
    np.testing.assert_array_equal(matrix.to_dense(), np.zeros((2, 2)))


@pytest.mark.parametrize("dirichlet_mode", ["ghost", "direct", "semi-implicit"])
@pytest.mark.parametrize("neumann_mode", ["ghost", "semi-implicit"])
@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("zero_convection", [False, True])
@pytest.mark.parametrize(
    "kind,h_exp,d_exp,g_exp,dt_exp",
    [
        ("D", 500, 0, 100, 500),
        ("D", 540, 0, 100, 540),
        ("N", 540, 600, 600, -660),
        ("N", -540, -600, -600, 660),
    ],
)
def test_six_legal_modes_keep_complete_forcing_in_the_theta_solution(
    dirichlet_mode, neumann_mode, side, zero_convection, kind, h_exp, d_exp, g_exp, dt_exp
):
    h, d, g, dt = (ldexp(1.0, exponent) for exponent in (h_exp, d_exp, g_exp, dt_exp))
    var = _endpoint(h, side, kind, g)
    diffusion = np.zeros(3)
    index = 0 if side == "left" else -1
    diffusion[index] = d
    kwargs = {"v_old": np.zeros(3), "v_new": np.zeros(3)} if zero_convection else {}
    result = theta_step(
        var,
        var,
        dt,
        d_new=diffusion,
        dirichlet_mode=dirichlet_mode,
        neumann_mode=neumann_mode,
        **kwargs,
    )
    forcing = _exact_endpoint(h, d, g, kind, side)
    denominator = 1 + Fraction(dt) * 2 * Fraction(d) / Fraction(h) ** 2 if kind == "D" else 1
    expected = np.zeros(2)
    expected[index] = float(Fraction(dt) * forcing / denominator)
    np.testing.assert_array_equal(result.value, expected)
    np.testing.assert_array_equal(var.value, [0.0, 0.0])


@pytest.mark.parametrize("side", ["left", "right"])
def test_zero_dirichlet_value_does_not_create_a_diffusivity_floor(side):
    matrix, forcing = make_diffusion_terms(
        [0.0, 0.0, 0.0], _endpoint(ldexp(1.0, -540), side, "D", 0.0)
    )
    np.testing.assert_array_equal(matrix.to_dense(), np.zeros((2, 2)))
    np.testing.assert_array_equal(forcing, [0.0, 0.0])


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("policy", ["warn", "ignore", "raise"])
@pytest.mark.parametrize(
    "kind,h_exp,d_exp,g_exp",
    [("D", -540, 0, None), ("D", 0, 0, 1023), ("N", -1, 1000, 1000)],
)
def test_unrepresentable_final_matrix_or_forcing_still_raises(
    side, policy, kind, h_exp, d_exp, g_exp
):
    h, d = ldexp(1.0, h_exp), ldexp(1.0, d_exp)
    g = 0.0 if g_exp is None else ldexp(1.0, g_exp)
    var = _endpoint(h, side, kind, g)
    diffusion = np.zeros(3)
    diffusion[0 if side == "left" else -1] = d
    with np.errstate(over=policy, invalid=policy, divide=policy):
        with pytest.raises(FloatingPointError):
            make_diffusion_terms(diffusion, var)
    np.testing.assert_array_equal(var.value, [0.0, 0.0])

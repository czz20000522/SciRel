"""Boundary diffusion must retain the original finite face-flux balance."""

from fractions import Fraction

import numpy as np
import pytest

from scirel.fvm import CellVariable, make_diffusion_terms, theta_step


def _dirichlet_variable(scale, values=(0.0, 0.0), left=1.0, right=1.0):
    return CellVariable(
        values,
        np.array([0.0, 1.0, 2.0]) * scale,
        left_face_constraint=left,
        right_face_constraint=right,
        left_face_grad_constraint=None,
        right_face_grad_constraint=None,
    )


@pytest.mark.parametrize("exponent", [-540, -200, 0, 200, 520])
@pytest.mark.parametrize("sign", [-1.0, 0.0, 1.0])
def test_common_scale_retains_exact_half_cell_flux_and_signed_matrix(exponent, sign):
    scale = np.ldexp(1.0, exponent)
    var = _dirichlet_variable(scale)
    matrix, forcing = make_diffusion_terms(np.full(3, sign * scale), var)
    # Oriented face fluxes are sign*(-2, 0, +2) for zero cell values.
    # For arbitrary u the two rows are sign/s*(-3*u0+u1+2, u0-3*u1+2).
    expected_matrix = (sign / scale) * np.array([[-3.0, 1.0], [1.0, -3.0]])
    expected_forcing = np.full(2, sign * np.ldexp(1.0, 1 - exponent))
    np.testing.assert_array_equal(matrix.to_dense(), expected_matrix)
    np.testing.assert_array_equal(forcing, expected_forcing)
    observed = matrix.matvec(var.value) + forcing
    np.testing.assert_array_equal(observed, expected_forcing)
    assert np.dot(var.cell_widths, observed) == 4.0 * sign
    state = np.array([0.25, -0.5])
    np.testing.assert_array_equal(
        (matrix.matvec(state) + forcing) * scale, sign * np.array([0.75, 3.75])
    )


def _fraction_residual(values, faces, diffusion, left, right):
    # Build the reference from oriented face fluxes, not production coefficients.
    f = [Fraction(float(x)) for x in faces]
    u = [Fraction(float(x)) for x in values]
    d = [Fraction(float(x)) for x in diffusion]
    widths = [b - a for a, b in zip(f, f[1:])]
    centers = [(a + b) / 2 for a, b in zip(f, f[1:])]
    flux = [d[0] * (u[0] - Fraction(float(left))) / (widths[0] / 2)]
    flux.extend(d[i] * (u[i] - u[i - 1]) / (centers[i] - centers[i - 1]) for i in range(1, len(u)))
    flux.append(d[-1] * (Fraction(float(right)) - u[-1]) / (widths[-1] / 2))
    return [(flux[i + 1] - flux[i]) / widths[i] for i in range(len(u))]


@pytest.mark.parametrize("exponent", [-540, 0, 520])
def test_nonuniform_boundary_assembly_matches_independent_fraction_flux(exponent):
    scale = np.ldexp(1.0, exponent)
    faces = np.array([0.0, 1.0, 3.0]) * scale
    diffusion = np.array([1.0, 2.0, 4.0]) * scale
    var = CellVariable(
        [0.25, -0.5],
        faces,
        left_face_constraint=1.0,
        right_face_constraint=-2.0,
        left_face_grad_constraint=None,
        right_face_grad_constraint=None,
    )
    matrix, forcing = make_diffusion_terms(diffusion, var)
    expected = _fraction_residual(var.value, faces, diffusion, 1.0, -2.0)
    expected_scaled = np.array([float(value * Fraction(float(scale))) for value in expected])
    observed = (matrix.matvec(var.value) + forcing) * scale
    np.testing.assert_allclose(observed, expected_scaled, rtol=2e-14, atol=2e-14)


@pytest.mark.parametrize("side", ["left", "right"])
def test_finite_dirichlet_coefficient_does_not_require_finite_twice_diffusivity(side):
    var = _dirichlet_variable(2.0)
    diffusion = np.zeros(3)
    diffusion[0 if side == "left" else -1] = 1.5e308
    matrix, forcing = make_diffusion_terms(diffusion, var)
    # 2*D/h**2 = D/2 is finite, although 2*D is not representable.
    expected = float(Fraction(float(1.5e308)) / 2)
    index = 0 if side == "left" else -1
    np.testing.assert_array_equal(matrix.diagonal[index], -expected)
    np.testing.assert_array_equal(forcing[index], expected)
    assert np.all(np.isfinite(matrix.diagonal))
    assert np.all(np.isfinite(forcing))


@pytest.mark.parametrize("exponent", [-540, 0, 520])
@pytest.mark.parametrize("theta", [0.0, 0.25, 0.5, 1.0])
def test_theta_downstream_retains_the_exact_dimensionless_two_cell_system(exponent, theta):
    scale = np.ldexp(1.0, exponent)
    var = _dirichlet_variable(scale)
    result = theta_step(
        var, var, scale, d_old=np.full(3, scale), d_new=np.full(3, scale), theta=theta
    )
    # Independently: C*s=[[-3,1],[1,-3]], b*s=[2,2], u_old=0.
    # Equal new values solve (1+2*theta)*u=2; theta=1 gives 2/3.
    expected = float(Fraction(2) / (1 + 2 * Fraction(float(theta))))
    np.testing.assert_allclose(result.value, [expected, expected], rtol=2e-14, atol=2e-15)
    np.testing.assert_array_equal(var.value, [0.0, 0.0])
    assert result.left_face_constraint == result.right_face_constraint == 1.0


@pytest.mark.parametrize("policy", ["warn", "ignore", "raise"])
@pytest.mark.parametrize("failure", ["coefficient", "forcing"])
def test_genuinely_unrepresentable_diffusion_outputs_still_fail(policy, failure):
    if failure == "coefficient":
        var = _dirichlet_variable(np.ldexp(1.0, -540))
        diffusion = [1.0, 0.0, 0.0]
    else:
        var = _dirichlet_variable(1.0, left=4.0)
        diffusion = [np.ldexp(1.0, 1022), 0.0, 0.0]
    with np.errstate(over=policy, invalid=policy, divide=policy):
        with pytest.raises(FloatingPointError):
            make_diffusion_terms(diffusion, var)
    np.testing.assert_array_equal(var.value, [0.0, 0.0])

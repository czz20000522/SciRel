"""Independent exact references for scale changes in the existing FVM rules."""

from fractions import Fraction as F
from math import ldexp

import numpy as np
import pytest

from scirel.fvm import CellVariable, make_convection_terms


def _q(value):
    return value if isinstance(value, F) else F.from_float(float(value))


def _quadratic_derivative(points, values, at):
    """Differentiate the three Lagrange basis polynomials in exact arithmetic."""
    points, values, at = list(map(_q, points)), list(map(_q, values)), _q(at)
    result = F(0)
    for i in range(3):
        j, k = [index for index in range(3) if index != i]
        result += (
            values[i]
            * (2 * at - points[j] - points[k])
            / ((points[i] - points[j]) * (points[i] - points[k]))
        )
    return result


def _face_derivatives(var):
    faces, u = list(map(_q, var.face_centers)), list(map(_q, var.value))
    centers = [(a + b) / 2 for a, b in zip(faces[:-1], faces[1:])]
    exact = [
        _q(var.left_face_grad_constraint)
        if var.left_face_constraint is None
        else (_q(u[0]) - _q(var.left_face_constraint)) / ((_q(faces[1]) - _q(faces[0])) / 2)
    ]
    for j in range(1, len(u)):
        if j < len(u) - 1:
            exact.append(_quadratic_derivative(centers[j - 1 : j + 2], u[j - 1 : j + 2], faces[j]))
        elif var.right_face_constraint is not None:
            exact.append(
                _quadratic_derivative(
                    [*centers[-2:], faces[-1]], [*u[-2:], var.right_face_constraint], faces[j]
                )
            )
        else:
            a, b, at = _q(centers[-2]), _q(centers[-1]), _q(faces[j])
            edge, g = _q(faces[-1]), _q(var.right_face_grad_constraint)
            slope = (_q(u[-1]) - _q(u[-2])) / (b - a)
            exact.append(slope + (g - slope) * (2 * at - a - b) / (2 * edge - a - b))
    exact.append(
        _q(var.right_face_grad_constraint)
        if var.right_face_constraint is None
        else (_q(var.right_face_constraint) - _q(u[-1])) / ((_q(faces[-1]) - _q(faces[-2])) / 2)
    )
    return exact


def _alpha(p):
    if abs(p) <= _q(0.001):
        return F(1, 2)
    attenuation = max(F(0), 1 - abs(p) / 10) ** 5
    return 1 - (1 - attenuation) / p if p > 0 else -(1 - attenuation) / p


def _zero_gradient_convection(var, velocity, diffusion):
    """One oriented flux per face; zero endpoint gradients imply endpoint u."""
    h = [_q(b) - _q(a) for a, b in zip(var.face_centers[:-1], var.face_centers[1:])]
    faces = list(map(_q, var.face_centers))
    centers = [(a + b) / 2 for a, b in zip(faces[:-1], faces[1:])]
    u, v, d = list(map(_q, var.value)), list(map(_q, velocity)), list(map(_q, diffusion))
    flux = [v[0] * u[0]]
    for j in range(1, len(u)):
        scale = max(abs(d[j]), _q(1e-20)) * (-1 if d[j] < 0 else 1)
        p = (centers[j] - centers[j - 1]) * v[j] / scale
        a = _alpha(p)
        flux.append(v[j] * (a * u[j - 1] + (1 - a) * u[j]))
    flux.append(v[-1] * u[-1])
    return [(flux[j] - flux[j + 1]) / h[j] for j in range(len(u))]


def _boundary_convection(var, velocity, diffusion, dirichlet_mode, neumann_mode):
    faces, u = list(map(_q, var.face_centers)), list(map(_q, var.value))
    h = [b - a for a, b in zip(faces[:-1], faces[1:])]
    centers = [(a + b) / 2 for a, b in zip(faces[:-1], faces[1:])]
    distances = [h[0] / 2, centers[1] - centers[0], h[-1] / 2]
    flux = []
    for j in range(3):
        v, d = _q(velocity[j]), _q(diffusion[j])
        scale = max(abs(d), _q(1e-20)) * (-1 if d < 0 else 1)
        a = _alpha(distances[j] * v / scale)
        if j == 1:
            ul, ur = u
        else:
            side, edge = ("left", 0) if j == 0 else ("right", -1)
            value = getattr(var, f"{side}_face_constraint")
            if value is not None:
                if dirichlet_mode == "direct":
                    flux.append(v * _q(value))
                    continue
                outside = 2 * _q(value) - u[edge] if dirichlet_mode == "ghost" else _q(value)
            else:
                gradient = _q(getattr(var, f"{side}_face_grad_constraint"))
                distance = h[edge] if neumann_mode == "ghost" else h[edge] / 2
                outside = u[edge] + (-1 if j == 0 else 1) * gradient * distance
            ul, ur = (outside, u[edge]) if j == 0 else (u[edge], outside)
        flux.append(v * (a * ul + (1 - a) * ur))
    return [(flux[j] - flux[j + 1]) / h[j] for j in range(2)]


@pytest.mark.parametrize("exponent", (0, 512), ids=("ordinary", "squared-coordinate-overflow"))
def test_affine_face_gradient_retains_unit_derivative(exponent):
    s = ldexp(1.0, exponent)
    var = CellVariable(
        [s / 2, 3 * s / 2],
        [0.0, s, 2 * s],
        left_face_grad_constraint=1.0,
        right_face_constraint=2 * s,
        right_face_grad_constraint=None,
    )
    np.testing.assert_array_equal(var.face_grad(), [1.0, 1.0, 1.0])


@pytest.mark.parametrize("exponent", (0, 512), ids=("ordinary", "peclet-product-overflow"))
def test_convection_retains_finite_peclet_after_scaling(exponent):
    s = ldexp(1.0, exponent)
    var = CellVariable([1.0, 0.0], [0.0, s, 2 * s])
    matrix, offset = make_convection_terms([s] * 3, [ldexp(1.0, 2 * exponent - 1)] * 3, var)
    # Exact p=2, A=(1-2/10)^5=1024/3125, alpha=4149/6250.
    np.testing.assert_allclose(
        matrix.matvec(var.value) + offset, [2101 / 6250, 4149 / 6250], rtol=2e-14, atol=2e-15
    )


@pytest.mark.parametrize("exponent", (-540, 0, 512))
@pytest.mark.parametrize("faces", ([0.0, 0.25, 1.0], [0.0, 0.125, 0.5, 1.25, 2.25]))
@pytest.mark.parametrize("right_kind", ("dirichlet", "neumann"))
@pytest.mark.parametrize("quadratic", (False, True))
def test_face_gradient_scaled_nonuniform_exact_polynomial(exponent, faces, right_kind, quadratic):
    s = ldexp(1.0, exponent)
    faces = np.asarray(faces)
    centers = faces[:-1] + np.diff(faces) / 2
    samples = centers * centers - 3 * centers + 2 if quadratic else centers
    left_gradient = -3 / s if quadratic else 1 / s
    right_gradient = (2 * faces[-1] - 3) / s if quadratic else 1 / s
    right_value = faces[-1] ** 2 - 3 * faces[-1] + 2 if quadratic else faces[-1]
    var = CellVariable(
        samples,
        np.ldexp(faces, exponent),
        left_face_grad_constraint=left_gradient,
        right_face_constraint=right_value if right_kind == "dirichlet" else None,
        right_face_grad_constraint=None if right_kind == "dirichlet" else right_gradient,
    )
    expected = np.asarray([float(value * _q(s)) for value in _face_derivatives(var)])
    # Scale the derivative back to O(1), so a fixed atol cannot hide tiny wrong outputs.
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        observed = np.ldexp(var.face_grad(), exponent)
    np.testing.assert_allclose(observed, expected, rtol=2e-13, atol=2e-14)


@pytest.mark.parametrize(
    "coordinate_exp,velocity_exp,diffusion_exp",
    ((0, 0, -1), (512, 512, 1023), (-540, -540, None), (512, -512, None)),
)
@pytest.mark.parametrize("sign", (-1, 0, 1))
@pytest.mark.parametrize("faces", ([0.0, 1.0, 2.0], [0.0, 0.125, 0.5, 1.25, 2.25]))
def test_convection_scaled_flux_matches_exact_ratio(
    coordinate_exp, velocity_exp, diffusion_exp, sign, faces
):
    faces = np.asarray(faces)
    n = len(faces) - 1
    values = [1.0, 0.0, -0.5, 0.25][:n]
    speed = sign * ldexp(1.0, velocity_exp)
    velocity = [speed] * (n + 1)
    diffusion = [0.0 if diffusion_exp is None else ldexp(1.0, diffusion_exp)] * (n + 1)
    var = CellVariable(values, np.ldexp(faces, coordinate_exp))
    exact = _zero_gradient_convection(var, velocity, diffusion)
    factor = F(2) ** (coordinate_exp - velocity_exp)
    expected = [float(value * factor) for value in exact]
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        matrix, offset = make_convection_terms(velocity, diffusion, var)
        observed = np.ldexp(matrix.matvec(var.value) + offset, coordinate_exp - velocity_exp)
    np.testing.assert_allclose(observed, expected, rtol=2e-14, atol=2e-15)


@pytest.mark.parametrize("sign", (-1, 1))
def test_true_peclet_overflow_keeps_signed_upwind_limit(sign):
    speed = sign * ldexp(1.0, 1000)
    var = CellVariable([1.0, 0.0], [0.0, 1.0, 2.0])
    matrix, offset = make_convection_terms([speed] * 3, [0.0] * 3, var)
    exact = _zero_gradient_convection(var, [speed] * 3, [0.0] * 3)
    np.testing.assert_allclose(
        (matrix.matvec(var.value) + offset) / abs(speed),
        [float(value / _q(abs(speed))) for value in exact],
        rtol=2e-14,
        atol=2e-15,
    )


@pytest.mark.parametrize(
    "p",
    (
        0.0,
        0.001,
        np.nextafter(0.001, 0.0),
        np.nextafter(0.001, np.inf),
        -0.001,
        np.nextafter(-0.001, -np.inf),
        10.0,
        np.nextafter(10.0, np.inf),
        -10.0,
        np.nextafter(-10.0, -np.inf),
    ),
)
def test_peclet_threshold_choices_keep_the_existing_exact_rule(p):
    var = CellVariable([1.0, 0.0], [0.0, 1.0, 2.0])
    velocity, diffusion = [p] * 3, [1.0] * 3
    matrix, offset = make_convection_terms(velocity, diffusion, var)
    np.testing.assert_allclose(
        matrix.matvec(var.value) + offset,
        list(map(float, _zero_gradient_convection(var, velocity, diffusion))),
        rtol=2e-14,
        atol=2e-15,
    )


@pytest.mark.parametrize("diffusion", (-1.0, -1e-22, 0.0, 1e-22))
def test_signed_diffusion_floor_keeps_its_existing_exact_rule(diffusion):
    var = CellVariable([1.0, 0.0], [0.0, 0.25, 1.0])
    velocity, diffusion = [-0.5, 0.75, -0.25], [diffusion] * 3
    matrix, offset = make_convection_terms(velocity, diffusion, var)
    np.testing.assert_allclose(
        matrix.matvec(var.value) + offset,
        list(map(float, _zero_gradient_convection(var, velocity, diffusion))),
        rtol=2e-14,
        atol=2e-15,
    )


BOUNDARY_MODES = [
    (pattern, dmode, nmode)
    for pattern in ("DD", "DN", "ND", "NN")
    for dmode in (("ghost", "direct", "semi-implicit") if "D" in pattern else ("ghost",))
    for nmode in (("ghost", "semi-implicit") if "N" in pattern else ("ghost",))
]


@pytest.mark.parametrize("pattern,dmode,nmode", BOUNDARY_MODES)
@pytest.mark.parametrize("exponent", (0, 512))
@pytest.mark.parametrize("sign", (-1, 1))
def test_scaled_convection_keeps_every_boundary_flux_mode(pattern, dmode, nmode, exponent, sign):
    s = ldexp(1.0, exponent)
    kwargs = {}
    for side, kind, value, gradient in zip(
        ("left", "right"), pattern, (0.75, -1.25), (-0.5 / s, 0.25 / s)
    ):
        kwargs[f"{side}_face_constraint"] = value if kind == "D" else None
        kwargs[f"{side}_face_grad_constraint"] = gradient if kind == "N" else None
    var = CellVariable([0.25, -0.5], [0.0, s, 2 * s], **kwargs)
    velocity, diffusion = [sign * s] * 3, [ldexp(1.0, 2 * exponent - 1)] * 3
    expected = _boundary_convection(var, velocity, diffusion, dmode, nmode)
    matrix, offset = make_convection_terms(velocity, diffusion, var, dmode, nmode)
    np.testing.assert_allclose(
        matrix.matvec(var.value) + offset, list(map(float, expected)), rtol=2e-14, atol=2e-15
    )


@pytest.mark.parametrize("policy", ("warn", "ignore", "raise"))
def test_genuinely_nonrepresentable_derivative_and_operator_raise(policy):
    tiny = ldexp(1.0, -540)
    var = CellVariable([0.0, ldexp(1.0, 600)], [0.0, tiny, 2 * tiny])
    with np.errstate(over=policy, invalid=policy, divide=policy):
        with pytest.raises(FloatingPointError):
            var.face_grad()
        with pytest.raises(FloatingPointError):
            make_convection_terms([ldexp(1.0, 600)] * 3, [0.0] * 3, var)


@pytest.mark.parametrize("policy", ("warn", "ignore", "raise"))
@pytest.mark.parametrize("exponent", (0, 1023), ids=("ordinary", "secant-overflow"))
@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("ends", ("DD", "DN", "ND", "NN"))
def test_weighted_secant_retains_finite_large_sample_gradient(policy, exponent, sign, ends):
    amplitude = sign * ldexp(1.5, exponent)
    kwargs = {}
    for side, kind, value in zip(("left", "right"), ends, (0.0, amplitude)):
        if kind == "D":
            kwargs[f"{side}_face_constraint"] = value
            kwargs[f"{side}_face_grad_constraint"] = None
    var = CellVariable([0.0, amplitude, amplitude], [0.0, 1.0, 1.125, 1.25], **kwargs)
    exact = _face_derivatives(var)
    # Raw Lagrange differentiation gives 64*A/99, although the first
    # unweighted secant is 16*A/9 and exceeds binary64 at the large amplitude.
    assert exact == [F(0), F(64, 99) * _q(amplitude), F(0), F(0)]
    with np.errstate(over=policy, invalid=policy, divide=policy):
        observed = var.face_grad()
    np.testing.assert_allclose(observed / amplitude, [0.0, 64 / 99, 0.0, 0.0], rtol=2e-14, atol=0)


@pytest.mark.parametrize("policy", ("warn", "ignore", "raise"))
@pytest.mark.parametrize("exponent", (0, 1023), ids=("ordinary", "unused-secant-overflow"))
@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("left_kind", ("D", "N"))
def test_zero_weight_does_not_materialize_unused_secant(policy, exponent, sign, left_kind):
    amplitude = sign * ldexp(1.5, exponent)
    kwargs = {}
    if left_kind == "D":
        kwargs = {"left_face_constraint": 0.0, "left_face_grad_constraint": None}
    var = CellVariable(
        [0.0, 0.0, amplitude],
        [0.0, 1.0, 2.0, 2.5],
        right_face_constraint=amplitude,
        right_face_grad_constraint=None,
        **kwargs,
    )
    exact = _face_derivatives(var)
    assert exact == [F(0), F(0), _q(amplitude), F(0)]
    with np.errstate(over=policy, invalid=policy, divide=policy):
        observed = var.face_grad()
    np.testing.assert_array_equal(observed, list(map(float, exact)))


@pytest.mark.parametrize("sign", (-1, 1))
@pytest.mark.parametrize("coordinate_exponent", (2, 512))
def test_weighted_gradient_retains_sample_difference_scale(sign, coordinate_exponent):
    amplitude = sign * ldexp(1.5, 1023)
    var = CellVariable(
        [amplitude, -amplitude, -amplitude],
        np.ldexp([0.0, 1.0, 1.125, 1.25], coordinate_exponent),
        right_face_constraint=-amplitude,
        right_face_grad_constraint=None,
    )
    exact = _face_derivatives(var)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        observed = var.face_grad()
    np.testing.assert_allclose(observed, list(map(float, exact)), rtol=2e-14, atol=0)


@pytest.mark.parametrize("sign", (-1, 1))
def test_weighted_gradient_rounds_subnormal_only_after_weighting(sign):
    tiny = sign * ldexp(1.0, -1074)
    var = CellVariable(
        [0.0, tiny],
        [0.0, 1.0, 4.0],
        right_face_constraint=tiny,
        right_face_grad_constraint=None,
    )
    exact = _face_derivatives(var)
    assert exact == [F(0), F(9, 14) * _q(tiny), F(0)]
    # The first secant tiny/2 rounds to zero; its weight 9/7 rescues a subnormal.
    np.testing.assert_array_equal(var.face_grad(), [0.0, tiny, 0.0])


@pytest.mark.parametrize("sign", (-1, 1))
def test_weighted_gradient_retains_underflowing_coordinate_weight(sign):
    tiny, amplitude = ldexp(1.0, -1074), sign * ldexp(1.5, 1023)
    var = CellVariable([0.0, 0.0, amplitude], [0.0, 4 * tiny, 6 * tiny, 8.0])
    exact = _face_derivatives(var)
    # The weight at face 1 is below the smallest subnormal, but multiplying
    # the large last secant produces a finite nonzero derivative.
    assert 0 < abs(exact[1]) < 1
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        observed = var.face_grad()
    np.testing.assert_allclose(observed, list(map(float, exact)), rtol=2e-14, atol=0)


@pytest.mark.parametrize("sign", (-1, 1))
def test_weighted_gradient_combines_opposing_unrepresentable_contributions(sign):
    amplitude = sign * ldexp(1.5, 1023)
    last = float(-F(171, 16384) * _q(amplitude))
    var = CellVariable(
        [0.0, amplitude, last],
        [0.0, 1 / 8, 3 / 16, 385 / 2048],
        right_face_constraint=last,
        right_face_grad_constraint=None,
    )
    exact = _face_derivatives(var)
    assert exact == [F(0), F(0), -F(77, 104) * _q(amplitude), F(0)]
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        observed = var.face_grad()
    # Each contribution at face 1 exceeds fmax; they must be added before
    # restoring their scale. Absolute error is measured in units of amplitude.
    np.testing.assert_allclose(
        observed / amplitude,
        [float(value / _q(amplitude)) for value in exact],
        rtol=2e-14,
        atol=2e-14,
    )


@pytest.mark.parametrize("sign", (-1, 1))
def test_weighted_gradient_preserves_mask_and_endpoint_rules(sign):
    amplitude = sign * ldexp(1.5, 1023)
    var = CellVariable(
        [0.0, amplitude, amplitude],
        [0.0, 4.0, 4.5, 5.0],
        left_face_constraint=amplitude / 4,
        left_face_grad_constraint=None,
        right_face_constraint=amplitude * (7 / 8),
        right_face_grad_constraint=None,
    )
    exact = _face_derivatives(var)
    exact[1] = (_q(amplitude) - 0) / F(9, 4)
    mask = [True, True, False, True]
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        observed = var.face_grad(two_point_mask=mask)
    np.testing.assert_allclose(observed, list(map(float, exact)), rtol=2e-14, atol=0)


@pytest.mark.parametrize("policy", ("warn", "ignore", "raise"))
def test_scaled_quadratic_still_rejects_genuinely_unrepresentable_result(policy):
    tiny = ldexp(1.0, -540)
    var = CellVariable(
        [0.0, ldexp(1.0, 600)],
        [0.0, tiny, 2 * tiny],
        right_face_constraint=ldexp(1.0, 600),
        right_face_grad_constraint=None,
    )
    with np.errstate(over=policy, invalid=policy, divide=policy):
        with pytest.raises(FloatingPointError):
            var.face_grad()

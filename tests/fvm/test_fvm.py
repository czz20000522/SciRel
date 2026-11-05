import pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import numpy as np
import pytest
from scirel.fvm import (
    CellVariable,
    TriDiagonal,
    make_diffusion_terms,
    make_convection_terms,
    theta_step,
)


def test_invalid_grid_rejected():
    with pytest.raises(ValueError):
        CellVariable([1], [0, 1])
    with pytest.raises(ValueError):
        CellVariable([1, 2], [0, 1, 1])
    with pytest.raises(ValueError):
        CellVariable([1, 2], [0, 1, 2], left_face_constraint=0, left_face_grad_constraint=0)


def test_nonuniform_linear_diffusion_zero_residual_and_conservation():
    f = np.array([0.0, 0.1, 0.4, 1.0])
    c = (f[:-1] + f[1:]) / 2
    u = c.copy()
    var = CellVariable(u, f, left_face_grad_constraint=1, right_face_grad_constraint=1)
    m, b = make_diffusion_terms(np.ones(4), var)
    np.testing.assert_allclose(m.to_dense() @ u + b, 0, atol=2e-13)
    rng = np.random.default_rng(4)
    u = rng.normal(size=3)
    var = CellVariable(u, f, left_face_grad_constraint=0, right_face_grad_constraint=0)
    m, b = make_diffusion_terms(np.array([0.4, 1.2, 0.7, 2.0]), var)
    r = m.to_dense() @ u + b
    np.testing.assert_allclose(
        np.dot(r, var.cell_widths), 2 * u[-1] * 0, atol=1e-13
    )  # zero net Neumann flux


def test_nonuniform_constant_convection_is_conservative():
    f = np.array([0.0, 0.1, 0.4, 1.0])
    var = CellVariable(np.ones(3), f, left_face_grad_constraint=0, right_face_grad_constraint=0)
    m, b = make_convection_terms(np.full(4, 2.0), np.zeros(4), var)
    np.testing.assert_allclose(m.to_dense() @ var.value + b, 0, atol=1e-12)


def test_overflow_peclet_is_finite_upwind_limit():
    var = CellVariable(np.ones(2), [0, 1, 2])
    m, b = make_convection_terms(np.full(3, 1e300), np.zeros(3), var)
    assert np.isfinite(m.to_dense()).all() and np.isfinite(b).all()
    np.testing.assert_allclose(m.to_dense() @ var.value + b, 0, atol=0)


def test_theta_constant_source():
    old = CellVariable(
        [0.0, 0.0], [0, 1, 2], left_face_grad_constraint=0, right_face_grad_constraint=0
    )
    new = theta_step(old, old, 0.2, source_old=np.ones(2), source_new=np.ones(2), theta=0.5)
    np.testing.assert_allclose(new.value, 0.2)


def test_theta_constant_profile_diffusion_preserved():
    old = CellVariable(
        [3.0, 3.0, 3.0],
        [0, 0.1, 0.4, 1.0],
        left_face_grad_constraint=0,
        right_face_grad_constraint=0,
    )
    new = theta_step(old, old, 0.7, d_old=np.ones(4), d_new=np.ones(4), theta=0.5)
    np.testing.assert_allclose(new.value, 3.0)


def test_diffusion_boundary_flux_conservation_nonzero():
    f = np.array([0.0, 0.1, 0.35, 0.7, 1.0])
    c = (f[:-1] + f[1:]) / 2
    u = np.array([0.4, -0.2, 0.9, 1.1])
    d = np.array([0.2, 0.8, 1.0, 0.4, 0.7])
    var = CellVariable(u, f, left_face_grad_constraint=0.3, right_face_grad_constraint=-0.2)
    m, b = make_diffusion_terms(d, var)
    flux = np.r_[d[0] * 0.3, d[1:-1] * np.diff(u) / np.diff(c), d[-1] * (-0.2)]
    np.testing.assert_allclose(m.matvec(u) + b, np.diff(flux) / np.diff(f), rtol=2e-14, atol=2e-14)
    np.testing.assert_allclose(
        np.dot(var.cell_widths, m.matvec(u) + b), flux[-1] - flux[0], rtol=2e-14, atol=2e-14
    )


def test_manufactured_diffusion_second_order_uniform():
    errors = []
    for n in (16, 32, 64):
        f = np.linspace(0.0, 1.0, n + 1)
        c = (f[:-1] + f[1:]) / 2
        v = CellVariable(
            np.zeros(n),
            f,
            left_face_constraint=0.0,
            left_face_grad_constraint=None,
            right_face_constraint=0.0,
            right_face_grad_constraint=None,
        )
        m, b = make_diffusion_terms(np.ones(n + 1), v)
        sol = np.linalg.solve(m.to_dense(), -b - np.pi**2 * np.sin(np.pi * c))
        errors.append(np.max(np.abs(sol - np.sin(np.pi * c))))
    assert errors[0] / errors[1] > 3.8
    assert errors[1] / errors[2] > 3.8


def test_theta_old_new_boundary_causality():
    old = CellVariable(np.zeros(4), np.linspace(0.0, 1.0, 5))
    new = CellVariable(
        np.zeros(4), old.face_centers, right_face_constraint=1.0, right_face_grad_constraint=None
    )
    x = theta_step(old, new, 0.02, d_old=np.ones(5), d_new=np.ones(5), theta=0.0)
    np.testing.assert_array_equal(x.value, 0.0)
    assert x.right_face_constraint == 1.0
    x = theta_step(old, new, 0.02, d_old=np.ones(5), d_new=np.ones(5), theta=1.0)
    assert np.all(x.value > 0.0)


def test_convection_manufactured_quadratic_upwind_first_order():
    # For v=1, D=0 and u=x^2, -d(vu)/dx=-2x. Compare inner cells,
    # whose face flux is exactly the upstream point value in the limit.
    errors = []
    for n in (16, 32, 64):
        f = np.linspace(0.0, 1.0, n + 1)
        c = (f[:-1] + f[1:]) / 2
        v = CellVariable(c * c, f)
        m, b = make_convection_terms(np.ones(n + 1), np.zeros(n + 1), v)
        observed = m.matvec(v.value) + b
        errors.append(np.max(np.abs(observed[1:-1] + 2 * c[1:-1])))
    np.testing.assert_allclose(errors, [1 / 16, 1 / 32, 1 / 64], rtol=3e-13, atol=2e-14)


def test_theta_singular_system_failure_and_linear_ode():
    # Diffusion eigenmode [1,-1] under zero Neumann has eigenvalue -2.
    v = CellVariable([1.0, -1.0], [0.0, 1.0, 2.0])
    for theta in (0.0, 0.5, 1.0):
        x = theta_step(v, v, 0.1, d_old=np.ones(3), d_new=np.ones(3), theta=theta)
        ratio = (1 - 0.2 * (1 - theta)) / (1 + 0.2 * theta)
        np.testing.assert_allclose(x.value, ratio * v.value, rtol=2e-14, atol=2e-15)
    # Signed anti-diffusion at dt=.5 makes I-dt*C singular.
    with pytest.raises(np.linalg.LinAlgError):
        theta_step(v, v, 0.5, d_new=-np.ones(3))


def test_tridiagonal_theta_step_does_not_materialize_dense_operator(monkeypatch):
    old = CellVariable(
        np.ones(2000),
        np.linspace(0.0, 1.0, 2001),
        left_face_grad_constraint=0,
        right_face_grad_constraint=0,
    )

    def fail_to_dense(self):
        raise AssertionError("theta_step unexpectedly materialized a dense matrix")

    monkeypatch.setattr(TriDiagonal, "to_dense", fail_to_dense)
    new = theta_step(old, old, 0.01, d_new=np.ones(2001), theta=1.0)
    np.testing.assert_allclose(new.value, old.value)


def test_fvm_malformed_and_nonfinite_inputs_fail():
    with pytest.raises(ValueError):
        CellVariable([1.0, np.nan], [0.0, 1.0, 2.0])
    with pytest.raises(ValueError):
        CellVariable(np.ma.array([1.0, 2.0], mask=[0, 1]), [0.0, 1.0, 2.0])
    with pytest.raises(TypeError):
        CellVariable([1j, 2j], [0.0, 1.0, 2.0])
    v = CellVariable([0.0, 0.0], [0.0, 1.0, 2.0])
    with pytest.raises(TypeError):
        theta_step(v, v, "0.1")
    with pytest.raises(TypeError):
        theta_step(v, v, 0.1, source_new=[True, False])
    with pytest.raises(ValueError):
        make_convection_terms([1.0, 1.0, 1.0], [1.0, 1.0, 1.0], v, dirichlet_mode="wrong")
    with pytest.raises(FloatingPointError):
        make_diffusion_terms([1e308, 1e308, 1e308], CellVariable([1.0, 1.0], [0.0, 0.01, 0.02]))


@pytest.mark.parametrize(
    "faces",
    [
        [0.0, 0.1, 0.4, 1.0],  # independent failure: unequal terminal widths
        [0.0, 0.2, 0.6, 1.0],  # original passing example: equal terminal widths
        [0.0, 0.1, 1.0],  # N=2, the sole internal face needs the boundary derivative
        [0.0, 0.8, 1.0],
        [0.0, 1.0, 2.0, 3.0],
    ],
)
@pytest.mark.parametrize(
    "coefficients", [(1.0, 0.0, 0.0), (0.0, -3.0, 2.0), (0.0, 0.0, 7.0), (-2.0, 3.0, 0.5)]
)
def test_face_grad_neumann_polynomial_exactness(faces, coefficients):
    f = np.asarray(faces)
    c = (f[:-1] + f[1:]) / 2
    a, b, d = coefficients
    v = CellVariable(
        a * c * c + b * c + d,
        f,
        left_face_grad_constraint=2 * a * f[0] + b,
        right_face_grad_constraint=2 * a * f[-1] + b,
    )
    np.testing.assert_allclose(v.face_grad(), 2 * a * f + b, rtol=2e-13, atol=2e-14)


def test_face_grad_dirichlet_mask_and_face_value_contracts():
    f = np.array([0.0, 0.1, 0.4, 1.0])
    c = (f[:-1] + f[1:]) / 2
    n = CellVariable(c * c, f, left_face_grad_constraint=0.0, right_face_grad_constraint=2.0)
    d = CellVariable(
        c * c,
        f,
        left_face_constraint=0.0,
        left_face_grad_constraint=None,
        right_face_constraint=1.0,
        right_face_grad_constraint=None,
    )
    np.testing.assert_allclose(d.face_grad()[1:-1], 2 * f[1:-1], rtol=2e-13, atol=2e-14)
    np.testing.assert_allclose(d.face_grad()[[0, -1]], [c[0], 1 + c[-1]], rtol=2e-13, atol=2e-14)
    mask = np.array([True, False, True, True])
    np.testing.assert_allclose(
        n.face_grad(two_point_mask=mask),
        [0.0, 0.2, (c[-1] ** 2 - c[-2] ** 2) / (c[-1] - c[-2]), 2.0],
        rtol=2e-13,
        atol=2e-14,
    )
    # Face values retain the declared linear boundary extrapolation; this repair
    # applies only to the unmasked last internal face derivative.
    assert n.right_face_value == n.value[-1] + 2 * np.diff(f)[-1] / 2
    for invalid in ([0, 1, 1, 0], [True, False], True):
        with pytest.raises(ValueError):
            n.face_grad(two_point_mask=invalid)

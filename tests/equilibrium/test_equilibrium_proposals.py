"""Pass-after checks for the private D2 proposal modules."""

from __future__ import annotations

import importlib

import numpy as np


def load(name):
    module_name = {
        "equilibrium": "scirel.equilibrium",
        "fieldline": "scirel.geometry.fieldline",
        "numerics": "scirel.geometry.numerics",
    }[name]
    return importlib.import_module(module_name)


def test_nonuniform_quadratic_and_duplicate_rejection():
    m = load("numerics")
    x = np.array([0.0, 0.5, 1.7, 4.0])
    first, second = m.diff_12_central(x, 3 * x * x - 2 * x + 7)
    np.testing.assert_allclose(first, 6 * x[1:-1] - 2, rtol=1e-13, atol=1e-13)
    np.testing.assert_allclose(second, 6.0, rtol=1e-13, atol=1e-13)
    try:
        m.diff_12_central([0.0, 1.0, 1.0], [0.0, 1.0, 1.0])
    except m.NumericalContractError:
        pass
    else:
        raise AssertionError("duplicate abscissae were accepted")


def test_arclength_quadratic_on_nonuniform_vertices():
    m = load("fieldline")
    x = np.array([0.0, 0.25, 1.0, 2.0, 4.0])
    vertices = np.c_[x, np.zeros_like(x)]
    s = np.r_[0.0, np.cumsum(np.diff(x))]
    np.testing.assert_allclose(m.d_ds_arclength(vertices, s * s), 2 * s, rtol=1e-13, atol=1e-13)


def test_equilibrium_terminal_contract():
    m = load("equilibrium")
    R = np.tile(np.arange(1.0, 6.0), (2, 1))
    Z = np.tile(np.array([-1.0, 0.0])[:, None], (1, 5))
    psi = R.copy()
    g = np.zeros((10, 10))
    result = m.compute_equilibrium(R, Z, lambda r: 5.0 - r, psi, g)
    assert result.status == "converged"
    assert result.iterations == 1
    assert result.residual == 0.0
    capped = m.compute_equilibrium(R, Z, lambda r: 5.0 - r, psi, g, maxiter=0)
    assert capped.status == "maxiter"
    assert capped.iterations == 0
    assert capped.reason == "iteration bound reached"


def test_equilibrium_current_uses_pressure_derivative():
    m = load("equilibrium")
    R = np.tile(np.arange(1.0, 6.0), (2, 1))
    Z = np.tile(np.array([-1.0, 0.0])[:, None], (1, 5))
    # psi=R, P=5-R => dP/dpsi=-1; dr=dz=1, so I=-R.
    result = m.compute_equilibrium(R, Z, lambda r: 5.0 - r, R, np.zeros((10, 10)))
    np.testing.assert_allclose(result.plas_currents, -R, rtol=1e-12, atol=1e-12)


def test_equilibrium_nonzero_feedback_and_relaxation_order():
    m = load("equilibrium")
    R = np.tile(np.arange(1.0, 6.0), (2, 1))
    Z = np.tile(np.array([-1.0, 0.0])[:, None], (1, 5))
    # Constant rank-one Green map: sum(-R)=-30, so flux shift=-0.1.
    # A uniform shift preserves dP/dpsi=-1. The second update is stationary.
    g = np.full((10, 10), 1.0 / 300.0)
    result = m.compute_equilibrium(R, Z, lambda r: 5.0 - r, R, g)
    assert result.status == "converged"
    assert result.iterations == 2
    np.testing.assert_allclose(result.psi, R - 0.1, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(result.plas_currents, -R, rtol=1e-12, atol=1e-12)
    assert result.residual <= 1e-12
    capped = m.compute_equilibrium(R, Z, lambda r: 5.0 - r, R, g, relax=0.5, maxiter=2)
    assert capped.status == "maxiter"
    assert capped.iterations == 2
    np.testing.assert_allclose(capped.plas_currents, -0.75 * R, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(capped.psi, R - 0.075, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(capped.residual, np.sqrt(10) * 0.025 / 4.925, rtol=1e-11, atol=1e-13)


def test_equilibrium_mask_and_nonfinite_terminal_state():
    m = load("equilibrium")
    R = np.tile(np.arange(1.0, 6.0), (2, 1))
    Z = np.tile(np.array([-1.0, 0.0])[:, None], (1, 5))
    mask = np.zeros_like(R, dtype=bool)
    mask[:, 2] = True
    result = m.compute_equilibrium(R, Z, lambda r: 5.0 - r, R, np.zeros((10, 10)), plas_clip=mask)
    expected = -R.copy()
    expected[mask] = 0.0
    np.testing.assert_allclose(result.plas_currents, expected, rtol=1e-12, atol=1e-12)
    decreasing = m.compute_equilibrium(R, Z, lambda r: 5.0 - r, -R, np.zeros((10, 10)))
    assert decreasing.status == "nonfinite"
    assert decreasing.iterations == 0
    assert decreasing.p_psifit is None
    assert "strictly increasing" in decreasing.reason


def test_derivative_failure_boundaries_and_reversal():
    numeric = load("numerics")
    field = load("fieldline")
    for x, y in [([0, 1], [0, 1]), ([0, 1, 2], [0, np.nan, 4]), ([2, 1, 0], [4, 1, 0])]:
        try:
            numeric.diff_12_central(x, y)
        except numeric.NumericalContractError:
            pass
        else:
            raise AssertionError("invalid derivative input accepted")
    vertices = np.c_[[0.0, 0.25, 1.0, 2.0, 4.0], np.zeros(5)]
    values = vertices[:, 0] ** 2
    np.testing.assert_allclose(
        field.d_ds_arclength(vertices[::-1], values[::-1]),
        -2 * vertices[::-1, 0],
        rtol=1e-13,
        atol=1e-13,
    )
    for vertices, values in [
        (np.zeros((3, 2)), np.arange(3.0)),
        (np.zeros((2, 2)), np.arange(2.0)),
    ]:
        try:
            field.d_ds_arclength(vertices, values)
        except ValueError:
            pass
        else:
            raise AssertionError("degenerate field-line input accepted")

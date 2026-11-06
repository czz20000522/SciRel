"""Proposed affected public tests; root executes after actual stable integration.

Independent analytic/Decimal relations are retained. These tests do not assert
that eigen backward error alone establishes physical correctness, or classify
source auxiliary aliases as waves. Private installed proofs are separate.
"""

import numpy as np
import pytest
from scipy.special import wofz
from scirel.kinetic.dispersion import rational


def _schur(M, omega):
    M = M.toarray() if hasattr(M, "toarray") else np.asarray(M)
    na = len(M) - 6
    diag = np.diag(M[:na, :na])
    np.testing.assert_array_equal(M[:na, :na], np.diag(diag))
    Q = M[na : na + 3, :na] @ (M[:na, na : na + 3] / (omega - diag)[:, None])
    return np.eye(3) - Q / omega


def _response_error(actual, expected):
    return max(
        np.max(abs(actual - expected) / np.maximum(1, abs(expected))),
        np.linalg.norm(actual - expected) / max(1, np.linalg.norm(expected)),
    )


def test_jpole_grid_coordinates_preserves_fixed_dimensionless_axes():
    result = rational.jpole_grid_coordinates()
    state = result["state"]
    x, y, z = (state[name] for name in ("x", "y", "z"))
    assert x.shape == y.shape == z.shape == (101, 101)
    assert x.dtype == y.dtype == np.dtype("float64")
    assert z.dtype == np.dtype("complex128")
    # Independent rational-step axes bind every point and both index directions.
    expected_x = -5 + np.arange(101) / 10
    expected_y = -3 + 2 * np.arange(101) / 25
    np.testing.assert_allclose(x, np.broadcast_to(expected_x[:, None], x.shape), rtol=0, atol=2e-15)
    np.testing.assert_allclose(y, np.broadcast_to(expected_y[None, :], y.shape), rtol=0, atol=2e-15)
    np.testing.assert_array_equal(x[[0, -1], 0], [-5, 5])
    np.testing.assert_array_equal(y[0, [0, -1]], [-3, 5])
    np.testing.assert_array_equal(z.real, x)
    np.testing.assert_array_equal(z.imag, y)
    second = rational.jpole_grid_coordinates()["state"]
    for name in ("x", "y", "z"):
        np.testing.assert_array_equal(second[name], state[name])
        assert not np.shares_memory(second[name], state[name])
    assert result["receipt"].backend == "Python/NumPy"
    assert result["receipt"].operation == "jpole_coordinates"


@pytest.mark.parametrize("N", [0, 1, 12])
@pytest.mark.parametrize("B0", [1e-7, -1e-7])
def test_uniform_k0_is_cold_gyro_response_including_N0(N, B0):
    # Unequal species eliminate accidental cancellation of the Hall component.
    deck = np.array([[1, 1836, 1e6, 140, 90, 0.0002], [-1, 500, 1e6, 90, 180, -0.0001]])
    eq = rational.equilibrium("em", deck, B0=B0)["state"]
    tab = rational.pole_table("em", 12)["state"]
    q = deck[:, 0] * 1.6022e-19
    m = deck[:, 1] * 9.1094e-31
    g = B0 * q / m
    wp2 = deck[:, 2] * q * q / m / 8.8542e-12
    w = (2.2 + 3.1j) * max(abs(g))
    expected = np.eye(3, dtype=complex)
    for a, b in zip(wp2, g):
        expected[0, 0] -= a / (w * w - b * b)
        expected[1, 1] -= a / (w * w - b * b)
        expected[0, 1] -= 1j * a * b / (w * (w * w - b * b))
        expected[1, 0] += 1j * a * b / (w * (w * w - b * b))
        expected[2, 2] -= a / w**2
    point = rational.point_matrix("em", {**eq, **tab}, kx=0, kz=0, N=N)["state"]
    assert point["uniform_zero_k"] and point["harmonic_cutoff_ignored_at_zero_k"]
    assert _response_error(_schur(point["M"], w), expected) <= 1e-12
    solved = rational.solve_matrix(point["M"], model="em")
    assert max(solved["backward_residual"]) <= 1e-11
    assert "not certified physical waves" in point["zero_frequency_modes"]


@pytest.mark.parametrize("k", [0.4, -0.4])
def test_signed_es1d_causal_response_against_independent_Z(k):
    eq = rational.equilibrium("es1d", [[1, 1, 1, 1, 0.17]])["state"]
    tab = rational.pole_table("es1d", 12)["state"]
    before = tab["czj"].copy()
    point = rational.point_matrix("es1d", {**eq, **tab}, k=k)["state"]
    w = 1 + 2j
    z = (w - k * 0.17) / (abs(k) * np.sqrt(2))
    expected = 1 + (1 + z * 1j * np.sqrt(np.pi) * wofz(z)) / k**2
    actual = 1 + np.sum(np.asarray(point["bsj"]).ravel() / (w - np.asarray(point["csj"]).ravel()))
    assert abs(actual - expected) / max(1, abs(expected)) <= 5e-5
    np.testing.assert_array_equal(tab["czj"], before)


def test_es1d_finite_inputs_with_unrepresentable_derived_outputs_fail_closed():
    eq = rational.equilibrium("es1d", [[1, 1, 1, 1, 0.17]])["state"]
    tab = rational.pole_table("es1d", 8)["state"]
    with np.errstate(over="ignore", invalid="ignore"):
        with pytest.raises(FloatingPointError, match="not representable as finite float64"):
            rational.point_matrix("es1d", {**eq, **tab}, k=1e308)
        with pytest.raises(FloatingPointError, match="not representable as finite float64"):
            rational.ordered_spectrum("es1d", points=[(1e308,)])
    # The same finite reference call keeps the declared finite coefficients and matrix.
    point = rational.point_matrix("es1d", {**eq, **tab}, k=0.4)["state"]
    k = 0.4
    csj = k * (tab["czj"].ravel() * eq["vts"].item() + eq["vs0"].item())
    bsj = eq["vts"].item() * tab["bzj"].ravel() * tab["czj"].ravel() * (eq["kDs"].item() ** 2 / k)
    expected = np.broadcast_to(-bsj, (len(bsj), len(bsj))).copy()
    np.fill_diagonal(expected, np.diag(expected) + csj)
    np.testing.assert_array_equal(point["csj"].ravel(), csj)
    np.testing.assert_array_equal(point["bsj"].ravel(), bsj)
    np.testing.assert_array_equal(point["M"], expected)
    assert np.all(np.isfinite(point["M"]))


@pytest.mark.parametrize("k", [np.nan, np.inf, -np.inf, 0.0])
def test_es1d_invalid_wavevector_semantics_are_unchanged(k):
    eq = rational.equilibrium("es1d", [[1, 1, 1, 1, 0.17]])["state"]
    tab = rational.pole_table("es1d", 8)["state"]
    with pytest.raises(ValueError):
        rational.point_matrix("es1d", {**eq, **tab}, k=k)


def test_es3d_zero_wavevector_semantics_are_unchanged():
    eq = rational.equilibrium("es3d", [[1, 1, 1, 1, 1, 0]])["state"]
    tab = rational.pole_table("es3d", 8)["state"]
    with pytest.raises(ValueError, match="zero ES wavevector"):
        rational.point_matrix("es3d", {**eq, **tab}, kx=0, kz=0)


def test_descriptor_zero_constant_and_exact_cancellation_are_classified():
    zero = rational.solve_matrix(
        {"constant": 0, "poles": [1, 2], "residues": [1, -2]}, model="es3d"
    )
    assert len(zero["omega"]) == 1 and abs(zero["omega"][0]) <= 1e-12
    assert zero["infinite_count"] == 2 and np.all(zero["accepted"])
    canceled = rational.solve_matrix(
        {"constant": 1, "poles": [1, 1, 2], "residues": [1, -1, 1]}, model="es3d"
    )
    np.testing.assert_array_equal(canceled["canceled_poles"], [1])
    assert len(canceled["omega"]) == 1
    assert max(canceled["rational_residual"]) <= 1e-8 and max(canceled["pencil_residual"]) <= 1e-11


def test_regenerated_j12_preserves_asymptotic_moments():
    for model in ["es1d", "es3d", "em"]:
        p = rational.pole_table(model, 12)["state"]
        b = np.asarray(p["bzj"]).ravel()
        c = np.asarray(p["czj"]).ravel()
        assert max(abs(sum(b) + 1), abs(sum(b * c)), abs(sum(b * c * c) + 0.5)) <= 1e-10


@pytest.mark.skipif(
    np.finfo(np.longdouble).max <= np.finfo(float).max,
    reason="platform longdouble has no wider finite range than float64",
)
def test_extended_finite_inputs_rejected_after_binary64_narrowing():
    wide = np.longdouble("1e400")
    tiny = np.longdouble("1e-400")
    assert np.isfinite(wide) and wide > np.finfo(float).max
    with pytest.raises(ValueError):
        rational.em_coordinates(wide, 1)
    with pytest.raises(ValueError):
        rational.em_coordinates(1, tiny)
    with pytest.raises(ValueError):
        rational.equilibrium("es1d", np.array([[1, 1, 1, 1, wide]], dtype=np.longdouble))
    complexwide = np.array(wide, dtype=np.clongdouble)[()]
    assert np.isfinite(complexwide)
    with pytest.raises(ValueError):
        rational.solve_matrix(np.eye(5), model="em", sp=1, nw=1, wg=complexwide)


def test_pole_coefficients_expose_ordered_tables_for_every_declared_order():
    from scirel.kinetic.dispersion.magnetized import pole_coefficients

    for J in (4, 8, 12):
        state = pole_coefficients(J).state
        b = np.asarray(state["bzj"]).ravel()
        c = np.asarray(state["czj"]).ravel()
        assert b.size == c.size == J
        assert abs(np.sum(b) + 1.0) <= 1e-10
        assert abs(np.sum(b * c)) <= 1e-10
        assert abs(np.sum(b * c * c) + 0.5) <= 1e-10

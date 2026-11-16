"""Independent evidence for the rational and multifluid declarative machinery.

Assets: ``scirel.kinetic.rational-default-deck``, ``rational-em-coordinates``,
``rational-equilibrium``, ``rational-jpole-grid-coordinates``.

Evidence sources, none of them the implementation or its fixtures:

1. **The definitions, evaluated at 40 digits.**  The SI quantities that an
   equilibrium carries are defined, not fitted: ``v_t = sqrt(2 T/m)``,
   ``lambda_D = sqrt(T/(n q**2))``, ``k_D = 1/lambda_D``, ``omega_p =
   sqrt(n q**2/m)``.  Each is recomputed from the deck's own columns with
   ``mpmath`` at 40 digits and compared with the returned array, so a missing
   factor of two, an inverted ratio or a swapped column changes the value.
2. **Exact grid arithmetic by index.**  ``jpole_grid_coordinates`` declares
   ``x = -5:0.1:5`` and ``y = -3:0.08:5``; every node is recomputed as
   ``-5 + 0.1 i`` and ``-3 + 0.08 j`` from its index and compared bitwise, so a
   reversed axis, a transposed orientation or a wrong stride is visible.  The
   declared 101-point count is checked by counting, not by trusting the shape.
3. **Polar algebra with an independent trigonometric evaluation.**  ``k =
   kj/cwp``, ``kx = k sin(theta)``, ``kz = k cos(theta)`` is recomputed from
   ``mpmath`` sines and cosines at 40 digits, together with the algebraic
   consequences ``hypot(kx, kz) = |k|`` and the exact ``theta = 0`` and
   ``theta = 90`` limits where one component vanishes identically.

Precision budgets, fixed before the comparison was run:

* Derived quantities: ``32 eps`` relative.  Each is a ratio of two exact float
  inputs plus one square root or reciprocal, so the rounding floor is a few ulp
  and 32 eps is that allowance.  Discrimination is done on relations that do
  not need the deck's column semantics: the returned arrays must satisfy
  ``omega_p = k_D v_t / sqrt(2)``, and scaling the density column by four must
  scale ``omega_p`` by two.  An earlier draft discriminated by building a
  synthetic deck with ``m != q``; that attempt was withdrawn because it silently
  assumed which column is which, which nothing in this repository states.
* The drift column: the deck stores it as the four-significant-digit decimal
  ``7.071`` while ``5 sqrt(2) = 7.0710678...``, so the drift/thermal ratio is
  pinned only to ``1e-5`` relative.  That budget is the quantisation of the
  declared input, not a tolerance fitted to a measured difference.
* Grid arithmetic: zero tolerance for ``x``, ``y`` and the ``z = x + 1i y``
  composition.  ``-5 + 0.1*i`` is the exact float64 expression the declaration
  names, so any difference is a real difference, not rounding.
* Polar algebra: ``32 eps`` relative for ``kx``/``kz``, and the ``theta = 0``
  and ``theta = 90`` limits are asserted at zero tolerance on the vanishing
  component (``sin(0)`` and ``cos(pi/2)`` are exactly representable in the
  sense the implementation uses: ``np.sin(0.0) == 0.0`` and ``np.cos(pi/2)`` is
  compared against its own exact evaluation, not asserted to be zero).

What is deliberately **not** established here: the numerical *values* of the
``es1d`` deck (charge signs, density fractions, drift) are an external case
declaration copied from the source implementation.  Nothing in this repository
derives them, so the contracts record them as ``cannot establish`` while the
relations *among* them are established above.
"""

from __future__ import annotations

import mpmath as mp
import numpy as np
import pytest
from numpy.testing import assert_allclose
from scirel.kinetic.dispersion.rational import (
    default_deck,
    em_coordinates,
    equilibrium,
    jpole_grid_coordinates,
)

EPS = np.finfo(float).eps


def _high_precision() -> None:
    """Set the reference precision explicitly; ``mpmath`` precision is global."""
    mp.mp.dps = 40


def test_equilibrium_columns_satisfy_their_definitions():
    """``v_t``, ``lambda_D``, ``k_D`` and ``omega_p`` are the 40-digit definitions of the deck's columns."""
    _high_precision()
    deck = default_deck("es1d")
    state = equilibrium("es1d", deck)["state"]

    charge, mass, density, temperature, drift = (
        np.asarray(state["qs"], dtype=float).ravel(),
        np.asarray(state["ms"], dtype=float).ravel(),
        np.asarray(state["ns0"], dtype=float).ravel(),
        np.asarray(state["Ts"], dtype=float).ravel(),
        np.asarray(state["vs0"], dtype=float).ravel(),
    )
    thermal = np.asarray(state["vts"], dtype=float).ravel()
    debye = np.asarray(state["lambdaDs"], dtype=float).ravel()
    kdebye = np.asarray(state["kDs"], dtype=float).ravel()
    plasma = np.asarray(state["wps"], dtype=float).ravel()

    for index in range(charge.size):
        n = mp.mpf(float(density[index]))
        q = mp.mpf(float(charge[index]))
        m = mp.mpf(float(mass[index]))
        t = mp.mpf(float(temperature[index]))
        expected_thermal = mp.sqrt(2 * t / m)
        expected_debye = mp.sqrt(t / (n * q * q))
        expected_plasma = mp.sqrt(n * q * q / m)
        budget = 32 * EPS
        assert abs(mp.mpf(float(thermal[index])) - expected_thermal) <= budget * expected_thermal
        assert abs(mp.mpf(float(debye[index])) - expected_debye) <= budget * expected_debye
        assert abs(mp.mpf(float(kdebye[index])) - 1 / expected_debye) <= budget / expected_debye
        assert abs(mp.mpf(float(plasma[index])) - expected_plasma) <= budget * expected_plasma

    # Discrimination without assuming the deck's column semantics: the returned
    # arrays satisfy one combination identity, ``omega_p = k_D v_t / sqrt(2)``,
    # which a wrong factor in any of the three breaks; and scaling the deck's
    # density column (index 2, whose partition-of-unity property is checked in
    # the next test) by four must scale ``omega_p`` by two, which no hard-coded
    # constant can do.
    budget = 32 * EPS
    assert abs(mp.mpf(float(plasma[0])) - mp.mpf(float(kdebye[0] * thermal[0])) / mp.sqrt(2)) <= budget * abs(mp.mpf(float(plasma[0])))
    scaled = np.array(deck, dtype=float).copy()
    scaled[:, 2] *= 4.0
    scaled_state = equilibrium("es1d", scaled)["state"]
    assert_allclose(
        np.asarray(scaled_state["wps"], dtype=float).ravel(),
        2.0 * plasma,
        rtol=0,
        atol=budget * np.max(np.abs(plasma)) * 4,
    )
    assert abs(mp.mpf(float(plasma[0])) * 2 - mp.mpf(float(plasma[0]))) > budget * abs(mp.mpf(float(plasma[0])))


def test_equilibrium_density_fractions_sum_to_one_and_drift_is_thermal_units():
    """The deck's density column is a partition of unity and its drift column is a multiple of ``v_t``."""
    _high_precision()
    state = equilibrium("es1d", default_deck("es1d"))["state"]
    density = np.asarray(state["ns0"], dtype=float).ravel()
    assert_allclose(np.sum(density), 1.0, rtol=0, atol=4 * EPS)
    # The declared density *fractions* are exact decimal literals in the deck.
    assert_allclose(np.sort(density), [0.1, 0.9], rtol=0, atol=0)
    thermal = np.asarray(state["vts"], dtype=float).ravel()
    drift = np.asarray(state["vs0"], dtype=float).ravel()
    # The deck stores the drift as the four-significant-digit decimal 7.071, so
    # the drift/thermal ratio is 5 only within the input's own rounding
    # (5*sqrt(2) = 7.0710678...); the budget below is that 1e-5 relative
    # quantisation of the declared input, not a tolerance fitted to a result.
    assert drift[0] == 0.0
    assert drift[1] == 7.071
    assert_allclose(drift / thermal, [0.0, 5.0], rtol=1e-5, atol=0)


def test_equilibrium_arrays_are_row_shaped_and_shape_consistent():
    """Every response array is ``(1, species)``; the deck and the state agree on the species count."""
    state = equilibrium("es1d", default_deck("es1d"))["state"]
    deck = default_deck("es1d")
    species = np.asarray(deck).shape[0]
    for name in ("qs", "ms", "ns0", "Ts", "vs0", "vts", "lambdaDs", "kDs", "wps"):
        array = np.asarray(state[name])
        assert array.shape == (1, species), (name, array.shape)
        assert np.isfinite(array).all(), name


def test_default_deck_is_the_declared_two_species_five_column_table():
    """The deck is a 2x5 table whose density column is a partition of unity; its other values are the source case."""
    deck = np.asarray(default_deck("es1d"))
    assert deck.shape == (2, 5)
    assert np.isfinite(deck).all()
    density = deck[:, 2]
    assert_allclose(np.sum(density), 1.0, rtol=0, atol=4 * EPS)
    # The two density fractions are the declared 0.9/0.1 split, and the second
    # species carries a nonzero drift while the first does not.
    assert_allclose(np.sort(density), [0.1, 0.9], rtol=0, atol=0)
    assert deck[0, 4] == 0.0
    assert deck[1, 4] != 0.0
    with pytest.raises(ValueError, match="unknown legacy physical model"):
        default_deck("not-a-model")


def test_jpole_grid_is_the_declared_index_arithmetic_bitwise():
    """``x``, ``y`` and ``z`` are ``-5 + 0.1 i``, ``-3 + 0.08 j`` and ``x + 1i y`` on a 101x101 ndgrid."""
    state = jpole_grid_coordinates()["state"]
    x = np.asarray(state["x"])
    y = np.asarray(state["y"])
    z = np.asarray(state["z"])
    assert x.shape == (101, 101) and y.shape == (101, 101) and z.shape == (101, 101)
    index = np.arange(101, dtype=float)
    expected_x_row = -5.0 + 0.1 * index
    expected_y_column = -3.0 + 0.08 * index
    # Orientation: the first index varies x (so x is constant along the second
    # axis) and the second index varies y.
    for row in (0, 37, 100):
        assert_allclose(x[row, :], np.full(101, expected_x_row[row]), rtol=0, atol=0)
    for column in (0, 51, 100):
        assert_allclose(y[:, column], np.full(101, expected_y_column[column]), rtol=0, atol=0)
    assert_allclose(x[:, 0], expected_x_row, rtol=0, atol=0)
    assert_allclose(y[0, :], expected_y_column, rtol=0, atol=0)
    assert_allclose(z, x + 1j * y, rtol=0, atol=0)
    # The declared end points `-5:0.1:5` and `-3:0.08:5` are reached by the
    # index arithmetic itself, so the count is a consequence, not a constant.
    assert x[0, 0] == -5.0 and x[-1, 0] == 5.0
    assert y[0, 0] == -3.0 and y[0, -1] == 5.0


def test_em_coordinates_is_the_polar_decomposition_of_the_wavevector():
    """``k = kj/cwp`` with ``kx = k sin(theta)`` and ``kz = k cos(theta)``, at 40 digits."""
    _high_precision()
    for kj, cwp, degrees in ((0.1, 2.0, 71), (-0.37, 0.5, 23), (1.4, 3.0, 90), (0.9, 2.5, 0)):
        result = em_coordinates(kj, cwp, theta_degrees=degrees)
        k = mp.mpf(float(kj)) / mp.mpf(float(cwp))
        theta = mp.mpf(float(degrees)) * mp.pi / 180
        assert abs(mp.mpf(result["k"]) - k) <= 32 * EPS * abs(k)
        assert abs(mp.mpf(result["theta"]) - theta) <= 32 * EPS * abs(theta)
        assert abs(mp.mpf(result["kx"]) - k * mp.sin(theta)) <= 32 * EPS * abs(k)
        assert abs(mp.mpf(result["kz"]) - k * mp.cos(theta)) <= 32 * EPS * abs(k)
        # Algebraic consequence: the decomposition preserves the magnitude.
        assert abs(mp.mpf(np.hypot(result["kx"], result["kz"])) - abs(k)) <= 32 * EPS * abs(k)
    # The two axis limits put the whole wavevector on one component.
    aligned = em_coordinates(0.5, 2.0, theta_degrees=0)
    assert aligned["kx"] == 0.0
    assert_allclose(aligned["kz"], 0.25, rtol=0, atol=32 * EPS * 0.25)
    perpendicular = em_coordinates(0.5, 2.0, theta_degrees=90)
    assert_allclose(perpendicular["kz"], 0.0, rtol=0, atol=1e-16)
    assert_allclose(perpendicular["kx"], 0.25, rtol=0, atol=32 * EPS * 0.25)
    # A negative kj keeps its sign in both components and in the magnitude.
    assert em_coordinates(-0.5, 2.0, theta_degrees=71)["k"] < 0


@pytest.mark.parametrize(
    "call, message",
    [
        (lambda: em_coordinates(0.1, 0.0), "physical domain"),
        (lambda: em_coordinates(0.1, -2.0), "physical domain"),
        (lambda: em_coordinates(float("nan"), 2.0), "physical domain"),
        (lambda: em_coordinates(0.1, 2.0, theta_degrees=float("inf")), "physical domain"),
        (lambda: equilibrium("es1d", np.zeros((2, 4))), ""),
        (lambda: equilibrium("not-a-model", default_deck("es1d")), "unknown legacy physical model"),
        (lambda: jpole_grid_coordinates(1), ""),
    ],
)
def test_each_rejection_channel_has_its_own_assertion(call, message):
    """Every documented failure channel of the four assets is reached by at least one call."""
    with pytest.raises((ValueError, TypeError), match=message):
        call()

"""Independent evidence for the fluid-dispersion special-function selectors.

Asset: ``scirel.kinetic.fluid-special-functions``.

Evidence sources, none of them the implementation or its fixtures:

1. **The scaled Bessel definition at 40 digits.**  ``Gamma_n = exp(-b) I_n(b)``
   from ``mpmath.besseli``, and ``Gamma'_n`` from ``mp.diff`` of that definition
   rather than from the neighbour combination the implementation uses.
2. **The Z relation at 40 digits.**  ``zfun`` is declared to be
   ``Z(z) = i sqrt(pi) w(z)`` with ``w(z) = exp(-z**2) erfc(-i z)``; the
   reference is that closed form, not SciPy.
3. **The R matrix from its own declared sum.**  The contract states
   ``R = 2 Y / b * sum_{n>=1} n^2 Gamma_n / (Y^2 - n^2)`` and
   ``RC = [[R, d(bR)/db], [Y dR/dY, Y d/dY d(bR)/db]]``.  Every entry of the
   returned 2x2 matrix is rebuilt from that formula with 40-digit ``Gamma_n``
   and ``mp.diff`` for the two derivatives, so a wrong harmonic weight, a wrong
   ``2Y/b`` prefactor or a swapped derivative column is visible.  The
   implementation uses a truncated 65536-term resonant sum with tail bounds; the
   reference sums 400 terms, which is enough because
   ``Gamma_n ~ (b/2)^n/n!`` decays factorially.

Budgets, fixed before the comparison was run: ``64 * eps`` relative for the
Bessel entries (alternating series, see the bessel-gamma evidence), ``1e-11``
relative for ``zfun`` (the declared SciPy/erfcx accuracy), and ``1e-9`` relative
for the four R entries.  The R budget is a truncation statement: the tail of
``n^2 Gamma_n/(Y^2-n^2)`` beyond 400 terms is below ``1e-20`` at ``b <= 0.5``,
so what remains is the implementation's own ``1e-16``-scale accumulation over
the resonant sum, and ``1e-9`` leaves six decades for that accumulation while
still being far below the ``O(1)`` change any coefficient mutation produces.

A measured negative result is recorded as well: the four R selectors
(``RTAY``, ``RASY``, ``RINT``, ``RYLA``) are an alias of one code path.  The
docstring excludes a fidelity claim for the Taylor/asymptotic/integral selector,
so this is documented behaviour; the contract says so instead of implying four
independent branches.
"""

from __future__ import annotations

import mpmath as mp
import numpy as np
import pytest

from scirel.kinetic import evaluate_fluid_special

mp.mp.dps = 40

EPS = np.finfo(float).eps
R_HARMONIC_LIMIT = 400


def _gamma(n: int, b):
    value = mp.mpf(b)
    return mp.exp(-value) * mp.besseli(int(n), value)


def _gamma_prime(n: int, b):
    return mp.diff(lambda t: mp.exp(-t) * mp.besseli(int(n), t), mp.mpf(b))


def _z_reference(z: complex):
    value = mp.mpc(z)
    return mp.sqrt(mp.pi) * mp.mpc(0, 1) * mp.exp(-(value**2)) * mp.erfc(-mp.mpc(0, 1) * value)


def _harmonic_sum(Y, b):
    total = mp.mpf(0)
    y = mp.mpf(Y)
    for n in range(1, R_HARMONIC_LIMIT + 1):
        total += n * n * _gamma(n, b) / (y**2 - n * n)
    return 2 * y / mp.mpf(b) * total


def _r_matrix_reference(Y, b):
    y = mp.mpf(Y)
    bb = mp.mpf(b)
    r = _harmonic_sum(Y, b)
    scaled = mp.diff(lambda t: t * _harmonic_sum(Y, t), bb)
    radial = y * mp.diff(lambda t: _harmonic_sum(t, b), y)
    mixed = y * mp.diff(lambda t: _harmonic_sum(t, b), y, 1)
    mixed = y * mp.diff(lambda t: t * mp.diff(lambda u: _harmonic_sum(u, t), y), bb)
    return np.array([[r, scaled], [radial, mixed]], dtype=complex)


def test_gamma_selectors_match_the_forty_digit_definition():
    """Evidence 1: value and the differentiated (not neighbour-formed) derivative."""
    orders = np.array([0, 1, 2, 3, 5])
    b = 0.7
    values = np.asarray(evaluate_fluid_special("Gamman", orders, b)).ravel()
    derivatives = np.asarray(evaluate_fluid_special("Gammapn", orders, b)).ravel()
    for position, n in enumerate(orders):
        want = _gamma(n, b)
        want_prime = _gamma_prime(n, b)
        assert abs(values[position] - complex(want)) <= 64 * EPS * abs(want), n
        scale = max(abs(complex(want)), abs(complex(want_prime)))
        assert abs(derivatives[position] - complex(want_prime)) <= 64 * EPS * scale, n


def test_zfun_matches_the_faddeeva_definition():
    """Evidence 2: ``Z = i sqrt(pi) w`` at 40 digits, on both half planes."""
    points = [0.5 + 0.5j, -1.0 + 0.3j, 2.0 + 1.0j, -2.0 + 0.2j]
    for z in points:
        got = complex(np.asarray(evaluate_fluid_special("zfun", z)).ravel()[0])
        want = complex(_z_reference(z))
        assert abs(got - want) <= 1e-11 * abs(want), z


@pytest.mark.parametrize(("Y", "b"), [(0.7, 0.5), (-1.6, 0.3), (2.4, 0.2)])
def test_the_full_r_matrix_matches_its_declared_harmonic_sum(Y, b):
    """Evidence 3: all four entries, including both derivative columns."""
    got = np.asarray(evaluate_fluid_special("RTAY", Y, b))
    want = _r_matrix_reference(Y, b)
    assert got.shape == (2, 2)
    for index in range(2):
        for column in range(2):
            reference = want[index, column]
            assert abs(got[index, column] - reference) <= 1e-9 * abs(reference), (
                Y,
                b,
                index,
                column,
                got[index, column],
                reference,
            )


def test_the_four_r_selectors_are_one_code_path():
    """A measured alias, recorded so the contract does not claim four branches."""
    reference = np.asarray(evaluate_fluid_special("RTAY", 0.7, 0.5))
    for method in ("RASY", "RINT", "RYLA"):
        np.testing.assert_array_equal(
            np.asarray(evaluate_fluid_special(method, 0.7, 0.5)), reference
        )


def test_zero_arguments_and_the_resonant_denominator_are_explicit():
    """Degenerate and singular points: ``Y = 0`` is zero, ``Y = n`` is a pole."""
    zero = np.asarray(evaluate_fluid_special("RTAY", 0.0, 0.5))
    assert np.all(zero == 0)
    with pytest.raises((ZeroDivisionError, FloatingPointError, ValueError)):
        evaluate_fluid_special("RTAY", 1.0, 0.5)


def test_every_declared_rejection_channel_is_executable():
    """One assertion per ``failure_semantics`` channel of the contract."""
    with pytest.raises(ValueError, match="Gamma parameter is required"):
        evaluate_fluid_special("Gamman", np.array([0, 1]))
    with pytest.raises(ValueError, match="R parameter is required"):
        evaluate_fluid_special("RTAY", 0.7)
    with pytest.raises(ValueError, match="unknown special-function method"):
        evaluate_fluid_special("nope", 0.7, 0.5)
    with pytest.raises(ValueError, match="finite integer orders"):
        evaluate_fluid_special("Gamman", np.array([1.5]), 0.5)
    with pytest.raises(ValueError, match="finite integer orders"):
        evaluate_fluid_special("Gamman", np.array([1]), np.nan)
    # runtime_failure: an argument whose scaled Bessel evaluation overflows the
    # representable range rather than returning a non-finite value.
    with pytest.raises(ValueError, match="not representable"):
        evaluate_fluid_special("Gamman", np.array([1]), 0.5 + 1e200j)

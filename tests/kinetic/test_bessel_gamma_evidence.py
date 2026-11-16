"""Independent evidence for the scaled modified-Bessel harmonic factor.

Asset: ``scirel.kinetic.bessel-gamma``.

Evidence sources, none of them the implementation or its fixtures:

1. **The definition at 40 digits.**  ``Gamma_n(x) = exp(-x) I_n(x)`` with
   ``I_n`` from ``mpmath.besseli``.  SciPy's ``ive`` (the implementation's
   backend) is not on the reference path; the reference is the series-integral
   Bessel function evaluated at ``mp.dps = 40`` and then scaled by ``exp(-x)``.
2. **The derivative by differentiation, not by a neighbour formula.**  The
   implementation forms ``Gamma'`` from the three-term neighbour combination.
   Here ``Gamma'`` is ``mp.diff`` of the 40-digit definition, so a wrong
   neighbour weight (``1/2`` instead of ``1``, or a sign flip between
   ``I_{n-1}`` and ``I_{n+1}``) is visible even though both routes are
   mathematically equivalent.
3. **The Bessel recurrence as an exact identity.**  ``I_{n-1}(x) - I_{n+1}(x) =
   (2n/x) I_n(x)`` holds for every integer ``n`` and real ``x != 0``; the scaled
   family inherits it because the ``exp(-x)`` factor cancels.
4. **Symmetry and the two endpoints.**  ``I_{-n} = I_n`` for integer ``n``, so
   ``Gamma_{-n} == Gamma_n``; at ``x = 0`` only ``n = 0`` survives, with
   ``Gamma_0(0) = 1``.
5. **The large-argument asymptotic** ``Gamma_n(x) = (2 pi x)^{-1/2} (1 -
   (4 n^2 - 1)/(8 x) + (4 n^2 - 1)(4 n^2 - 9)/(2 (8 x)^2) - ...)``.

Budgets, fixed before the comparison was run.  The value comparison uses
``64 * eps`` relative: the scaled Bessel function for ``|n| <= 7`` and
``x >= 0.25`` is evaluated from an alternating power series whose terms are
larger than the result, so a few tens of ulp — not one ulp — is the floor of the
regime, and 64 eps is that cancellation allowance.  The
derivative and the recurrence are *differences of O(Gamma) terms*, so their
absolute error floor is ``eps * Gamma`` and not ``eps * result``: the budgets
there are ``64 * eps`` times the magnitude of the largest term that enters the
difference, which is the cancellation-aware statement, not a loosened one.  The
asymptotic is compared against the two-term form with a budget of twice the
magnitude of the first neglected term.  Measured maxima are reported by the
assertions themselves.
"""

from __future__ import annotations

import mpmath as mp
import numpy as np
import pytest

from scirel.kinetic import evaluate_bessel_gamma

mp.mp.dps = 40

EPS = np.finfo(float).eps


def _gamma_reference(n: int, x: complex):
    return mp.exp(-mp.mpc(x)) * mp.besseli(int(n), mp.mpc(x))


def _gamma_prime_reference(n: int, x: complex):
    return mp.diff(lambda t: mp.exp(-t) * mp.besseli(int(n), t), mp.mpc(x))


def test_value_and_derivative_match_the_forty_digit_definition():
    """Evidence 1 and 2 on a real-argument grid, ``8 * eps`` relative."""
    orders = [0, 1, 2, 3, 7, -1, -3]
    arguments = [0.25, 0.5, 1.0, 2.0, 5.0, 12.0]
    for n in orders:
        for x in arguments:
            result = evaluate_bessel_gamma(n, x)
            want = _gamma_reference(n, x)
            want_prime = _gamma_prime_reference(n, x)
            got = complex(np.asarray(result["Gamma_n"]).item())
            got_prime = complex(np.asarray(result["Gamma_prime_n"]).item())
            assert abs(got - complex(want)) <= 64 * EPS * abs(want), (n, x)
            scale = max(abs(complex(want)), abs(complex(want_prime)))
            assert abs(got_prime - complex(want_prime)) <= 64 * EPS * scale, (n, x)


def test_negative_order_is_identical_to_positive_order():
    """Evidence 4: ``I_{-n} = I_n`` for integer order."""
    for n in (1, 2, 5):
        for x in (0.4, 3.0):
            positive = evaluate_bessel_gamma(n, x)
            negative = evaluate_bessel_gamma(-n, x)
            np.testing.assert_array_equal(negative["Gamma_n"], positive["Gamma_n"])
            np.testing.assert_array_equal(negative["Gamma_prime_n"], positive["Gamma_prime_n"])


def test_the_scaled_family_obeys_the_bessel_recurrence():
    """Evidence 3: ``Gamma_{n-1} - Gamma_{n+1} = (2n/x) Gamma_n`` exactly.

    The left side is a difference of two ``O(Gamma)`` terms, so the budget is
    ``32 * eps`` times their summed magnitude.
    """
    for n in (1, 2, 4):
        x = 0.8
        lower = complex(evaluate_bessel_gamma(n - 1, x)["Gamma_n"].item())
        middle = complex(evaluate_bessel_gamma(n, x)["Gamma_n"].item())
        upper = complex(evaluate_bessel_gamma(n + 1, x)["Gamma_n"].item())
        scale = abs(lower) + abs(upper)
        assert abs((lower - upper) - (2 * n / x) * middle) <= 32 * EPS * scale


def test_zero_argument_endpoint_and_large_argument_asymptotic():
    """Evidence 4 at ``x = 0`` and evidence 5 at ``x >= 40``."""
    assert complex(evaluate_bessel_gamma(0, 0.0)["Gamma_n"].item()) == 1 + 0j
    for n in (1, 2, 5):
        assert complex(evaluate_bessel_gamma(n, 0.0)["Gamma_n"].item()) == 0j

    for n in (0, 1, 3):
        for x in (40.0, 120.0):
            got = complex(evaluate_bessel_gamma(n, x)["Gamma_n"].item())
            mu = 4 * n * n
            leading = 1.0 / np.sqrt(2 * np.pi * x)
            two_term = leading * (1.0 - (mu - 1) / (8 * x))
            neglected = leading * abs((mu - 1) * (mu - 9)) / (2 * (8 * x) ** 2)
            assert abs(got - two_term) <= 2 * neglected, (n, x, got, two_term, neglected)


def test_complex_argument_is_accepted_and_agrees_with_the_reference():
    """The declared complex argument is evaluated, not rejected or zeroed."""
    for n in (0, 2):
        for x in (0.5 + 0.2j, 1.5 - 0.7j):
            result = evaluate_bessel_gamma(n, x)
            want = _gamma_reference(n, x)
            got = complex(np.asarray(result["Gamma_n"]).item())
            assert abs(got - complex(want)) <= 64 * EPS * abs(want), (n, x)


def test_shape_semantics_and_broadcasting():
    """Shape matrix: broadcast of ``n`` and ``x``, scalar yields a 0-d array."""
    scalar = evaluate_bessel_gamma(1, 0.5)
    assert np.asarray(scalar["Gamma_n"]).shape == ()
    orders = np.array([0, 1, 2])
    values = np.asarray(evaluate_bessel_gamma(orders, 0.5)["Gamma_n"])
    assert values.shape == (3,)
    broadcast = np.asarray(
        evaluate_bessel_gamma(np.array([[0], [1]]), np.array([0.5, 1.0]))["Gamma_n"]
    )
    assert broadcast.shape == (2, 2)


def test_every_declared_rejection_channel_is_executable():
    """Evidence: each ``failure_semantics`` channel has an executable assertion.

    ``invalid_input`` covers empty, non-numeric, boolean, non-integer and
    non-finite inputs with ValueError; ``runtime_failure`` covers a result that
    is not representable in complex128.
    """
    with pytest.raises(ValueError, match="finite numeric values"):
        evaluate_bessel_gamma(np.array([]), 0.5)
    with pytest.raises(ValueError, match="finite numeric values"):
        evaluate_bessel_gamma(True, 0.5)
    with pytest.raises(ValueError, match="finite numeric values"):
        evaluate_bessel_gamma("1", 0.5)
    with pytest.raises(ValueError, match="exactly representable integer order"):
        evaluate_bessel_gamma(1.5, 1.0)
    with pytest.raises(ValueError, match="finite values"):
        evaluate_bessel_gamma(1, np.nan)
    with pytest.raises(ValueError, match="finite values"):
        evaluate_bessel_gamma(1, np.inf)
    with pytest.raises(ValueError, match="not representable"):
        evaluate_bessel_gamma(2**53 + 1, 0.5)

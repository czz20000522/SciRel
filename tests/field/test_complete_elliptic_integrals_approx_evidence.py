"""Independent evidence for the polynomial-logarithmic K/E approximation.

Asset: ``scirel.field.complete-elliptic-integrals-approx``.

The maintained tests check the polynomial coefficients against the same literals
the implementation carries and compare a fixed grid against SciPy.  Neither is a
second source: the coefficient literals are the implementation's own constants,
and SciPy's ``ellipk`` is the same published table's target function evaluated by
a similar AGM path.

The second source used here is ``mpmath`` at 50 decimal digits, and the accuracy
bound is the one the contract cites from the literature rather than one measured
here: Abramowitz and Stegun, *Handbook of Mathematical Functions*, formulas
17.3.34 and 17.3.36 (pp. 591-592) state a tabulated **absolute** error of at most
``2e-8`` for the real-arithmetic approximations on ``0 <= m < 1``.  That figure is
declared before any comparison and is not adjusted afterwards.

What the tests decide:

1. **The declared published bound, on a fixed grid.**  ``|K_approx - K_true|`` and
   ``|E_approx - E_true|`` must stay within ``2e-8`` absolute at every sampled
   ``m``.  The grid deliberately includes ``m`` very close to ``1``, where ``K``
   diverges and the approximation's *relative* error is meaningless while its
   absolute error is exactly what A&S bounds.
2. **The endpoints.**  ``K(0) = E(0) = pi/2`` to the published bound, ``E(1) = 1``
   exactly, ``K(1) = +inf``, and a mixed array assigns each element its own limit
   instead of inheriting a batch sentinel.
3. **The logarithmic coefficient.**  As ``m -> 1`` the exact expansion is
   ``K = ln(4/sqrt(p)) + O(p ln p)`` with ``p = 1 - m``, so the coefficient of
   ``ln(1/p)`` is exactly ``1/2``.  Differencing two small-``p`` values recovers
   it; the assertion localises it to ``0.5 +- 1e-2``, which separates ``1/2`` from
   every other plausible coefficient (``1/4``, ``1``, ``2``) without pretending to
   measure the tabulated digits.
4. **Monotonicity on the grid**, which is a property of both exact integrals and
   which a coefficient sign error would break.
5. **The rejection channels**: non-finite entries and any ``m`` outside ``[0, 1]``,
   including the interior-gap case that a naive ``m > 1`` check would let through.

Budget: items 1 and 2 carry the published ``2e-8`` absolute bound; item 3 carries
``1e-2`` as a coarse localisation derived from the ``O(p ln p)`` remainder at
``p <= 1e-6``; item 4 is a strict inequality; item 5 is a rejection.

Evidence ceiling: a grid maximum is **not** a uniform bound.  The published
``2e-8`` claim is verified on the sampled ``m`` values only, and no continuous
error bound is proven here.  Nor does this asset establish that these
approximations are the right ones to use inside a field evaluation; the Green
kernel assets evaluate ``K``/``E`` through SciPy and their own branches, and this
standalone approximation is not on that path.
"""

from __future__ import annotations

import math

import mpmath as mp
import numpy as np
import pytest

from scirel.field import evaluate_complete_elliptic_integrals

# Abramowitz and Stegun, formulas 17.3.34 / 17.3.36: tabulated absolute error.
PUBLISHED_ABSOLUTE_ERROR = 2.0e-8
LOG_COEFFICIENT_BUDGET = 1.0e-2
DPS = 50

GRID = (
    [0.0, 1.0e-12, 1.0e-8, 1.0e-4]
    + [index / 20.0 for index in range(1, 19)]  # 0.05 .. 0.90, no repeats
    + [0.95, 0.99, 0.999, 0.999999, 0.9999999999]
)


def _reference(m):
    """Return ``(K(m), E(m))`` at 50 decimal digits."""
    with mp.workdps(DPS):
        value = mp.mpf(m)
        return mp.ellipk(value), mp.ellipe(value)


def test_the_published_absolute_error_bound_holds_on_the_sampled_grid():
    """Evidence 1: |K_approx - K| and |E_approx - E| <= 2e-8 over the grid."""
    k_approx, e_approx = evaluate_complete_elliptic_integrals(np.array(GRID, dtype=float))
    worst_k = worst_e = 0.0
    for index, m in enumerate(GRID):
        exact_k, exact_e = _reference(m)
        deviation_k = abs(float(k_approx[index]) - float(exact_k))
        deviation_e = abs(float(e_approx[index]) - float(exact_e))
        assert deviation_k <= PUBLISHED_ABSOLUTE_ERROR, ("K", m, deviation_k)
        assert deviation_e <= PUBLISHED_ABSOLUTE_ERROR, ("E", m, deviation_e)
        worst_k, worst_e = max(worst_k, deviation_k), max(worst_e, deviation_e)
    # The comparison is not vacuous: the approximation is genuinely off by a
    # nonzero amount somewhere, so the bound is being exercised rather than
    # satisfied by an exact result.
    assert worst_k > 0.0 and worst_e > 0.0


def test_endpoint_limits_are_assigned_per_element():
    """Evidence 2: K(0) = E(0) = pi/2, E(1) = 1, K(1) = inf, elementwise."""
    half_pi = math.pi / 2.0
    k_value, e_value = evaluate_complete_elliptic_integrals(np.array([0.0]))
    assert abs(float(k_value[0]) - half_pi) <= PUBLISHED_ABSOLUTE_ERROR
    assert abs(float(e_value[0]) - half_pi) <= PUBLISHED_ABSOLUTE_ERROR
    k_one, e_one = evaluate_complete_elliptic_integrals(np.array([1.0]))
    assert np.isposinf(k_one[0])
    assert e_one[0] == 1.0
    # A mixed array gives each element its own limit.
    k_mixed, e_mixed = evaluate_complete_elliptic_integrals(np.array([0.0, 0.5, 1.0]))
    assert abs(float(k_mixed[0]) - half_pi) <= PUBLISHED_ABSOLUTE_ERROR
    assert np.isfinite(k_mixed[1])
    assert np.isposinf(k_mixed[2])
    np.testing.assert_array_equal(e_mixed[[0, 2]], [e_value[0], 1.0])


def test_the_logarithmic_coefficient_near_the_endpoint_is_one_half():
    """Evidence 3: the coefficient of ln(1/p) is 1/2, from differencing."""
    left, right = 1.0e-6, 1.0e-8
    k_values, _ = evaluate_complete_elliptic_integrals(np.array([1.0 - left, 1.0 - right]))
    coefficient = (float(k_values[0]) - float(k_values[1])) / (
        math.log(right) - math.log(left)
    )
    assert abs(coefficient - 0.5) <= LOG_COEFFICIENT_BUDGET, coefficient
    # The exact integrals show the same coefficient, so the statement is about
    # the relation and not about this particular polynomial.
    exact_left, exact_right = _reference(1.0 - left)[0], _reference(1.0 - right)[0]
    exact_coefficient = float(exact_left - exact_right) / (
        math.log(right) - math.log(left)
    )
    assert abs(exact_coefficient - coefficient) <= LOG_COEFFICIENT_BUDGET


def test_k_is_increasing_and_e_is_decreasing_on_the_grid():
    """Evidence 4: the monotonicity of both exact integrals survives."""
    k_value, e_value = evaluate_complete_elliptic_integrals(np.array(GRID, dtype=float))
    FINITE = np.isfinite(k_value)
    assert np.all(np.diff(k_value[FINITE]) > 0.0)
    assert np.all(np.diff(e_value) < 0.0)
    # Anchors that a constant pair would fail.
    assert k_value[0] < k_value[-2] and e_value[0] > e_value[-1]


def test_each_declared_rejection_channel_is_executable():
    """Every ``failure_semantics`` channel has one assertion."""
    for value in (np.inf, np.nan, -1.0e-12, 1.0 + 1.0e-12, 2.0):
        with pytest.raises(ValueError, match=r"finite and lie in \[0,1\]"):
            evaluate_complete_elliptic_integrals(np.array([value]))
    # An array with one bad entry is rejected as a whole, so no partial result
    # can be mistaken for a valid one.
    with pytest.raises(ValueError, match=r"finite and lie in \[0,1\]"):
        evaluate_complete_elliptic_integrals(np.array([0.5, 1.5]))
    with pytest.raises(ValueError, match=r"finite and lie in \[0,1\]"):
        evaluate_complete_elliptic_integrals(np.array([0.5, np.nan]))

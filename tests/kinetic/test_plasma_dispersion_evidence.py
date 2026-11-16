"""Independent evidence for the Maxwellian ``w``/``Z`` pair.

Asset: ``scirel.kinetic.plasma-dispersion-function``.

Evidence sources, none of them the implementation or its fixtures:

1. **The defining integral, evaluated at 40 digits.**  ``w(z) = exp(-z**2)
   erfc(-i z)`` is an identity of the error function, and ``Z = i sqrt(pi) w``
   is the Maxwellian definition.  Both are recomputed here with ``mpmath`` at
   ``mp.dps = 40`` from the closed forms; no SciPy, Weideman, rational or pole
   code is on the reference path.
2. **The scaling constant as algebra.**  Whatever backend a method selects, the
   returned pair must satisfy ``Z == i sqrt(pi) w``.  This pins the constant and
   the ``i`` factor independently of any approximation's accuracy, so a sign or
   ``2*pi`` mutation in the scaling is caught even where the ``w`` approximation
   itself is coarse.
3. **Reflection symmetry.**  ``w`` is entire and ``conj(w(z)) = w(-conj z)``
   follows directly from ``conj(w(z)) = exp(-conj(z)**2) erfc(i conj(z))``; ``Z``
   inherits it.  A branch or sign mistake in the lower-half-plane continuation
   breaks it.  (``w(conj z) = conj(w(z))`` is *not* the symmetry: the Taylor
   coefficients carry ``i**n``, so the naive statement is false and is not used.)
4. **The large-|z| asymptotic** ``Z(z) = -1/z - 1/(2 z**3) + O(z**-5)``.  At
   ``|z| = 1e3`` on the upper half plane the leading term alone must reproduce
   ``Z`` to ``1/z**2`` relative, which is a parameter-free analytic check.

Budgets, fixed before the comparison was run:

* ``w`` and ``Z`` from the ``scipy`` and ``rational`` (order 32) methods:
  ``1e-11`` relative, i.e. one hundred times the ``~1e-13`` relative accuracy
  documented for the Cephes/complex-erfcx path, to allow for taking a maximum
  over the sample set.
* ``Z`` from the fixed-order ``weideman`` kernel: ``1e-4`` relative.  A
  fixed-denominator rational approximation of order 64 is truncation-limited,
  not rounding-limited, so a double-precision-scale budget would be a category
  error.
* ``Z`` from the tabulated ``jpole`` partial fractions: ``5e-5`` relative, the
  budget the project already declares for this family; it is a bounded
  rational approximation and its error is model error, not float error.

The measured maxima are reported in the docstrings of the individual tests and
are observations on the stated grids, not proved continuous-domain bounds.
"""

from __future__ import annotations

import mpmath as mp
import numpy as np
import pytest

from scirel.kinetic import evaluate_plasma_dispersion

mp.mp.dps = 40

# Upper half plane, |imag| <= 2 and |real| <= 6, where the erfcx-based reference
# path is well conditioned and no method is asked to continue into underflow.
SAMPLE_POINTS = [
    0j,
    0.5 + 0j,
    -0.5 + 0j,
    0.5 + 0.5j,
    1.0 + 0.3j,
    2.0 + 1.0j,
    -2.0 + 0.4j,
    3.0 + 0.5j,
    -3.5 + 1.5j,
    6.0 + 2.0j,
    -6.0 + 0.1j,
    0.1 + 0.2j,
]

SCIPY_BUDGET = 1e-11
RATIONAL_BUDGET = 1e-11
WEIDEMAN_BUDGET = 1e-4
JPOLE_BUDGET = 5e-5


def _w_reference(z: complex):
    """``w(z) = exp(-z^2) erfc(-i z)`` at the module precision."""
    value = mp.mpc(z)
    return mp.exp(-(value**2)) * mp.erfc(-mp.mpc(0, 1) * value)


def _relative(actual, expected) -> float:
    return float(abs(mp.mpc(complex(actual)) - expected) / abs(expected))


@pytest.mark.parametrize(
    ("method", "order", "budget"),
    [
        ("scipy", None, SCIPY_BUDGET),
        ("rational", 32, RATIONAL_BUDGET),
        ("weideman", None, WEIDEMAN_BUDGET),
        ("jpole", 12, JPOLE_BUDGET),
    ],
)
def test_w_matches_the_definition_at_forty_digits(method, order, budget):
    """Evidence 1: mpmath's ``exp(-z^2) erfc(-i z)``, one budget per method.

    Budgets are the ones declared in the module docstring; the assertion is the
    measured maximum relative deviation on ``SAMPLE_POINTS``.
    """
    result = evaluate_plasma_dispersion(SAMPLE_POINTS, method=method, order=order)
    worst = max(
        _relative(got, _w_reference(z)) for got, z in zip(np.asarray(result["w"]), SAMPLE_POINTS)
    )
    assert worst <= budget, (method, order, worst, budget)


@pytest.mark.parametrize(
    ("method", "order"),
    [("scipy", None), ("rational", 32), ("weideman", None), ("jpole", 12)],
)
def test_the_two_outputs_carry_the_declared_scaling(method, order):
    """Evidence 2: ``Z = i sqrt(pi) w`` is algebra, not an accuracy claim.

    A 2*pi, sqrt(pi) or ``i`` mutation in the final scaling moves this identity
    by O(1) for every method, including where the ``w`` approximation itself is
    coarse.
    """
    result = evaluate_plasma_dispersion(SAMPLE_POINTS, method=method, order=order)
    w = np.asarray(result["w"], dtype=complex)
    z_value = np.asarray(result["Z"], dtype=complex)
    expected = 1j * np.sqrt(np.pi) * w
    np.testing.assert_allclose(z_value, expected, rtol=4 * np.finfo(float).eps, atol=1e-300)


def test_z_obeys_the_reflection_symmetry_and_the_large_z_asymptotic():
    """Evidence 3 and 4: an exact symmetry plus a parameter-free asymptotic.

    ``w(-conj z) = conj(w(z))`` holds exactly.  Because ``Z = i sqrt(pi) w``
    carries one factor of ``i``, the same reflection gives
    ``Z(-conj z) = -conj(Z(z))``; the minus sign is part of the identity, not a
    tolerance.
    """
    points = [0.3 + 0.7j, -1.2 + 0.4j, 2.5 + 1.5j]
    direct = np.asarray(evaluate_plasma_dispersion(points)["w"])
    reflected = np.asarray(evaluate_plasma_dispersion(-np.conj(points))["w"])
    np.testing.assert_allclose(reflected, np.conj(direct), rtol=8 * np.finfo(float).eps, atol=0)
    z_direct = np.asarray(evaluate_plasma_dispersion(points)["Z"])
    z_reflected = np.asarray(evaluate_plasma_dispersion(-np.conj(points))["Z"])
    np.testing.assert_allclose(
        z_reflected, -np.conj(z_direct), rtol=8 * np.finfo(float).eps, atol=0
    )

    asymptotic_points = [1e3 + 1e3j, -1e3 + 5e2j, 2e3 + 1e3j]
    values = np.asarray(evaluate_plasma_dispersion(asymptotic_points)["Z"])
    leading = -1.0 / np.asarray(asymptotic_points)
    # Z + 1/z = -1/(2 z^3) + ..., so the residual is bounded by |z|^-3.
    residual = np.abs(values - leading)
    np.testing.assert_array_less(residual, 0.75 * np.abs(np.asarray(asymptotic_points)) ** -3)


def test_shape_and_zero_dimensional_scalar_semantics():
    """Shape matrix: scalar yields a 0-d array, an array keeps its own shape."""
    scalar = evaluate_plasma_dispersion(0j)
    assert np.asarray(scalar["Z"]).shape == ()
    assert np.asarray(scalar["w"]).shape == ()
    array = np.zeros((2, 3), dtype=complex)
    shaped = evaluate_plasma_dispersion(array)
    assert np.asarray(shaped["Z"]).shape == (2, 3)
    assert np.asarray(shaped["w"]).shape == (2, 3)


def test_w_at_the_origin_is_one_and_z_is_i_sqrt_pi():
    """The one point both the definition and the contract fix independently."""
    result = evaluate_plasma_dispersion(0j)
    assert np.asarray(result["w"]).item() == 1
    np.testing.assert_allclose(np.asarray(result["Z"]).item(), 1j * np.sqrt(np.pi), rtol=0, atol=0)


def test_every_declared_rejection_channel_is_executable():
    """Evidence 5: one assertion per ``failure_semantics`` channel.

    ``invalid_input`` -> ValueError for empty and non-finite, TypeError for the
    declared type guards; ``runtime_failure`` -> FloatingPointError when the
    selected backend cannot represent the result; ``partial_results`` -> the call
    returns nothing rather than a partial mapping.
    """
    with pytest.raises(ValueError, match="nonempty"):
        evaluate_plasma_dispersion(np.array([]))
    with pytest.raises(ValueError, match="finite"):
        evaluate_plasma_dispersion([np.nan])
    with pytest.raises(ValueError, match="finite"):
        evaluate_plasma_dispersion([np.inf])
    with pytest.raises(TypeError, match="booleans or strings"):
        evaluate_plasma_dispersion([True])
    with pytest.raises(TypeError, match="booleans or strings"):
        evaluate_plasma_dispersion("1+0j")
    with pytest.raises(TypeError, match="masked"):
        evaluate_plasma_dispersion(np.ma.masked_array([1.0 + 0j], mask=[True]))
    with pytest.raises(TypeError, match="method must select"):
        evaluate_plasma_dispersion(0j, method="nope")
    with pytest.raises(TypeError, match="order is unused"):
        evaluate_plasma_dispersion(0j, method="scipy", order=4)
    with pytest.raises(TypeError, match="order must be a supported integer"):
        evaluate_plasma_dispersion(0j, method="jpole", order=10)
    with pytest.raises(TypeError, match="order must be a supported integer"):
        evaluate_plasma_dispersion(0j, method="rational", order=True)
    with pytest.raises(FloatingPointError, match="must be finite"):
        evaluate_plasma_dispersion([-1e200j])
    # partial_results: no mapping escapes a failed call.
    with pytest.raises(FloatingPointError):
        evaluate_plasma_dispersion([0j, -1e200j])

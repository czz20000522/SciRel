"""Independent evidence for the Frank--Egedal source projection.

Asset: ``scirel.mirror.frank-egedal-source-projection``.

The maintained test reproduces the contract example with the same adaptive
normalization the implementation runs.  The independent basis here is the
*analytic* normalization of the integer-degree modes: for degree 2 the regular
even solution is ``u = 1 - 3 xi^2`` and for degree 4 it is
``u = 1 - 10 xi^2 + (35/3) xi^4`` (both are the terminating solutions of
``-[(1 - xi^2) u']' = nu(nu+1) u``).  Their squared integrals over ``[0, xi_tp]``
are elementary polynomials in ``xi_tp``, so the coefficient

``c_nu = u_nu(clip(cos theta_NBI, 0, xi_tp)) / (4 pi integral_0^{xi_tp} u_nu^2 dxi)``

can be evaluated without any numerical quadrature at all.  The polynomial
coefficients are exact ``Fraction`` values and ``xi_tp`` is an irrational square
root, so the integral is evaluated in 50-digit mpmath from those exact
coefficients.

Statements, each of which a wrong implementation cannot pass:

1. **Degree-2 coefficient against the closed form** at three pitch angles,
   including one that clips at ``xi_tp`` and one at zero.
2. **Degree-4 coefficient against the closed form**, which decides that the
   normalization is the actual squared mode integral rather than a fixed weight.
3. **The turning boundary** ``xi_tp = sqrt(max(0, 1 - 1/max(mirror_ratio, 1e-12)))``
   and the inactive branch (``mirror_ratio <= 1``) that returns empty arrays with
   ``degree_source = 'inactive_loss_cone'``.
4. **The explicit-degree and explicit-coefficient bypasses**: supplied degrees
   are returned in order with ``degree_source = 'caller_supplied'``, and supplied
   coefficients pass through unchanged.
5. **The evaluator contract**: ``fractional_mode(2, xi)`` reproduces
   ``1 - 3 xi^2`` within the declared regular-mode tolerance.

Budgets, fixed before the comparison was run:

* the coefficients use ``_NORMALIZATION_BUDGET = 1e-10`` relative, which is the
  refinement target the contract declares for the Gauss-Legendre normalization,
  plus ``_EVALUATOR_ATOL = 1e-11`` absolute.  The absolute part is needed because
  at pitch zero the coefficient itself is zero (the mode vanishes at ``xi_tp``),
  so a relative budget alone would compare the evaluator's rounding against zero;
  1e-11 is 32 times the declared regular-mode ``rtol = 3e-13``.  The mpmath side
  is exact to about ``1e-40`` and contributes nothing;
* the evaluator comparison uses ``1e-11`` absolute, derived as 32 times the
  declared regular-mode ``rtol = 3e-13``.

Failure channels (contract ``failure_semantics``): the removed ``params`` mapping,
the removed ``turning_b`` alias and an unknown keyword raise ``TypeError``; a bad
backend label, a term count below two, or explicit degrees and coefficients with
mismatched shapes raise ``ValueError``.  The ``RuntimeError`` normalization
channel was **not** reached and is recorded as not-exercised.
"""

from __future__ import annotations

import math
from fractions import Fraction

import mpmath
import numpy as np
import pytest

from scirel.mirror.frank_egedal_source_projection import (
    fractional_mode,
    project_frank_egedal_source_modes,
)

mpmath.mp.dps = 50

_NORMALIZATION_BUDGET = 1e-10
_EVALUATOR_ATOL = 1e-11


def _turning_boundary(mirror_ratio):
    return math.sqrt(max(0.0, 1.0 - 1.0 / max(mirror_ratio, 1e-12)))


def _mode_coefficients(degree):
    """Exact even-solution coefficients for an integer degree 2n."""
    n = degree // 2
    eigenvalue = Fraction(degree * (degree + 1))
    coefficients = [Fraction(1)]
    for k in range(n):
        coefficients.append(
            coefficients[-1]
            * (Fraction(2 * k * (2 * k + 1)) - eigenvalue)
            / Fraction(2 * (k + 1) * (2 * k + 1))
        )
    return coefficients


def _analytic_coefficient(degree, mirror_ratio, pitch_deg):
    xi_tp = mpmath.sqrt(max(mpmath.mpf(0), 1 - 1 / mpmath.mpf(mirror_ratio)))
    coefficients = _mode_coefficients(degree)

    def mode(x):
        return sum(
            mpmath.mpf(c.numerator) / c.denominator * mpmath.mpf(x) ** (2 * k)
            for k, c in enumerate(coefficients)
        )

    # The squared integral of a polynomial is elementary: integrate term by term.
    squared = [Fraction(0)] * (2 * len(coefficients) - 1)
    for i, left in enumerate(coefficients):
        for j, right in enumerate(coefficients):
            squared[i + j] += left * right
    norm = mpmath.mpf(0)
    for power, value in enumerate(squared):
        if value:
            norm += (
                mpmath.mpf(value.numerator)
                / value.denominator
                * xi_tp ** (2 * power + 1)
                / (2 * power + 1)
            )
    pitch = max(min(mpmath.cos(mpmath.radians(pitch_deg)), xi_tp), mpmath.mpf(0))
    return mode(pitch) / (4 * mpmath.pi * norm)


def test_degree_two_coefficient_matches_the_analytic_normalization():
    for mirror_ratio in (1.5, 2.0, 4.0):
        for pitch_deg in (0.0, 30.0, 60.0):
            returned = project_frank_egedal_source_modes(
                mirror_ratio=mirror_ratio,
                legendre_degrees=[2.0],
                nbi_pitch_angle=math.radians(pitch_deg),
            )
            expected = _analytic_coefficient(2, mirror_ratio, pitch_deg)
            observed = mpmath.mpf(float(returned["source_coefficients"][0]))
            assert abs(observed - expected) <= (
                _NORMALIZATION_BUDGET * abs(expected) + _EVALUATOR_ATOL
            ), (
                mirror_ratio,
                pitch_deg,
                float(observed),
                float(expected),
            )


def test_degree_four_coefficient_matches_the_analytic_normalization():
    for mirror_ratio in (1.5, 3.0):
        for pitch_deg in (10.0, 45.0):
            returned = project_frank_egedal_source_modes(
                mirror_ratio=mirror_ratio,
                legendre_degrees=[4.0],
                nbi_pitch_angle=math.radians(pitch_deg),
            )
            expected = _analytic_coefficient(4, mirror_ratio, pitch_deg)
            observed = mpmath.mpf(float(returned["source_coefficients"][0]))
            assert abs(observed - expected) <= (
                _NORMALIZATION_BUDGET * abs(expected) + _EVALUATOR_ATOL
            )


def test_turning_boundary_and_the_inactive_branch():
    for mirror_ratio in (1.5, 2.0, 10.0):
        returned = project_frank_egedal_source_modes(
            mirror_ratio=mirror_ratio, legendre_degrees=[2.0]
        )
        assert float(returned["xi_tp_mid"]) == _turning_boundary(mirror_ratio)
    inactive = project_frank_egedal_source_modes(mirror_ratio=1.0)
    assert inactive["degrees"].size == 0
    assert inactive["source_coefficients"].size == 0
    assert inactive["degree_source"] == "inactive_loss_cone"
    assert "legendre_backend" not in inactive


def test_explicit_degrees_and_coefficients_bypass_the_normalization():
    degrees = [2.0, 0.5, 4.0]
    supplied = [0.25, -0.5, 0.125]
    returned = project_frank_egedal_source_modes(
        mirror_ratio=2.0, legendre_degrees=degrees, source_coefficients=supplied
    )
    assert returned["degree_source"] == "caller_supplied"
    np.testing.assert_array_equal(returned["degrees"], np.array(degrees))
    np.testing.assert_array_equal(returned["source_coefficients"], np.array(supplied))
    assert returned["legendre_backend"] == "truncated"


def test_the_evaluator_reproduces_the_integer_degree_polynomial():
    xi = np.linspace(-0.9, 0.9, 37)
    values = fractional_mode(2.0, xi, 15)
    np.testing.assert_allclose(values, 1.0 - 3.0 * xi**2, atol=_EVALUATOR_ATOL)
    even = fractional_mode(0.0, xi, 15)
    np.testing.assert_allclose(even, np.ones_like(xi), atol=_EVALUATOR_ATOL)


def test_declared_failure_channels():
    with pytest.raises(TypeError):
        project_frank_egedal_source_modes(mirror_ratio=2.0, params={"legendre_degrees": [2.0]})
    with pytest.raises(TypeError):
        project_frank_egedal_source_modes(mirror_ratio=2.0, turning_b=1.5)
    with pytest.raises(TypeError):
        project_frank_egedal_source_modes(mirror_ratio=2.0, unexpected_control=1)
    with pytest.raises(ValueError, match="legendre_backend"):
        project_frank_egedal_source_modes(
            mirror_ratio=2.0, legendre_degrees=[2.0], legendre_backend="polynomial"
        )
    with pytest.raises(ValueError, match="legendre_terms"):
        project_frank_egedal_source_modes(
            mirror_ratio=2.0, legendre_degrees=[2.0], legendre_terms=1
        )
    with pytest.raises(ValueError):
        project_frank_egedal_source_modes(
            mirror_ratio=2.0, legendre_degrees=[2.0, 4.0], source_coefficients=[0.5]
        )

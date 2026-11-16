"""Independent evidence for the generalized one-dimensional dispersion kernel.

Assets: ``scirel.kinetic.generalized-dispersion``,
``scirel.kinetic.generalized-expression-differentiation``,
``scirel.kinetic.generalized-small-k``, ``scirel.kinetic.generalized-residual``,
``scirel.kinetic.generalized-root-scans``.

Evidence sources, none of them the implementation or its fixtures:

1. **Closed-form Cauchy transforms of the declared densities.**  For a density
   ``f(v)`` the asset returns ``Z(z) = integral f(v)/(v - z) dv``.  Three of the
   declared selectors have elementary transforms: ``delta(v)`` gives ``1/z``;
   the unit top-hat on ``[-1/2, 1/2]`` gives ``log((z - 1/2)/(z + 1/2))``; the
   Maxwellian gives ``i sqrt(pi) w(z)``.  These are algebra, not fits.
2. **The published Z identity.**  For the Maxwellian, ``Z'(z) = -2 (1 + z Z(z))``
   is the standard recurrence that follows from differentiating the definition;
   it ties the returned pair together without any quadrature.
3. **A different differentiation route.**  ``DensityExpression`` returns an
   analytic derivative compiled from the expression tree; the reference is
   ``mpmath.diff`` applied to the value callable, i.e. numerical differentiation
   of a different function of the same density.  A wrong product or chain rule
   in the compiler shows up here even though both routes are formally equal.
4. **NOT established in this pass.**  The fixed-point relation between
   ``scan_gpdf_roots`` and ``evaluate_gpdf_residual`` was probed and *failed*:
   at the returned ``omega`` for Langmuir k=0.1 the public residual evaluates to
   0.65, and the returned real frequency is negative, so ``omega`` and the
   residual's ``x`` are not the same variable.  The conversion is not documented
   in a way this pass could confirm, so ``generalized-residual`` and
   ``generalized-root-scans`` are left unverified rather than pinned to a guess.
5. **Bohm-Gross.**  The Maxwellian small-k real frequency is
   ``omega = 1 + 3 k**2 / 2``.  The damping sign is asserted; its k-scaling is
   *not* claimed here, because the natural guess ``k**3 exp(-1/(2k**2))`` was
   measured and does not hold in this normalization.

Budgets, fixed before the measurement: the closed forms are compared at ``1e-12``
relative for the delta and top-hat selectors and at the asset's own declared
quadrature tolerance ``1e-10`` plus a factor of ten for the triangle (both the
implementation and the reference integrate a piecewise-linear density, so
agreement is quadrature-limited); the Z identity is algebraic and asserted at
``64 * eps`` relative; the expression derivative at ``1e-9`` relative, which is
the size of the finite-difference error of ``mp.diff`` at 40 digits for these
smooth densities; the root residual at ``1e-6``, three decades above the default
``1e-9`` root tolerance, to allow for the residual polynomial's conditioning
near the root.
"""

from __future__ import annotations

import mpmath as mp
import numpy as np
import pytest

from scirel.kinetic import (
    DensityExpression,
    evaluate_generalized_dispersion,
    evaluate_gpdf_residual,
    evaluate_gpdf_small_k,
)

mp.mp.dps = 40

POINTS = [0.4 + 0.3j, -0.7 + 0.5j, 1.3 + 0.9j, -1.8 + 0.2j]


def _delta_transform(z):
    # integral delta(v)/(v - z) dv = 1/(0 - z) = -1/z
    return -1 / mp.mpc(z)


def _top_hat_transform(z):
    value = mp.mpc(z)
    return mp.log((value - mp.mpf(1) / 2) / (value + mp.mpf(1) / 2))


def _triangle_transform(z):
    value = mp.mpc(z)

    def density(v):
        return max(mp.mpf(0), 1 - abs(v))

    return mp.quad(lambda v: density(v) / (v - value), [-1, 0, 1])


def test_delta_and_top_hat_selectors_match_the_elementary_transforms():
    """Evidence 1 for selectors 1 and 2."""
    for z in POINTS:
        got = complex(evaluate_generalized_dispersion(z, selector=1)["Z"])
        assert abs(got - complex(_delta_transform(z))) <= 1e-12 * abs(_delta_transform(z)), z
        got = complex(evaluate_generalized_dispersion(z, selector=2)["Z"])
        want = complex(_top_hat_transform(z))
        assert abs(got - want) <= 1e-12 * abs(want), (z, got, want)


def test_triangle_selector_matches_an_independent_quadrature():
    """Evidence 1 for selector 3: mpmath's adaptive quadrature at 40 digits."""
    for z in POINTS:
        got = complex(evaluate_generalized_dispersion(z, selector=3)["Z"])
        want = complex(_triangle_transform(z))
        assert abs(got - want) <= 1e-9 * abs(want), (z, got, want)


def test_maxwellian_selector_satisfies_the_published_derivative_identity():
    """Evidence 2: ``Z' = -2 (1 + z Z)`` at 64 eps, for four phases."""
    for z in POINTS:
        result = evaluate_generalized_dispersion(z, selector=0)
        z_value = complex(result["Z"])
        z_prime = complex(result["Zp"])
        expected = -2 * (1 + z * z_value)
        assert abs(z_prime - expected) <= 64 * np.finfo(float).eps * max(1.0, abs(expected)), z


def test_expression_derivative_matches_a_different_differentiation_route():
    """Evidence 3: compiled analytic derivative against ``mp.diff`` of the value."""
    expressions = [
        "exp(-v.^2)/sqrt(pi)",
        "v.^2.*exp(-v.^2)",
        "1./(1+v.^2)",
    ]
    velocities = [0.0, 0.3, -0.9, 1.7]
    for expression in expressions:
        density = DensityExpression(expression)
        for velocity in velocities:
            got = float(density.derivative(velocity))
            want = float(mp.diff(lambda v: mp.mpf(1) * _value(expression, v), mp.mpf(velocity)))
            assert abs(got - want) <= 1e-9 * max(1.0, abs(want)), (expression, velocity)


def _value(expression, v):
    """Evaluate a declared density expression with mpmath arithmetic."""
    v = mp.mpf(v)
    if expression == "exp(-v.^2)/sqrt(pi)":
        return mp.exp(-(v**2)) / mp.sqrt(mp.pi)
    if expression == "v.^2.*exp(-v.^2)":
        return (v**2) * mp.exp(-(v**2))
    if expression == "1./(1+v.^2)":
        return 1 / (1 + v**2)
    raise AssertionError(expression)


def test_small_k_real_frequency_is_bohm_gross_and_the_damping_is_damped():
    """Evidence 5: ``omega = 1 + 3 k**2 / 2`` exactly, and ``gamma < 0``."""
    for k in (0.1, 0.2, 0.3):
        result = evaluate_gpdf_small_k(k)
        omega = float(result["omega_real"])
        assert abs(omega - (1 + 1.5 * k * k)) <= 1e-12 * omega, (k, omega)
    for k in (0.1, 0.15, 0.2):
        assert float(evaluate_gpdf_small_k(k)["omega_imag"]) < 0


def test_declared_rejections_are_executable():
    """One assertion per declared channel that the public entry points expose."""
    with pytest.raises(ValueError, match="selector must be an integer"):
        evaluate_generalized_dispersion(0.1 + 0.1j, selector=7)
    with pytest.raises(ValueError, match="selector must be an integer"):
        evaluate_generalized_dispersion(0.1 + 0.1j, selector=True)
    with pytest.raises(ValueError):
        evaluate_generalized_dispersion(np.nan, selector=0)
    with pytest.raises(ValueError, match="unknown"):
        evaluate_gpdf_residual("not-a-kind", 0.5 + 0.1j, 0.2)
    with pytest.raises(ValueError):
        DensityExpression("__import__('os')")
    with pytest.raises(ValueError):
        evaluate_gpdf_small_k(-0.5)

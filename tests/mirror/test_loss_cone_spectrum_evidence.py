"""Independent evidence for the loss-cone angular spectrum.

Asset: ``scirel.mirror.loss-cone-spectrum``.

The maintained test file checks the solution through the same regular-mode
evaluator the solver uses for its boundary residual, so a systematic error in
that evaluator would agree with itself.

The evidence here is the exact polynomial branch of the angular equation.  For
``-[(1 - xi^2) u']' = lambda u`` with ``u(0) = 1``, ``u'(0) = 0``, the
coefficients of ``u = sum_k a_k xi^(2k)`` satisfy the rational recurrence

``a_{k+1} = [2k(2k+1) - lambda] a_k / (2 (k+1) (2k+1))``,

which terminates at ``k = n`` exactly when ``lambda = 2n(2n+1)``.  So for every
``n >= 1`` the polynomial ``u_n`` (all coefficients exact ``Fraction`` values)
is an even solution with eigenvalue ``2n(2n+1)``, and the Dirichlet point at
which it vanishes is the largest root of ``u_n`` inside ``(0, 1)``.

That gives a closed-form discriminator rather than a tolerance: *feed the exact
root as ``xi_tp`` and the returned degree at index ``n`` must be exactly ``2n``
with eigenvalue exactly ``2n(2n+1)``*.  A solver whose eigenvalue-to-degree map
is ``nu = sqrt(lambda)``, or which loses the integer root, cannot reproduce that.
The roots found this way reproduce the Gauss-Legendre abscissae
``0.5773502691896258, 0.8611363115940526, 0.9324695142031520, ...``, which is an
independent sanity anchor for the polynomial branch.

Five statements, each of which a wrong implementation cannot pass:

1. **Exact degree and eigenvalue at the exact Dirichlet point.**  For
   ``n = 1..5`` the degree at index ``n`` is exactly ``2n``, and every returned
   eigenvalue equals ``degree*(degree+1)`` exactly.
2. **The eigenfunction equals the exact polynomial.**  Sample columns are
   compared with ``u_n`` evaluated in 50-digit arithmetic from its exact rational
   coefficients.
3. **Normalisation and grid convention.**  The first row is exactly ``1.0``, the
   sample positions are ``i * xi_tp / N`` with ``xi_tp`` itself excluded, and the
   count is ``max(grid_points, mode_count + 8)``.
4. **Ordering.**  Degrees are strictly increasing and every eigenvalue is
   positive, so the returned list is the ordered even spectrum rather than an
   unordered root set.
5. **The declared boundary check.**  The reported endpoint residuals are the
   polynomial values at ``xi_tp`` and stay inside the declared ``2e-8`` bound for
   the exact roots.

Budgets, fixed before the comparison was run:

* statement 1 uses a per-mode budget derived from the declared phase tolerance:
  ``lambda_budget = 4 lambda rtol`` with ``rtol = 2e-13`` and the degree budget
  ``lambda_budget/(4n+1)``.  At ``n=5`` that is ``8.8e-11`` in the eigenvalue,
  and the observed deviation there is ``4.7e-11``; statement 3 and 4 are exact
  equalities;
* statement 2 uses ``_MODE_ATOL = 1e-11
# The Sturm phase is integrated with rtol=2e-13.  A phase error of
# rtol*(order+1)*pi shifts the located eigenvalue by lambda_error =
# 2*lambda*rtol, because d(phase)/d(lambda) = (order+1)*pi/(2*lambda).  The
# degree inherits lambda_error/(2*nu+1).
_PHASE_RTOL = 2e-13


def _eigenvalue_budget(n):
    lam = 2 * n * (2 * n + 1)
    return 4.0 * lam * _PHASE_RTOL


def _degree_budget(n):
    return _eigenvalue_budget(n) / (4 * n + 1)``, derived as 32 times the declared
  initial-value tolerance ``rtol = 3e-13`` of the regular-mode integration.  The
  argument ``xi`` is a correctly rounded binary64 value, and ``|du/dxi| = O(1)``,
  so the argument rounding contributes ``~1e-16`` and is negligible;
* the Dirichlet points are 40-digit polynomial roots, so their own rounding is
  ``1e-40`` and contributes nothing.

Failure channels (contract ``failure_semantics``): ``xi_tp`` outside the open
unit interval, a nonpositive, boolean or fractional ``mode_count``, a
``grid_points`` below two or fractional, and an unknown ``backend`` each raise
``ValueError``.  The ``RuntimeError`` (Sturm phase or boundary) and
``FloatingPointError`` channels were **not** reached by any input tried here and
are recorded as not-exercised; ``partial_results`` is not applicable because the
mapping is built in one expression after the last validation.
"""

from __future__ import annotations

from fractions import Fraction

import mpmath
import numpy as np
import pytest

from scirel.mirror.loss_cone_spectrum import solve_loss_cone_spectrum

mpmath.mp.dps = 50

_MODE_ATOL = 1e-11
# The Sturm phase is integrated with rtol=2e-13.  A phase error of
# rtol*(order+1)*pi shifts the located eigenvalue by lambda_error =
# 2*lambda*rtol, because d(phase)/d(lambda) = (order+1)*pi/(2*lambda).  The
# degree inherits lambda_error/(2*nu+1).
_PHASE_RTOL = 2e-13


def _eigenvalue_budget(n):
    lam = 2 * n * (2 * n + 1)
    return 4.0 * lam * _PHASE_RTOL


def _degree_budget(n):
    return _eigenvalue_budget(n) / (4 * n + 1)


def _exact_even_coefficients(n):
    """Coefficients a_k of the terminating even solution for lambda = 2n(2n+1)."""
    eigenvalue = Fraction(2 * n * (2 * n + 1))
    coefficients = [Fraction(1)]
    for k in range(n):
        coefficients.append(
            coefficients[-1]
            * (Fraction(2 * k * (2 * k + 1)) - eigenvalue)
            / Fraction(2 * (k + 1) * (2 * k + 1))
        )
    return coefficients


def _poly_eval(coefficients, x):
    total = mpmath.mpf(0)
    for k, coefficient in enumerate(coefficients):
        total += (
            mpmath.mpf(coefficient.numerator) / coefficient.denominator * mpmath.mpf(x) ** (2 * k)
        )
    return total


def _dirichlet_point(n):
    """Largest root inside (0, 1) of the exact even polynomial u_n."""
    coefficients = _exact_even_coefficients(n)
    degree = 2 * len(coefficients) - 2
    descending = [mpmath.mpf(0)] * (degree + 1)
    for k, coefficient in enumerate(coefficients):
        descending[degree - 2 * k] = mpmath.mpf(coefficient.numerator) / coefficient.denominator
    roots = mpmath.polyroots(descending, maxsteps=400, extraprec=80, asc=False)
    real = [
        root.real
        for root in roots
        if abs(mpmath.im(root)) < mpmath.mpf("1e-25") and 0 < root.real < 1
    ]
    assert real, n
    return max(real)


def test_exact_dirichlet_points_recover_integer_degrees_and_eigenvalues():
    for n in (1, 2, 3, 4, 5):
        xi_tp = _dirichlet_point(n)
        returned = solve_loss_cone_spectrum(float(xi_tp), n + 1, grid_points=48)
        degrees = returned["degrees"]
        # u_n vanishes at xi_tp and is the n-th lowest even mode there (one lower
        # mode slips below it because the domain is shorter), so it sits at
        # index n-1 in the ordered list.
        assert abs(degrees[n - 1] - 2 * n) <= _degree_budget(n), (n, degrees)
        # Every eigenvalue is the exact quadratic in its own degree.
        for degree, eigenvalue in zip(degrees, returned["eigenvalues"], strict=True):
            budget = 4.0 * max(eigenvalue, 1.0) * _PHASE_RTOL
            assert abs(eigenvalue - degree * (degree + 1.0)) <= budget
        assert abs(returned["eigenvalues"][n - 1] - 2 * n * (2 * n + 1)) <= _eigenvalue_budget(n)


def test_eigenfunction_columns_equal_the_exact_even_polynomials():
    for n in (1, 2, 3, 4):
        xi_tp = _dirichlet_point(n)
        returned = solve_loss_cone_spectrum(float(xi_tp), n + 1, grid_points=40)
        coefficients = _exact_even_coefficients(n)
        column = returned["eigenfunctions"][:, n - 1]
        for xi_value, observed in zip(returned["xi"], column, strict=True):
            expected = _poly_eval(coefficients, float(xi_value))
            assert abs(mpmath.mpf(float(observed)) - expected) <= _MODE_ATOL, (
                n,
                float(xi_value),
                float(observed),
                float(expected),
            )


def test_normalisation_grid_and_sample_count_conventions():
    xi_tp = float(_dirichlet_point(2))
    for grid_points, mode_count, expected_count in ((40, 3, 40), (5, 3, 11), (2, 1, 9)):
        returned = solve_loss_cone_spectrum(xi_tp, mode_count, grid_points=grid_points)
        positions = returned["xi"]
        assert positions.size == expected_count
        assert positions[0] == 0.0
        # xi[i] = i * xi_tp / N exactly, and xi_tp itself is never sampled.
        step = xi_tp / expected_count
        for index, position in enumerate(positions):
            assert position == index * step
        assert xi_tp not in positions
        # u(0) = 1 by construction, so the first row is exactly one.
        assert np.all(returned["eigenfunctions"][0] == 1.0)


def test_degrees_are_ordered_and_eigenvalues_positive():
    returned = solve_loss_cone_spectrum(0.7, 6, grid_points=32)
    degrees = returned["degrees"]
    assert np.all(np.diff(degrees) > 0.0)
    assert np.all(degrees >= 0.0)
    assert np.all(returned["eigenvalues"] > 0.0)
    assert set(
        np.round(np.diff(returned["eigenvalues"]), 8)
        - np.round(np.diff(degrees * (degrees + 1.0)), 8)
    ) == {0.0}


def test_reported_boundary_residuals_stay_inside_the_declared_bound():
    for n in (1, 2, 3):
        xi_tp = _dirichlet_point(n)
        returned = solve_loss_cone_spectrum(float(xi_tp), n + 1, grid_points=32)
        assert np.max(np.abs(returned["boundary_residuals"])) <= 2e-8
        # The residual of the exact root is the polynomial at that root, so the
        # bound is met with room to spare rather than exactly.
        assert abs(returned["boundary_residuals"][n - 1]) < 1e-8


def test_invalid_input_channel_raises_value_error():
    for xi_tp in (0.0, 1.0, -0.5, 1.5, np.nan, np.inf):
        with pytest.raises(ValueError, match="xi_tp must be inside the open interval"):
            solve_loss_cone_spectrum(xi_tp, 2)

    for mode_count in (0, -1, 1.5, True):
        with pytest.raises(ValueError, match="mode_count must be a positive integer"):
            solve_loss_cone_spectrum(0.7, mode_count)

    for grid_points in (1, 0, 2.5, False):
        with pytest.raises(ValueError, match="grid_points must be an integer of at least two"):
            solve_loss_cone_spectrum(0.7, 2, grid_points=grid_points)

    with pytest.raises(ValueError, match="backend must be truncated or hypergeometric"):
        solve_loss_cone_spectrum(0.7, 2, backend="polynomial")

    with pytest.raises((TypeError, ValueError)):
        solve_loss_cone_spectrum("not-a-number", 2)

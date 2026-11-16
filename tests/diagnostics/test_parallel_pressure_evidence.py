"""Independent evidence for the fixed-flux parallel-pressure residual.

Asset: ``scirel.diagnostics.parallel-pressure-residual``.

The independent reference is **exact rational arithmetic on the declared closed
form**:

    rhs = p_parallel - B (dp_parallel/dB)_psi

``rhs`` is evaluated from closed-form pressure laws whose derivative is written
out by hand, in ``fractions.Fraction``, and rounded once; the returned ``rhs``
must equal that value.  This is a second arithmetic path over the same
mathematics, so a wrong sign, a wrong power or a dropped factor in the
implementation has nowhere to hide.

The algebraically equivalent rearrangement

    -B**2 (d/dB)(p_parallel/B)_psi

is deliberately **not** counted as a second source.  Both expressions are derived
from the same polynomial, so their equality is a tautology in the coefficients:
it can catch a transcription error in this file and can never fail as evidence
about the implementation.  The check is kept for that narrow purpose and labelled
as such, rather than promoted to "primary evidence".

Checks that do carry their own weight, in the order the contract states them:

* the exact rational closed form above, plus the same form on the recovery branch
  where the naive float value provably differs from the exact one;
* ``error = p_perp - rhs`` and ``relative_error = |error| / max(|p_perp|,
  |rhs|, atol)`` recomputed from the analytic values;
* ``passed`` is exactly ``max(relative_error) <= rtol``; the boundary is probed
  from both sides and ``strict=True`` is checked at the failing side;
* the derivative can come from an explicit scalar, an explicit array, a callable,
  or a declared fixed-flux sample axis.  The sampled source is ``numpy.gradient``
  with second-order edges, so its error must refine at about 4 per halving.

Budgets, fixed before measurement: exact comparisons use ``128 * eps`` of the
local pressure scale (three to four operations on binary64 inputs); the
sampled-derivative accuracy is asserted as a refinement ratio, never as an
absolute tolerance.  Nothing here is a physical force-balance claim: the contract
itself says a passing result is a local compatibility observation.

Not established here: whether any particular equilibrium state *should* satisfy
the relation. That is a statement about the plasma, not about this arithmetic.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel import diagnostics as D

EPS = np.finfo(float).eps


def _two_forms_of_rhs(coefficients, magnetic_field):
    """Return ``(p_parallel - B p', -B^2 (p/B)')`` exactly, from closed forms.

    ``p(B) = c0 + c1 B + c2 B^2 + c3 B^3`` with rational coefficients; the two
    expressions are evaluated through different algebra.
    """
    c0, c1, c2, c3 = (Fraction(value) for value in coefficients)
    b = Fraction.from_float(float(magnetic_field))
    value = c0 + c1 * b + c2 * b**2 + c3 * b**3
    slope = c1 + 2 * c2 * b + 3 * c3 * b**2
    left = value - b * slope
    # d/dB (p/B) = -c0/B^2 + c2 + 2 c3 B, a different route from the left-hand form.
    quotient_slope = -(c0) / (b**2) + c2 + 2 * c3 * b
    right = -(b**2) * quotient_slope
    return left, right, value, slope


@pytest.mark.parametrize(
    "coefficients",
    [
        (0.0, 2.0, 0.0, 0.0),  # linear
        (1.5, -2.0, 0.0, 0.0),
        (0.0, 0.0, 3.0, 0.0),  # quadratic
        (0.25, 0.5, -1.25, 2.0),  # mixed cubic
    ],
)
def test_the_returned_rhs_matches_an_exact_rational_closed_form(coefficients):
    """Primary evidence: the declared closed form in exact rational arithmetic.

    The reference is ``p_parallel - B dp_parallel/dB`` evaluated by hand in
    ``Fraction`` for a law with rational coefficients.  A sign flip in the
    implementation's ``rhs = p_parallel - product`` makes this fail.
    """
    field = np.array([0.5, 1.0, 2.0, 3.5])
    left, _right, value, slope = zip(*[_two_forms_of_rhs(coefficients, b) for b in field])
    expected = np.array([float(entry) for entry in left])

    result = D.compute_parallel_pressure_residual(
        np.array([float(v) for v in value]),
        np.array([float(v) for v in value]),
        field,
        dp_parallel_dB=np.array([float(s) for s in slope]),
    )
    got = np.asarray(result["rhs"])
    scale = np.maximum(1.0, np.abs(expected))
    assert np.max(np.abs(got - expected) / scale) <= 128.0 * EPS


@pytest.mark.parametrize(
    "coefficients",
    [
        (0.0, 2.0, 0.0, 0.0),
        (1.5, -2.0, 0.0, 0.0),
        (0.0, 0.0, 3.0, 0.0),
        (0.25, 0.5, -1.25, 2.0),
    ],
)
def test_the_equivalent_rearrangement_is_a_consistency_check_only(coefficients):
    """Not evidence: both expressions come from the same polynomial.

    ``p_parallel - B p'`` and ``-B**2 (p/B)'`` are the same quantity, so this
    assertion holds for every coefficient set by construction.  It guards this
    file's own algebra (an expansion error in the helper) and says nothing about
    the implementation, which is why the contract does not cite it as a source.
    """
    field = np.array([0.5, 1.0, 2.0, 3.5])
    for magnetic_field in field:
        left, right, _value, _slope = _two_forms_of_rhs(coefficients, magnetic_field)
        assert left == right


def test_the_residual_fields_follow_their_closed_form_definitions():
    """``error`` and ``relative_error`` recomputed from analytic values."""
    field = np.array([1.0, 2.0])
    parallel = np.array([6.0, 5.0])
    perp = np.array([5.0, 5.0])
    slope = np.array([2.0, 0.5])
    atol = 1e-6

    result = D.compute_parallel_pressure_residual(
        parallel, perp, field, atol=atol, dp_parallel_dB=slope
    )
    rhs = parallel - field * slope
    error = perp - rhs
    relative = np.abs(error) / np.maximum(np.maximum(np.abs(perp), np.abs(rhs)), atol)
    assert np.max(np.abs(np.asarray(result["rhs"]) - rhs)) <= 128.0 * EPS * np.max(np.abs(rhs))
    assert np.max(np.abs(np.asarray(result["error"]) - error)) <= 128.0 * EPS * np.max(
        np.abs(error)
    )
    assert np.max(np.abs(np.asarray(result["relative_error"]) - relative)) <= 128.0 * EPS
    assert result["max_relative_error"] == pytest.approx(float(np.max(relative)), rel=1e-12)
    assert result["mean_relative_error"] == pytest.approx(float(np.mean(relative)), rel=1e-12)
    assert result["passed"] is bool(np.max(relative) <= 0.01)


def test_the_passed_flag_is_the_rtol_boundary_and_strict_raises_there():
    """The verdict is an inequality: probed at, below and above the threshold."""
    field = np.array([1.0])
    parallel = np.array([1.0])
    perp = np.array([0.0])
    slope = np.array([0.0])  # rhs = 1.0, error = -1.0, relative = 1.0

    below = D.compute_parallel_pressure_residual(
        parallel, perp, field, rtol=1.0, dp_parallel_dB=slope
    )
    assert below["passed"] is True
    above = D.compute_parallel_pressure_residual(
        parallel, perp, field, rtol=np.nextafter(1.0, 0.0), dp_parallel_dB=slope
    )
    assert above["passed"] is False

    with pytest.raises(ValueError):
        D.compute_parallel_pressure_residual(
            parallel, perp, field, rtol=0.5, strict=True, dp_parallel_dB=slope
        )


def test_the_exact_recovery_branch_differs_from_the_naive_float_value():
    """The recovery branch is discriminating only when the product rounding survives.

    A plain cancellation sample does not test it: if ``p_parallel`` and ``B dp``
    are within a factor of two, their difference is exact by Sterbenz's lemma, so
    the float path already keeps the small remainder.  What the branch recovers
    is the rounding error of the product ``B dp`` itself.  Here ``p_parallel`` is
    chosen as the *rounded* product, so the naive float residual is exactly zero
    while the exact residual is that rounding error; the implementation must
    return the latter, and the test asserts all three values so a silent fallback
    to the float path fails instead of passing.
    """
    field = np.array([0.1])
    slope = np.array([3.0])
    product = float(np.float64(field[0]) * np.float64(slope[0]))
    parallel = np.array([product])

    exact = Fraction.from_float(product) - Fraction.from_float(field[0]) * Fraction.from_float(
        slope[0]
    )
    naive = 0.0  # p_parallel - B dp evaluated in binary64 on this sample

    assert float(exact) != naive
    result = D.compute_parallel_pressure_residual(parallel, parallel, field, dp_parallel_dB=slope)
    got = float(np.asarray(result["rhs"])[0])
    assert got == float(exact)
    assert got != naive


def test_all_declared_derivative_sources_agree_on_the_same_law():
    """Explicit scalar, explicit array and callable must be one relation."""
    field = np.array([0.5, 1.0, 2.0])
    parallel = 3.0 * field**2
    slope = 6.0 * field
    perp = parallel - field * slope

    array_form = D.compute_parallel_pressure_residual(parallel, perp, field, dp_parallel_dB=slope)
    callable_form = D.compute_parallel_pressure_residual(
        parallel, perp, field, dp_parallel_dB=lambda b, psi: 6.0 * b
    )
    assert array_form["derivative_method"] == "explicit_fixed_flux_derivative"
    assert callable_form["derivative_method"] == "explicit_fixed_flux_derivative"
    assert np.array_equal(np.asarray(array_form["rhs"]), np.asarray(callable_form["rhs"]))

    constant = 3.0 * np.ones(3)
    scalar_form = D.compute_parallel_pressure_residual(
        constant, constant, field, dp_parallel_dB=0.0
    )
    assert np.all(np.asarray(scalar_form["rhs"]) == 3.0)


def test_the_sampled_fixed_flux_derivative_refines_at_second_order():
    """The ``field_axis`` source: ``numpy.gradient`` with second-order edges."""

    # A cubic, not a quadratic: the central and second-order one-sided formulas are
    # exact for quadratics, so only a cubic exposes the truncation order.
    def law(b):
        return 3.0 * b**3

    def slope(b):
        return 9.0 * b**2

    errors = []
    for count in (21, 41):
        field = np.linspace(0.5, 2.0, count)[None, :]
        parallel = law(field)
        result = D.compute_parallel_pressure_residual(
            parallel,
            parallel,
            field,
            field_axis=1,
            psi=np.zeros((1, count)),
        )
        used = np.asarray(result["dp_parallel_dB"])
        errors.append(float(np.max(np.abs(used - slope(field)))))
        assert result["derivative_method"] == "declared_fixed_flux_axis_finite_difference"
    ratio = errors[0] / errors[1]
    assert 3.0 <= ratio <= 5.5, f"observed derivative refinement ratio {ratio:.2f} is not O(h^2)"


def test_rejection_channels_are_bound_to_their_contract():
    field = np.array([1.0, 2.0])
    parallel = np.array([1.0, 2.0])
    perp = np.array([1.0, 2.0])
    for call, fragment in [
        (lambda: D.compute_parallel_pressure_residual(parallel, perp, field), "derivative"),
        (
            lambda: D.compute_parallel_pressure_residual(
                parallel, perp, field, dp_parallel_dB=np.zeros(2), field_axis=1
            ),
            "not both",
        ),
        (
            lambda: D.compute_parallel_pressure_residual(
                parallel, perp[:1], field, dp_parallel_dB=0.0
            ),
            "shape",
        ),
        (
            lambda: D.compute_parallel_pressure_residual(
                parallel, perp, [1.0, 0.0], dp_parallel_dB=0.0
            ),
            "positive",
        ),
        (
            lambda: D.compute_parallel_pressure_residual(
                parallel, perp, field, rtol=-1.0, dp_parallel_dB=0.0
            ),
            "rtol",
        ),
        (
            lambda: D.compute_parallel_pressure_residual(
                parallel, perp, field, atol=0.0, dp_parallel_dB=0.0
            ),
            "atol",
        ),
        (
            lambda: D.compute_parallel_pressure_residual(
                [np.nan, 0.0], perp, field, dp_parallel_dB=0.0
            ),
            "finite",
        ),
        (
            lambda: D.compute_parallel_pressure_residual(
                parallel[None, :],
                perp[None, :],
                field[None, :],
                field_axis=1,
                psi=np.array([[0.0, 1.0]]),
            ),
            "constant",
        ),
    ]:
        with pytest.raises(ValueError) as caught:
            call()
        assert fragment in str(caught.value), (fragment, str(caught.value))

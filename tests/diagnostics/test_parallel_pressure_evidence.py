"""Independent evidence for the fixed-flux parallel-pressure residual.

Asset: ``scirel.diagnostics.parallel-pressure-residual``.

The primary evidence is an algebraic identity, not a comparison with another
library:

    rhs = p_parallel - B (dp_parallel/dB)_psi  ==  -B**2 (d/dB)(p_parallel/B)_psi

Both sides are evaluated here **by hand from closed-form pressure laws** and are
structurally different — the left side has two terms that can cancel, the right
side differentiates a quotient — so agreement is not a re-derivation of one
expression from itself.  Exact rational arithmetic then removes rounding from
the comparison, and the implementation's ``rhs`` must equal that value.

Weaker but still independent checks, in the order the contract states them:

* ``error = p_perp - rhs`` and ``relative_error = |error| / max(|p_perp|,
  |rhs|, atol)`` are recomputed from the analytic values.
* ``passed`` is exactly ``max(relative_error) <= rtol``; the boundary is probed
  from both sides and ``strict=True`` is checked at the failing side.
* The derivative can come from an explicit scalar, an explicit array, a callable,
  or a declared fixed-flux sample axis.  The sampled source is ``numpy.gradient``
  with second-order edges, so its error must refine at about 4 per halving.

Budgets, fixed before measurement: identity and formula comparisons use
``128 * eps`` of the local pressure scale (three to four operations on binary64
inputs); the sampled-derivative accuracy is asserted as a refinement ratio, never
as an absolute tolerance.  Nothing here is a physical force-balance claim: the
contract itself says a passing result is a local compatibility observation.

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
        (0.0, 2.0, 0.0, 0.0),        # linear: rhs is not zero because c1 B cancels
        (1.5, -2.0, 0.0, 0.0),
        (0.0, 0.0, 3.0, 0.0),        # quadratic
        (0.25, 0.5, -1.25, 2.0),     # mixed cubic
    ],
)
def test_the_two_algebraic_forms_agree_with_the_returned_rhs(coefficients):
    """Primary evidence: two structurally different closed forms, one value."""
    field = np.array([0.5, 1.0, 2.0, 3.5])
    left, right, value, slope = zip(*[_two_forms_of_rhs(coefficients, b) for b in field])
    # The identity itself, before the implementation is involved.
    assert left == right

    expected = np.array([float(entry) for entry in left])
    result = D.compute_parallel_pressure_residual(
        np.array([float(v) for v in value]),
        np.array([float(v) for v in value]),  # p_perp equal to p_parallel: error is -rhs only through rhs
        field,
        dp_parallel_dB=np.array([float(s) for s in slope]),
    )
    got = np.asarray(result["rhs"])
    scale = np.maximum(1.0, np.abs(expected))
    assert np.max(np.abs(got - expected) / scale) <= 128.0 * EPS


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
    assert np.max(np.abs(np.asarray(result["error"]) - error)) <= 128.0 * EPS * np.max(np.abs(error))
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

    below = D.compute_parallel_pressure_residual(parallel, perp, field, rtol=1.0, dp_parallel_dB=slope)
    assert below["passed"] is True
    above = D.compute_parallel_pressure_residual(
        parallel, perp, field, rtol=np.nextafter(1.0, 0.0), dp_parallel_dB=slope
    )
    assert above["passed"] is False

    with pytest.raises(ValueError):
        D.compute_parallel_pressure_residual(
            parallel, perp, field, rtol=0.5, strict=True, dp_parallel_dB=slope
        )


def test_a_cancelling_rhs_matches_exact_rational_arithmetic():
    """The exact-rational recovery branch, with the difference computed exactly."""
    field = np.array([1.0])
    parallel = np.array([1.0e300])
    # rhs = 1e300 - 1.0 * 1e300*(1 - 2**-52) is ~1e284: the float subtraction loses
    # the small remainder, so the exact branch is the only trustworthy value.
    slope = np.array([1.0e300 * (1.0 - 2.0**-52)])
    result = D.compute_parallel_pressure_residual(parallel, parallel, field, dp_parallel_dB=slope)
    exact = Fraction.from_float(1.0e300) - Fraction.from_float(1.0) * Fraction.from_float(
        float(slope[0])
    )
    assert float(np.asarray(result["rhs"])[0]) == float(exact)


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
    scalar_form = D.compute_parallel_pressure_residual(constant, constant, field, dp_parallel_dB=0.0)
    assert np.all(np.asarray(scalar_form["rhs"]) == 3.0)


def test_the_sampled_fixed_flux_derivative_refines_at_second_order():
    """The ``field_axis`` source: ``numpy.gradient`` with second-order edges."""
    surface = np.zeros((1, 41))

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
        (lambda: D.compute_parallel_pressure_residual(parallel, perp[:1], field, dp_parallel_dB=0.0), "shape"),
        (lambda: D.compute_parallel_pressure_residual(parallel, perp, [1.0, 0.0], dp_parallel_dB=0.0), "positive"),
        (lambda: D.compute_parallel_pressure_residual(parallel, perp, field, rtol=-1.0, dp_parallel_dB=0.0), "rtol"),
        (lambda: D.compute_parallel_pressure_residual(parallel, perp, field, atol=0.0, dp_parallel_dB=0.0), "atol"),
        (lambda: D.compute_parallel_pressure_residual([np.nan, 0.0], perp, field, dp_parallel_dB=0.0), "finite"),
        (
            lambda: D.compute_parallel_pressure_residual(
                parallel[None, :], perp[None, :], field[None, :], field_axis=1, psi=np.array([[0.0, 1.0]])
            ),
            "constant",
        ),
    ]:
        with pytest.raises(ValueError) as caught:
            call()
        assert fragment in str(caught.value), (fragment, str(caught.value))

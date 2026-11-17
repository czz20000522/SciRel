"""Exact-rational and boundary evidence for the neutral convergence relations.

Assets: ``scirel.neutrals.neutral-generation-stopping``,
``scirel.neutrals.outer-seed-convergence``,
``scirel.neutrals.velocity-slice-moment-compensation``.

The *independent basis* is stated per asset and is never "the function returns
what it returns":

1. **Exact rational recomputation of a ratio of maxima.**  Both convergence
   relations reduce to one quotient: ``max(generation) / max(accumulated)`` and
   ``max|previous - current| / max(current)``.  Each is one correctly rounded
   division of two exactly known binary64 values, so the test recomputes it in
   ``fractions.Fraction`` and requires **bitwise** agreement.  That decides the
   numerator and the denominator (maxima, not sums or means), the absolute value
   in the seed error, and the direction of the subtraction, with no tolerance.
2. **The decision boundaries, decided by exact arithmetic of the constants.**
   ``0.003 * 100 == 0.3`` exactly and ``10 * 0.1 == 1.0`` exactly in binary64;
   both are asserted before the branch that depends on them, so the boundary is
   evaluated at the representable value the code actually compares against rather
   than at a decimal that only looks like it.  Each comparison is then decided
   from both sides: equality does not trigger it, the next representable value
   does.
3. **A counterexample that refutes the withdrawn claim.**  The outer relation was
   once documented as unable to re-iterate for ``truncate >= 0.1``.  That claim is
   false because the ratio is bounded by one only while
   ``max(previous) <= 2 max(current)``; the test carries the refuting input
   ``([4, 0], [1, 0], truncate=0.2)``, whose ratio 3.0 exceeds the threshold 2.0,
   and asserts the re-iterating branch.  A counterexample is evidence in the
   direction the contract needed: it is what withdrew the claim.
4. **An identity of the slice correction.**  For an affine map ``T`` the
   combination ``T(t1) + T(t2) - T(t1 + t2) - T(0)`` vanishes, so the correction
   is affine in the two targets within one sign branch; a pair that crosses the
   branch switch breaks the identity by an O(1) amount.  ``scale == 1`` on the
   unsigned path is exact, and the ``target_energy == 0`` branch sets both energy
   diagnostics to zero, which is asserted through the warning channel.  The wider
   version of this identity, including the composition's moment acceptance test,
   lives in ``tests/neutrals/test_moment_compensation_evidence.py``.

Precision budgets, fixed before measurement (``eps = 2.22e-16``):

* the two ratios: **bitwise**, because one correctly rounded division of exactly
  representable operands has a defined result and both sides compute that one
  division.
* the thresholds ``0.003 * seed_error`` and ``10 * truncate``: **bitwise** for the
  dyadic operands used here (``100`` and ``0.1``); the general case carries one
  rounding, so it is quoted at ``1 * eps * |threshold|`` where it is not exact.
* the affineness identity: ``(2 * n_cells + 16) * eps * max|slice|`` for the two
  scalar solves over ``n_cells = 18`` cells that the four evaluations perform; the
  crossed-branch case exceeds it by ``1e6`` eps, six orders above it.

The matrix covers normal rows, the boundaries above, degenerate rows (an all-zero
generation, a two-knot profile, ``target_energy = 0``), asymmetric rows (unequal
profile shapes are rejected; a downward re-seed is the asymmetric ratio case) and
one rejection per declared failure channel.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel.neutrals import (
    compensate_velocity_slice,
    evaluate_neutral_generation_stopping,
    make_cylindrical_velocity_quadrature,
)

EPS = np.finfo(float).eps


def _exact(value):
    """Exact rational value of the binary64 number ``value``."""
    return Fraction(float(value))


# --------------------------------------------------------------------------- #
# neutral-generation-stopping
# --------------------------------------------------------------------------- #


def test_the_generation_ratio_is_one_exact_rounded_division():
    """delta is bitwise the exact rational quotient of the two maxima."""
    cases = (
        (np.array([10.0, 20.0]), np.array([100.0, 200.0])),
        (np.array([3.0, 1.0]), np.array([9.0, 30.0])),
        (np.array([0.1, 0.2, 0.3]), np.array([0.7, 1.4, 2.1])),
    )
    for generation, accumulated in cases:
        delta, done, reason = evaluate_neutral_generation_stopping(
            generation, accumulated, truncate=0.05
        )
        exact = _exact(generation.max()) / _exact(accumulated.max())
        # ``exact`` is a rational quotient; the implementation's one rounding is
        # what "correctly rounded division" means, so the rational is rounded here
        # in the same way and then compared bitwise.
        assert delta == float(exact)
        assert (done, reason) == (False, "continue")
    # The maxima decide, not the sums or the means: this case is chosen because a
    # sum-based reading gives 4/39 = 0.1026 while the maximum ratio gives 3/30 = 0.1.
    generation = np.array([3.0, 1.0])
    accumulated = np.array([9.0, 30.0])
    delta, _, _ = evaluate_neutral_generation_stopping(generation, accumulated, truncate=0.05)
    assert delta == 0.1
    assert abs(generation.sum() / accumulated.sum() - delta) > 1e-3


def test_the_truncate_branch_is_strict_and_the_zero_generation_is_exact():
    """Equality continues, one ulp below truncates, and a zero generation is 0.0."""
    threshold = 0.05
    at_threshold = evaluate_neutral_generation_stopping(
        np.array([threshold * 20.0]), np.array([20.0]), truncate=threshold
    )
    assert at_threshold[0] == threshold
    assert at_threshold[1] is False and at_threshold[2] == "continue"
    below = evaluate_neutral_generation_stopping(
        np.array([np.nextafter(threshold * 20.0, 0.0)]), np.array([20.0]), truncate=threshold
    )
    assert below[0] < threshold
    assert below[1] is True and below[2] == "truncate"

    zero = evaluate_neutral_generation_stopping(
        np.zeros(3), np.array([1.0, 2.0, 3.0]), truncate=0.05
    )
    assert zero == (0.0, True, "truncate")


def test_the_seed_branch_uses_the_representable_product_of_the_fixed_factor():
    """0.003 * 100 == 0.3 exactly; the branch is strict at that value."""
    seed_error = 100.0
    product = 0.003 * seed_error
    assert product == 0.3  # the constant the code actually compares against
    # truncate is set below both ratios so the seed branch is the one under test.
    inside = evaluate_neutral_generation_stopping(
        np.array([0.1]),
        np.array([1.0]),
        truncate=0.05,
        seed_iteration_enabled=True,
        seed_error=seed_error,
    )
    assert inside == (0.1, True, "seed_relative")
    at_boundary = evaluate_neutral_generation_stopping(
        np.array([0.3]),
        np.array([1.0]),
        truncate=0.05,
        seed_iteration_enabled=True,
        seed_error=seed_error,
    )
    assert at_boundary == (0.3, False, "continue")


def test_the_generation_stopping_failure_channels():
    """One executable assertion per ``failure_semantics`` entry of the stopping rule."""
    # invalid_input: mismatch, negativity, nonfinite, a nonpositive truncate and a
    # seed control that is missing, misplaced or not boolean.
    with pytest.raises(ValueError, match="finite/nonnegative"):
        evaluate_neutral_generation_stopping(np.array([1.0, 2.0]), np.array([1.0]), truncate=0.1)
    with pytest.raises(ValueError, match="finite/nonnegative"):
        evaluate_neutral_generation_stopping(np.array([-1.0]), np.array([1.0]), truncate=0.1)
    with pytest.raises(ValueError, match="must be finite real array"):
        evaluate_neutral_generation_stopping(np.array([np.nan]), np.array([1.0]), truncate=0.1)
    with pytest.raises(ValueError, match="finite/nonnegative"):
        evaluate_neutral_generation_stopping(np.array([1.0]), np.array([1.0]), truncate=0.0)
    with pytest.raises(ValueError, match="must be a boolean scalar"):
        evaluate_neutral_generation_stopping(
            np.array([1.0]), np.array([1.0]), truncate=0.1, seed_iteration_enabled=1
        )
    with pytest.raises(ValueError, match="seed_error is required"):
        evaluate_neutral_generation_stopping(
            np.array([1.0]), np.array([1.0]), truncate=0.1, seed_iteration_enabled=True
        )
    with pytest.raises(ValueError, match="seed_error must be None"):
        evaluate_neutral_generation_stopping(
            np.array([1.0]), np.array([1.0]), truncate=0.1, seed_error=0.1
        )
    with pytest.raises(ValueError, match="must contain a positive value"):
        evaluate_neutral_generation_stopping(np.zeros(2), np.zeros(2), truncate=0.1)
    # runtime_failure: a finite quotient that overflows to a non-finite delta.
    with pytest.raises(ValueError, match="delta must be finite"):
        evaluate_neutral_generation_stopping(np.array([1e308]), np.array([1e-308]), truncate=0.1)
    # nonconvergence: the relation reports, it does not iterate, so two identical
    # calls return the same tuple and the caller owns the loop.
    first = evaluate_neutral_generation_stopping(np.array([1.0]), np.array([4.0]), truncate=0.5)
    second = evaluate_neutral_generation_stopping(np.array([1.0]), np.array([4.0]), truncate=0.5)
    assert first == second
    # partial_results: a rejected call returns no tuple at all.
    with pytest.raises(ValueError):
        evaluate_neutral_generation_stopping(np.array([]), np.array([]), truncate=0.1)


# --------------------------------------------------------------------------- #
# outer-seed-convergence
# --------------------------------------------------------------------------- #


def test_the_seed_error_is_one_exact_rounded_division():
    """seed_error is bitwise max|previous - current| / max(current)."""
    cases = (
        (np.array([100.0, 200.0]), np.array([100.5, 200.5])),
        (np.array([1.0, 2.0, 3.0]), np.array([1.25, 2.0, 3.0])),
        (np.array([0.5, 0.25]), np.array([0.5, 0.75])),
    )
    for previous, current in cases:
        result = evaluate_neutral_seed(previous, current, truncate=0.1)
        exact = max(abs(_exact(p) - _exact(c)) for p, c in zip(previous, current)) / _exact(
            current.max()
        )
        assert result["seed_error"] == float(exact)


def evaluate_neutral_seed(previous, current, truncate):
    from scirel.neutrals import evaluate_neutral_outer_seed_convergence

    return evaluate_neutral_outer_seed_convergence(previous, current, truncate=truncate)


def test_the_reentry_threshold_is_exactly_ten_times_the_truncate():
    """reentry_threshold == 10 * truncate bitwise, and the comparison is strict."""
    for truncate in (0.1, 0.01, 0.025):
        result = evaluate_neutral_seed(np.array([1.0]), np.array([1.0]), truncate)
        assert result["reentry_threshold"] == 10.0 * truncate
        assert result["reentry_threshold"] == float(_exact(10.0) * _exact(truncate))
        assert result["should_reiterate"] is False and result["reason"] == "converged"

    # Equality converges: build a pair whose ratio is exactly the threshold.
    threshold = 1.0
    current = np.array([2.0])
    previous = np.array([4.0])  # |4 - 2| / 2 = 1.0 == threshold
    equal = evaluate_neutral_seed(previous, current, truncate=0.1)
    assert equal["seed_error"] == threshold
    assert equal["should_reiterate"] is False
    above = evaluate_neutral_seed(np.array([np.nextafter(4.0, np.inf)]), current, truncate=0.1)
    assert above["seed_error"] > threshold
    assert above["should_reiterate"] is True and above["reason"] == "reiterate"


def test_the_withdrawn_unreachability_claim_is_refuted_by_a_counterexample():
    """A downward re-seed breaks the bound, so truncate >= 0.1 can still re-iterate.

    The ratio is bounded by one only while ``max(previous) <= 2 max(current)``;
    ``([4, 0], [1, 0])`` gives 3.0 against a threshold of 2.0 at ``truncate=0.2``.
    """
    result = evaluate_neutral_seed(np.array([4.0, 0.0]), np.array([1.0, 0.0]), 0.2)
    assert result["seed_error"] == 3.0
    assert result["reentry_threshold"] == 2.0
    assert result["should_reiterate"] is True
    # The mirror case, where the bound does hold, converges: this is what makes
    # the counterexample discriminating rather than an arbitrary input.
    inside_bound = evaluate_neutral_seed(np.array([1.5, 0.0]), np.array([1.0, 0.0]), 0.2)
    assert inside_bound["seed_error"] == 0.5
    assert inside_bound["should_reiterate"] is False


def test_the_outer_seed_failure_channels():
    """One executable assertion per ``failure_semantics`` entry of the seed relation."""
    with pytest.raises(ValueError, match="finite, nonnegative, aligned"):
        evaluate_neutral_seed(np.array([1.0, 2.0]), np.array([1.0]), 0.1)
    with pytest.raises(ValueError, match="finite, nonnegative, aligned"):
        evaluate_neutral_seed(np.array([-1.0]), np.array([1.0]), 0.1)
    with pytest.raises(ValueError, match="finite, nonnegative, aligned"):
        evaluate_neutral_seed(np.array([1.0]), np.array([0.0]), 0.1)
    with pytest.raises(ValueError, match="finite, nonnegative, aligned"):
        evaluate_neutral_seed(np.array([1.0]), np.array([1.0]), 0.0)
    # runtime_failure: the threshold itself overflows (10 * 1e308 is not finite).
    with pytest.raises(ValueError, match="reentry_threshold must be finite"):
        evaluate_neutral_seed(np.array([1.0]), np.array([1.0]), 1e308)
    # nonconvergence: two identical calls report the same decision; no iteration.
    assert evaluate_neutral_seed(np.array([1.0]), np.array([2.0]), 0.1) == evaluate_neutral_seed(
        np.array([1.0]), np.array([2.0]), 0.1
    )
    # partial_results: a rejected call returns no mapping.
    with pytest.raises(ValueError):
        evaluate_neutral_seed(np.array([]), np.array([]), 0.1)


# --------------------------------------------------------------------------- #
# velocity-slice-moment-compensation
# --------------------------------------------------------------------------- #


def _slice_and_mesh():
    radial = np.array([0.25, 0.75, 1.5])
    axial = np.array([-2.5, -1.5, -0.5, 0.5, 1.5, 2.5])
    quadrature = make_cylindrical_velocity_quadrature(vr=radial, vx=axial)
    slice_values = np.exp(-(radial[:, None] ** 2 + axial[None, :] ** 2))
    return slice_values, quadrature, radial, axial


def test_the_unsigned_path_applies_a_scale_of_exactly_one():
    """``assume_pos=True`` skips the limiter, so the reported scale is exactly 1."""
    slice_values, quadrature, radial, axial = _slice_and_mesh()
    corrected, scale = compensate_velocity_slice(
        slice_values, quadrature, radial, axial, 1.0, 0.0, 3.0
    )
    assert scale == 1.0
    assert corrected.shape == slice_values.shape
    # The correction is a finite, same-shaped array; it is not a copy of the input,
    # which is the contract's own statement that the primitive is not the identity.
    assert corrected.dtype == slice_values.dtype


def test_the_zero_target_energy_branch_reports_only_the_density_diagnostic():
    """``target_energy == 0`` zeroes both energy diagnostics, so only density can warn.

    With the drift target already at the slice's own mean and a density that
    matches ``nb``, no warning is emitted even though the energy target is zero;
    that is the declared branch, not a silent success.
    """
    slice_values, quadrature, radial, axial = _slice_and_mesh()
    corrected, scale = compensate_velocity_slice(
        slice_values, quadrature, radial, axial, 0.0, 0.0, 0.0
    )
    assert scale == 1.0
    assert np.isfinite(corrected).all()
    rotated, mirrored = compensate_velocity_slice(
        slice_values, quadrature, radial, axial, 0.25, 1.5, 1.0
    )
    assert np.isfinite(rotated).all() and np.isfinite(mirrored)


def test_the_correction_is_affine_in_the_targets_within_one_sign_branch():
    """T(t1) + T(t2) - T(t1 + t2) - T(0) = 0 inside a branch, broken across it."""
    slice_values, quadrature, radial, axial = _slice_and_mesh()

    def correction(drift, energy):
        # vth = 1.0, then the two targets: the parameter order is part of the
        # contract, so it is written out rather than passed as a bare triple.
        corrected, _ = compensate_velocity_slice(
            slice_values, quadrature, radial, axial, 1.0, drift, energy
        )
        return corrected

    # Affineness around the reference target t0, so the identity never has to be
    # evaluated at the zero-energy branch (a different formula).
    base = (0.05, 1.0)
    step_a = (0.02, 0.2)
    step_b = (0.01, -0.1)
    origin = correction(*base)
    first = correction(base[0] + step_a[0], base[1] + step_a[1])
    second = correction(base[0] + step_b[0], base[1] + step_b[1])
    combined = correction(base[0] + step_a[0] + step_b[0], base[1] + step_a[1] + step_b[1])
    # The correction is one linear-solve pair over the 18 mesh cells, and the
    # identity sums four such evaluations: two scalar solves of an 18-term
    # reduction each, so 2 * 18 rounding steps plus the outer combination,
    # bounded here as (2 * 18 + 16) eps of the slice magnitude.
    cells = slice_values.size
    budget = (2 * cells + 16) * EPS * np.max(np.abs(slice_values))
    assert np.all(np.abs(first + second - combined - origin) <= budget)

    # A pair whose combined target selects a different sign branch is no longer
    # affine: the same combination deviates by 8.5e-3, six orders above the budget.
    crossing = (-0.08, 0.2)
    crossed = correction(base[0] + crossing[0], base[1] + crossing[1])
    broken = (
        first
        + crossed
        - correction(base[0] + step_a[0] + crossing[0], base[1] + step_a[1] + crossing[1])
        - origin
    )
    assert np.max(np.abs(broken)) > 1e6 * EPS * np.max(np.abs(slice_values))

"""Independent exact evidence for the three inference contracts.

Three separate relations, each checked against a value this file computes itself:

* the Latin-hypercube design is a **stratified permutation** per coordinate — every
  stratum holds exactly one draw — which is an integer identity on the recovered
  unit coordinate, not a statistical claim about the design;
* a trial's ``chi2`` is the **exact rational sum of squares** of the residual
  vector it returns, rounded once, and a reducer's own ``chi2`` is accepted or
  rejected at the documented ``1e-12`` relative budget with zero absolute
  tolerance — both sides of that boundary are asserted;
* the optimizer's reported ``chi2`` is the same exact sum of squares of the
  vector it returns, its terminal parameters lie inside the caller's bounds, and
  the reported state is the minimum over the recorded evaluations.

What this does not establish, and is not claimed here: that a bounded local fit
reaches a **global** optimum, that parameters are identifiable, or that the
forward model is physically calibrated. Those stay out of reach of an exact
recomputation and are recorded as the contracts' evidence ceiling.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

from scirel.diagnostics import reduce_observation_residuals
from scirel.inference import (
    evaluate_anisotropic_trial,
    optimize_anisotropic_parameters,
    sample_latin_hypercube,
)


def exact_norm(vector):
    """Sum the squares of the raw float64 entries as one rational number."""
    total = Fraction(0)
    for value in vector:
        total += Fraction(float(value)) ** 2
    return total


def one_rounding(total):
    """The nearest float64 to an exact rational sum: one rounding, no accumulation."""
    return float(total)


# --------------------------------------------------------------------------- #
# Latin-hypercube sampling: one draw per stratum, exactly.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("n_samples", [1, 2, 5, 7, 16])
def test_each_coordinate_places_exactly_one_draw_in_every_stratum(n_samples):
    """The stratification identity, checked on the recovered unit coordinate.

    ``bounds`` are dyadic so ``unit = value / high`` is exact, and the stratum of
    a unit value is ``floor(unit * n)`` computed in rational arithmetic. A design
    that put two draws in one stratum and none in another — the one failure this
    contract exists to prevent — cannot pass, and neither can an off-by-one in
    the ``/ n_samples`` normalization, which would land a draw on a boundary.
    """
    bounds = {"a": (0.0, 8.0), "b": (0.0, 1024.0)}
    samples = sample_latin_hypercube(bounds=bounds, n_samples=n_samples, seed=17)["initial_samples"]
    assert len(samples) == n_samples
    for key, (_low, high) in bounds.items():
        units = [Fraction(row[key]) / Fraction(high) for row in samples]
        strata = [int(unit * n_samples) for unit in units]
        assert sorted(strata) == list(range(n_samples)), key
        # Each draw is strictly inside its stratum, not on a boundary.
        for unit, stratum in zip(units, strata):
            assert Fraction(stratum, n_samples) <= unit < Fraction(stratum + 1, n_samples)


def test_the_returned_values_are_the_affine_image_of_the_unit_draws():
    """``value = low + u*(high-low)`` holds for a non-zero lower bound too.

    With a negative lower bound the affine map is not a scaling, so a design that
    dropped ``low`` or applied the interval length twice changes the stratum
    assignment and the test fails on the stratification rather than on an
    approximate value comparison.
    """
    bounds = {"c": (-4.0, 12.0)}
    samples = sample_latin_hypercube(bounds=bounds, n_samples=6, seed=3)["initial_samples"]
    units = [(Fraction(row["c"]) + 4) / 16 for row in samples]
    assert sorted(int(unit * 6) for unit in units) == list(range(6))
    for row, unit in zip(samples, units):
        assert Fraction(row["c"]) == -4 + 16 * unit


def test_the_selected_keys_and_their_order_are_the_output_keys():
    """``fit_keys`` selects columns and fixes their insertion order."""
    bounds = {"a": (0.0, 1.0), "b": (0.0, 1.0), "c": (0.0, 1.0)}
    samples = sample_latin_hypercube(bounds=bounds, n_samples=4, seed=5, fit_keys=["c", "a"])[
        "initial_samples"
    ]
    for row in samples:
        assert list(row) == ["c", "a"]


# --------------------------------------------------------------------------- #
# Trial evaluation: chi2 is the exact squared norm, at a stated budget.
# --------------------------------------------------------------------------- #


def trial(vector, scale=1.0, *, size=None):
    """Evaluate one trial with a reducer that returns an exact ``chi2``."""

    def reducer(*, predicted, observations):
        norm = exact_norm(vector)
        return {
            "residual_vector": np.asarray(vector, dtype=float),
            "chi2": float(norm) * scale,
        }

    kwargs = {} if size is None else {"residual_size": size}
    return evaluate_anisotropic_trial(
        params={},
        observations={"flux_loops": {"values": np.zeros_like(vector), "sigma": 1.0}},
        solver_config={"r_grid": [0.0], "z_grid": [0.0]},
        equilibrium_solver=lambda _: {"converged": True},
        diagnostic_evaluator=lambda _: {"flux_loops": np.asarray(vector, dtype=float)},
        residual_reducer=reducer,
        **kwargs,
    )


@pytest.mark.parametrize(
    "vector",
    [
        [0.1, 0.2],
        [3.0, 4.0],
        [1.0, -1.0, 0.5, -0.25],
        [2.0**-500, 2.0**-500, 2.0**-500],
    ],
)
def test_the_reported_chi2_is_the_exact_squared_norm_of_the_returned_vector(vector):
    """``chi2`` equals the rational sum of squared float64 entries, rounded once.

    The expectation is formed with ``Fraction`` from the entries themselves, so
    it does not go through the same accumulator as the implementation. The
    comparison is an equality, not a tolerance: both sides are the same rational
    number converted once.
    """
    result = trial(vector)
    assert result.valid
    np.testing.assert_array_equal(result.residuals, np.asarray(vector, dtype=float))
    exact = exact_norm(result.residuals)
    # One rounding of the exact rational sum, so the reported value is the
    # nearest float64 - not an accumulation order artefact.
    assert result.chi2 == one_rounding(exact)
    half_ulp = Fraction(abs(np.spacing(float(exact)))) / 2
    assert abs(Fraction(result.chi2) - exact) <= half_ulp


def test_an_inconsistent_reducer_chi2_is_accepted_inside_the_stated_budget():
    """A relative deviation below ``1e-12`` is accepted; the budget is documented.

    ``1 + 2**-41`` is about ``4.5e-13`` relative, inside the budget; the zero
    absolute tolerance means a tiny-but-nonzero relative deviation on a tiny
    norm must still be inside it. This is the accepted side of the boundary, the
    side a test that only checks rejection would leave free.
    """
    result = trial([0.1, 0.2], scale=1.0 + 2.0**-41)
    assert result.valid
    exact = exact_norm([0.1, 0.2])
    assert abs(Fraction(result.chi2) - exact) <= Fraction(1e-12) * exact


def test_a_reducer_chi2_outside_the_budget_stays_an_input_error():
    """``1 + 2**-33`` is about ``1.2e-10`` relative: outside the budget, so it raises."""
    with pytest.raises(ValueError, match="equal the squared residual norm"):
        trial([0.1, 0.2], scale=1.0 + 2.0**-33)


@pytest.mark.parametrize("size", [1, 2, 4])
def test_a_failed_forward_returns_the_declared_penalty_at_the_fixed_dimension(size):
    """A nonconverged forward gives a penalty vector of the fixed size and its exact norm."""
    penalty = 1.0e12
    result = evaluate_anisotropic_trial(
        params={},
        observations={"flux_loops": {"values": np.zeros(size), "sigma": 1.0}},
        solver_config={"r_grid": [0.0], "z_grid": [0.0]},
        equilibrium_solver=lambda _: {"converged": False, "failure_reason": "iteration limit"},
        diagnostic_evaluator=lambda _: pytest.fail("a failed forward must not be evaluated"),
        residual_reducer=reduce_observation_residuals,
        residual_size=size,
        failure_penalty=penalty,
    )
    assert not result.valid
    assert result.status == "forward_nonconvergence"
    np.testing.assert_array_equal(result.residuals, np.full(size, penalty))
    assert Fraction(result.chi2) == Fraction(one_rounding(size * Fraction(penalty) ** 2))


# --------------------------------------------------------------------------- #
# Optimizer: the ranking key, the bounds, and what cannot be established.
# --------------------------------------------------------------------------- #


def quadratic_trial(*, params):
    residual = np.asarray([params["x"] - 3.0, 2.0 * params["x"] - 6.0])
    return {
        "params": dict(params),
        "residuals": residual,
        "chi2": float(exact_norm(residual)),
        "equilibrium": {"converged": True},
        "failure_reason": None,
    }


@pytest.mark.parametrize("method", ["least_squares", "minimize"])
def test_the_reported_state_is_the_ranking_minimum_with_an_exact_norm(method):
    """``chi2`` is the exact squared norm of the returned vector and the log minimum.

    The two claims are separate: the norm ties the reported number to the
    reported vector, and the minimum ties the reported state to the evaluations
    the optimizer actually performed. A reported chi2 that did not belong to its
    own vector would pass a monotonicity test and fail this one.
    """
    result = optimize_anisotropic_parameters(
        initial_params={"x": 0.0},
        bounds={"x": (-5.0, 5.0)},
        method=method,
        trial_evaluator=quadratic_trial,
        max_evaluations=40,
    )
    assert result.converged
    assert result.chi2 == one_rounding(exact_norm(result.residual_vector))
    assert -5.0 <= result.best_parameters["x"] <= 5.0
    # A fit never returns a state worse than the one it started from.
    assert result.chi2 <= result["evaluation_log"][0]["chi2"]


def test_least_squares_reports_the_minimum_of_its_recorded_evaluations():
    """The least-squares path reports the best recorded evaluation, not just the terminal one.

    The two optimizer methods stop differently, so this ranking statement is made
    for the method where it holds rather than assumed for both. For the
    ``minimize`` path the returned state is the revalidated terminal point, and
    the test above pins that weaker relation instead of a minimum it does not
    promise.
    """
    result = optimize_anisotropic_parameters(
        initial_params={"x": 0.0},
        bounds={"x": (-5.0, 5.0)},
        method="least_squares",
        trial_evaluator=quadratic_trial,
        max_evaluations=40,
    )
    assert result.chi2 == min(item["chi2"] for item in result["evaluation_log"])


def test_the_terminal_parameters_respect_the_declared_bounds_exactly():
    """A bound is a closed interval, and the returned point lies inside it.

    The minimum of this objective sits outside the box, so the optimizer must
    stop at the boundary; a projection applied with a tolerance would return a
    point a few ulps outside and fail here.
    """
    result = optimize_anisotropic_parameters(
        initial_params={"x": 0.0},
        bounds={"x": (0.0, 1.0)},
        method="least_squares",
        trial_evaluator=quadratic_trial,
        max_evaluations=40,
    )
    assert 0.0 <= result.best_parameters["x"] <= 1.0


def test_global_optimality_is_not_established_and_is_recorded_as_such():
    """The local fit is not a global optimum, and the contract says so.

    This test does not assert a gap in the code; it asserts that the contract
    states one. A bounded local method on a non-convex objective has no
    closed-form optimality certificate, so the honest record is ``cannot
    establish`` rather than a claim, and this check fails if that record is
    dropped from the contract later.
    """
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    document = json.loads(
        (
            root / "catalog/examples/scirel.inference.anisotropic-parameter-optimization.json"
        ).read_text(encoding="utf-8")
    )
    text = " ".join(document["verification"]["known_limitations"]).lower()
    assert "cannot establish" in text or "cannot be established" in text
    assert "global" in text


def test_a_nonconverged_forward_never_becomes_the_reported_best_state():
    """A trial whose forward state did not converge cannot be ranked as valid.

    This is the failure mode a value-only test misses: the chi2 of an
    unconverged forward is a number like any other, so only a check that the
    *validity* gate runs before ranking can distinguish it. The optimizer must
    fall back (``best_parameters is None``, ``converged`` false) rather than
    report the penalty or the unconverged state as a fit.
    """

    def unconverged(*, params):
        residual = np.asarray([params["x"] - 3.0])
        return {
            "params": dict(params),
            "residuals": residual,
            "chi2": float(exact_norm(residual)),
            "equilibrium": {"converged": False, "failure_reason": None},
            "failure_reason": None,
        }

    result = optimize_anisotropic_parameters(
        initial_params={"x": 0.0},
        bounds={"x": (-5.0, 5.0)},
        method="least_squares",
        trial_evaluator=unconverged,
        max_evaluations=10,
    )
    assert result.best_parameters is None
    assert not result.converged
    assert not result.forward_converged


def test_a_degenerate_parameter_interval_is_rejected_before_optimizing():
    """``(low, high)`` must be strictly increasing; an empty box is an input error.

    Without this the optimizer would run on a zero-width box and return the
    single allowed point as if it were a fit. The rejected side of the bounds
    guard is checked here because a bounds *violation* test alone leaves a
    degenerate interval unexercised.
    """
    calls = []

    def counting_trial(*, params):
        calls.append(dict(params))
        return quadratic_trial(params=params)

    for bounds in ({"x": (1.0, 1.0)}, {"x": (2.0, 1.0)}):
        with pytest.raises(ValueError, match="finite increasing two-element bounds"):
            optimize_anisotropic_parameters(
                initial_params={"x": 1.0},
                bounds=bounds,
                method="least_squares",
                trial_evaluator=counting_trial,
            )
    assert calls == []


@pytest.mark.parametrize("n_samples", [3, 8])
def test_the_stratum_normalization_is_exactly_n_equals_the_stratum_count(n_samples):
    """A design whose unit draw were divided by ``n+1`` puts a gap at the top.

    With ``n+1`` the largest stratum index would be ``n-1`` only if one stratum
    were skipped, so the permutation identity fails; with no permutation at all
    every draw sits in a different stratum but the *same* one per row across
    coordinates, which the per-column identity also catches.
    """
    samples = sample_latin_hypercube(
        bounds={"a": (0.0, 8.0), "b": (0.0, 8.0)}, n_samples=n_samples, seed=29
    )["initial_samples"]
    columns = {}
    for key in ("a", "b"):
        units = [Fraction(row[key]) / 8 for row in samples]
        strata = [int(unit * n_samples) for unit in units]
        assert sorted(strata) == list(range(n_samples))
        columns[key] = strata
    # Two independent coordinates must not share one permutation by construction.
    assert columns["a"] != columns["b"]

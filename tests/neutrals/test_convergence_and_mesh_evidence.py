"""Independent evidence for the adaptive velocity mesh and the three stopping relations.

Assets: ``scirel.neutrals.adaptive-neutral-velocity-mesh``,
``scirel.neutrals.outer-convergence``,
``scirel.neutrals.outer-seed-convergence``,
``scirel.neutrals.generation-stopping``.

All four are closed-form constructions or threshold decisions, so the evidence is
an exact recomputation plus a **discriminator at each decision boundary**:

1. **Exact mesh construction.**  The uniform branch is an exact affine map
   ``v_k = k * 3.5 / nv``; the radial axis is its tail and the axial axis is its
   exact mirror, and the normalization temperature is the exact mean of the
   selected population.
2. **Population selection is decided.**  A cap removes the hot temperatures from
   the normalization population while every positive requested energy is still
   inserted as an exact node, so the two effects are separated rather than
   inferred from the output size.
3. **Exact relative errors.**  ``seed_error`` and ``delta`` are recomputed in
   rational arithmetic from the exact binary64 inputs, and their scale invariance
   under a common factor of two is asserted exactly.
4. **Strict comparisons, decided at equality.**  Every branch is
   ``error > threshold`` or ``error < threshold``; each is exercised exactly at
   the boundary (where the strict comparison must not fire) and one ulp on the
   other side (where it must).  This is the discriminator for ``>`` versus ``>=``.
5. **The factor ten of the seed threshold.**  The seed relation's
   ``reentry_threshold`` is exactly ten times the outer relation's threshold for
   the same ``truncate``, which ties the two contracts together.
6. **The 0.003 seed branch of the generation stopping.**  ``seed_error = 100``
   puts ``0.003 * seed_error = 0.3`` exactly, so a ``delta`` strictly below and
   exactly at the boundary decide the branch without rounding ambiguity.
7. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel of each asset.

Budgets, fixed before measurement:

* the exact quantities (mesh nodes, tnorm, error, delta): ``8 * eps`` relative,
  because the implementation performs a handful of exact-scaling operations and
  one division.
* the decision boundaries: exact equality versus one ulp, using values whose
  ratio is exactly representable (``10/100``, ``1000/1000``, ``0.5``).
* the factor-ten relation: exact for ``truncate = 0.1`` (``10 * 0.1 == 1.0``).
"""

from __future__ import annotations

from fractions import Fraction
import math

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


# --------------------------------------------------------------------------- #
# adaptive-neutral-velocity-mesh
# --------------------------------------------------------------------------- #


def test_uniform_branch_is_the_exact_affine_map():
    """Evidence 1: nodes, mirror, indices and the exact mean normalization."""
    vx, vr, tnorm, ix, ir = N.create_adaptive_neutral_velocity_mesh(4, (1.0, 1.05))
    expected = np.arange(1, 5) * 3.5 / 4.0
    assert np.array_equal(vr, expected)
    assert np.array_equal(vx, np.concatenate((-vr[::-1], vr)))
    assert tnorm == (1.0 + 1.05) / 2.0
    # No requested energy was given, so the last inserted node is the sentinel 0.0
    # and neither axis contains it: both index arrays are empty.
    assert np.size(ix) == 0
    assert np.size(ir) == 0


def test_requested_energy_is_inserted_and_cap_only_filters_the_population():
    """Evidence 2: the cap drops a hot temperature from the normalization population."""
    vx, vr, tnorm, ix, ir = N.create_adaptive_neutral_velocity_mesh(
        4, (1.0, 9.0), temperature_cap_ev=4.0
    )
    # 9.0 >= 4.0 is dropped from the normalization population, so tnorm is 1.0
    # and the base mesh is the uniform one.
    assert tnorm == 1.0
    assert np.array_equal(vr, np.arange(1, 5) * 3.5 / 4.0)


def test_an_energy_above_the_cap_is_still_inserted_as_a_node():
    """Evidence 2: insertion is independent of the normalization filter."""
    vx, vr, tnorm, ix, ir = N.create_adaptive_neutral_velocity_mesh(
        4, (1.0, 9.0), requested_energy_ev=(9.0,), temperature_cap_ev=4.0
    )
    assert tnorm == 1.0
    node = math.sqrt(9.0 / 1.0)
    assert node in vr
    assert vr.size == 5
    assert np.all(np.diff(vr) > 0.0)
    assert np.array_equal(np.atleast_1d(ir), np.flatnonzero(vr == node))
    assert np.array_equal(np.atleast_1d(ix), np.flatnonzero(np.abs(vx) == node))


def test_adaptive_mesh_rejects_each_declared_channel():
    """Evidence 7: one executable assertion per rejection channel."""
    call = N.create_adaptive_neutral_velocity_mesh
    with pytest.raises(ValueError, match="nv must be a positive integer"):
        call(0, (1.0,))
    with pytest.raises(ValueError, match="nv must be a positive integer"):
        call(4.0, (1.0,))
    with pytest.raises(ValueError, match="nv must be positive; temperatures"):
        call(4, (0.0,))
    with pytest.raises(ValueError, match="nv must be positive; temperatures"):
        call(4, (1.0, np.nan))
    with pytest.raises(ValueError, match="must be a finite one-dimensional array"):
        call(4, (1.0,), requested_energy_ev=(np.inf,))
    with pytest.raises(ValueError, match="cap nonnegative"):
        call(4, (1.0,), temperature_cap_ev=-1.0)
    with pytest.raises(ValueError, match="must be nonempty and positive"):
        call(4, (1.0,), temperature_cap_ev=0.5)


# --------------------------------------------------------------------------- #
# outer-convergence / outer-seed-convergence
# --------------------------------------------------------------------------- #


def test_outer_error_is_the_exact_relative_maximum_change():
    """Evidence 3: max|current - previous| / max(current), recomputed exactly."""
    previous = np.array([90.0, 100.0, 50.0])
    current = np.array([100.0, 110.0, 60.0])
    result = N.evaluate_outer_convergence(previous, current, truncate=0.2)
    exact = max(abs(_frac(c) - _frac(p)) for p, c in zip(previous, current)) / _frac(
        np.max(current)
    )
    assert abs(result["seed_error"] - float(exact)) <= 8 * EPS * float(exact)
    assert result["reentry_threshold"] == 0.2
    # Scale invariance: a common factor of two leaves the relative error exact.
    scaled = N.evaluate_outer_convergence(2.0 * previous, 2.0 * current, truncate=0.2)
    assert scaled["seed_error"] == result["seed_error"]


def test_outer_convergence_uses_a_strict_comparison():
    """Evidence 4: equality at the threshold does not re-iterate."""
    previous = np.array([90.0])
    current = np.array([100.0])
    at_threshold = N.evaluate_outer_convergence(previous, current, truncate=0.1)
    assert at_threshold["seed_error"] == 0.1
    assert at_threshold["should_reiterate"] is False
    assert at_threshold["reason"] == "converged"
    just_above = N.evaluate_outer_convergence(
        np.array([np.nextafter(90.0, 0.0)]), current, truncate=0.1
    )
    assert just_above["should_reiterate"] is True
    assert just_above["reason"] == "reiterate"


def test_seed_threshold_is_exactly_ten_times_the_outer_threshold():
    """Evidence 5: the seed relation multiplies the threshold by ten."""
    previous = np.array([90.0])
    current = np.array([100.0])
    outer = N.evaluate_outer_convergence(previous, current, truncate=0.1)
    seed = N.evaluate_neutral_outer_seed_convergence(previous, current, truncate=0.1)
    assert seed["reentry_threshold"] == 10.0 * outer["reentry_threshold"]
    assert seed["reentry_threshold"] == 1.0
    assert seed["seed_error"] == outer["seed_error"] == 0.1
    assert seed["should_reiterate"] is False
    # The ratio is at most one only while max(previous) <= 2*max(current); when
    # `previous` greatly exceeds `current` it is unbounded, so the branch does fire
    # above truncate = 0.1. This counterexample guards against the earlier, wrong
    # claim that the branch was unreachable (ticket T-2026-0004).
    counterexample = N.evaluate_neutral_outer_seed_convergence(
        np.array([4.0, 0.0]), np.array([1.0, 0.0]), truncate=0.2
    )
    assert counterexample["seed_error"] == 3.0
    assert counterexample["reentry_threshold"] == 2.0
    assert counterexample["should_reiterate"] is True
    assert counterexample["reason"] == "reiterate"
    reseeded = N.evaluate_neutral_outer_seed_convergence(
        np.array([10.0, 0.0]), np.array([1.0, 0.0]), truncate=0.2
    )
    assert reseeded["seed_error"] == 9.0 and reseeded["should_reiterate"] is True
    # Below the bound the branch also fires; the threshold is exactly 10*truncate.
    above = N.evaluate_neutral_outer_seed_convergence(
        np.array([10.0]), np.array([20.0]), truncate=0.01
    )
    assert above["seed_error"] == 0.5
    assert above["reentry_threshold"] == 0.1
    assert above["should_reiterate"] is True and above["reason"] == "reiterate"


def test_outer_convergence_rejects_each_declared_channel():
    """Evidence 7: one executable assertion per rejection channel."""
    outer = N.evaluate_outer_convergence
    seed = N.evaluate_neutral_outer_seed_convergence
    good = (np.array([1.0, 2.0]), np.array([1.0, 2.0]), 0.1)
    assert outer(*good)["reentry_threshold"] == 0.1
    with pytest.raises(ValueError, match="top-level outer density"):
        outer(np.array([1.0, 2.0]), np.array([1.0]), 0.1)
    with pytest.raises(ValueError, match="top-level outer density"):
        outer(np.array([-1.0, 2.0]), good[1], 0.1)
    with pytest.raises(ValueError, match="top-level outer density"):
        outer(good[0], np.zeros(2), 0.1)
    with pytest.raises(ValueError, match="top-level outer density"):
        outer(good[0], good[1], 0.0)
    with pytest.raises(ValueError, match="outer seed density"):
        seed(np.array([1.0]), np.array([1.0, 2.0]), 0.1)
    with pytest.raises(ValueError, match="outer seed density"):
        seed(good[0], good[1], -0.5)


# --------------------------------------------------------------------------- #
# generation-stopping
# --------------------------------------------------------------------------- #


def test_generation_delta_is_the_exact_maximum_ratio():
    """Evidence 3: delta = max(generation) / max(accumulated)."""
    generation = np.array([10.0, 20.0])
    accumulated = np.array([100.0, 200.0])
    delta, done, reason = N.evaluate_neutral_generation_stopping(generation, accumulated, 0.05)
    assert delta == 0.1
    assert done is False and reason == "continue"
    # A zero generation is the exact zero ratio and stops on the truncate branch.
    zero, done_zero, reason_zero = N.evaluate_neutral_generation_stopping(
        np.zeros(2), accumulated, 0.05
    )
    assert zero == 0.0 and done_zero is True and reason_zero == "truncate"


def test_generation_stopping_uses_strict_comparisons_at_both_branches():
    """Evidence 4 + 6: equality at truncate continues; the 0.003 branch is strict too."""
    at_truncate, done, reason = N.evaluate_neutral_generation_stopping(
        np.array([10.0]), np.array([100.0]), 0.1
    )
    assert at_truncate == 0.1 and done is False and reason == "continue"
    below, done_below, reason_below = N.evaluate_neutral_generation_stopping(
        np.array([np.nextafter(10.0, 0.0)]), np.array([100.0]), 0.1
    )
    assert done_below is True and reason_below == "truncate"
    # seed_error = 100 makes 0.003 * seed_error = 0.3 exactly.
    inside, done_inside, reason_inside = N.evaluate_neutral_generation_stopping(
        np.array([10.0]), np.array([100.0]), 0.001, True, 100.0
    )
    assert inside == 0.1 and done_inside is True and reason_inside == "seed_relative"
    boundary, done_boundary, reason_boundary = N.evaluate_neutral_generation_stopping(
        np.array([30.0]), np.array([100.0]), 0.001, True, 100.0
    )
    assert boundary == 0.3 and done_boundary is False and reason_boundary == "continue"


def test_generation_stopping_rejects_each_declared_channel():
    """Evidence 7: one executable assertion per rejection channel."""
    call = N.evaluate_neutral_generation_stopping
    good = (np.array([10.0]), np.array([100.0]), 0.05)
    assert call(*good)[2] == "continue"
    with pytest.raises(ValueError, match="density vectors"):
        call(np.array([10.0]), np.array([100.0, 1.0]), 0.05)
    with pytest.raises(ValueError, match="density vectors"):
        call(np.array([-1.0]), np.array([100.0]), 0.05)
    with pytest.raises(ValueError, match="density vectors"):
        call(np.array([10.0]), np.array([100.0]), 0.0)
    with pytest.raises(ValueError, match="must contain a positive value"):
        call(np.array([0.0]), np.array([0.0]), 0.05)
    with pytest.raises(ValueError, match="must be a boolean scalar"):
        call(good[0], good[1], 0.05, 1, None)
    with pytest.raises(ValueError, match="seed_error is required"):
        call(good[0], good[1], 0.05, True, None)
    with pytest.raises(ValueError, match="must be None"):
        call(good[0], good[1], 0.05, False, 1.0)
    with pytest.raises(ValueError, match="must be nonnegative"):
        call(good[0], good[1], 0.05, True, -1.0)

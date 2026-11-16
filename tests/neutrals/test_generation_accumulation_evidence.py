"""Independent evidence for the neutral generation accumulation state update.

Asset: ``scirel.neutrals.generation-accumulation-update``.

The contract is a cumulative state update: each call appends one generation and
must keep ``total_distribution`` / ``total_density_m3`` equal to the *ordered*
sum of the retained per-generation stacks, with a zero-based
``completed_generation_index``.  The scientific content is conservation across
appends and the internal consistency check that refuses a corrupted state.
Evidence:

1. **Conservation against an exact rational ordered sum.**  After *n* appends the
   accumulated total is recomputed with :class:`fractions.Fraction` from the *n*
   append arguments alone, independently of the state the implementation threaded
   through the calls, and rounded once.  A dropped, duplicated or reordered
   generation moves the total by O(|generation|).
2. **Append identity.**  A zero generation is the additive identity: it must
   leave both totals bit-identical while still advancing the index and the stack.
   This is the degenerate zero-density case of the contract, and it is checked as
   an equality, not a tolerance.
3. **Stack immutability.**  The retained per-generation rows must stay bit-equal
   to the values that were appended; a later append may not rewrite history.
4. **State consistency is enforced, not assumed.**  A supplied state whose
   totals disagree with its own stacks, whose index is off by one, or which is
   missing a field must be rejected instead of silently repaired.  Without this
   the conservation claim would only hold for states the caller never corrupted.
5. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel: non-real/non-finite/misaligned generation fields, a negative density,
   an incomplete or inconsistent state, and the accumulation overflow that must
   fail closed.

Budgets, fixed before measurement:

* ordered sum of *n* generations: ``n * eps * sum_k |generation_k|`` per cell.
  A left-to-right accumulation performs ``n-1`` roundings, each bounded by
  ``eps`` times the running magnitude (at most ``eps * sum |x|``), and the
  round-once exact reference adds the ``(1+eps)`` slack; ``n * eps`` is the
  textbook forward bound for that accumulation, not a fitted threshold.
* zero-generation identity and stack immutability: exact equality.
"""

from __future__ import annotations

from fractions import Fraction

import numpy as np
import pytest

import scirel.neutrals as N

EPS = np.finfo(float).eps


def _frac(value):
    """Exact rational value of a binary64 number."""
    return Fraction(float(value))


def _exact_ordered_sum(generations):
    """Round-once exact ordered sum of a list of same-shape arrays."""
    shape = generations[0].shape
    out = np.empty(shape, dtype=object)
    for index in np.ndindex(*shape):
        total = Fraction(0)
        for generation in generations:
            total += _frac(generation[index])
        out[index] = total
    return np.array([float(value) for value in out.ravel()]).reshape(shape)


def test_accumulation_conserves_the_ordered_stack_sum():
    """Evidence 1: totals equal the exact ordered sum of the appended stacks."""
    rng = np.random.default_rng(401)
    shape = (2, 2, 3)
    distributions = [rng.uniform(-3.0, 3.0, size=shape) for _ in range(5)]
    densities = [rng.uniform(0.0, 2.0, size=(3,)) for _ in range(5)]
    state = None
    for generation, density in zip(distributions, densities):
        state = N.update_neutral_generation_accumulation(state, generation, density)
    assert state["completed_generation_index"] == 4
    assert state["generation_distributions"].shape == (5, *shape)
    assert state["generation_density_m3"].shape == (5, 3)

    expected_distribution = _exact_ordered_sum(distributions)
    scale = np.zeros(shape)
    for generation in distributions:
        scale = scale + np.abs(generation)
    budget = len(distributions) * EPS * scale
    assert np.all(np.abs(state["total_distribution"] - expected_distribution) <= budget)

    expected_density = _exact_ordered_sum(densities)
    density_scale = np.zeros(3)
    for density in densities:
        density_scale = density_scale + np.abs(density)
    assert np.all(
        np.abs(state["total_density_m3"] - expected_density) <= len(densities) * EPS * density_scale
    )


def test_accumulation_keeps_every_retained_generation_bit_identical():
    """Evidence 3: appending another generation does not rewrite history."""
    rng = np.random.default_rng(409)
    shape = (1, 2, 2)
    first = rng.uniform(-1.0, 1.0, size=shape)
    second = rng.uniform(-1.0, 1.0, size=shape)
    density_first = np.array([1.0, 2.0])
    density_second = np.array([3.0, 4.0])
    state = N.update_neutral_generation_accumulation(None, first, density_first)
    snapshot = state["generation_distributions"].copy()
    state = N.update_neutral_generation_accumulation(state, second, density_second)
    assert np.array_equal(state["generation_distributions"][0], snapshot[0])
    assert np.array_equal(state["generation_distributions"][1], second)
    assert np.array_equal(state["generation_density_m3"][0], density_first)
    assert np.array_equal(state["generation_density_m3"][1], density_second)


def test_zero_generation_is_the_additive_identity():
    """Evidence 2: a zero generation leaves both totals bit-identical."""
    rng = np.random.default_rng(419)
    shape = (2, 1, 2)
    first = rng.uniform(-1.0, 1.0, size=shape)
    state = N.update_neutral_generation_accumulation(None, first, np.array([1.0, 0.0]))
    zero = N.update_neutral_generation_accumulation(state, np.zeros(shape), np.array([0.0, 0.0]))
    assert np.array_equal(zero["total_distribution"], state["total_distribution"])
    assert np.array_equal(zero["total_density_m3"], state["total_density_m3"])
    assert zero["completed_generation_index"] == 1
    assert zero["generation_density_m3"].shape == (2, 2)


def test_accumulation_works_on_a_single_cell_mesh():
    """Evidence 2: the degenerate single-cell state still conserves."""
    state = N.update_neutral_generation_accumulation(None, np.array([[[2.0]]]), np.array([3.0]))
    assert state["completed_generation_index"] == 0
    assert np.array_equal(state["total_distribution"], np.array([[[2.0]]]))
    assert np.array_equal(state["total_density_m3"], np.array([3.0]))
    second = N.update_neutral_generation_accumulation(state, np.array([[[0.5]]]), np.array([0.25]))
    assert np.array_equal(second["total_distribution"], np.array([[[2.5]]]))
    assert np.array_equal(second["total_density_m3"], np.array([3.25]))


def test_accumulation_refuses_an_inconsistent_state_instead_of_repairing_it():
    """Evidence 4: totals, index and completeness are checked, not trusted."""
    rng = np.random.default_rng(421)
    shape = (1, 1, 2)
    generation = rng.uniform(-1.0, 1.0, size=shape)
    state = N.update_neutral_generation_accumulation(None, generation, np.array([1.0, 1.0]))

    corrupted = dict(state)
    corrupted["total_distribution"] = state["total_distribution"] + 1.0
    with pytest.raises(ValueError, match="ordered generation stacks"):
        N.update_neutral_generation_accumulation(corrupted, generation, np.array([1.0, 1.0]))

    corrupted = dict(state)
    corrupted["total_density_m3"] = state["total_density_m3"] + 0.5
    with pytest.raises(ValueError, match="ordered generation stacks"):
        N.update_neutral_generation_accumulation(corrupted, generation, np.array([1.0, 1.0]))

    corrupted = dict(state)
    corrupted["completed_generation_index"] = 7
    with pytest.raises(ValueError, match="inconsistent shapes"):
        N.update_neutral_generation_accumulation(corrupted, generation, np.array([1.0, 1.0]))

    incomplete = dict(state)
    del incomplete["total_density_m3"]
    with pytest.raises(ValueError, match="complete accumulation fields"):
        N.update_neutral_generation_accumulation(incomplete, generation, np.array([1.0, 1.0]))

    with pytest.raises(ValueError, match="complete accumulation fields"):
        N.update_neutral_generation_accumulation([1, 2, 3], generation, np.array([1.0, 1.0]))


def test_accumulation_rejects_each_declared_channel():
    """Evidence 5: one executable assertion per rejection channel."""
    shape = (1, 1, 2)
    generation = np.ones(shape)
    density = np.array([1.0, 1.0])
    call = N.update_neutral_generation_accumulation

    with pytest.raises(ValueError, match="finite and density"):
        call(None, np.ones((1, 2)), density)
    with pytest.raises(ValueError, match="finite and density"):
        call(None, generation, np.array([1.0, 1.0, 1.0]))
    with pytest.raises(ValueError, match="finite and density"):
        call(None, generation, np.array([-1.0, 1.0]))
    with pytest.raises(ValueError, match="finite real array"):
        call(None, np.array([[["a", "b"]]]), density)
    with pytest.raises(ValueError, match="finite real array"):
        call(None, np.array([[[1j, 1.0]]]), density)
    with pytest.raises(ValueError, match="finite real array"):
        call(None, np.array([[[np.nan, 1.0]]]), density)
    with pytest.raises(ValueError, match="finite real array"):
        call(None, generation, np.array([np.inf, 1.0]))

    state = call(None, np.full(shape, 1.7e308), np.array([1.0, 1.0]))
    with pytest.raises(ValueError, match="finite"):
        call(state, np.full(shape, 1.7e308), np.array([1.0, 1.0]))

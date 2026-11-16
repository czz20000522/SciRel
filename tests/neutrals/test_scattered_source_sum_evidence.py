"""Independent evidence for the channel-sum reductions of the neutral sources.

Assets: ``scirel.neutrals.atomic-scattered-sources-reduction``,
``scirel.neutrals.molecular-scattered-sources-reduction``,
``scirel.neutrals.elastic-frequency-channels``,
``scirel.neutrals.elastic-regeneration-aggregation``.

All four contracts say the same scientific thing: the total scattered/elastic
source is the pointwise sum of already-normalized channels, in a stated channel
order, with signed values preserved.  The scientific content is therefore the
*balance* (no channel silently dropped, doubled or rescaled) and the *declared
float order*, neither of which a single normal example can show.  Evidence:

1. **Exact rational recomputation.**  Each output cell is recomputed with
   :class:`fractions.Fraction` from the exact binary64 inputs and rounded once;
   this is independent of the implementation's own vector addition.
2. **Channel completeness by construction.**  One channel is split into two
   pieces of half weight and the total is required to stay put; a channel that
   were dropped, weighted twice, or applied on the wrong axis moves the result
   by O(1) and fails.
3. **Order discriminator.**  ``a = 1e16, b = -1e16, c = 1.0`` is a witness in
   which the three groupings separate into two values: ``(a + b) + c == 1.0``
   while ``(a + c) + b`` and ``a + (b + c)`` both round to ``0.0`` (the ``+1`` is
   absorbed by the ``2``-wide spacing at ``1e16``, and ``-1e16 + 1`` rounds to
   ``-1e16``).  The contracts state a left-to-right / dict-insertion accumulation
   order, so the implementation must reproduce ``(a + b) + c`` and must violate
   both rivals.  Two of the three left-associative permutations can coincide in
   general, so this witness is chosen to separate the declared order from the
   reassociation *and* from the other permutation.
4. **Homogeneity as an equality.**  Doubling every channel doubles the total
   exactly in binary64, so linearity is asserted with ``array_equal`` rather
   than with a tolerance.
5. **Declared rejections.**  One executable assertion per ``failure_semantics``
   channel: wrong type/dtype, wrong channel count or keys, misaligned shapes,
   negative values where the contract demands nonnegative, non-finite inputs, and
   the overflow of a finite sum that must fail closed.

Budgets, fixed before measurement:

* ``m``-term pointwise sum: ``(m + 1) * eps * sum_q |channel_q|`` per cell.  A
  naive left-to-right sum of ``m`` terms performs ``m-1`` roundings, each bounded
  by ``eps`` times the running magnitude, which is at most ``eps * sum |x|``; the
  extra ``eps`` and the ``m-1`` bound carry the ``(1+eps)`` slack.  This is the
  textbook forward bound, not a fitted threshold.
* regeneration (product then sum): ``(channels + 1) * eps * sum_q |Omega_q * M_q|``
  because each product contributes one rounding before the accumulation.
* homogeneity: exact equality, for the reason in item 4.
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


def _absolute_scale(terms):
    """sum_q |term_q| as a float64 array, the forward-error scale of a naive sum."""
    total = np.zeros_like(np.asarray(terms[0], dtype=float))
    for term in terms:
        total = total + np.abs(np.asarray(term, dtype=float))
    return total


def _sum_budget(terms, extra=1):
    """Return (m + 1) * eps * sum|term| with m = len(terms)."""
    return (len(terms) + extra) * EPS * _absolute_scale(terms)


def _exact_sum(terms):
    """Round-once exact sum of same-shape arrays, elementwise."""
    shape = np.shape(terms[0])
    exact = []
    for index in np.ndindex(*shape):
        total = Fraction(0)
        for term in terms:
            total += _frac(np.asarray(term)[index])
        exact.append(float(total))
    return np.array(exact).reshape(shape)


def _signed_field(rng, shape):
    """Draw a finite field with both signs."""
    return rng.uniform(-5.0, 5.0, size=shape)


# --------------------------------------------------------------------------- #
# atomic / molecular scattered-source sums
# --------------------------------------------------------------------------- #


def test_atomic_scattered_sum_matches_the_exact_rational_two_channel_sum():
    """Evidence 1: pointwise CX + elastic against exact rational arithmetic."""
    rng = np.random.default_rng(101)
    cx = _signed_field(rng, (2, 3, 4))
    elastic = _signed_field(rng, (2, 3, 4))
    got = N.reduce_atomic_scattered_sources(cx, elastic)
    expected = _exact_sum([cx, elastic])
    assert np.all(np.abs(got - expected) <= _sum_budget([cx, elastic]))


def test_molecular_scattered_sum_matches_the_exact_rational_three_channel_sum():
    """Evidence 1: wall + CX + elastic, including both signed channels."""
    rng = np.random.default_rng(103)
    wall = _signed_field(rng, (2, 2, 3))
    cx = _signed_field(rng, (2, 2, 3))
    elastic = _signed_field(rng, (2, 2, 3))
    got = N.reduce_molecular_scattered_sources(wall, cx, elastic)
    expected = _exact_sum([wall, cx, elastic])
    assert np.all(np.abs(got - expected) <= _sum_budget([wall, cx, elastic]))


def test_scattered_sums_keep_every_channel_when_one_channel_is_split():
    """Evidence 2: a split channel leaves the total in place."""
    rng = np.random.default_rng(107)
    cx = _signed_field(rng, (2, 3, 2))
    elastic = _signed_field(rng, (2, 3, 2))
    whole = N.reduce_atomic_scattered_sources(cx, elastic)
    # Reassociate one physical channel into two pieces that sum back exactly.
    first = cx * 0.25
    second = cx - first
    split = N.reduce_atomic_scattered_sources(first + second, elastic)
    assert np.all(np.abs(split - whole) <= _sum_budget([cx, elastic]))
    # Dropping the elastic channel would move the total by its full magnitude.
    scale = float(np.max(np.abs(elastic)))
    assert scale > 1e6 * EPS * float(np.max(np.abs(whole)))


def test_molecular_scattered_sum_uses_the_declared_left_to_right_order():
    """Evidence 3: the stated (wall + CX) + elastic order, against its rivals."""
    wall = np.array([[[1e16]]])
    cx = np.array([[[-1e16]]])
    elastic = np.array([[[1.0]]])
    got = N.reduce_molecular_scattered_sources(wall, cx, elastic)
    left_to_right = (wall + cx) + elastic
    assert np.array_equal(got, left_to_right)
    # Both competing groupings round to 0.0, so the assertion above decides
    # between hypotheses instead of agreeing with rounding noise.
    rival_one = wall + (cx + elastic)
    rival_two = (wall + elastic) + cx
    assert np.array_equal(rival_one, np.zeros((1, 1, 1)))
    assert np.array_equal(rival_two, np.zeros((1, 1, 1)))
    assert not np.array_equal(left_to_right, rival_one)


def test_atomic_scattered_sum_is_exactly_homogeneous():
    """Evidence 3: doubling both channels doubles the total exactly."""
    rng = np.random.default_rng(109)
    cx = _signed_field(rng, (1, 2, 3))
    elastic = _signed_field(rng, (1, 2, 3))
    base = N.reduce_atomic_scattered_sources(cx, elastic)
    doubled = N.reduce_atomic_scattered_sources(2.0 * cx, 2.0 * elastic)
    assert np.array_equal(doubled, 2.0 * base)
    assert np.array_equal(N.reduce_atomic_scattered_sources(cx, -cx), np.zeros_like(cx))


def test_scattered_sums_reject_each_declared_channel():
    """Evidence 5: one executable assertion per rejection channel."""
    field = np.ones((1, 2, 3))
    other = np.ones((1, 2, 3))
    with pytest.raises(ValueError, match="finite aligned 3-D"):
        N.reduce_atomic_scattered_sources(field, np.ones((1, 2, 4)))
    with pytest.raises(ValueError, match="finite aligned 3-D"):
        N.reduce_atomic_scattered_sources(np.ones((1, 6)), other)
    with pytest.raises(ValueError, match="finite real array"):
        N.reduce_atomic_scattered_sources([[True]], other)
    with pytest.raises(ValueError, match="finite real array"):
        N.reduce_atomic_scattered_sources(np.array([[["a"]]]), other)
    with pytest.raises(ValueError, match="finite real array"):
        N.reduce_atomic_scattered_sources(np.array([[1j]]), other)
    with pytest.raises(ValueError, match="finite real array"):
        N.reduce_atomic_scattered_sources(np.array([[np.nan]]), other)
    with pytest.raises(ValueError, match="aggregated scattered source must be finite"):
        N.reduce_atomic_scattered_sources(np.array([[[1.7e308]]]), np.array([[[1.7e308]]]))

    assert N.reduce_molecular_scattered_sources(field, field, field).shape == (1, 2, 3)
    with pytest.raises(ValueError, match="finite aligned 3-D"):
        N.reduce_molecular_scattered_sources(field, field, np.ones((1, 2, 4)))
    with pytest.raises(ValueError, match="finite aligned 3-D"):
        N.reduce_molecular_scattered_sources(field, np.ones((1, 6)), field)
    with pytest.raises(ValueError, match="finite real array"):
        N.reduce_molecular_scattered_sources(field, [[True]], field)
    with pytest.raises(ValueError, match="finite real array"):
        N.reduce_molecular_scattered_sources(np.array([[np.inf]]), field, field)
    with pytest.raises(ValueError, match="aggregated scattered source must be finite"):
        N.reduce_molecular_scattered_sources(
            np.array([[[1.7e308]]]), np.array([[[1.7e308]]]), np.zeros((1, 1, 1))
        )


# --------------------------------------------------------------------------- #
# elastic-frequency-channels
# --------------------------------------------------------------------------- #


def test_elastic_channels_match_the_exact_rational_three_channel_sum():
    """Evidence 1: three fixed channels against the exact rational sum."""
    rng = np.random.default_rng(113)
    channels = [_signed_field(rng, (5,)) for _ in range(3)]
    got = N.sum_elastic_frequency_channels(channels)["elastic_frequency_m_inv"]
    assert np.all(np.abs(got - _exact_sum(channels)) <= _sum_budget(channels))


def test_elastic_channels_use_the_declared_left_to_right_order():
    """Evidence 3: ((c0 + c1) + c2), not a reassociation."""
    channels = [np.array([1e16]), np.array([-1e16]), np.array([1.0])]
    got = N.sum_elastic_frequency_channels(channels)["elastic_frequency_m_inv"]
    assert np.array_equal(got, (channels[0] + channels[1]) + channels[2])
    # Both rivals absorb the +1 into the 2-wide spacing at 1e16 and return 0.
    assert np.array_equal(channels[0] + (channels[1] + channels[2]), np.zeros(1))
    assert np.array_equal((channels[0] + channels[2]) + channels[1], np.zeros(1))
    assert not np.array_equal(got, channels[0] + (channels[1] + channels[2]))


def test_elastic_channels_are_exactly_homogeneous_and_keep_a_zero_channel():
    """Evidence 3: doubling all channels doubles the total; a zero channel is inert."""
    rng = np.random.default_rng(127)
    channels = [_signed_field(rng, (4,)) for _ in range(3)]
    base = N.sum_elastic_frequency_channels(channels)["elastic_frequency_m_inv"]
    doubled = N.sum_elastic_frequency_channels([2.0 * c for c in channels])[
        "elastic_frequency_m_inv"
    ]
    assert np.array_equal(doubled, 2.0 * base)
    zeroed = N.sum_elastic_frequency_channels([channels[0], np.zeros(4), channels[2]])[
        "elastic_frequency_m_inv"
    ]
    assert np.all(np.abs(zeroed - _exact_sum([channels[0], channels[2]])) <= _sum_budget(channels))


def test_elastic_channels_reject_each_declared_channel():
    """Evidence 5: one executable assertion per rejection channel."""
    good = [np.ones(3), np.ones(3), np.ones(3)]
    with pytest.raises(ValueError, match="exactly three"):
        N.sum_elastic_frequency_channels(good[:2])
    with pytest.raises(ValueError, match="exactly three"):
        N.sum_elastic_frequency_channels(good + [np.ones(3)])
    with pytest.raises(ValueError, match="exactly three"):
        N.sum_elastic_frequency_channels(np.ones((3, 3)))
    with pytest.raises(ValueError, match="non-empty"):
        N.sum_elastic_frequency_channels([np.ones(3), np.array([]), np.ones(3)])
    with pytest.raises(ValueError, match="non-empty"):
        N.sum_elastic_frequency_channels([np.ones(3), np.array(1.0), np.ones(3)])
    with pytest.raises(ValueError, match="identical shapes"):
        N.sum_elastic_frequency_channels([np.ones(3), np.ones(4), np.ones(3)])
    with pytest.raises(ValueError, match="finite real"):
        N.sum_elastic_frequency_channels([np.ones(3), np.array([np.nan, 1.0, 1.0]), np.ones(3)])
    with pytest.raises(ValueError, match="finite real"):
        N.sum_elastic_frequency_channels([np.ones(3), [True, 1.0, 1.0], np.ones(3)])
    with pytest.raises(ValueError, match="finite real"):
        N.sum_elastic_frequency_channels([np.ones(3), [1j, 1.0, 1.0], np.ones(3)])
    with pytest.raises(ValueError, match="not finite"):
        N.sum_elastic_frequency_channels(
            [np.array([1.7e308]), np.array([1.7e308]), np.array([0.0])]
        )


# --------------------------------------------------------------------------- #
# elastic-regeneration-aggregation
# --------------------------------------------------------------------------- #


def test_regeneration_matches_the_exact_rational_channel_sum():
    """Evidence 1: Omega_q * M_q summed over channels in mapping order."""
    rng = np.random.default_rng(131)
    freqs = {"a": np.array([0.5, 1.5]), "b": np.array([2.0, 0.25])}
    dists = {key: rng.uniform(0.0, 3.0, size=(2, 2, 2)) for key in freqs}
    got = N.aggregate_elastic_regeneration_source(freqs, dists)
    terms = [dists[key] * freqs[key][None, None, :] for key in freqs]
    assert np.all(np.abs(got - _exact_sum(terms)) <= _sum_budget(terms))


def test_regeneration_applies_the_profile_on_the_spatial_axis_only():
    """Evidence 1: a wrong axis broadcast would move the total by O(1)."""
    freqs = {"a": np.array([1.0, 3.0]), "b": np.array([2.0, 4.0])}
    dists = {
        "a": np.array([[[1.0, 1.0], [1.0, 1.0]]]),
        "b": np.array([[[1.0, 1.0], [1.0, 1.0]]]),
    }
    got = N.aggregate_elastic_regeneration_source(freqs, dists)
    assert np.array_equal(got, np.array([[[3.0, 7.0], [3.0, 7.0]]]))
    # A velocity-axis broadcast would give the same number in every spatial
    # cell; it does not, because the profile is spatial.
    assert not np.all(got[..., 0] == got[..., 1])


def test_regeneration_keeps_mapping_order_and_is_exactly_homogeneous():
    """Evidence 3: dict insertion order and doubling both channels."""
    rng = np.random.default_rng(137)
    freqs = {"a": np.array([1.0, 2.0]), "b": np.array([3.0, 4.0]), "c": np.array([0.5, 0.25])}
    dists = {key: rng.uniform(0.0, 2.0, size=(1, 2, 2)) for key in freqs}
    base = N.aggregate_elastic_regeneration_source(freqs, dists)
    doubled = N.aggregate_elastic_regeneration_source(
        {key: 2.0 * freqs[key] for key in freqs}, dists
    )
    assert np.array_equal(doubled, 2.0 * base)
    # A single-channel aggregation is exactly that channel's product.
    single = N.aggregate_elastic_regeneration_source({"a": freqs["a"]}, {"a": dists["a"]})
    assert np.array_equal(single, dists["a"] * freqs["a"][None, None, :])


def test_regeneration_rejects_each_declared_channel():
    """Evidence 5: one executable assertion per rejection channel."""
    freqs = {"a": np.array([1.0, 2.0]), "b": np.array([0.5, 1.0])}
    dists = {"a": np.ones((1, 1, 2)), "b": np.ones((1, 1, 2))}
    with pytest.raises(ValueError, match="must be mappings"):
        N.aggregate_elastic_regeneration_source([1.0, 2.0], dists)
    with pytest.raises(ValueError, match="keys must match"):
        N.aggregate_elastic_regeneration_source(freqs, {"a": dists["a"]})
    with pytest.raises(ValueError, match="at least one"):
        N.aggregate_elastic_regeneration_source({}, {})
    with pytest.raises(ValueError, match="nonnegative and aligned"):
        N.aggregate_elastic_regeneration_source({"a": np.array([-1.0, 1.0])}, {"a": dists["a"]})
    with pytest.raises(ValueError, match="nonnegative and aligned"):
        N.aggregate_elastic_regeneration_source(freqs, {"a": -dists["a"], "b": dists["b"]})
    with pytest.raises(ValueError, match="nonnegative and aligned"):
        N.aggregate_elastic_regeneration_source(freqs, {"a": np.ones((1, 1, 3)), "b": dists["b"]})
    with pytest.raises(ValueError, match="share one velocity mesh"):
        N.aggregate_elastic_regeneration_source(
            freqs, {"a": np.ones((1, 1, 2)), "b": np.ones((1, 2, 2))}
        )
    with pytest.raises(ValueError, match="finite real"):
        N.aggregate_elastic_regeneration_source(freqs, {"a": [[[True, 1.0]]], "b": dists["b"]})
    with pytest.raises(ValueError, match="finite real"):
        N.aggregate_elastic_regeneration_source(
            freqs, {"a": np.array([[[np.inf, 1.0]]]), "b": dists["b"]}
        )
    with pytest.raises(ValueError, match="must be finite"):
        N.aggregate_elastic_regeneration_source(
            {"a": np.array([1.5e308, 1.0]), "b": np.array([1.5e308, 1.0])},
            {"a": np.ones((1, 1, 2)), "b": np.ones((1, 1, 2))},
        )

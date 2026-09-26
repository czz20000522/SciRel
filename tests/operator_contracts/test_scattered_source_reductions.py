"""Direct contract tests for the scattered-generation source assets:
``reduce_atomic_scattered_sources``, ``reduce_molecular_scattered_sources``,
``aggregate_elastic_regeneration_source``, ``assemble_simple_charge_exchange_source``.

The saved KN1DPy packages (anchors kinetic_h.py:1297-1317, kinetic_h2.py:1422-1546,
kinetic_h.py:1340-1398 / kinetic_h2.py:1468-1538, kinetic_h.py:1297-1317 /
kinetic_h2.py:1444-1461 as recorded by the saved bundle's provenance) are
reproduced bit for bit; no repair is claimed.
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.kinetic import (
    aggregate_elastic_regeneration_source,
    assemble_simple_charge_exchange_source,
    reduce_atomic_scattered_sources,
    reduce_molecular_scattered_sources,
)


def test_atomic_reduction_sums_two_explicit_sources_and_preserves_signed_values():
    source = np.ones((1, 2, 3))
    np.testing.assert_allclose(reduce_atomic_scattered_sources(source, 2 * source), 3 * source)
    np.testing.assert_allclose(reduce_atomic_scattered_sources(source, -source), np.zeros_like(source))


def test_atomic_reduction_rejects_misaligned_or_nonfinite_fields():
    source = np.ones((1, 2, 3))
    with pytest.raises(ValueError, match="finite aligned 3-D"):
        reduce_atomic_scattered_sources(source, np.ones((1, 2, 4)))
    with pytest.raises(ValueError, match="finite aligned 3-D"):
        reduce_atomic_scattered_sources(source, np.full((1, 2, 3), np.nan))
    with pytest.raises(ValueError, match="finite aligned 3-D"):
        reduce_atomic_scattered_sources(source, np.ones((1, 2)))


def test_molecular_reduction_sums_three_channels_in_saved_source_order():
    rng = np.random.default_rng(31)
    wall, cx, elastic = (rng.random((2, 3, 4)) for _ in range(3))
    result = reduce_molecular_scattered_sources(wall, cx, elastic)
    np.testing.assert_array_equal(result, wall + cx + elastic)


def test_molecular_reduction_rejects_misaligned_fields():
    with pytest.raises(ValueError, match="finite aligned 3-D"):
        reduce_molecular_scattered_sources(np.ones((2, 3, 4)), np.ones((2, 3, 4)), np.ones((2, 3, 5)))


def test_regeneration_aggregation_sums_channel_weighted_distributions():
    rng = np.random.default_rng(32)
    freqs = {"a": rng.random(5), "b": rng.random(5)}
    dists = {"a": rng.random((2, 3, 5)), "b": rng.random((2, 3, 5))}
    result = aggregate_elastic_regeneration_source(freqs, dists)
    expected = dists["a"] * freqs["a"][None, None, :] + dists["b"] * freqs["b"][None, None, :]
    np.testing.assert_array_equal(result, expected)


def test_regeneration_aggregation_key_and_field_contracts_fail_closed():
    freqs = {"a": np.ones(5), "b": np.ones(5)}
    dists = {"a": np.ones((2, 3, 5))}
    with pytest.raises(ValueError, match="channel keys must match"):
        aggregate_elastic_regeneration_source(freqs, dists)
    with pytest.raises(ValueError, match="finite, nonnegative"):
        aggregate_elastic_regeneration_source({"a": np.full(5, -1.0)}, {"a": np.ones((2, 3, 5))})
    with pytest.raises(ValueError, match="finite, nonnegative"):
        aggregate_elastic_regeneration_source({"a": np.ones(5)}, {"a": np.full((2, 3, 4), np.nan)})
    with pytest.raises(ValueError, match="at least one elastic channel"):
        aggregate_elastic_regeneration_source({}, {})


def test_simple_cx_source_is_cell_local_weighted_rate_times_target():
    target = np.ones((1, 2, 2))
    alpha = np.array([[[2.0, 3.0], [4.0, 5.0]]])
    previous = np.ones((1, 2, 2))
    weight = np.ones((1, 2))
    dvx = np.array([0.5, 1.0])
    result = assemble_simple_charge_exchange_source(target, alpha, previous, weight, dvx)
    expected_rate = np.array([
        np.sum(weight * alpha[:, :, k] * previous[:, :, k] * dvx[None, :]) for k in range(2)
    ])
    np.testing.assert_allclose(result, np.broadcast_to(expected_rate[None, None, :], (1, 2, 2)))
    np.testing.assert_allclose(result, [[[5.0, 6.5], [5.0, 6.5]]])


def test_simple_cx_source_alignment_and_nonnegativity_contracts_fail_closed():
    target = np.ones((2, 2, 2))
    alpha = np.ones((2, 2, 2))
    previous = np.ones((2, 2, 2))
    weight = np.ones((2, 2))
    dvx = np.array([0.5, 1.0])
    with pytest.raises(ValueError, match="finite and aligned"):
        assemble_simple_charge_exchange_source(target, alpha, previous, weight, np.array([0.5, -1.0]))
    with pytest.raises(ValueError, match="finite and aligned"):
        assemble_simple_charge_exchange_source(target, alpha, previous, np.ones((3, 2)), dvx)
    with pytest.raises(ValueError, match="finite and aligned"):
        assemble_simple_charge_exchange_source(
            target, -alpha, previous, weight, dvx
        )

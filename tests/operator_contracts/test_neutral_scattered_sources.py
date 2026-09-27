"""Direct contracts for four explicit neutral scattered-source leaves."""

import numpy as np
import pytest

from scirel.kinetic import (
    aggregate_elastic_regeneration_source,
    assemble_simple_charge_exchange_source,
    reduce_atomic_scattered_sources,
    reduce_molecular_scattered_sources,
)


def test_saved_finite_samples_remain_fixed():
    source = np.ones((1, 2, 3))
    np.testing.assert_allclose(reduce_atomic_scattered_sources(source, 2 * source), 3 * source)
    np.testing.assert_allclose(reduce_atomic_scattered_sources(source, -source), np.zeros_like(source))

    rng = np.random.default_rng(31)
    wall, cx, elastic = (rng.random((2, 3, 4)) for _ in range(3))
    np.testing.assert_array_equal(reduce_molecular_scattered_sources(wall, cx, elastic), wall + cx + elastic)
    np.testing.assert_allclose(
        reduce_molecular_scattered_sources(source, 2 * source, 3 * source), 6 * source
    )
    np.testing.assert_allclose(
        reduce_molecular_scattered_sources(source, -source, source), source
    )

    frequencies = {"a": np.array([1.0, 2.0]), "b": np.array([0.5, 1.0])}
    distributions = {key: np.ones((1, 1, 2)) for key in frequencies}
    np.testing.assert_array_equal(
        aggregate_elastic_regeneration_source(frequencies, distributions), [[[1.5, 3.0]]]
    )
    np.testing.assert_allclose(
        aggregate_elastic_regeneration_source(
            {"h": [2, 3], "p": [1, 4]},
            {"h": np.ones((1, 1, 2)), "p": 2 * np.ones((1, 1, 2))},
        ),
        [[[4, 11]]],
    )

    target = np.ones((1, 2, 2))
    alpha = np.array([[[2.0, 3.0], [4.0, 5.0]]])
    result = assemble_simple_charge_exchange_source(
        target, alpha, target, np.ones((1, 2)), np.array([0.5, 1.0])
    )
    np.testing.assert_allclose(result, [[[5.0, 6.5], [5.0, 6.5]]])


def test_atomic_sum_preserves_signed_cells():
    cx = np.array([[[-2.0, 3.0]]])
    elastic = np.array([[[1.0, -3.0]]])
    np.testing.assert_array_equal(reduce_atomic_scattered_sources(cx, elastic), cx + elastic)


def test_molecular_sum_preserves_source_order_and_signed_cells():
    wall = np.array([[[1.0e16, -2.0]]])
    cx = np.array([[[-1.0e16, 3.0]]])
    elastic = np.array([[[1.0, -4.0]]])
    np.testing.assert_array_equal(
        reduce_molecular_scattered_sources(wall, cx, elastic), (wall + cx) + elastic
    )


@pytest.mark.parametrize("bad", [[[True]], [["1"]], [[1.0 + 0j]]])
def test_atomic_rejects_implicit_real_conversion(bad):
    with pytest.raises(ValueError, match="charge_exchange_source_distribution"):
        reduce_atomic_scattered_sources(bad, np.ones((1, 1, 1)))


def test_scattered_sums_reject_shape_and_derived_overflow():
    one = np.ones((1, 1, 1))
    with pytest.raises(ValueError, match="aligned"):
        reduce_atomic_scattered_sources(one, np.ones((1, 1, 2)))
    with pytest.raises(ValueError, match="aligned"):
        reduce_molecular_scattered_sources(one, one, np.ones((1, 1, 2)))
    large = np.full((1, 1, 1), 1.0e308)
    with pytest.raises(ValueError, match="finite"):
        reduce_atomic_scattered_sources(large, large)
    with pytest.raises(ValueError, match="finite"):
        reduce_molecular_scattered_sources(large, large, large)


def test_regeneration_aggregation_preserves_mapping_order():
    omega = {key: np.ones(1) for key in ("large", "first", "second")}
    regenerated = {
        "large": np.full((1, 1, 1), 1.0e16),
        "first": np.ones((1, 1, 1)),
        "second": np.ones((1, 1, 1)),
    }
    expected = regenerated["large"] * omega["large"][None, None, :]
    expected = expected + regenerated["first"] * omega["first"][None, None, :]
    expected = expected + regenerated["second"] * omega["second"][None, None, :]
    np.testing.assert_array_equal(aggregate_elastic_regeneration_source(omega, regenerated), expected)


def test_regeneration_rejects_keys_meshes_and_nonfinite_output():
    one = np.ones((1, 1, 2))
    with pytest.raises(ValueError, match="mappings"):
        aggregate_elastic_regeneration_source([], [])
    with pytest.raises(ValueError, match="keys"):
        aggregate_elastic_regeneration_source({"a": np.ones(2)}, {"b": one})
    with pytest.raises(ValueError, match="at least one"):
        aggregate_elastic_regeneration_source({}, {})
    with pytest.raises(ValueError, match="one velocity mesh"):
        aggregate_elastic_regeneration_source(
            {"a": np.ones(2), "b": np.ones(2)},
            {"a": one, "b": np.ones((2, 2, 2))},
        )
    with pytest.raises(ValueError, match="finite"):
        aggregate_elastic_regeneration_source(
            {"a": np.full(2, 1.0e308)}, {"a": np.full((1, 1, 2), 1.0e308)}
        )


@pytest.mark.parametrize("bad", [[True], ["1"], [1.0 + 0j]])
def test_regeneration_rejects_implicit_real_conversion(bad):
    with pytest.raises(ValueError, match="frequencies_s_inv"):
        aggregate_elastic_regeneration_source({"a": bad}, {"a": np.ones((1, 1, 1))})


def test_simple_cx_source_is_cell_local_and_preserves_signed_factors():
    target = np.array([[[1.0, -2.0], [3.0, 4.0]]])
    alpha = np.array([[[2.0, 3.0], [4.0, 5.0]]])
    previous = np.array([[[1.0, -1.0], [2.0, 1.0]]])
    weight = np.ones((1, 2))
    dvx = np.array([0.5, 1.0])
    rate = np.sum(weight[:, :, None] * alpha * previous * dvx[None, :, None], axis=(0, 1))
    np.testing.assert_array_equal(
        assemble_simple_charge_exchange_source(target, alpha, previous, weight, dvx),
        target * rate[None, None, :],
    )


def test_simple_cx_rejects_alignment_and_derived_overflow():
    one = np.ones((1, 1, 1))
    with pytest.raises(ValueError, match="aligned"):
        assemble_simple_charge_exchange_source(one, one, one, np.ones((1, 1)), np.ones(2))
    with pytest.raises(ValueError, match="nonnegative"):
        assemble_simple_charge_exchange_source(one, -one, one, np.ones((1, 1)), np.ones(1))
    with pytest.raises(ValueError, match="finite"):
        assemble_simple_charge_exchange_source(
            one, np.full((1, 1, 1), 1.0e308), np.full((1, 1, 1), 1.0e308),
            np.ones((1, 1)), np.ones(1),
        )


@pytest.mark.parametrize("bad", [[True], ["1"], [1.0 + 0j]])
def test_simple_cx_rejects_implicit_real_conversion(bad):
    with pytest.raises(ValueError, match="dvx"):
        assemble_simple_charge_exchange_source(
            np.ones((1, 1, 1)), np.ones((1, 1, 1)), np.ones((1, 1, 1)),
            np.ones((1, 1)), bad,
        )

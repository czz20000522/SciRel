"""Malformed source states must fail without corrupting an existing source."""

import numpy as np
import pytest
from scirel.electromagnetism import ArbitraryPoints, RectangularCoil, MagnetRing


@pytest.mark.parametrize("points", [[[-1.0, 0.0]], [[1.0, np.nan]]])
def test_arbitrary_points_validate_at_construction(points):
    with pytest.raises(ValueError):
        ArbitraryPoints(points)


def test_point_replacement_rejects_cardinality_change():
    source = ArbitraryPoints([[1.0, 0.0]])
    before = source.rzw.copy()
    with pytest.raises(ValueError):
        source.rz_pts = [[1.0, 0.0], [2.0, 0.0]]
    np.testing.assert_array_equal(source.rzw, before)


def test_ring_weight_resize_rejected():
    source = MagnetRing()
    before = source.rzw.copy()
    with pytest.raises(ValueError):
        source.weights = [-1.0, 1.0]
    np.testing.assert_array_equal(source.rzw, before)


@pytest.mark.parametrize("name,value", [("nr", 2), ("r0", -1.0), ("dr", np.nan), ("angle", np.inf)])
def test_coil_invalid_setter_is_atomic(name, value):
    source = RectangularCoil()
    before = source.rzw.copy()
    old = getattr(source, name)
    with pytest.raises(ValueError):
        setattr(source, name, value)
    assert getattr(source, name) == old
    np.testing.assert_array_equal(source.rzw, before)


@pytest.mark.parametrize("name,value", [("width", -1.0), ("height", np.nan), ("r0", -1.0)])
def test_ring_invalid_setter_is_atomic(name, value):
    source = MagnetRing()
    before = source.rzw.copy()
    old = getattr(source, name)
    with pytest.raises(ValueError):
        setattr(source, name, value)
    assert getattr(source, name) == old
    np.testing.assert_array_equal(source.rzw, before)


@pytest.mark.parametrize("source", [ArbitraryPoints([[1.0, 0.0]]), RectangularCoil(), MagnetRing()])
def test_invalid_translation_is_atomic(source):
    before = source.rzw.copy()
    with pytest.raises(ValueError):
        source.translate([-2.0, 0.0])
    np.testing.assert_array_equal(source.rzw, before)


def test_generated_points_must_have_nonnegative_radius():
    with pytest.raises(ValueError):
        RectangularCoil(0.01, nr=2, dr=0.1)
    with pytest.raises(ValueError):
        MagnetRing(0.001, width=0.1)


@pytest.mark.parametrize("factory", [RectangularCoil, MagnetRing])
def test_invalid_centroid_replacement_is_atomic(factory):
    source = factory()
    before = source.rzw.copy()
    center = source.centroid.copy()
    with pytest.raises(ValueError):
        source.centroid = [2.0, np.nan]
    np.testing.assert_array_equal(source.centroid, center)
    np.testing.assert_array_equal(source.rzw, before)


@pytest.mark.parametrize("factory", [RectangularCoil, MagnetRing])
def test_rotation_to_negative_radius_is_atomic(factory):
    source = factory()
    before = source.rzw.copy()
    center = source.centroid.copy()
    with pytest.raises(ValueError):
        source.rotate(180.0)
    np.testing.assert_array_equal(source.centroid, center)
    np.testing.assert_array_equal(source.rzw, before)


def test_cache_mutation_does_not_change_later_evaluation():
    source = ArbitraryPoints([[1.0, 0.0]], mesh=np.array([[0.2, 0.3]]))
    expected = source.gpsi().copy()
    exposed = source.gpsi()
    exposed[:] = 42.0
    np.testing.assert_array_equal(source.gpsi(), expected)

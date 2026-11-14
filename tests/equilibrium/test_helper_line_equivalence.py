"""Check selected line diagnostics, known class differences, and contour factories.

Boundary/intersection behavior is covered by test_fieldline_geometry_repair;
curvature accuracy is covered by test_fieldline_t7_precision and
test_curvature_consumer. This file does not cover every method of both classes.
"""

from types import SimpleNamespace

import numpy as np
import pytest

from scirel.geometry.fieldline import (
    FieldLine,
    HelperFieldLine,
    contour_points,
    helper_contour_points,
)

VERTS = np.array([[0.2, 0.0], [0.6, 0.1], [1.0, 0.0], [1.2, 0.2]])


def _pair():
    return FieldLine(0.2, VERTS), HelperFieldLine(0.2, VERTS)


def _grid():
    r, z = np.meshgrid(np.linspace(0.1, 1.3, 15), np.linspace(-0.3, 0.4, 15))
    return r, z, np.sin(r) + z


def test_selected_diagnostics_agree_bit_for_bit_on_the_same_input():
    field_line, helper = _pair()
    np.testing.assert_array_equal(field_line.verts, helper.verts)
    np.testing.assert_array_equal(field_line.u, helper.u)
    for left, right in zip(field_line.tck, helper.tck):
        np.testing.assert_array_equal(left, right)

    np.testing.assert_array_equal(field_line.get_svec(), helper.get_svec())
    np.testing.assert_array_equal(field_line.get_ds(), helper.get_ds())
    assert field_line.get_length() == helper.get_length()
    assert field_line.is_closed() == helper.is_closed()

    u = np.array([0.2, 0.5, 0.8])
    np.testing.assert_array_equal(field_line.interpolate(u), helper.interpolate(u))

    r, z, q = _grid()
    br = np.full_like(r, 0.15)
    bz = np.ones_like(r)
    np.testing.assert_array_equal(
        field_line.interpolate_onto(r, z, q), helper.interpolate_onto(r, z, q)
    )
    np.testing.assert_array_equal(
        field_line.get_gradpsi(r, z, br, bz), helper.get_gradpsi(r, z, br, bz)
    )
    values = np.sin(field_line.verts[:, 0]) + field_line.verts[:, 1]
    np.testing.assert_array_equal(field_line.d_ds(values), helper.d_ds(values))


@pytest.mark.parametrize("klass", [FieldLine, HelperFieldLine])
@pytest.mark.parametrize("shape", ["grid", "column", "wrong-length"])
def test_d_ds_rejects_values_that_are_not_matched_line_samples(klass, shape):
    line = klass(0.2, VERTS)
    if shape == "grid":
        _, _, values = _grid()
    elif shape == "column":
        values = np.ones((line.verts.shape[0], 1))
    else:
        values = np.ones(line.verts.shape[0] - 1)

    with pytest.raises(ValueError, match="values must be"):
        line.d_ds(values)


def test_curvature_values_match_while_the_return_shape_differs():
    field_line, helper = _pair()
    r, z, _ = _grid()
    br = np.full_like(r, 0.15)
    bz = np.ones_like(r)

    array = field_line.get_kappa_n(r, z, br, bz)
    pair = helper.get_kappa_n(r, z, br, bz)

    assert array.shape == (field_line.verts.shape[0], 2)
    assert isinstance(pair, tuple) and len(pair) == 2
    np.testing.assert_array_equal(array[:, 0], pair[0])
    np.testing.assert_array_equal(array[:, 1], pair[1])


@pytest.mark.parametrize(
    "kwargs",
    [{"npts": 200}, {"u": [0.0, 0.2, 0.6, 1.0]}, {"s": 0.001}, {"k": 3}],
)
def test_only_field_line_accepts_fit_keywords(kwargs):
    line = FieldLine(0.2, VERTS, **kwargs)
    assert line.verts.shape == (kwargs.get("npts", 1000), 2)
    with pytest.raises(TypeError):
        HelperFieldLine(0.2, VERTS, **kwargs)


def test_flux_gradient_curvature_is_only_exposed_by_field_line():
    assert callable(FieldLine.get_kappa_n_2)
    assert not hasattr(HelperFieldLine, "get_kappa_n_2")


def test_non_finite_source_samples_are_filtered_only_by_field_line():
    r, z, q = _grid()
    poisoned = q.copy()
    poisoned[0, 0] = np.nan
    field_line, helper = _pair()

    filtered = field_line.interpolate_onto(r, z, poisoned)
    forwarded = helper.interpolate_onto(r, z, poisoned)

    assert np.all(np.isfinite(filtered))
    assert np.all(np.isnan(forwarded))


@pytest.mark.parametrize(
    ("factory", "klass"),
    [(contour_points, FieldLine), (helper_contour_points, HelperFieldLine)],
)
def test_factories_preserve_levels_segments_and_default_construction(factory, klass):
    shifted = VERTS + [2.0, 0.5]
    shorter = VERTS[:3]
    contour = SimpleNamespace(levels=[0.7, 0.2, 0.5], allsegs=[[VERTS, shifted], [], [shorter]])

    result = factory(contour)

    assert list(result) == [0.7, 0.2, 0.5]
    assert [len(result[level]) for level in [0.7, 0.2, 0.5]] == [2, 0, 1]
    for level, segments in [(0.7, [VERTS, shifted]), (0.2, []), (0.5, [shorter])]:
        for line, segment in zip(result[level], segments, strict=True):
            assert type(line) is klass
            assert line.psi == level
            np.testing.assert_array_equal(line._verts, segment)
            expected = klass(level, segment)
            assert line.verts.shape == (1000, 2)
            np.testing.assert_array_equal(line.verts, expected.verts)
            np.testing.assert_array_equal(line.u, expected.u)
            for actual_part, expected_part in zip(line.tck, expected.tck, strict=True):
                np.testing.assert_array_equal(actual_part, expected_part)


@pytest.mark.parametrize("factory", [contour_points, helper_contour_points])
def test_factories_accept_an_empty_contour_collection(factory):
    assert factory(SimpleNamespace(levels=[], allsegs=[])) == {}


@pytest.mark.parametrize(
    ("factory", "klass"),
    [(contour_points, FieldLine), (helper_contour_points, HelperFieldLine)],
)
@pytest.mark.parametrize("segment", [VERTS[:2], np.repeat(VERTS[:1], 3, axis=0)])
def test_factories_propagate_invalid_segment_constructor_errors(factory, klass, segment):
    with pytest.raises((ValueError, TypeError)) as constructor_error:
        klass(0.2, segment)

    contour = SimpleNamespace(levels=[0.7, 0.2], allsegs=[[VERTS], [VERTS, segment]])
    with pytest.raises(type(constructor_error.value)) as factory_error:
        factory(contour)
    assert str(factory_error.value) == str(constructor_error.value)

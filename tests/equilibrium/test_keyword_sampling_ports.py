"""Explicit sampling ports preserve positional field numerical paths.

The removed mapping alias is rejected rather than retained as compatibility.
"""

import inspect

import numpy as np
import pytest
from scipy.interpolate import griddata
from scipy.spatial import QhullError
from scirel.geometry import sampling


def test_regular_grid_explicit_signature_and_removed_values_mapping():
    signature = inspect.signature(sampling.regular_grid)
    assert str(signature) == (
        "(xx, yy, *fields, nx=200, ny=200, xi=None, yi=None, method='linear')"
    )
    assert signature.parameters["fields"].kind is inspect.Parameter.VAR_POSITIONAL
    for name in ("nx", "ny", "xi", "yi", "method"):
        assert signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY

    x, y = np.meshgrid(np.linspace(0, 1, 4), np.linspace(0, 1, 4))
    q = x + 2 * y
    explicit = sampling.regular_grid(x, y, q, nx=5, ny=6)
    assert len(explicit) == 3
    assert explicit[0].shape == explicit[1].shape == explicit[2].shape == (5, 6)
    with pytest.raises(TypeError, match="values"):
        sampling.regular_grid(x, y, values=[q], nx=5, ny=6)


def test_regular_grid_regenerates_both_axes_when_one_query_axis_is_missing():
    x, y = np.meshgrid(np.linspace(-1, 1, 4), np.linspace(-0.5, 0.5, 4))
    q = x + 2 * y
    actual_x, actual_y, _ = sampling.regular_grid(
        x,
        y,
        q,
        nx=5,
        ny=6,
        xi=np.linspace(-10.0, 10.0, 4),
    )
    expected_x, expected_y = np.meshgrid(
        np.linspace(x.min(), x.max(), 5),
        np.linspace(y.min(), y.max(), 6),
        indexing="ij",
    )
    np.testing.assert_array_equal(actual_x, expected_x)
    np.testing.assert_array_equal(actual_y, expected_y)


def test_reflection_named_quantities_match_legacy_positional_fields():
    x, y = np.meshgrid([0.0, 0.5, 1.0], [-0.2, 0.2])
    q = x * x + y
    old = sampling.reflect_and_hstack(x, y, q)
    named = sampling.reflect_and_hstack(x, y, quantities=[q])
    assert len(named) == len(old) == 3
    for a, b in zip(named, old):
        np.testing.assert_array_equal(a, b)
    with pytest.raises(ValueError):
        sampling.reflect_and_hstack(x, y, q, quantities=[q])


@pytest.mark.parametrize("method", ["linear", "cubic", "nearest"])
def test_regular_grid_multi_field_parity_with_griddata(method):
    """Reusing one triangulation must preserve every griddata field result."""
    rng = np.random.default_rng(20261017)
    points = rng.uniform(-1.0, 1.0, size=(40, 2))
    fields = [rng.normal(size=points.shape[0]), rng.normal(size=points.shape[0])]
    fields[1][3] = np.nan
    xi, yi = np.meshgrid(
        np.linspace(-1.4, 1.4, 17),
        np.linspace(-1.3, 1.3, 13),
        indexing="ij",
    )

    actual = sampling.regular_grid(points[:, 0], points[:, 1], *fields, xi=xi, yi=yi, method=method)
    expected = [griddata(points, field, (xi, yi), method=method) for field in fields]
    assert actual[0] is xi and actual[1] is yi
    for got, want in zip(actual[2:], expected):
        np.testing.assert_array_equal(got, want)


def test_regular_grid_empty_fields_and_failure_paths_remain_unchanged():
    x, y = np.meshgrid(np.linspace(0.0, 1.0, 4), np.linspace(0.0, 1.0, 4))
    xi, yi = np.meshgrid(
        np.linspace(-1.0, 2.0, 3),
        np.linspace(-1.0, 2.0, 5),
        indexing="ij",
    )
    empty = sampling.regular_grid(x, y, xi=xi, yi=yi, method="linear")
    assert len(empty) == 2
    assert empty[0] is xi and empty[1] is yi

    with pytest.raises(ValueError, match="different number of values and points"):
        sampling.regular_grid(x, y, np.ones(3), xi=xi, yi=yi, method="linear")
    with pytest.raises(
        ValueError,
        match="Unknown interpolation method 'bogus' for 2 dimensional data",
    ):
        sampling.regular_grid(x, y, x + y, xi=xi, yi=yi, method="bogus")
    with pytest.raises(TypeError, match="metod"):
        sampling.regular_grid(x, y, x + y, xi=xi, yi=yi, metod="cubic")

    degenerate_x = np.zeros((2, 2))
    degenerate_y = np.zeros((2, 2))
    with pytest.raises(QhullError):
        sampling.regular_grid(
            degenerate_x,
            degenerate_y,
            np.ones_like(degenerate_x),
            xi=np.array([0.0]),
            yi=np.array([0.0]),
            method="linear",
        )

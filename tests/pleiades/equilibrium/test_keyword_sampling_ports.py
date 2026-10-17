"""Named exact-document ports preserve original positional numerical paths.

The pre-adapter source failures are retained in keyword-ports-before.stdout.
"""
import numpy as np
import pytest
from scipy.interpolate import griddata
from scipy.spatial import QhullError
from scirel.geometry import sampling

def test_regular_grid_named_values_match_legacy_positional_fields():
    x,y=np.meshgrid(np.linspace(0,1,4),np.linspace(0,1,4))
    q=x+2*y
    old=sampling.regular_grid(x,y,q,nx=5,ny=6)
    named=sampling.regular_grid(x,y,values=[q],nx=5,ny=6)
    assert len(named)==len(old)==3
    for a,b in zip(named,old):np.testing.assert_array_equal(a,b)
    with pytest.raises(ValueError):sampling.regular_grid(x,y,q,values=[q])

def test_reflection_named_quantities_match_legacy_positional_fields():
    x,y=np.meshgrid([0.,.5,1.],[-.2,.2]);q=x*x+y
    old=sampling.reflect_and_hstack(x,y,q)
    named=sampling.reflect_and_hstack(x,y,quantities=[q])
    assert len(named)==len(old)==3
    for a,b in zip(named,old):np.testing.assert_array_equal(a,b)
    with pytest.raises(ValueError):sampling.reflect_and_hstack(x,y,q,quantities=[q])


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

    actual = sampling.regular_grid(
        points[:, 0], points[:, 1], *fields, xi=xi, yi=yi, method=method
    )
    expected = [
        griddata(points, field, (xi, yi), method=method)
        for field in fields
    ]
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
        sampling.regular_grid(
            x, y, np.ones(3), xi=xi, yi=yi, method="linear"
        )
    with pytest.raises(ValueError, match="Unknown interpolation method"):
        sampling.regular_grid(x, y, x + y, xi=xi, yi=yi, method="bogus")

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

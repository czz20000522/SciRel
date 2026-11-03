"""Fail-closed input validation for the public spline constructors."""

import numpy as np
import pytest

from scirel.geometry.basis import (
    ClampedCubicSpline,
    FirstClampedCubicSpline,
    NaturalCubicSpline,
    SecondClampedCubicSpline,
)


@pytest.mark.parametrize(
    "constructor",
    [
        NaturalCubicSpline,
        ClampedCubicSpline,
        FirstClampedCubicSpline,
        SecondClampedCubicSpline,
    ],
)
def test_spline_constructors_reject_unsupported_knot_geometry(constructor):
    """The declared spline domain must fail before matrix construction."""
    cases = [
        ([0.0, 1.0], [0.0, 1.0]),
        ([0.0, 0.0, 1.0], [0.0, 1.0, 2.0]),
        ([0.0, 2.0, 1.0], [0.0, 1.0, 2.0]),
        ([0.0, np.nan, 1.0], [0.0, 1.0, 2.0]),
        ([0.0, 1.0, 2.0], [0.0, np.nan, 2.0]),
    ]
    for x_data, y_data in cases:
        with pytest.raises(ValueError, match="finite|strictly increasing|at least 3"):
            constructor(x_data, y_data)


@pytest.mark.parametrize("x_data", [[1.0, 2.0, 3.0], [-3.0, -2.0, -1.0], [-2.0, -1.0, 0.0]])
def test_second_clamped_spline_rejects_knots_outside_its_declared_domain(x_data):
    """These knots used to return meaningless or NaN slopes without an error."""
    with pytest.raises(ValueError, match="x_data must start at 0"):
        SecondClampedCubicSpline(x_data, [0.0, 0.2, 1.0])


def test_clamped_spline_default_slopes_are_not_a_shared_mutable_object():
    assert ClampedCubicSpline.__init__.__defaults__ == ((0, 0),)

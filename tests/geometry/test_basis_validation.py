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

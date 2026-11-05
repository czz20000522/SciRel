"""Closed-contour normalization for the public segment parser."""

import numpy as np
import pytest

from scirel.geometry.sampling import parse_segment


@pytest.mark.parametrize(
    ("clockwise", "expected"),
    [
        (True, np.array([[0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0], [0.0, 1.0]])),
        (False, np.array([[0.0, 1.0], [0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])),
    ],
)
def test_closed_contour_is_reclosed_without_a_zero_length_step(clockwise, expected):
    points = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]])

    segment = parse_segment(points, start_coord=(0.0, 1.0), clockwise=clockwise)

    np.testing.assert_array_equal(segment, expected)
    assert np.all(np.linalg.norm(np.diff(segment, axis=0), axis=1) > 0.0)


def test_explicit_end_suppresses_automatic_reclosing():
    points = np.array([[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]])

    segment = parse_segment(
        points,
        start_coord=(0.0, 1.0),
        end_coord=(1.0, 0.0),
        clockwise=True,
    )

    np.testing.assert_array_equal(
        segment,
        np.array([[0.0, 1.0], [1.0, 1.0], [1.0, 0.0]]),
    )

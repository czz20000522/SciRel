"""Thresholded SVD pseudo-inverse: identity, truncation and rejection."""
import numpy as np
import pytest

from scirel.geometry import truncated_svd_inverse


def test_matches_numpy_pinv_on_square_tall_and_wide_matrices():
    rng = np.random.default_rng(7)
    for shape in ((4, 4), (5, 3), (3, 5)):
        matrix = rng.normal(size=shape)
        np.testing.assert_allclose(
            truncated_svd_inverse(matrix), np.linalg.pinv(matrix),
            rtol=1e-12, atol=1e-14)


def test_truncates_rank_deficient_spectrum():
    matrix = np.array([[1.0, 2.0], [2.0, 4.0]])
    np.testing.assert_allclose(
        truncated_svd_inverse(matrix), np.linalg.pinv(matrix, rcond=1e-10),
        rtol=1e-12, atol=1e-14)


def test_projects_onto_range_and_nullspace():
    rng = np.random.default_rng(11)
    matrix = rng.normal(size=(6, 4))
    inverse = truncated_svd_inverse(matrix)
    np.testing.assert_allclose(matrix @ inverse @ matrix, matrix,
                               rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize("bad", [np.zeros(3), np.zeros((2, 2, 2))])
def test_rejects_non_2d_input(bad):
    with pytest.raises(ValueError, match="2-D"):
        truncated_svd_inverse(bad)


def test_rejects_nonfinite_matrix_and_bad_threshold():
    with pytest.raises(ValueError, match="finite"):
        truncated_svd_inverse([[1.0, np.nan], [0.0, 1.0]])
    with pytest.raises(ValueError, match="rcond"):
        truncated_svd_inverse(np.eye(2), rcond=0.0)
    with pytest.raises(ValueError, match="rcond"):
        truncated_svd_inverse(np.eye(2), rcond=float("inf"))


def test_rcond_is_relative_to_the_largest_singular_value():
    matrix = np.diag([1.0e-11, 1.0e-6])
    inverse = truncated_svd_inverse(matrix, rcond=1.0e-10)
    np.testing.assert_allclose(
        inverse, np.linalg.pinv(matrix, rcond=1.0e-10), rtol=1e-14, atol=0.0
    )

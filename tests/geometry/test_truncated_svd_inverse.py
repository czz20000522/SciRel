"""Thresholded SVD pseudo-inverse: identity, truncation and rejection."""

import numpy as np
import pytest

from scirel.geometry import truncated_svd_inverse


def test_matches_numpy_pinv_on_square_tall_and_wide_matrices():
    rng = np.random.default_rng(7)
    for shape in ((4, 4), (5, 3), (3, 5)):
        matrix = rng.normal(size=shape)
        np.testing.assert_allclose(
            truncated_svd_inverse(matrix), np.linalg.pinv(matrix), rtol=1e-12, atol=1e-14
        )


def test_truncates_rank_deficient_spectrum():
    matrix = np.array([[1.0, 2.0], [2.0, 4.0]])
    np.testing.assert_allclose(
        truncated_svd_inverse(matrix), np.linalg.pinv(matrix, rcond=1e-10), rtol=1e-12, atol=1e-14
    )


def test_projects_onto_range_and_nullspace():
    rng = np.random.default_rng(11)
    matrix = rng.normal(size=(6, 4))
    inverse = truncated_svd_inverse(matrix)
    np.testing.assert_allclose(matrix @ inverse @ matrix, matrix, rtol=1e-12, atol=1e-12)


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


@pytest.mark.parametrize("bad_rcond", [None, "1e-10", [1.0e-10], True])
def test_rejects_non_real_threshold(bad_rcond):
    with pytest.raises(ValueError, match="rcond"):
        truncated_svd_inverse(np.eye(2), rcond=bad_rcond)


def test_rcond_is_relative_to_the_largest_singular_value():
    matrix = np.diag([1.0e-11, 1.0e-6])
    inverse = truncated_svd_inverse(matrix, rcond=1.0e-10)
    np.testing.assert_allclose(inverse, np.linalg.pinv(matrix, rcond=1.0e-10), rtol=1e-14, atol=0.0)


def test_zero_matrix_returns_zero_pseudo_inverse():
    inverse = truncated_svd_inverse(np.zeros((3, 2)))
    assert inverse.shape == (2, 3)
    assert np.all(inverse == 0.0)
    assert np.isfinite(inverse).all()


def test_threshold_still_discards_singular_values_below_rcond():
    # A singular value below the relative threshold is legitimately truncated,
    # so its overflowing reciprocal is never formed.
    matrix = np.diag([1.0, 1.0e-310])
    np.testing.assert_allclose(
        truncated_svd_inverse(matrix),
        np.linalg.pinv(matrix, rcond=1.0e-10),
        rtol=1e-14,
        atol=0.0,
    )


def test_finite_input_with_unrepresentable_retained_reciprocal_raises():
    with pytest.raises(FloatingPointError, match="not representable as finite float64"):
        truncated_svd_inverse(np.array([[1.0e-310]]))


def test_finite_input_retained_only_by_small_rcond_still_raises():
    matrix = np.diag([1.0, 1.0e-310])
    with pytest.raises(FloatingPointError, match="not representable as finite float64"):
        truncated_svd_inverse(matrix, rcond=1.0e-320)


def test_representable_small_reciprocal_keeps_its_numeric_value():
    matrix = np.array([[1.0e-300]])
    inverse = truncated_svd_inverse(matrix)
    np.testing.assert_allclose(inverse, np.linalg.pinv(matrix), rtol=1e-14, atol=0.0)
    assert np.isfinite(inverse).all()


def test_finite_input_with_unrepresentable_singular_values_raises():
    with pytest.raises(FloatingPointError, match="singular values"):
        truncated_svd_inverse(np.full((2, 2), 1.0e308))

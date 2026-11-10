"""Regression tests for the retained spline boundary and basis conventions."""

import numpy as np
import pytest

from scirel.geometry import basis


def test_finite_outside_and_nonfinite_queries_retain_zero_fill():
    fitted = [
        basis.NaturalCubicSpline([-0.6, -0.4, 0.2, 0.9, 1.4], np.cos([-0.6, -0.4, 0.2, 0.9, 1.4])),
        basis.ClampedCubicSpline([-0.6, -0.4, 0.2, 0.9, 1.4], np.cos([-0.6, -0.4, 0.2, 0.9, 1.4])),
        basis.FirstClampedCubicSpline([0.1, 0.3, 0.8, 1.4], [0.0, 0.2, 0.7, 1.0]),
        basis.SecondClampedCubicSpline([0.0, 0.3, 0.8, 1.4], [0.0, 0.2, 0.7, 1.0]),
    ]
    for fit in fitted:
        x = fit.x_data
        queries = np.array([x[0] - 1.0, np.nextafter(x[-1], np.inf), np.nan, np.inf, -np.inf])
        for deriv in (0, 1, 2, 3):
            np.testing.assert_array_equal(fit(queries, deriv=deriv), np.zeros(queries.size))


def test_polynomial_basis_matrix_does_not_zero_outside_or_nonfinite_queries():
    matrix = basis.BasisMatrix("poly")(np.array([-1.0, 2.0, np.nan]))

    np.testing.assert_allclose(matrix[:2], [[1.0, -1.0, 1.0], [1.0, 2.0, 4.0]])
    assert np.isnan(matrix[2]).all()


def test_second_clamped_spline_rejects_nonzero_origin_ordinate():
    with pytest.raises(ValueError, match=r"y_data\[0\] must be 0"):
        basis.SecondClampedCubicSpline([0.0, 0.3, 1.0], [0.1, 0.2, 1.0])


def test_second_clamped_default_basis_is_homogeneous_at_the_origin():
    matrix = basis.BasisMatrix("clamped_cubic_spline2", n_knots=5)

    assert matrix.basis_dim == 4
    values = matrix(np.linspace(0.0, 1.0, 5))
    assert values.shape == (5, 4)
    np.testing.assert_array_equal(values[0], np.zeros(4))


@pytest.mark.parametrize(
    ("name", "yp"),
    [("clamped_cubic_spline", (1.0, 0.0)), ("clamped_cubic_spline1", 1.0)],
)
def test_basis_matrix_rejects_nonzero_clamped_endpoint_slopes(name, yp):
    with pytest.raises(ValueError, match=r"yp=0.*zero endpoint slopes"):
        basis.BasisMatrix(name, n_knots=5, yp=yp)


def test_basis_matrix_accepts_zero_clamped_endpoint_slopes():
    matrix = basis.BasisMatrix("clamped_cubic_spline", n_knots=5, yp=(0.0, 0.0))

    assert matrix.basis_dim == 5


def test_spline_basis_rejects_too_few_knots():
    with pytest.raises(ValueError, match="n_knots must be at least 3"):
        basis.BasisMatrix("clamped_cubic_spline2", n_knots=1)


def test_basis_matrix_forwards_keywords_to_spline_columns_and_polynomial_rejects_them():
    matrix = basis.BasisMatrix("clamped_cubic_spline2", n_knots=5)
    domain = np.linspace(0.0, 1.0, 4)
    forwarded = matrix(domain, deriv=1)
    expected = np.column_stack([fn(domain, deriv=1) for fn in matrix.basis_fns])
    np.testing.assert_array_equal(forwarded, expected)
    assert not np.array_equal(forwarded, matrix(domain))
    with pytest.raises(TypeError):
        basis.BasisMatrix("poly")(domain, deriv=1)

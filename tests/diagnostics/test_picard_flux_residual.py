import numpy as np
import pytest

from scirel.diagnostics.picard_flux_residual import compute_picard_flux_residual, compute_picard_flux_residual as scientific_function


@pytest.mark.parametrize("previous,following,expected", [
    ([[1e308]], [[-1e308]], 2.0),
    ([[1.0, 0.0]], [[1.0, 1e-200]], 1e-200),
    ([[1e100]], [[1e300]], 1e200),
    ([[1e-300]], [[2e-300]], 1e-270),
])
def test_admitted_numerical_boundaries(previous, following, expected):
    with np.errstate(over="ignore", invalid="ignore"):
        actual = compute_picard_flux_residual(previous, following)["residual"]
    assert actual == pytest.approx(expected, rel=2e-14, abs=0)


def test_unrepresentable_residual_is_rejected():
    with pytest.raises(ValueError):
        compute_picard_flux_residual([[0.0]], [[1e308]])


def test_returns_zero_for_unchanged_flux():
    assert scientific_function([[1.0]], [[1.0]])["residual"] == 0.0


def test_returns_l2_relative_change():
    result = scientific_function([[3.0, 4.0]], [[6.0, 8.0]])
    assert np.isclose(result["residual"], 1.0)


def test_rejects_mismatched_or_nonfinite_flux_states():
    with pytest.raises(ValueError, match="same-shape two-dimensional"):
        scientific_function([[1.0, 2.0]], [[1.0], [2.0]])
    with pytest.raises(ValueError, match="only finite values"):
        scientific_function([[1.0]], [[np.nan]])


def test_reviewed_relation_example():
    from scirel.diagnostics.picard_flux_residual import compute_picard_flux_residual
    import numpy as np

    previous = np.array([[3.0, 4.0]])
    unchanged = compute_picard_flux_residual(previous, previous)
    doubled = compute_picard_flux_residual(previous, 2.0 * previous)
    assert unchanged["residual"] == 0.0
    assert np.isclose(doubled["residual"], 1.0)

import numpy as np

from scirel.diagnostics.picard_flux_residual import compute_picard_flux_residual, compute_picard_flux_residual as scientific_operator


def test_returns_zero_for_unchanged_flux():
    assert scientific_operator([[1.0]], [[1.0]])["residual"] == 0.0


def test_returns_l2_relative_change():
    result = scientific_operator([[3.0, 4.0]], [[6.0, 8.0]])
    assert np.isclose(result["residual"], 1.0)


def test_reviewed_relation_example():
    from scirel.diagnostics.picard_flux_residual import compute_picard_flux_residual
    import numpy as np

    previous = np.array([[3.0, 4.0]])
    unchanged = compute_picard_flux_residual(previous, previous)
    doubled = compute_picard_flux_residual(previous, 2.0 * previous)
    assert unchanged["residual"] == 0.0
    assert np.isclose(doubled["residual"], 1.0)

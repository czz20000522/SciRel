"""Direct contract tests for ``scirel.collisions.collrad_h0_ionization_rate``.

The saved KN1DPy leaf (source anchor ``KN1DPy/collrad_sigmav_ion_h0.py:16-217``,
reachable from ``KN1DPy/kinetic_h.py:841-855``) maps paired electron density and
temperature onto the COLLRAD (DEGAS-2) H0 Maxwellian-averaged electron-impact
ionization rate through bilinear interpolation of ``log(rate)`` on a 15x60
``log(n)``/``log(T)`` table.  The tests assert the table anchors, the
log-log bilinear midpoint as the geometric mean of the four corners, the
endpoint clamping, and the fail-closed contracts.  One documented repair
relative to the saved implementation is exercised: the result is returned with
the paired inputs' shape (the saved document declares the broadcast input shape
but its implementation always flattened to one dimension) and the paired inputs
must have equal shapes (the saved implementation compared flattened sizes only,
so two different-shaped arrays of the same size were silently accepted).
"""
from __future__ import annotations

import numpy as np
import pytest

from scirel.collisions import evaluate_collrad_h0_ionization_rate


def test_grid_anchor_and_shape():
    values = evaluate_collrad_h0_ionization_rate(
        [1.0e16, 1.0e17],
        [10.0**-1.2, 10.0**-1.2],
    )
    np.testing.assert_allclose(values, [1.0e-105, 5.02155e-100], rtol=2e-14, atol=0.0)
    assert values.shape == (2,)


def test_log_bilinear_midpoint_is_the_geometric_mean_of_the_corners():
    result = evaluate_collrad_h0_ionization_rate([10.0**16.25], [10.0**-1.15])[0]
    corners = np.array([1.0e-105, 1.93923e-89, 1.0e-105, 3.08801e-89])
    expected = np.exp(np.log(corners).mean())
    np.testing.assert_allclose(result, expected, rtol=1e-12, atol=0.0)


def test_endpoint_clamping_is_preserved():
    low = evaluate_collrad_h0_ionization_rate([1.0e6], [1.0e-3])[0]
    low_edge = evaluate_collrad_h0_ionization_rate([1.0e6], [10.0**-1.2])[0]
    high = evaluate_collrad_h0_ionization_rate([1.0e23], [1.0e6])[0]
    high_edge = evaluate_collrad_h0_ionization_rate([1.0e23], [10.0**4.7])[0]
    assert low == low_edge
    assert high == high_edge


def test_two_dimensional_input_returns_the_input_shape():
    """Documented repair: the saved implementation flattened to one dimension."""
    density = np.array([[1.0e16, 1.0e17], [1.0e18, 1.0e19]])
    temperature = np.array([[1.0, 2.0], [4.0, 8.0]])
    result = evaluate_collrad_h0_ionization_rate(density, temperature)
    assert result.shape == (2, 2)
    flat = evaluate_collrad_h0_ionization_rate(density.ravel(), temperature.ravel())
    np.testing.assert_array_equal(result, flat.reshape(2, 2))


def test_scalar_input_returns_zero_dimensional_result():
    result = evaluate_collrad_h0_ionization_rate(1.0e18, 2.0)
    assert np.ndim(result) == 0
    assert np.isfinite(result) and result > 0.0


def test_all_outputs_are_finite_and_positive():
    density = np.logspace(16, 23, 8)
    temperature = np.logspace(-1, 4, 8)
    result = evaluate_collrad_h0_ionization_rate(density, temperature)
    assert np.all(np.isfinite(result)) and np.all(result > 0.0)


def test_mismatched_shapes_are_rejected():
    with pytest.raises(ValueError, match="shape"):
        evaluate_collrad_h0_ionization_rate(np.array([[1.0e18, 2.0e18]]), np.array([1.0, 2.0, 3.0]))


def test_same_size_different_shape_was_silently_accepted_by_the_saved_implementation():
    """Documented repair witness: equal flattened sizes no longer pass."""
    with pytest.raises(ValueError, match="shape"):
        evaluate_collrad_h0_ionization_rate(
            np.array([[1.0e18, 2.0e18], [3.0e18, 4.0e18]]), np.array([1.0, 2.0, 3.0, 4.0])
        )


def test_nonfinite_and_nonpositive_fail_closed():
    with pytest.raises(ValueError, match="finite"):
        evaluate_collrad_h0_ionization_rate([1.0e18, np.nan], [2.0, 4.0])
    with pytest.raises(ValueError, match="positive"):
        evaluate_collrad_h0_ionization_rate([0.0, 1.0e18], [2.0, 4.0])
    with pytest.raises(ValueError, match="positive"):
        evaluate_collrad_h0_ionization_rate([1.0e18, 2.0e18], [2.0, -1.0])


def test_decreasing_interpolation_coordinates_fail_closed():
    with pytest.raises(ValueError, match="nondecreasing"):
        evaluate_collrad_h0_ionization_rate([1.0e19, 1.0e18], [2.0, 20.0])
    with pytest.raises(ValueError, match="nondecreasing"):
        evaluate_collrad_h0_ionization_rate([1.0e18, 2.0e18], [20.0, 2.0])

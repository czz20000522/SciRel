"""Direct contract tests for the development planar wavevector relation."""

import numpy as np
import pytest

from scirel.geometry import project_planar_wavevector


def test_polar_projection_keeps_the_declared_angle_at_zero_magnitude():
    result = project_planar_wavevector(k_grid=[0.0, 5.0], theta_rad=np.pi / 2)

    np.testing.assert_allclose(result["kx"], [0.0, 5.0], rtol=0, atol=1e-15)
    np.testing.assert_allclose(result["kz"], [0.0, 0.0], rtol=0, atol=1e-15)
    np.testing.assert_array_equal(result["k"], [0.0, 5.0])
    assert result["theta_rad"] == np.pi / 2
    assert result["projection_mode"] == "polar"


def test_cartesian_components_are_paired_and_hypot_avoids_spurious_overflow():
    result = project_planar_wavevector(kx_grid=[3.0, 1e200], kz_grid=[4.0, 0.0])

    np.testing.assert_array_equal(result["k"], [5.0, 1e200])
    np.testing.assert_array_equal(result["kx"], [3.0, 1e200])
    np.testing.assert_array_equal(result["kz"], [4.0, 0.0])
    assert result["theta_rad"] is None
    assert result["projection_mode"] == "cartesian"


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"k_grid": [-1.0]},
        {"k_grid": [float("nan")]},
        {"k_grid": ["1.0"]},
        {"k_grid": [True]},
        {"k_grid": [1, True]},
        {"kx_grid": [1.0, True], "kz_grid": [1.0, 1.0]},
        {"kx_grid": [np.bool_(True), 1.0], "kz_grid": [1.0, 1.0]},
        {"k_grid": [1.0], "theta_rad": np.array([0.3])},
        {"k_grid": [1.0], "theta_rad": True},
        {"k_grid": [1.0], "kx_grid": [1.0]},
        {"kx_grid": [1.0], "kz_grid": [1.0, 2.0]},
        {"kx_grid": ["3.0"], "kz_grid": [4.0]},
        {"kx_grid": [1.7e308], "kz_grid": [1.7e308]},
    ],
)
def test_invalid_modes_and_nonfinite_results_fail(kwargs):
    with pytest.raises(ValueError):
        project_planar_wavevector(**kwargs)


def test_mixed_boolean_containers_are_rejected_before_numeric_coercion():
    # NumPy coerces [1, True] to an integer array and [np.bool_(True), 1.0] to
    # float, so dtype-kind inspection alone silently accepts boolean pseudo-numbers.
    for kwargs in (
        {"k_grid": [1, True]},
        {"kx_grid": [1.0, True], "kz_grid": [1.0, 1.0]},
        {"kx_grid": [np.bool_(True), 1.0], "kz_grid": [1.0, 1.0]},
    ):
        with pytest.raises(ValueError):
            project_planar_wavevector(**kwargs)

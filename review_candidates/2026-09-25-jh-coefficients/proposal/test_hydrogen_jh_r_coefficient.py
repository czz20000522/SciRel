"""Direct contract tests for ``scirel.collisions.hydrogen_jh_r_coefficient``.

The saved KN1DPy package (source anchor ``KN1DPy/jh_related/jhr_coef.py:12-66``
as recorded by the saved bundle's extraction report) evaluates the
Johnson-Hinnov hydrogen r coefficient as a cubic B-spline over
``(log Te, log n)``.  On the source-complete ``no_null=1`` branch the saved
implementation reproduces the raw source's ``result = Density;
result[:] = 1e32`` initialization, so the spline's density coordinate is the
clipped ``1e32`` null sentinel and the output does not depend on the
caller's density values beyond shape and validation.  That observable quirk
is preserved bit for bit and asserted here as the density-independence
witness; whether it is the intended published contract or a source defect to
repair is an open expert-review question.

The tests re-verify the relation against an independent FITPACK evaluation
of the same spline (``RectBivariateSpline.ev`` at the clipped coordinates),
the ion/level channel selection, the endpoint clipping, and the full input
and failure contracts.  No repair is claimed for this leaf.
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy.interpolate import RectBivariateSpline

from scirel.collisions import evaluate_h_jh_r_coefficient

_NULL_DENSITY_M3 = 1.0e32


def make_payload():
    """Build a synthetic spline payload exactly as the saved package's tests do."""
    temperature_axis = np.linspace(-1.0, 1.0, 5)
    density_axis = np.linspace(30.0, 32.0, 5)
    surface = np.add.outer(temperature_axis, density_axis)
    spline = RectBivariateSpline(temperature_axis, density_axis, surface, kx=4, ky=4)
    temperature_knots, density_knots = spline.get_knots()
    coefficients = np.zeros((spline.get_coeffs().size, 2, 5), dtype=float)
    coefficients[:, 0, 1] = spline.get_coeffs()
    coefficients[:, 1, 4] = spline.get_coeffs() + 0.25
    return density_knots, temperature_knots, spline, coefficients


def independent_oracle(density, temperature, ion, level, density_knots, temperature_knots, spline):
    """Independent evaluation: exp of the spline at the clipped coordinates.

    The r branch overwrites the density coordinate with the source's 1e32
    sentinel before clipping, so the oracle's density argument is unused
    beyond the shape it shares with the temperature.
    """
    log_density = np.clip(np.log(np.full(density.shape, _NULL_DENSITY_M3)), density_knots[0], density_knots[-1])
    log_temperature = np.clip(np.log(temperature), temperature_knots[0], temperature_knots[-1])
    expected = np.empty(density.shape, dtype=float)
    for index in range(density.size):
        expected[index] = np.exp(float(np.atleast_1d(spline.ev(log_temperature[index], log_density[index]))[0]))
    return expected


def test_r_coefficient_matches_independent_fitpack_oracle():
    density_knots, temperature_knots, spline, coefficients = make_payload()
    density = np.array([1.0e19, 5.0e19, 1.0e20])
    temperature = np.array([1.0, 5.0, 20.0])
    actual = evaluate_h_jh_r_coefficient(
        density, temperature, 0, 3, density_knots, temperature_knots, 4, coefficients
    )
    expected = independent_oracle(density, temperature, 0, 3, density_knots, temperature_knots, spline)
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=0.0)
    assert actual.shape == density.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_out_of_range_coordinates_are_clipped_to_the_knot_ends():
    """The saved implementation clips both coordinates to the knot range;
    inputs outside it must land exactly on the endpoint evaluations."""
    density_knots, temperature_knots, spline, coefficients = make_payload()
    hot = evaluate_h_jh_r_coefficient(
        np.array([1.0e20]), np.array([np.exp(50.0)]), 1, 6, density_knots, temperature_knots, 4, coefficients
    )
    at_top = evaluate_h_jh_r_coefficient(
        np.array([1.0e20]), np.array([np.exp(temperature_knots[-1])]), 1, 6, density_knots, temperature_knots, 4, coefficients
    )
    np.testing.assert_array_equal(hot, at_top)


def test_ion_and_level_select_distinct_coefficient_channels():
    density_knots, temperature_knots, _, coefficients = make_payload()
    density = np.array([np.exp(31.0)])
    temperature = np.array([np.exp(0.5)])
    base = evaluate_h_jh_r_coefficient(density, temperature, 0, 3, density_knots, temperature_knots, 4, coefficients)
    alternate = evaluate_h_jh_r_coefficient(density, temperature, 1, 6, density_knots, temperature_knots, 4, coefficients)
    assert not np.allclose(base, alternate)


def test_output_is_independent_of_the_caller_density_on_the_admitted_branch():
    """The no_null=1 density overwrite: different densities, same output."""
    density_knots, temperature_knots, _, coefficients = make_payload()
    temperature = np.array([np.exp(0.5), np.exp(0.5)])
    low = evaluate_h_jh_r_coefficient(
        np.array([np.exp(30.0), 1.0e10]), temperature, 0, 3, density_knots, temperature_knots, 4, coefficients
    )
    high = evaluate_h_jh_r_coefficient(
        np.array([np.exp(32.0), 1.0e20]), temperature, 0, 3, density_knots, temperature_knots, 4, coefficients
    )
    np.testing.assert_array_equal(low, high)


def test_invalid_ion_level_or_branch_fail_closed():
    density_knots, temperature_knots, _, coefficients = make_payload()
    density = np.array([np.exp(31.0)])
    temperature = np.array([np.exp(0.5)])
    with pytest.raises(ValueError, match="ion must be 0 or 1"):
        evaluate_h_jh_r_coefficient(density, temperature, 2, 3, density_knots, temperature_knots, 4, coefficients)
    with pytest.raises(ValueError, match=r"integer in \[2, 6\]"):
        evaluate_h_jh_r_coefficient(density, temperature, 0, 1, density_knots, temperature_knots, 4, coefficients)
    with pytest.raises(ValueError, match=r"integer in \[2, 6\]"):
        evaluate_h_jh_r_coefficient(density, temperature, 0, 7, density_knots, temperature_knots, 4, coefficients)
    with pytest.raises(ValueError, match="no_null=1"):
        evaluate_h_jh_r_coefficient(density, temperature, 0, 3, density_knots, temperature_knots, 4, coefficients, no_null=0)


def test_shape_or_domain_violations_fail_closed():
    density_knots, temperature_knots, _, coefficients = make_payload()
    good = np.array([np.exp(31.0)])
    good_temperature = np.array([np.exp(0.5)])
    with pytest.raises(ValueError, match="same-shaped 1-D"):
        evaluate_h_jh_r_coefficient(np.array([[np.exp(31.0)]]), np.array([[np.exp(0.5)]]), 0, 3, density_knots, temperature_knots, 4, coefficients)
    with pytest.raises(ValueError, match="same-shaped 1-D"):
        evaluate_h_jh_r_coefficient(np.array([np.exp(31.0), 1.0e20]), good_temperature, 0, 3, density_knots, temperature_knots, 4, coefficients)
    with pytest.raises(ValueError, match="finite and positive"):
        evaluate_h_jh_r_coefficient(np.array([0.0]), good_temperature, 0, 3, density_knots, temperature_knots, 4, coefficients)
    with pytest.raises(ValueError, match="finite and positive"):
        evaluate_h_jh_r_coefficient(good, np.array([np.nan]), 0, 3, density_knots, temperature_knots, 4, coefficients)


def test_inconsistent_knots_or_coefficients_fail_closed():
    density_knots, temperature_knots, _, coefficients = make_payload()
    density = np.array([np.exp(31.0)])
    temperature = np.array([np.exp(0.5)])
    with pytest.raises(ValueError, match="non-decreasing"):
        evaluate_h_jh_r_coefficient(density, temperature, 0, 3, density_knots[::-1].copy(), temperature_knots, 4, coefficients)
    with pytest.raises(ValueError, match="non-decreasing"):
        evaluate_h_jh_r_coefficient(density, temperature, 0, 3, density_knots, temperature_knots[::-1].copy(), 4, coefficients)
    with pytest.raises(ValueError, match=r"shape \(n_coefficients, 2, 5\)"):
        evaluate_h_jh_r_coefficient(density, temperature, 0, 3, density_knots, temperature_knots, 4, coefficients[:, :, :3])
    with pytest.raises(ValueError, match="inconsistent with knots and spline_order"):
        evaluate_h_jh_r_coefficient(density, temperature, 0, 3, density_knots[:-1].copy(), temperature_knots, 4, coefficients)
    with pytest.raises(ValueError, match="positive integer"):
        evaluate_h_jh_r_coefficient(density, temperature, 0, 3, density_knots, temperature_knots, 0, coefficients)

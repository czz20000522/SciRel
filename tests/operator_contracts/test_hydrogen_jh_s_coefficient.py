"""Direct contract tests for ``scirel.collisions.hydrogen_jh_s_coefficient``.

The saved KN1DPy package (source anchor ``KN1DPy/jh_related/jhs_coef.py:24-60``
as recorded by the saved bundle's extraction report) evaluates the
Johnson-Hinnov hydrogen s coefficient as a tensor-product B-spline over
``(log Te, log n)`` on the caller's clipped coordinates, reading the
``LogS_BSCoef`` vector from an exact-field validated payload.  Unlike the
sibling r and alpha branches, this branch consumes the caller's density;
the tests assert that dependence explicitly.

Degree convention: the payload's ``order`` field is consumed by scipy's
FITPACK ``bisplev`` as the spline *degree* (scipy documents ``kx``/``ky``
as degrees), so the admitted order-4 payload executes a degree-four
(quartic) surface, not the cubic surface the saved source's label
describes.  The degree witness below pins the executed surface against an
independent numpy Cox-de Boor evaluation at degree 4.

The tests re-verify the relation against an independent FITPACK evaluation
of the same spline (``RectBivariateSpline.ev`` at the clipped coordinates),
the endpoint clipping, the payload validation contract, and the full input
and failure contracts.  No repair is claimed for this leaf.
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy.interpolate import RectBivariateSpline

from scirel.collisions import evaluate_h_jh_s_coefficient


def make_jh_payload():
    """Build a synthetic payload with the exact saved field set and the
    saved knot geometry (order field 4, a degree-four surface under
    FITPACK's degree convention, describing exactly 77 coefficients via an
    11-point temperature axis and a 7-point density axis)."""
    temperature_axis = np.linspace(-1.0, 1.0, 11)
    density_axis = np.linspace(30.0, 32.0, 7)
    surface = np.add.outer(temperature_axis, density_axis)
    spline = RectBivariateSpline(temperature_axis, density_axis, surface, kx=4, ky=4)
    temperature_knots, density_knots = spline.get_knots()
    return {
        "DKnot": density_knots,
        "TKnot": temperature_knots,
        "order": 4,
        "LogR_BSCoef": np.zeros((spline.get_coeffs().size, 2, 5)),
        "LogS_BSCoef": spline.get_coeffs().copy(),
        "LogAlpha_BSCoef": spline.get_coeffs().copy() + 0.25,
        "A_Lyman": np.ones(15),
        "A_Balmer": np.ones(15),
    }, spline


def _cox_de_boor_surface_value(x, y, temperature_knots, density_knots, coefficients, degree):
    """Independent tensor-product B-spline evaluation (numpy only, no scipy):
    the Cox-de Boor recurrence at the given degree, with FITPACK's coefficient
    layout (x-major) and the right-endpoint convention."""
    coefficients = np.asarray(coefficients, dtype=float)
    n_x = len(temperature_knots) - degree - 1
    n_y = len(density_knots) - degree - 1
    grid = coefficients.reshape(n_x, n_y)

    def basis(i, k, v, knots):
        if v == knots[-1]:
            return 1.0 if i == len(knots) - k - 2 else 0.0
        if k == 0:
            return 1.0 if knots[i] <= v < knots[i + 1] else 0.0
        left = right = 0.0
        if knots[i + k] > knots[i]:
            left = (v - knots[i]) / (knots[i + k] - knots[i]) * basis(i, k - 1, v, knots)
        if knots[i + k + 1] > knots[i + 1]:
            right = (knots[i + k + 1] - v) / (knots[i + k + 1] - knots[i + 1]) * basis(i + 1, k - 1, v, knots)
        return left + right

    weight_x = np.array([basis(i, degree, x, temperature_knots) for i in range(n_x)])
    weight_y = np.array([basis(j, degree, y, density_knots) for j in range(n_y)])
    return float(weight_x @ grid @ weight_y)


def independent_oracle(density, temperature, density_knots, temperature_knots, spline):
    log_density = np.clip(np.log(density), density_knots[0], density_knots[-1])
    log_temperature = np.clip(np.log(temperature), temperature_knots[0], temperature_knots[-1])
    expected = np.empty(density.shape, dtype=float)
    for index in range(density.size):
        expected[index] = np.exp(float(np.atleast_1d(spline.ev(log_temperature[index], log_density[index]))[0]))
    return expected


def test_s_coefficient_matches_independent_fitpack_oracle():
    payload, spline = make_jh_payload()
    density = np.array([1.0e19, 5.0e19, 1.0e20])
    temperature = np.array([1.0, 5.0, 20.0])
    actual = evaluate_h_jh_s_coefficient(density, temperature, payload)
    expected = independent_oracle(density, temperature, payload["DKnot"], payload["TKnot"], spline)
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=0.0)
    assert actual.shape == density.shape
    assert np.all(np.isfinite(actual)) and np.all(actual > 0.0)


def test_the_s_branch_consumes_the_caller_density():
    """Witness for the branch split: unlike r/alpha, the density enters."""
    payload, spline = make_jh_payload()
    temperature = np.array([np.exp(0.5), np.exp(0.5)])
    low = evaluate_h_jh_s_coefficient(np.array([np.exp(30.0), 1.0e10]), temperature, payload)
    high = evaluate_h_jh_s_coefficient(np.array([np.exp(32.0), 1.0e20]), temperature, payload)
    assert not np.allclose(low, high)
    # and matches the oracle at the caller's density
    expected_low = independent_oracle(np.array([np.exp(30.0), 1.0e10]), temperature, payload["DKnot"], payload["TKnot"], spline)
    np.testing.assert_allclose(low, expected_low, rtol=1e-12, atol=0.0)


def test_out_of_range_coordinates_are_clipped_to_the_knot_ends():
    payload, _ = make_jh_payload()
    sparse = evaluate_h_jh_s_coefficient(
        np.array([np.exp(10.0)]), np.array([np.exp(50.0)]), payload
    )
    at_knots = evaluate_h_jh_s_coefficient(
        np.array([np.exp(payload["DKnot"][0])]), np.array([np.exp(payload["TKnot"][-1])]), payload
    )
    np.testing.assert_array_equal(sparse, at_knots)


def test_the_executed_surface_is_degree_four_under_fitpacks_degree_convention():
    """scipy's bisplev/RectBivariateSpline document kx/ky as the spline
    DEGREE, so the admitted order-4 payload executes a degree-four (quartic)
    surface, not the cubic surface the saved source's label describes.
    Witness: an independent numpy Cox-de Boor evaluation at degree 4
    (no scipy) reproduces the module output on interior coordinates.  The
    saved coefficient-count contract (knots - 4 - 1) products closes only
    under the degree reading (the order reading would need 96, not 77,
    coefficients for the packaged geometry)."""
    payload, _ = make_jh_payload()
    density = np.array([np.exp(30.6), np.exp(31.3)])
    temperature = np.array([np.exp(-0.4), np.exp(0.6)])
    actual = evaluate_h_jh_s_coefficient(density, temperature, payload)
    expected = np.array([
        np.exp(_cox_de_boor_surface_value(
            np.clip(np.log(temperature[i]), payload["TKnot"][0], payload["TKnot"][-1]),
            np.clip(np.log(density[i]), payload["DKnot"][0], payload["DKnot"][-1]),
            payload["TKnot"],
            payload["DKnot"],
            payload["LogS_BSCoef"],
            4,
        ))
        for i in range(density.size)
    ])
    np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=0.0)


def test_invalid_payloads_fail_closed():
    payload, _ = make_jh_payload()
    density = np.array([np.exp(31.0)])
    temperature = np.array([np.exp(0.5)])
    with pytest.raises(ValueError, match="mapping"):
        evaluate_h_jh_s_coefficient(density, temperature, ["not", "a", "mapping"])
    missing = {key: value for key, value in payload.items() if key != "A_Balmer"}
    with pytest.raises(ValueError, match="fields are incomplete"):
        evaluate_h_jh_s_coefficient(density, temperature, missing)
    bad_order = dict(payload)
    bad_order["order"] = 3
    with pytest.raises(ValueError, match="knots/order are invalid"):
        evaluate_h_jh_s_coefficient(density, temperature, bad_order)
    bad_knots = dict(payload)
    bad_knots["DKnot"] = payload["DKnot"][:-1]
    with pytest.raises(ValueError, match="77 coefficients"):
        evaluate_h_jh_s_coefficient(density, temperature, bad_knots)
    nonfinite = dict(payload)
    nonfinite["LogS_BSCoef"] = payload["LogS_BSCoef"].copy()
    nonfinite["LogS_BSCoef"][0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        evaluate_h_jh_s_coefficient(density, temperature, nonfinite)


def test_branch_shape_and_domain_violations_fail_closed():
    payload, _ = make_jh_payload()
    density = np.array([np.exp(31.0)])
    temperature = np.array([np.exp(0.5)])
    with pytest.raises(ValueError, match="finite positive same-shaped 1-D"):
        evaluate_h_jh_s_coefficient(np.array([[np.exp(31.0)]]), np.array([[np.exp(0.5)]]), payload)
    with pytest.raises(ValueError, match="finite positive same-shaped 1-D"):
        evaluate_h_jh_s_coefficient(np.array([0.0]), temperature, payload)
    with pytest.raises(ValueError, match="finite positive same-shaped 1-D"):
        evaluate_h_jh_s_coefficient(density, np.array([np.inf]), payload)
    with pytest.raises(ValueError, match="no_null=1"):
        evaluate_h_jh_s_coefficient(density, temperature, payload, no_null=0)

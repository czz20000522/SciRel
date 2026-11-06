"""Molecular Omega conditioning, status and finite-output regressions."""

import numpy as np
import pytest
from scirel._result import Result
from scirel.collisions import assemble_molecular_hydrogen_omega_frequencies as op


def run(boost, *, target=False, H2_P_EL=False, H2_H_EL=False, H2_H2_EL=True):
    f = np.array([[[1.0], [3.0]]])
    z = np.zeros_like(f)
    return op(
        f,
        np.array([4.0]),
        z,
        z,
        np.zeros((2, 2)),
        np.ones(1),
        np.ones(2),
        np.array([1.0]),
        np.array([-1.0, 1.0]) + boost,
        1.0,
        np.array([boost]),
        np.array([boost]),
        moment_state="target" if target else "central",
        target_distribution=f if target else None,
        H2_P_EL=H2_P_EL,
        H2_H_EL=H2_H_EL,
        H2_H2_EL=H2_H2_EL,
    )


def test_molecular_default_is_central_and_boost_invariant():
    a = run(0)
    b = run(0.25)
    assert type(a) is Result
    assert a.Wperp_paraH2 is a["Wperp_paraH2"]
    assert a.status_H2_H2 is a["status_H2_H2"]
    assert a.status_H2_H2.dtype == np.dtype("<U48")
    assert all(isinstance(value, np.ndarray) for value in a.values())
    np.testing.assert_array_equal(a["Wperp_paraH2"], [-0.5])
    np.testing.assert_array_equal(a["Wperp_paraH2"], b["Wperp_paraH2"])


def test_molecular_result_preserves_undefined_nan_and_status():
    result = run(0, target=True)

    assert type(result) is Result
    assert np.isnan(result.Omega_H2_H2).all()
    assert not result.defined_H2_H2.any()
    assert (result.status_H2_H2 == "near_equilibrium_ill_conditioned_denominator").all()
    assert result.Omega_H2_H2 is result["Omega_H2_H2"]
    assert result.defined_H2_H2 is result["defined_H2_H2"]
    assert result.status_H2_H2 is result["status_H2_H2"]
    assert result.Omega_H2_H2.shape == (1,)
    assert result.Omega_H2_H2.dtype == np.dtype("float64")
    assert result.defined_H2_H2.dtype == np.dtype("bool")
    assert all(isinstance(value, np.ndarray) for value in result.values())


def _mixed_case(flow1):
    from scirel.collisions._elastic_moments import reduce_elastic_moments

    f = np.array([[[1.0], [3.0]]])
    z = np.zeros_like(f)
    return reduce_elastic_moments(
        f,
        np.array([4.0]),
        np.array([[[1.0], [1.0]]]),
        z,
        np.zeros((2, 2)),
        np.ones(1),
        np.ones(2),
        np.array([1.0]),
        np.array([-1.0, 1.0]),
        1.0,
        np.array([flow1]),
        np.array([1.0]),
        moment_state="central",
        target_distribution=None,
        enabled=(True, True, True),
        names=("H2_P", "H2_H", "H2_H2"),
        flow_name="VxH2",
        stress_name="Wperp_paraH2",
        mass_fractions=(1 / 3, 1 / 3),
    )


def _conditioning_witness():
    result = run(0, target=True)
    assert result.Wperp_paraH2[0] == 0.0
    assert np.isnan(result.Omega_H2_H2).all()
    assert not result.defined_H2_H2.any()
    assert result.status_H2_H2[0] == "near_equilibrium_ill_conditioned_denominator"
    assert not result.defined_EL[0]
    assert np.isnan(result.nu_EL[0])
    return result


def test_exact_zero_denominator_is_conditioning_undefined_not_physical():
    result = _conditioning_witness()
    assert np.isfinite(result.moment_H2_H2).all()
    assert np.isfinite(result.moment_rate_H2_H2).all()


def test_tiny_denominators_above_and_at_boundary_are_separated():
    boundary = 8.0 * np.finfo(float).eps * 2.0
    below = _mixed_case(np.float64(0.5) - np.float64(boundary) / 2.0)
    at = _mixed_case(np.float64(0.5) - np.float64(boundary))
    above = _mixed_case(np.float64(0.5) - np.float64(boundary) * 2.0)
    assert below["status_H2_P"][0] == "near_equilibrium_ill_conditioned_denominator"
    assert not below["defined_H2_P"][0]
    assert np.isnan(below["Omega_H2_P"][0])
    assert at["status_H2_P"][0] == "near_equilibrium_ill_conditioned_denominator"
    assert not at["defined_H2_P"][0]
    assert np.isnan(at["Omega_H2_P"][0])
    assert above["status_H2_P"][0] == "finite_nonnegative"
    assert above["defined_H2_P"][0]
    assert np.isfinite(above["Omega_H2_P"][0]) and above["Omega_H2_P"][0] > 0.0


def test_nonfinite_enabled_result_fails_closed_like_finite_output_policy():
    from scirel.collisions._elastic_moments import reduce_elastic_moments

    f = np.array([[[1.0], [3.0]]])
    large = np.finfo(float).max
    sig0 = -np.nextafter(large / 4.0, 0.0)
    with np.errstate(over="ignore"):
        with pytest.raises(FloatingPointError, match="not representable"):
            reduce_elastic_moments(
                f,
                np.array([4.0]),
                np.array([[[-large], [0.0]]]),
                np.array([[[-large], [0.0]]]),
                np.array([[sig0, 0.0], [0.0, 0.0]]),
                np.ones(1),
                np.ones(2),
                np.array([1.0]),
                np.array([-1.0, 1.0]),
                1.0,
                np.array([1.0]),
                np.array([1.0]),
                moment_state="central",
                target_distribution=None,
                enabled=(True, True, True),
                names=("H2_P", "H2_H", "H2_H2"),
                flow_name="VxH2",
                stress_name="Wperp_paraH2",
                mass_fractions=(1 / 3, 1 / 3),
            )


def test_disabled_and_usable_nonnegative_are_not_confused():
    result = run(0, H2_P_EL=False, H2_H_EL=False, H2_H2_EL=False)
    assert result.status_H2_H2[0] == "disabled"
    assert result.defined_H2_H2[0]
    assert result.Omega_H2_H2[0] == 0.0

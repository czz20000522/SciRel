"""Regression for the former molecular zero-accumulator raw-moment error."""

import numpy as np
from scirel._result import Result
from scirel.collisions import assemble_molecular_hydrogen_omega_frequencies as op


def run(boost, *, target=False):
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
        H2_P_EL=False,
        H2_H_EL=False,
    )


def test_molecular_default_is_central_and_boost_invariant():
    a = run(0)
    b = run(0.25)
    assert type(a) is Result
    assert a.Wperp_paraH2 is a["Wperp_paraH2"]
    assert a.status_H2_H2 is a["status_H2_H2"]
    assert a.status_H2_H2.dtype == np.dtype("<U32")
    assert all(isinstance(value, np.ndarray) for value in a.values())
    np.testing.assert_array_equal(a["Wperp_paraH2"], [-0.5])
    np.testing.assert_array_equal(a["Wperp_paraH2"], b["Wperp_paraH2"])


def test_molecular_result_preserves_undefined_nan_and_status():
    result = run(0, target=True)

    assert type(result) is Result
    assert np.isnan(result.Omega_H2_H2).all()
    assert not result.defined_H2_H2.any()
    assert (result.status_H2_H2 == "undefined_zero_denominator").all()
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
        conditioning_policy="molecular_near_equilibrium",
    )


def test_molecular_exact_zero_keeps_distinct_undefined_status():
    result = run(0, target=True)
    assert result.status_H2_H2[0] == "undefined_zero_denominator"
    assert not result.defined_H2_H2[0]
    assert np.isnan(result.Omega_H2_H2[0])
    assert result.status_H2_H2.dtype == np.dtype("<U32")


def test_molecular_nonzero_boundary_is_separately_ill_conditioned():
    boundary = 8.0 * np.finfo(float).eps * 2.0
    below = _mixed_case(np.float64(0.5) - np.float64(boundary) / 2.0)
    at = _mixed_case(np.float64(0.5) - np.float64(boundary))
    above = _mixed_case(np.float64(0.5) - np.float64(boundary) * 2.0)
    for result in (below, at):
        assert result["status_H2_P"][0] == "ill_conditioned_denominator"
        assert not result["defined_H2_P"][0]
        assert np.isnan(result["Omega_H2_P"][0])
        assert np.isnan(result["nu_H2_P"][0])
        assert np.isnan(result["Omega_EL"][0])
        assert np.isnan(result["nu_EL"][0])
        assert not result["defined_EL"][0]
        assert result["status_H2_P"].dtype == np.dtype("<U32")
    assert above["status_H2_P"][0] == "finite_nonnegative"
    assert above["defined_H2_P"][0]
    assert np.isfinite(above["Omega_H2_P"][0])
    assert above["Omega_H2_P"][0] > 0.0


def test_molecular_policy_is_explicit_not_atomic_default():
    from scirel.collisions._elastic_moments import reduce_elastic_moments

    f = np.array([[[1.0], [3.0]]])
    z = np.zeros_like(f)
    boundary = 8.0 * np.finfo(float).eps * 2.0
    args = (
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
        np.array([0.5 - boundary]),
        np.array([1.0]),
    )
    kwargs = dict(
        moment_state="central",
        target_distribution=None,
        enabled=(True, True, True),
        names=("H2_P", "H2_H", "H2_H2"),
        flow_name="VxH2",
        stress_name="Wperp_paraH2",
        mass_fractions=(1 / 3, 1 / 3),
    )
    default = reduce_elastic_moments(*args, **kwargs)
    molecular = reduce_elastic_moments(
        *args, **kwargs, conditioning_policy="molecular_near_equilibrium"
    )
    assert default["status_H2_P"][0] == "finite_nonnegative"
    assert molecular["status_H2_P"][0] == "ill_conditioned_denominator"

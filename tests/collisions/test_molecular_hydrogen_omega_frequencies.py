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

"""Independent exact-limit and error-channel regressions for issue #302.

At b=0, the harmonic definitions give R=H=x/(x*x-1) and
x*dR/dx=x*dH/dx=-x*(x*x+1)/(x*x-1)**2.  The oracle evaluates these
rational expressions at 800 decimal digits after exact binary64 conversion;
it does not call a product helper or borrow the J8 approximation.
"""

import math

import mpmath as mp
import numpy as np
import pytest

from scirel.kinetic import (
    evaluate_dielectric_response,
    evaluate_ronnmark_r,
    evaluate_kinetic_dispersion_relation,
    kinetic_dispersion_relation as relation,
    solve_kinetic_wavevector_roots,
)


ENDPOINTS = [
    0.0,
    -0.0,
    2.0,
    -2.0,
    2.0 + 0.0j,
    -2.0 + 0.0j,
    0.5,
    -0.5,
    0.5 + 0.25j,
    -0.5 - 0.25j,
    2j,
    -2j,
    math.nextafter(1.0, 0.0),
    math.nextafter(1.0, 2.0),
    math.nextafter(-1.0, 0.0),
    math.nextafter(-1.0, -2.0),
    1e308,
    -1e308,
    1e308 + 1e308j,
    -1e308 + 1e308j,
    float.fromhex("0x1.fffffffffffffp+1023") * (1 + 1j),
    1e-308,
    -1e-308,
    1e-308 + 1e-308j,
    math.ulp(0.0),
    -math.ulp(0.0),
    complex(math.ulp(0.0), math.ulp(0.0)),
    1.0 + 1e-154j,
    -1.0 - 1e-154j,
    1.0 + 1e-100j,
    -1.0 + 1e-100j,
    1e-100 + 1e100j,
    1e100 + 1e-100j,
]


def _exact_mp(value):
    numerator, denominator = float(value).as_integer_ratio()
    return mp.mpf(numerator) / denominator


def _zero_limit(x):
    with mp.workdps(800):
        z = complex(x)
        z = mp.mpc(_exact_mp(z.real), _exact_mp(z.imag))
        denominator = z * z - 1
        response = z / denominator
        scaled_dx = -z * (z * z + 1) / denominator**2
        return [[complex(response), complex(response)], [complex(scaled_dx), complex(scaled_dx)]]


def _assert_components(actual, expected):
    for value, reference in zip(np.ravel(actual), np.ravel(expected), strict=True):
        for component, target in ((value.real, reference.real), (value.imag, reference.imag)):
            # Frozen before candidate calls: 16 eps relative per real/imaginary
            # component, plus 8 minimum subnormals. Never use |complex| to hide
            # a weak real or imaginary component behind the other component.
            budget = 16 * np.finfo(float).eps * abs(target) + 8 * math.ulp(0.0)
            assert math.isfinite(component), "a representable exact zero-b limit must remain finite"
            assert abs(component - target) <= budget, (
                "zero-b RC must match the independent rational limit per component"
            )


@pytest.mark.parametrize("x", ENDPOINTS)
@pytest.mark.parametrize("b", [0.0, -0.0, 0.0j])
def test_zero_b_exact_limit_keeps_removable_and_extreme_components(x, b):
    result = evaluate_ronnmark_r(x, b)
    _assert_components(result["RC"], _zero_limit(x))
    assert result["R"] == result["RC"][0, 0]
    assert result["H"] == result["RC"][0, 1]
    assert result["branch"] == "RTAY(AL<4)"


@pytest.mark.parametrize("x", [1.0, -1.0, 1.0 + 0j, -1.0 + 0j, 1.0 + 1e-155j])
def test_genuine_pole_or_unrepresentable_companion_is_numerical_failure(x):
    with pytest.raises(FloatingPointError, match="(?i)(ronnmark|response|RC)"):
        evaluate_ronnmark_r(x, 0.0)


@pytest.mark.parametrize("x,b", [(2.0, 0.2), (1e308, 1.0), (1.0, 1.0)])
def test_nonzero_b_nonfinite_response_cannot_be_an_ordinary_result(x, b):
    with pytest.raises(FloatingPointError):
        evaluate_ronnmark_r(x, b)


COLD = dict(B0=1.0, qs=[1.0], ms=[1.0], ns0=[1.0], Ts0=[1.0], kz=0.0, kx=0.0)


def test_full_j8_nonresonant_cold_control_must_be_computed():
    result = evaluate_dielectric_response(method="ronnmark", **COLD, omega=2.0)
    # This is model B with its actual rounded table, not an ideal-M0 cold
    # Maxwellian oracle. Independent B summation is in the existing fixture.
    for name in ("K", "D", "determinant", "vts", "wcs", "wps2", "a", "b", "nx", "nz"):
        assert np.isfinite(result[name]).all(), (
            f"supported omega=2 cold control must return finite {name}"
        )
    assert result["K"][0, 0].real != 1.0, (
        "cold susceptibility cannot be silently replaced by vacuum"
    )


def test_full_j8_exact_cold_pole_raises_numerical_failure():
    with pytest.raises(FloatingPointError):
        evaluate_dielectric_response(method="ronnmark", **COLD, omega=1.0)


@pytest.mark.parametrize(
    "change",
    [
        {"B0": 1e-300},
        {"ms": [1e-320]},
        {"Ts0": [1e308], "ms": [1e-300]},
        {"ns0": [1e308]},
        {"omega": 1e-320},
        {"kx": 1e308},
        {"f": 1e308},
        {"qs": [1e-200]},
    ],
)
def test_full_j8_unrepresentable_derived_scales_are_numerical_failures(change, monkeypatch):
    if "f" in change:
        # Preserve the original finite-Hz overflow on the real relation boundary.
        monkeypatch.setattr(relation, "omega_to_frequency", lambda **kwargs: {"f": change["f"]})
        with pytest.raises(FloatingPointError):
            evaluate_kinetic_dispersion_relation(
                B0=1.0,
                qs=[1.0],
                ms=[1.0],
                ns_unit=[1.0],
                Ts_unit=[1.0],
                n00=1.0,
                T00=1.0,
                omega_frac=2.0,
                kz=1.0,
                kx_frac=1.0,
            )
    else:
        args = COLD | {"omega": 2.0} | change
        with pytest.raises(FloatingPointError):
            evaluate_dielectric_response(method="ronnmark", **args)


def test_root_propagates_initial_numerical_failure_instead_of_zero_division():
    args = {key: value for key, value in COLD.items() if key != "kx"}
    with pytest.raises(FloatingPointError):
        solve_kinetic_wavevector_roots(**args, omegas=[1.0], kx_start=0.0)


@pytest.mark.parametrize("change", [{"B0": 0.0}, {"qs": [0.0]}, {"omega": 0.0}, {"omega": np.inf}])
def test_invalid_tensor_inputs_remain_caller_errors(change):
    with pytest.raises(ValueError):
        evaluate_dielectric_response(method="ronnmark", **(COLD | {"omega": 2.0} | change))

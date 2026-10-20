"""Bounded r43 numerical variants alongside the existing analytic entries."""

import numpy as np
import pytest
from scipy.special import ive

from scirel.kinetic import (
    evaluate_fluid_kinetic_dispersion_sum,
    evaluate_kinetic_dispersion_sum,
    evaluate_plasma_dispersion_weideman,
)
from scirel.kinetic.kinetic_dispersion_sum_fluid import _gamma_and_prime


@pytest.mark.parametrize("n,b", [(-15, 0.0), (-3, 1e-12), (0, 2.5), (11, 100.0)])
def test_fluidbw_gamma_pair_preserves_scalar_ive_contract(n, b):
    expected_gamma = float(ive(n, b))
    expected_derivative = float((ive(n - 1, b) + ive(n + 1, b)) / 2.0 - ive(n, b))

    assert _gamma_and_prime(n, b) == (expected_gamma, expected_derivative)


def test_weideman_source_values_and_branch():
    result = evaluate_plasma_dispersion_weideman([0j, 0.5 + 0.5j, 8.0])
    np.testing.assert_allclose(
        result["Z"],
        [
            1.7724538509055159j,
            -0.40852975330578489 + 0.94499566007504165j,
            -0.12600039741510677 + 1.2298869221005176e-17j,
        ],
        rtol=1e-12,
        atol=1e-13,
    )
    assert list(result["method"]) == ["erfc", "rational", "rational"]


@pytest.mark.parametrize("z", [np.nan, np.inf + 1j])
def test_weideman_rejects_nonfinite_argument(z):
    with pytest.raises(ValueError, match="finite"):
        evaluate_plasma_dispersion_weideman(z)


def test_sum_n_source_clamp_preserves_existing_failure_contract():
    args = dict(
        B0=1.0,
        qs=[-1.60217662e-19],
        ms=[9.1094e-31],
        ns0=[6.075e19],
        Ts0=[1000 * 1.6022e-19 / 1.38064852e-23],
        f=175881684853.009 / (2 * np.pi),
        kx=13261.94247879565,
    )
    with pytest.raises(ValueError):
        evaluate_kinetic_dispersion_sum(**args, kz=0.0)
    source = evaluate_fluid_kinetic_dispersion_sum(**args, kz=0.0)
    explicit = evaluate_fluid_kinetic_dispersion_sum(**args, kz=1e-10)
    assert source["determinant"] == explicit["determinant"]
    assert source["determinant"] == pytest.approx(
        -4.2165739181024277e52 - 3.1799139420426738e42j, rel=1e-8
    )


def test_source_sum_rejects_fractional_harmonic_limit():
    with pytest.raises(ValueError, match="lmx"):
        evaluate_fluid_kinetic_dispersion_sum(
            B0=1.0, qs=[-1.60217662e-19], ms=[9.1094e-31],
            ns0=[6.075e19], Ts0=[1e7], f=1e10, kz=1.0, kx=1.0, lmx=5.5,
        )


@pytest.mark.parametrize("change", [{"B0": np.nan}, {"f": np.inf},
                                     {"kx": np.nan}, {"qs": [0.0]}])
def test_source_sum_rejects_invalid_wavepoint(change):
    args = dict(B0=1.0, qs=[-1.60217662e-19], ms=[9.1094e-31],
                ns0=[6.075e19], Ts0=[1e7], f=1e10, kz=1.0, kx=1.0)
    args.update(change)
    with pytest.raises(ValueError):
        evaluate_fluid_kinetic_dispersion_sum(**args)

"""Bounded r43 numerical variants alongside the existing analytic entries."""

from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
from scipy.special import ive

from scirel.kinetic import evaluate_dielectric_response, evaluate_plasma_dispersion
from scirel.kinetic._dielectric_weideman import _gamma_and_prime


@pytest.mark.parametrize("n,b", [(-15, 0.0), (-3, 1e-12), (0, 2.5), (11, 100.0)])
def test_fluidbw_gamma_pair_preserves_scalar_ive_contract(n, b):
    expected_gamma = float(ive(n, b))
    expected_derivative = float((ive(n - 1, b) + ive(n + 1, b)) / 2.0 - ive(n, b))

    assert _gamma_and_prime(n, b) == (expected_gamma, expected_derivative)


def test_weideman_source_values_and_branch():
    result = evaluate_plasma_dispersion([0j, 0.5 + 0.5j, 8.0], method="weideman")
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
    assert set(result) == {"w", "Z"}  # Input-derived labels explicitly retired.


@pytest.mark.parametrize("z", [np.nan, np.inf + 1j])
def test_weideman_rejects_nonfinite_argument(z):
    with pytest.raises(ValueError, match="finite"):
        evaluate_plasma_dispersion(z, method="weideman")


def test_explicit_former_surrogate_preserves_source_value_and_default_order():
    args = dict(
        B0=1.0,
        qs=[-1.60217662e-19],
        ms=[9.1094e-31],
        ns0=[6.075e19],
        Ts0=[1000 * 1.6022e-19 / 1.38064852e-23],
        omega=2.0 * np.pi * float(175881684853.009 / (2 * np.pi)),
        kx=13261.94247879565,
    )
    with pytest.raises(ValueError):
        evaluate_dielectric_response(method="harmonic", **args, kz=0.0)
    # Retire the implicit source policy, retain its numerical assertion at its
    # actual wavepoint. This is source parity, not a physical zero-kz limit.
    with pytest.raises(ValueError, match="kz.*nonzero"):
        evaluate_dielectric_response(method="harmonic_weideman", **args, kz=0.0)
    source = evaluate_dielectric_response(method="harmonic_weideman", **args, kz=1e-10, harmonics=5)
    explicit = evaluate_dielectric_response(method="harmonic_weideman", **args, kz=1e-10)
    for key in ("K", "D"):
        np.testing.assert_array_equal(source[key], explicit[key])
    assert source["diagnostics"]["harmonics"] == explicit["diagnostics"]["harmonics"] == 5
    assert source["determinant"] == explicit["determinant"]
    assert source["determinant"] == pytest.approx(
        -4.2165739181024277e52 - 3.1799139420426738e42j, rel=1e-8
    )


def test_source_sum_rejects_fractional_harmonic_limit():
    with pytest.raises(TypeError, match="harmonics"):
        evaluate_dielectric_response(
            method="harmonic_weideman",
            B0=1.0,
            qs=[-1.60217662e-19],
            ms=[9.1094e-31],
            ns0=[6.075e19],
            Ts0=[1e7],
            omega=2.0 * np.pi * float(1e10),
            kz=1.0,
            kx=1.0,
            harmonics=5.5,
        )


@pytest.mark.parametrize(
    "change",
    [{"B0": np.nan}, {"omega": 2.0 * np.pi * float(np.inf)}, {"kx": np.nan}, {"qs": [0.0]}],
)
def test_source_sum_rejects_invalid_wavepoint(change):
    args = dict(
        B0=1.0,
        qs=[-1.60217662e-19],
        ms=[9.1094e-31],
        ns0=[6.075e19],
        Ts0=[1e7],
        omega=2.0 * np.pi * float(1e10),
        kz=1.0,
        kx=1.0,
    )
    args.update(change)
    with pytest.raises(ValueError):
        evaluate_dielectric_response(method="harmonic_weideman", **args)


@pytest.mark.parametrize(
    "change",
    [
        {"qs": []},
        {"qs": [[-1.0]]},
        {"ms": [1.0, 2.0]},
        {"ms": [0.0]},
        {"ns0": [0.0]},
        {"Ts0": [0.0]},
        {"qs": [np.nan]},
        {"ms": [np.inf]},
        {"ns0": [np.nan]},
        {"Ts0": [np.inf]},
        {"B0": 0.0},
        {"omega": 2.0 * np.pi * float(0.0)},
        {"kz": np.inf},
        {"harmonics": -1},
        {"harmonics": True},
    ],
)
def test_fluid_shape_and_invalid_domain_still_fail_closed(change):
    args = dict(
        B0=1.0,
        qs=[-1.0],
        ms=[1.0],
        ns0=[1.0],
        Ts0=[1.0],
        omega=2.0 * np.pi * float(1.0),
        kz=1.0,
        kx=1.0,
    )
    expected = TypeError if isinstance(change.get("harmonics"), bool) else ValueError
    with pytest.raises(expected):
        evaluate_dielectric_response(method="harmonic_weideman", **(args | change))


@pytest.mark.parametrize(
    "name", ["evaluate_dielectric_response", "evaluate_kinetic_dispersion_relation"]
)
def test_zero_kz_rejection_in_fresh_process_keeps_backends_lazy(name):
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            """
import sys
sys.path.insert(0, sys.argv[1])
import scirel.kinetic as kinetic
name = sys.argv[2]
call = getattr(kinetic, name)
arguments = dict(B0=1., qs=[-1.], ms=[1.], kz=0.)
if name == 'evaluate_dielectric_response':
    arguments.update(ns0=[1.], Ts0=[1.], omega=2.0 * 3.141592653589793 * float(1.), kx=1., method='harmonic_weideman')
else:
    arguments.update(ns_unit=[1.], Ts_unit=[1.], n00=1., T00=1., omega_frac=1., kx_frac=1.)
try:
    call(**arguments)
except ValueError as error:
    assert 'nonzero' in str(error) and 'Ronnmark' in str(error)
else:
    raise AssertionError('zero kz was evaluated')
assert not any(key == 'scipy' or key.startswith('scipy.') for key in sys.modules)
assert 'scirel.kinetic._dielectric_ronnmark' not in sys.modules
assert 'scirel.kinetic.species_equilibrium_scales' not in sys.modules
""",
            str(Path(__file__).resolve().parents[2] / "src"),
            name,
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

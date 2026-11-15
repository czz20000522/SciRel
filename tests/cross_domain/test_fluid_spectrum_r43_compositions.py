"""Composition contracts for the three fluid-dispersion paths."""

import builtins
import importlib
from fractions import Fraction

import numpy as np
import pytest

from scirel._result import Result
from scirel.kinetic import (
    evaluate_kinetic_dispersion_relation,
    scan_fluid_wavevectors,
    scan_kinetic_wavevectors,
    solve_kinetic_wavevector_roots,
)


CASE = dict(
    ms=[9.1094e-31],
    qs=[-1.60217662e-19],
    ns_unit=[1.0],
    Ts_unit=[1.0],
    B0=1.0,
    n00=6.075e19,
    T00=1000.0,
)
WN = 175881684853.009
KN = 13261.94247879565


@pytest.mark.parametrize("kz", [0.0, -0.0])
def test_two_path_zero_kz_is_rejected_before_dependencies(kz, monkeypatch):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        assert not any(
            part in name
            for part in (
                "species_equilibrium_scales",
                "dielectric_response",
                "_dielectric_weideman",
                "_dielectric_ronnmark",
            )
        ), f"zero kz loaded a graph dependency: {name}"
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    with pytest.raises(ValueError, match="kz.*nonzero.*Ronnmark") as error:
        evaluate_kinetic_dispersion_relation(**CASE, omega_frac=1.0, kz=kz, kx_frac=1.0)
    assert "scirel.kinetic.kinetic-dispersion-relation" in str(error.value)


def test_kinetic_relation_returns_both_source_paths():
    result = evaluate_kinetic_dispersion_relation(
        **CASE, omega_frac=1.0, kz=1326.1942478795652, kx_frac=1.0
    )
    assert isinstance(result, Result)
    assert result["omega"] == pytest.approx(WN)
    assert result["kx"] == pytest.approx(KN)
    assert result["determinant_sum_n"] == pytest.approx(
        1184249.3244493124 + 4322451.2861608062j, rel=1e-12
    )
    assert result["determinant_ronnmark"] == pytest.approx(
        1184258.061758124 + 4322544.0839688079j, rel=1e-12
    )


@pytest.mark.parametrize(
    "omega,expected_sum,expected_ronnmark",
    [
        (
            431047494.35601676,
            84156144001125.656 + 29822940983252.656j,
            84154917089965.141 + 29822444270111.691j,
        ),
        (
            718412490.59336126,
            13174325513551.057 + 8828415003972.5879j,
            13173663914380.654 + 8828066693749.1387j,
        ),
    ],
)
def test_two_species_relation_matches_both_frozen_source_paths(
    omega, expected_sum, expected_ronnmark
):
    case = dict(
        ms=[9.1094e-31, 2 * 1.6726219e-27],
        qs=[-1.60217662e-19, 1.60217662e-19],
        ns_unit=[1.0, 1.0],
        Ts_unit=[1.0, 1.0],
        B0=6.0,
        n00=2e20,
        T00=4000.0,
    )
    result = evaluate_kinetic_dispersion_relation(
        **case,
        omega_frac=omega / 287364996.2373445,
        kz=65.65372832698084,
        kx_frac=1.0,
    )
    assert result["determinant_sum_n"] == pytest.approx(expected_sum, rel=1e-12)
    assert result["determinant_ronnmark"] == pytest.approx(expected_ronnmark, rel=1e-12)
    assert len(result["branches"]) == 16


def test_fluid_scan_source_branch_and_internal_axis():
    result = scan_fluid_wavevectors(
        **CASE,
        omega_scale=0.5,
        omega_step=0.05,
        omega_stop=0.5,
        kz_scale=0.1,
        max_harmonic=6,
        j_order=8,
    )
    assert result["count"] == 1
    assert result["omegas"][0] == 0.5 * WN
    assert result["matrix_sizes"][0] == (490, 77092)
    np.testing.assert_allclose(
        result["kx_head"][0],
        [
            905.1790141262235 + 1098.4405252549827j,
            905.3284546850839 - 1099.1401577361607j,
            17460.574000679004 - 3076.8115609398164j,
            17460.57399242396 + 3076.811575501693j,
            17460.769014362882 - 3078.808722147245j,
        ],
        rtol=0,
        atol=1e-4,
    )


def test_kinetic_scan_keeps_absolute_zero_kz_and_fixed_seed():
    result = scan_kinetic_wavevectors(
        **CASE,
        kz=0.0,
        omega_scale=0.11,
        omega_step=0.05,
        omega_stop=0.11,
    )
    assert result["count"] == 1
    assert result["kx_start"] == 0.6 * KN
    assert result["kz"] == 0.0
    assert result["roots"][0] == pytest.approx(
        -0.1724798740276431 - 0.12372615593987332j, rel=1e-9, abs=1e-9
    )
    assert isinstance(result, Result)
    assert result.status[0] == 0
    assert result.success[0] == False
    assert result.message[0]
    assert "converged" not in result and "exit_flags" not in result


def _trace_response(monkeypatch, consumer):
    """Observe the real consumer's API boundary without replacing its calculations."""
    module = importlib.import_module("scirel.kinetic.dielectric_response")
    original = module.evaluate_dielectric_response
    calls = []

    def observe(**kwargs):
        result = original(**kwargs)
        calls.append((kwargs, result))
        return result

    monkeypatch.setattr(module, "evaluate_dielectric_response", observe)
    if hasattr(consumer, "evaluate_dielectric_response"):
        monkeypatch.setattr(consumer, "evaluate_dielectric_response", observe)
    return calls


@pytest.mark.parametrize("kz", [1326.1942478795652, -1326.1942478795652])
def test_relation_uses_explicit_methods_and_original_hz_roundtrip(monkeypatch, kz):
    module = importlib.import_module("scirel.kinetic.kinetic_dispersion_relation")
    calls = _trace_response(monkeypatch, module)
    # Find a representable unit-conversion probe with a visible one-bit roundtrip.
    # This chooses inputs only, never a scientific expected tensor.
    fraction = next(
        value
        for value in (0.12345678901234566, 0.11, 0.37, 0.83, 1.43)
        if (2.0 * np.pi * float(value * WN / (2.0 * np.pi))) != value * WN
    )
    result = evaluate_kinetic_dispersion_relation(**CASE, omega_frac=fraction, kz=kz, kx_frac=1.0)
    assert isinstance(result, Result)
    assert len(calls) == 2
    assert [options["method"] for options, _ in calls] == ["harmonic_weideman", "ronnmark"]
    expected_omega = 2.0 * np.pi * float(result.omega / (2.0 * np.pi))
    assert float(expected_omega).hex() != float(result.omega).hex()
    for options, _ in calls:
        assert float(options["omega"]).hex() == float(expected_omega).hex()
        assert options["kz"] == kz
        assert "f" not in options
    assert calls[0][0]["harmonics"] == 5
    assert calls[1][0].get("harmonics") is None
    for suffix, (_, response) in zip(("sum_n", "ronnmark"), calls, strict=True):
        np.testing.assert_array_equal(result[f"K_{suffix}"], response.K)
        np.testing.assert_array_equal(result[f"D_{suffix}"], response.D)
        assert result[f"determinant_{suffix}"] == response.determinant
    assert result.branches == calls[1][1].diagnostics.branches


def test_relation_finite_hz_conversion_overflow_remains_numerical_failure(monkeypatch):
    module = importlib.import_module("scirel.kinetic.kinetic_dispersion_relation")
    response = importlib.import_module("scirel.kinetic.dielectric_response")
    calls = []

    def forbidden_leaf(**kwargs):
        calls.append(kwargs)
        pytest.fail("Hz conversion overflow reached the dielectric leaf")

    monkeypatch.setattr(response, "evaluate_dielectric_response", forbidden_leaf)
    if hasattr(module, "evaluate_dielectric_response"):
        monkeypatch.setattr(module, "evaluate_dielectric_response", forbidden_leaf)
    # Inject at the existing unit adapter: a finite Hz value overflows in 2*pi*f.
    monkeypatch.setattr(module, "omega_to_frequency", lambda **kwargs: {"f": 1e308})
    with np.errstate(all="ignore"), pytest.raises(FloatingPointError):
        evaluate_kinetic_dispersion_relation(
            **CASE, omega_frac=1.0, kz=1326.1942478795652, kx_frac=1.0
        )
    assert not calls


@pytest.mark.parametrize("kz", [0.0, 1000.0, -1000.0])
def test_roots_route_omega_directly_and_keep_real_solver_status(monkeypatch, kz):
    module = importlib.import_module("scirel.kinetic.kinetic_wavevector_roots")
    calls = _trace_response(monkeypatch, module)
    # Keep the original FMA flag-0 wavepoint and add a distinct unit-boundary probe.
    original_omega = 0.11 * WN
    probe_omega = next(
        value * WN
        for value in (0.12345678901234566, 0.37, 0.83, 1.43)
        if (2.0 * np.pi * float(value * WN / (2.0 * np.pi))) != value * WN
    )
    result = solve_kinetic_wavevector_roots(
        B0=1.0,
        qs=CASE["qs"],
        ms=CASE["ms"],
        ns0=[6.075e19],
        Ts0=[1e3 * 1.6022e-19 / 1.38064852e-23],
        omegas=[original_omega, probe_omega],
        kz=kz,
        kx_start=0.6 * KN,
    )
    assert isinstance(result, Result)
    assert calls
    for options, _ in calls:
        assert options["method"] == "ronnmark"
        assert float(options["omega"]).hex() in {
            float(original_omega).hex(),
            float(probe_omega).hex(),
        }
        assert options["kz"] == kz
        assert "f" not in options and options.get("harmonics") is None
    assert result.solver == "reference_fsolve_dogleg_on_fDR"
    assert result.tol_fun == result.tol_x == 1e-16
    assert result.max_iterations == 400 and result.max_function_evals == 100
    assert {float(options["omega"]).hex() for options, _ in calls} == {
        float(original_omega).hex(),
        float(probe_omega).hex(),
    }
    assert result.status.shape == result.success.shape == (2,)
    assert len(result.message) == 2
    assert all(isinstance(message, str) and message for message in result.message)
    np.testing.assert_array_equal(result.success, result.status > 0)
    assert "converged" not in result and "exit_flags" not in result
    if kz == 0.0:
        assert result.roots[0] == pytest.approx(
            -0.1724798740276431 - 0.12372615593987332j, rel=1e-9, abs=1e-9
        )
        assert result.status[0] == 0 and result.success[0] == False


def test_scan_carries_root_fields_and_original_ladder_and_fixed_seed(monkeypatch):
    roots_module = importlib.import_module("scirel.kinetic.kinetic_wavevector_roots")
    original = roots_module.solve_kinetic_wavevector_roots
    calls = []
    seeds = []
    solver = roots_module._reference_fsolve

    def observe_solver(function, seed, *controls):
        seeds.append(seed)
        return solver(function, seed, *controls)

    def observe_roots(**kwargs):
        result = original(**kwargs)
        calls.append((kwargs, result))
        return result

    monkeypatch.setattr(roots_module, "_reference_fsolve", observe_solver)
    monkeypatch.setattr(roots_module, "solve_kinetic_wavevector_roots", observe_roots)
    result = scan_kinetic_wavevectors(
        **CASE,
        kz=-1000.0,
        omega_scale=0.11,
        omega_step=0.05,
        omega_stop=0.21,
    )
    assert isinstance(result, Result)
    assert len(calls) == 1
    controls, solved = calls[0]
    expected = np.array([float(Fraction(0.11) + k * Fraction(0.05)) for k in range(3)]) * WN
    np.testing.assert_array_equal(result.omegas, expected)
    np.testing.assert_array_equal(controls["omegas"], expected)
    assert result.count == 3
    assert seeds == [complex(0.6 * KN, 0)] * 3
    assert controls["kx_start"] == result.kx_start == 0.6 * KN
    assert controls["tol_fun"] == controls["tol_x"] == 1e-16
    assert controls["max_iterations"] == 400 and controls["max_function_evals"] == 100
    for key in (
        "roots",
        "residuals",
        "determinant_scale",
        "status",
        "success",
        "message",
        "iterations",
        "function_evals",
        "solver",
    ):
        np.testing.assert_array_equal(result[key], solved[key])
    assert len(result.message) == 3
    assert "converged" not in result and "exit_flags" not in result

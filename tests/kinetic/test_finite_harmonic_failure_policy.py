"""Issue #303: numerical failures stay distinct from invalid caller inputs."""

import numpy as np
import pytest

from scirel.kinetic import (
    dielectric_tensor_diagnostic as diagnostic,
    evaluate_fluid_kinetic_dispersion_sum,
    evaluate_kinetic_dielectric_tensor,
    evaluate_kinetic_dispersion_sum,
    kinetic_dispersion_sum_n as conventional,
)


CALLS = (
    pytest.param(evaluate_kinetic_dispersion_sum, id="S"),
    pytest.param(evaluate_fluid_kinetic_dispersion_sum, id="F"),
    pytest.param(evaluate_kinetic_dielectric_tensor, id="G"),
)


def _case(**changes):
    arguments = dict(
        B0=1.0,
        qs=[-1.60217662e-19],
        ms=[9.1094e-31],
        ns0=[6.075e19],
        Ts0=[11604941.036704937],
        f=1e10,
        kz=1e3,
        kx=13261.94247879565,
        lmx=5,
    )
    arguments.update(changes)
    return arguments


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"ns0": [1e-320]}, id="underflowed-plasma-scale"),
        pytest.param({"Ts0": [1e-320]}, id="underflowed-thermal-scale"),
        pytest.param({"f": 1e308}, id="overflowed-frequency"),
        pytest.param({"kx": 1e-200}, id="underflowed-bessel-scale"),
        pytest.param({"kx": 1e200}, id="overflowed-bessel-scale"),
        pytest.param({"kx": 1e9}, id="unrepresentable-bessel-backend"),
        pytest.param({"kz": 1e-320}, id="nonfinite-resonance"),
        pytest.param({"kz": 1e308}, id="overflowed-resonance-scale"),
        pytest.param({"kz": 1e-155}, id="unrepresentable-response"),
        pytest.param({"f": 1e-200}, id="unrepresentable-frequency-square"),
        pytest.param({"ns0": [1e300]}, id="nonfinite-tensor-or-determinant"),
    ],
)
def test_valid_inputs_with_unavailable_numerics_raise_fpe(call, changes):
    with np.errstate(all="ignore"), pytest.raises(FloatingPointError):
        call(**_case(**changes))


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"ms": [[1.0]]}, id="species-rank"),
        pytest.param({"ms": [1.0, 2.0], "qs": [-1.0, 1.0, -1.0]}, id="species-shape"),
        pytest.param({"qs": []}, id="empty-species"),
        pytest.param({"ms": [-1.0]}, id="mass-domain"),
        pytest.param({"kz": 0.0}, id="zero-kz"),
        pytest.param({"kx": np.inf}, id="nonfinite-input"),
        pytest.param({"lmx": -1}, id="negative-cutoff"),
        pytest.param({"lmx": 1.5}, id="cutoff-type"),
    ],
)
def test_invalid_input_keeps_value_error(call, changes):
    with pytest.raises(ValueError):
        call(**_case(**changes))


@pytest.mark.parametrize("call", CALLS)
def test_normal_tensor_remains_finite(call):
    result = call(**_case())
    assert np.isfinite(result["K"]).all()
    assert np.isfinite(result["D"]).all()
    assert np.isfinite(result.get("determinant", result.get("det_D")))


@pytest.mark.parametrize("call", CALLS)
def test_positive_tail_budget_failure_reaches_every_consumer(call, monkeypatch):
    original = conventional._gamma_positive_tail
    monkeypatch.setattr(
        conventional, "_gamma_positive_tail", lambda b, start: original(b, start, limit=0)
    )
    with pytest.raises(FloatingPointError, match="term budget"):
        call(**_case())


@pytest.mark.parametrize("call", CALLS)
def test_positive_tail_underflow_reaches_every_consumer(call):
    with pytest.raises(FloatingPointError, match="reliable precision"):
        call(**_case(lmx=500))


@pytest.mark.parametrize("call", CALLS)
def test_unrelated_helper_value_error_is_not_reclassified(call, monkeypatch):
    failure = ValueError("unrelated helper defect")

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(conventional, "_gamma_positive_tail", fail)
    with pytest.raises(ValueError) as caught:
        call(**_case())
    assert caught.value is failure


@pytest.mark.parametrize("site", ["harmonic", "edge", "head", "tail"])
def test_specific_bessel_numerical_failure_is_reclassified(site, monkeypatch):
    original = conventional.evaluate_bessel_gamma

    def backend(n, b):
        selected = (
            (site == "harmonic" and np.ndim(n) == 0 and n == -5)
            or (site == "edge" and np.ndim(n) == 0 and n == 6)
            or (site == "head" and np.ndim(n) == 1 and n[0] == 0)
            or (site == "tail" and np.ndim(n) == 1 and n[0] == 6)
        )
        if selected:
            raise ValueError("Bessel-Gamma value is not representable")
        return original(n, b)

    monkeypatch.setattr(conventional, "evaluate_bessel_gamma", backend)
    with pytest.raises(FloatingPointError, match="Bessel-Gamma value is not representable"):
        evaluate_kinetic_dispersion_sum(**_case())


@pytest.mark.parametrize("message", ["unrelated backend defect", "n must contain integer orders"])
def test_bessel_value_errors_outside_the_numerical_site_propagate(message, monkeypatch):
    failure = ValueError(message)

    def backend(*args, **kwargs):
        raise failure

    monkeypatch.setattr(conventional, "evaluate_bessel_gamma", backend)
    with pytest.raises(ValueError) as caught:
        evaluate_kinetic_dispersion_sum(**_case())
    assert caught.value is failure


@pytest.mark.parametrize("first", [0, 6])
def test_nonfinite_positive_tail_terms_raise_fpe(first, monkeypatch):
    original = conventional.evaluate_bessel_gamma

    def backend(n, b):
        if np.ndim(n) == 1 and n[0] == first:
            return {"Gamma_n": np.full(len(n), np.nan)}
        return original(n, b)

    monkeypatch.setattr(conventional, "evaluate_bessel_gamma", backend)
    with pytest.raises(FloatingPointError, match="finite and nonnegative"):
        conventional._gamma_positive_tail(1.0, 6)


@pytest.mark.parametrize("b,start,limit", [(1 + 0.5j, 501, 20000), (1 + 0.5j, 16, 0)])
def test_complex_tail_underflow_and_budget_raise_fpe(b, start, limit):
    with pytest.raises(FloatingPointError):
        diagnostic._gamma_complex_tail(b, start, limit=limit)


def test_complex_tail_severe_cancellation_raises_fpe(monkeypatch):
    # Finite terms with a tiny nonzero sum reach the existing conditioning test.
    values = np.array([1.0, -1.0, 1e-20] + [0.0] * 61, dtype=complex)
    monkeypatch.setattr(diagnostic, "_gamman", lambda orders, b: values)
    with pytest.raises(FloatingPointError, match="ill-conditioned"):
        diagnostic._gamma_complex_tail(1 + 0.5j, 16)


@pytest.mark.parametrize(
    "leading",
    [
        pytest.param([1e308, -1e308, 1e-20], id="absolute-sum"),
        pytest.param([1e308], id="doubled-tail"),
    ],
)
def test_complex_tail_unrepresentable_accumulation_raises_fpe(leading, monkeypatch):
    values = np.array(leading + [0.0] * (64 - len(leading)), dtype=complex)
    monkeypatch.setattr(diagnostic, "_gamman", lambda orders, b: values)
    with np.errstate(all="ignore"), pytest.raises(FloatingPointError):
        diagnostic._gamma_complex_tail(1 + 0.5j, 16)


@pytest.mark.parametrize("sign", [-1, 1])
def test_unrepresentable_asymptotic_response_raises_fpe(sign):
    with np.errstate(all="ignore"), pytest.raises(FloatingPointError):
        conventional._a_function(np.asarray(sign * 1e200))


@pytest.mark.parametrize("values", [[complex(np.inf, 0), complex(-np.inf, 0)], [1e308, 1e308]])
def test_unavailable_complex_component_sum_raises_fpe(values):
    with pytest.raises(FloatingPointError):
        diagnostic._complex_sum(values)


@pytest.mark.parametrize("kx", [0.0, 13261.94247879565])
@pytest.mark.parametrize(
    "changes",
    [{"ns0": [1e-320]}, {"ns0": [1e300], "f": 1e-100}, {"kz": 1e-320}],
)
def test_diagnostic_partial_does_not_permit_unrelated_numerical_failure(kx, changes):
    with np.errstate(all="ignore"), pytest.raises(FloatingPointError):
        evaluate_kinetic_dielectric_tensor(**_case(kx=kx, **changes))


@pytest.mark.parametrize("kx", [0.0, 13261.94247879565])
def test_diagnostic_unavailable_parallel_component_rejects_even_at_partial_endpoint(
    kx, monkeypatch
):
    monkeypatch.setattr(diagnostic, "_zfun", lambda z: complex(np.nan, 0.0))
    with pytest.raises(FloatingPointError):
        evaluate_kinetic_dielectric_tensor(**_case(kx=kx))


@pytest.mark.parametrize("density", [6.075e19, 1e300])
def test_diagnostic_partial_keeps_raw_mask_and_large_finite_components(density):
    result = evaluate_kinetic_dielectric_tensor(**_case(kx=0.0, ns0=[density]))
    expected = np.array([[False, True, False], [True, False, True], [False, True, True]])
    for key in ("K", "D"):
        np.testing.assert_array_equal(np.isfinite(result[key]), expected)
    assert not np.isfinite(result["det_D"])


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize("first", [0, 6])
def test_bessel_tail_numerical_error_reaches_all_consumers(call, first, monkeypatch):
    original = conventional.evaluate_bessel_gamma

    def backend(n, b):
        if np.ndim(n) == 1 and n[0] == first:
            raise ValueError("Bessel-Gamma value is not representable")
        return original(n, b)

    monkeypatch.setattr(conventional, "evaluate_bessel_gamma", backend)
    with pytest.raises(FloatingPointError) as caught:
        call(**_case())
    assert type(caught.value.__cause__) is ValueError


@pytest.mark.parametrize("b", [0.0, -1.0, np.nan, np.inf])
def test_private_tail_invalid_arguments_still_raise_value_error(b):
    with pytest.raises(ValueError, match="argument must be finite and positive"):
        conventional._gamma_positive_tail(b, 6)


@pytest.mark.parametrize("b", [0.0, complex(np.nan, 0), complex(0, np.inf)])
def test_private_complex_tail_invalid_arguments_still_raise_value_error(b):
    with pytest.raises(ValueError, match="argument must be finite and nonzero"):
        diagnostic._gamma_complex_tail(b, 6)


@pytest.mark.parametrize("call", CALLS)
def test_unsupported_scalar_error_kind_is_preserved(call):
    expected = TypeError if call is evaluate_fluid_kinetic_dispersion_sum else ValueError
    with pytest.raises(expected):
        call(**_case(f=object()))

"""The shared dielectric interface preserves each method's scientific obligations."""

import importlib
import inspect

import numpy as np
import pytest

from scirel._result import Result


METHODS = ("harmonic", "harmonic_weideman", "ronnmark")
CORE_KEYS = {
    "K",
    "D",
    "determinant",
    "omega",
    "nx",
    "nz",
    "vts",
    "wcs",
    "wps2",
    "a",
    "b",
    "diagnostics",
}
RAW_KEYS = {
    "K_raw",
    "D_raw",
    "determinant_raw",
    "omega",
    "nx",
    "nz",
    "vts",
    "wcs",
    "wps2",
    "a",
    "b",
    "rhocs",
    "z0s",
    "diagnostics",
}
CONVENTION = "K_ij = delta_ij - sigma_ij/(i*omega*epsilon0)"


@pytest.fixture
def response():
    return importlib.import_module(
        "scirel.kinetic.dielectric_response"
    ).evaluate_dielectric_response


@pytest.fixture
def diagnostic():
    return importlib.import_module(
        "scirel.kinetic.dielectric_diagnostics"
    ).evaluate_dielectric_diagnostics


def _case(**changes):
    # Preserve the old Hz wavepoint's float conversion; it is a unit adapter.
    values = dict(
        B0=1.0,
        qs=[-1.60217662e-19],
        ms=[9.1094e-31],
        ns0=[6.075e19],
        Ts0=[11604941.036704937],
        omega=2.0 * np.pi * float(1e10),
        kz=1000.0,
        kx=13261.94247879565,
    )
    return values | changes


def _error_context(error, parameter, received, contract):
    message = str(error.value)
    assert parameter in message
    expected_value = repr(int(received)) if isinstance(received, np.integer) else repr(received)
    assert expected_value in message
    assert contract in message
    return message


def test_canonical_signatures_are_keyword_only(response, diagnostic):
    common = ["B0", "qs", "ms", "ns0", "Ts0", "omega", "kz", "kx"]
    for function, controls in ((response, ["method", "harmonics"]), (diagnostic, ["harmonics"])):
        signature = inspect.signature(function)
        assert list(signature.parameters) == common + controls
        assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in signature.parameters.values())
    assert inspect.signature(response).parameters["method"].default == "harmonic"
    assert inspect.signature(response).parameters["harmonics"].default is None
    assert inspect.signature(diagnostic).parameters["harmonics"].default == 15


@pytest.mark.parametrize("method", METHODS)
def test_methods_share_complete_result_and_exact_method_diagnostics(response, method):
    result = response(**_case(), method=method)
    assert isinstance(result, Result)
    assert set(result) == CORE_KEYS
    assert result.K is result["K"] and result.diagnostics is result["diagnostics"]
    assert result.K.shape == result.D.shape == (3, 3)
    for key in CORE_KEYS - {"diagnostics"}:
        assert np.isfinite(result[key]).all(), key
    details = result.diagnostics
    assert isinstance(details, Result)
    expected = {"method", "tensor_convention"}
    expected |= {"bzj", "czj", "j_order", "branches"} if method == "ronnmark" else {"harmonics"}
    assert set(details) == expected
    assert details.method == method
    assert details.tensor_convention == CONVENTION
    if method == "ronnmark":
        assert details.j_order == 8
        assert details.bzj.shape == details.czj.shape == (8,)
        assert len(details.branches) == 8
        assert all(isinstance(branch, str) and branch for branch in details.branches)
    else:
        assert details.harmonics == 5


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize(
    "change,sign", [({}, -1), ({"kx": -13261.94247879565}, 1), ({"B0": -1.0}, 1)]
)
def test_signed_a_is_preserved_instead_of_positive_sqrt_b(response, method, change, sign):
    result = response(**_case(**change), method=method)
    assert result.a.shape == result.b.shape == (1,)
    assert np.sign(result.a.real[0]) == sign
    assert result.a.imag[0] == 0
    assert result.b.real[0] > 0


@pytest.mark.parametrize(
    "method,module,field",
    [
        ("harmonic", "_dielectric_harmonic", "a"),
        ("harmonic_weideman", "_dielectric_weideman", "a"),
        ("ronnmark", "_dielectric_ronnmark", "as"),
        ("diagnostic", "_dielectric_diagnostic", "as"),
    ],
)
def test_a_is_the_original_kernel_value(response, diagnostic, monkeypatch, method, module, field):
    kernel = importlib.import_module(f"scirel.kinetic.{module}")
    original = kernel._evaluate
    observations = []

    def observe(**kwargs):
        raw = original(**kwargs)
        observations.append(raw[field])
        return raw

    monkeypatch.setattr(kernel, "_evaluate", observe)
    result = diagnostic(**_case()) if method == "diagnostic" else response(**_case(), method=method)
    assert len(observations) == 1
    assert result.a is observations[0]


@pytest.mark.parametrize("method", ["harmonic", "harmonic_weideman"])
def test_finite_methods_default_and_none_use_five_harmonics(response, method):
    explicit = response(**_case(), method=method, harmonics=5)
    for options in ({}, {"harmonics": None}):
        result = response(**_case(), method=method, **options)
        assert result.diagnostics.harmonics == 5
        for key in CORE_KEYS - {"diagnostics"}:
            np.testing.assert_array_equal(result[key], explicit[key])


def test_omitted_method_selects_harmonic(response):
    default = response(**_case())
    explicit = response(**_case(), method="harmonic")
    assert default.diagnostics.method == "harmonic"
    for key in CORE_KEYS - {"diagnostics"}:
        np.testing.assert_array_equal(default[key], explicit[key])


@pytest.mark.parametrize("method", ["harmonic", "harmonic_weideman"])
@pytest.mark.parametrize("harmonics", [0, np.int64(2)])
def test_finite_methods_accept_nonnegative_integer_harmonics(response, method, harmonics):
    result = response(**_case(), method=method, harmonics=harmonics)
    assert result.diagnostics.harmonics == harmonics


@pytest.mark.parametrize("method", ["harmonic", "harmonic_weideman", "diagnostic"])
@pytest.mark.parametrize("harmonics", [True, False, np.bool_(True), 1.5, 5.0, "5", [5], 1 + 0j])
def test_harmonic_type_errors_name_input_and_legal_condition(
    response, diagnostic, method, harmonics
):
    function = diagnostic if method == "diagnostic" else response
    options = {} if method == "diagnostic" else {"method": method}
    with pytest.raises(TypeError) as error:
        function(**_case(), **options, harmonics=harmonics)
    contract = "scirel.kinetic.dielectric-" + (
        "diagnostics" if method == "diagnostic" else "response"
    )
    message = _error_context(error, "harmonics", harmonics, contract)
    assert "integer" in message and ("nonnegative" in message or "non-negative" in message)


@pytest.mark.parametrize("method", ["harmonic", "harmonic_weideman", "diagnostic"])
@pytest.mark.parametrize("harmonics", [-1, np.int64(-5)])
def test_negative_harmonics_are_value_errors(response, diagnostic, method, harmonics):
    function = diagnostic if method == "diagnostic" else response
    options = {} if method == "diagnostic" else {"method": method}
    with pytest.raises(ValueError) as error:
        function(**_case(), **options, harmonics=harmonics)
    contract = "scirel.kinetic.dielectric-" + (
        "diagnostics" if method == "diagnostic" else "response"
    )
    _error_context(error, "harmonics", harmonics, contract)


def test_diagnostic_none_is_not_a_default_cutoff(diagnostic):
    with pytest.raises(TypeError) as error:
        diagnostic(**_case(), harmonics=None)
    _error_context(error, "harmonics", None, "scirel.kinetic.dielectric-diagnostics")


@pytest.mark.parametrize("harmonics", [0, 5, -1, True, np.bool_(False), 1.5, "5", [], {}])
def test_ronnmark_refuses_every_unused_harmonic_control(response, harmonics):
    with pytest.raises(TypeError) as error:
        response(**_case(), method="ronnmark", harmonics=harmonics)
    assert "None" in _error_context(
        error, "harmonics", harmonics, "scirel.kinetic.dielectric-response"
    )


def test_ronnmark_accepts_none_without_cutoff_metadata(response):
    result = response(**_case(), method="ronnmark", harmonics=None)
    assert "harmonics" not in result.diagnostics


@pytest.mark.parametrize("method", [None, True, 3, [], {}])
def test_method_requires_a_string(response, method):
    with pytest.raises(TypeError) as error:
        response(**_case(), method=method)
    message = _error_context(error, "method", method, "scirel.kinetic.dielectric-response")
    assert all(value in message for value in METHODS)


@pytest.mark.parametrize("method", ["", "Harmonic", "auto", "weideman"])
def test_unknown_method_is_not_automatically_substituted(response, method):
    with pytest.raises(ValueError) as error:
        response(**_case(), method=method)
    message = _error_context(error, "method", method, "scirel.kinetic.dielectric-response")
    assert all(value in message for value in METHODS)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("omega", [0.0, np.nan, np.inf, -np.inf])
def test_nonfinite_or_zero_omega_is_invalid_input(response, method, omega):
    with pytest.raises(ValueError):
        response(**_case(omega=omega), method=method)


@pytest.mark.parametrize("omega", [0.0, np.nan, np.inf, -np.inf])
def test_diagnostic_nonfinite_or_zero_omega_is_invalid_input(diagnostic, omega):
    with pytest.raises(ValueError):
        diagnostic(**_case(omega=omega))


@pytest.mark.parametrize("method", ["harmonic", "harmonic_weideman"])
@pytest.mark.parametrize("change", [{"kz": 0.0}, {"kx": 10000 + 2000j}])
def test_finite_methods_do_not_inherit_ronnmark_domain(response, method, change):
    # Preserve the original float-conversion TypeError on the Weideman path.
    error = TypeError if method == "harmonic_weideman" and "kx" in change else ValueError
    with pytest.raises(error):
        response(**_case(**change), method=method)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("change", [{"ns0": [1e-320]}, {"ns0": [1e300]}])
def test_numerical_failure_still_raises_instead_of_filling_result(response, method, change):
    with np.errstate(all="ignore"), pytest.raises(FloatingPointError):
        response(**_case(**change), method=method)


@pytest.mark.parametrize(
    "method,expected,tolerance",
    [
        ("harmonic", 1184249.3244493124 + 4322451.2861608062j, 1e-13),
        ("harmonic_weideman", 1184249.3244493124 + 4322451.2861608062j, 1e-12),
        ("ronnmark", 1184258.061758124 + 4322544.0839688079j, 1e-12),
    ],
)
def test_new_interface_keeps_frozen_source_wavepoint(response, method, expected, tolerance):
    # Existing source values, not tensors recalculated by a duplicate implementation.
    omega = 175881684853.009
    result = response(
        **_case(
            omega=2.0 * np.pi * float(omega / (2.0 * np.pi)),
            kz=1326.1942478795652,
            Ts0=[1e3 * 1.6022e-19 / 1.38064852e-23],
        ),
        method=method,
    )
    assert abs(result.determinant - expected) <= tolerance * abs(expected)


def test_diagnostic_default_result_and_exact_fields(diagnostic):
    result = diagnostic(**_case())
    assert isinstance(result, Result) and set(result) == RAW_KEYS
    assert isinstance(result.diagnostics, Result)
    assert set(result.diagnostics) == {
        "harmonics",
        "tensor_convention",
        "finite_K",
        "finite_D",
        "finite_determinant",
        "complete",
        "message",
    }
    assert result.diagnostics.harmonics == 15
    assert result.diagnostics.tensor_convention == CONVENTION
    assert result.diagnostics.complete
    for key, mask in (("K_raw", "finite_K"), ("D_raw", "finite_D")):
        np.testing.assert_array_equal(result.diagnostics[mask], np.isfinite(result[key]))
        assert result.diagnostics[mask].dtype == np.dtype(bool)
    assert result.diagnostics.finite_determinant == bool(np.isfinite(result.determinant_raw))
    assert isinstance(result.diagnostics.message, str) and result.diagnostics.message
    explicit = diagnostic(**_case(), harmonics=15)
    for key in RAW_KEYS - {"diagnostics"}:
        np.testing.assert_array_equal(result[key], explicit[key])


@pytest.mark.parametrize("harmonics", [0, np.int64(2)])
def test_diagnostic_accepts_nonnegative_integer_cutoffs(diagnostic, harmonics):
    result = diagnostic(**_case(), harmonics=harmonics)
    assert result.diagnostics.harmonics == harmonics
    assert result.diagnostics.complete


@pytest.mark.parametrize("density", [6.075e19, 1e300])
def test_diagnostic_masks_describe_original_partial_values(diagnostic, density):
    result = diagnostic(**_case(kx=0.0, ns0=[density]), harmonics=5)
    expected = np.array([[False, True, False], [True, False, True], [False, True, True]])
    for raw, mask in (("K_raw", "finite_K"), ("D_raw", "finite_D")):
        np.testing.assert_array_equal(np.isfinite(result[raw]), expected)
        np.testing.assert_array_equal(result.diagnostics[mask], np.isfinite(result[raw]))
    assert not np.isfinite(result.determinant_raw)
    assert result.diagnostics.finite_determinant == bool(np.isfinite(result.determinant_raw))
    assert not result.diagnostics.complete
    assert isinstance(result.diagnostics.message, str) and result.diagnostics.message


def test_diagnostic_keeps_broadcast_species_and_complex_signed_a(diagnostic):
    result = diagnostic(
        **_case(
            qs=[-1.60217662e-19, 1.60217662e-19],
            ms=[9.1094e-31, 1.67262192369e-27],
            kx=10000 + 2000j,
        )
    )
    assert result.a.shape == result.b.shape == result.rhocs.shape == (2,)
    assert result.a[0].real < 0 and result.a[0].imag < 0
    assert result.a[1].real > 0 and result.a[1].imag > 0
    assert np.all(result.b.imag != 0)
    assert result.diagnostics.complete


@pytest.mark.parametrize("kx", [0.0, 13261.94247879565])
def test_diagnostic_partial_does_not_hide_other_numerical_failures(diagnostic, kx):
    with np.errstate(all="ignore"), pytest.raises(FloatingPointError):
        diagnostic(**_case(kx=kx, ns0=[1e-320]))


def test_ronnmark_companion_is_H_from_original_RC():
    from scirel.kinetic import evaluate_ronnmark_r

    result = evaluate_ronnmark_r(0.5, 0.25)
    assert isinstance(result, Result)
    assert set(result) == {"R", "H", "branch", "RC"}
    assert result.R == result.RC[0, 0]
    assert result.H == result.RC[0, 1]
    assert not hasattr(result, "dR_dlambda")

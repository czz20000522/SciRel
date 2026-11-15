"""Original numerical references carried to the two canonical dispersion questions."""

import numpy as np
import pytest
from scipy.special import wofz

from scirel._result import Result
from scirel.kinetic import evaluate_plasma_dispersion
from scirel.numerics import evaluate_faddeeva


@pytest.mark.parametrize("order", [32, 16])
def test_defaults_and_independent_complex_error_function(order):
    z = np.array([[0, 0.1 + 0.2j, 2 + 1j], [-2 - 0.5j, 1 - 2j, 40j]])
    # Default32 and explicit16 preserve the original two numerical budgets.
    result = evaluate_faddeeva(z) if order == 32 else evaluate_faddeeva(z, order=16)
    np.testing.assert_allclose(
        result,
        wofz(z),
        rtol=1e-6 if order == 16 else 5e-13,
        atol=3e-7 if order == 16 else 5e-13,
    )
    assert result.shape == z.shape


def test_imaginary_axis_overflow_regression():
    # Historical exp(y*y)*erfc(y) gives inf*0 for y=40, though w(40i) is finite.
    with np.errstate(over="ignore", invalid="ignore"):
        from scipy.special import erfc

        assert np.isnan(np.exp(40.0**2) * erfc(40.0))
    np.testing.assert_allclose(evaluate_faddeeva(40j), wofz(40j), rtol=2e-15)


@pytest.mark.parametrize("order", [16, 32, 64])
def test_fft_normalization_and_reflection(order):
    z = np.array([0.2 + 1j, 2 - 1j, 1 + 0j])
    w = evaluate_faddeeva(z, order=order)
    result = evaluate_plasma_dispersion(z, method="rational", order=order)
    np.testing.assert_allclose(result["Z"], 1j * np.sqrt(np.pi) * w)
    np.testing.assert_array_equal(result["w"], w)
    np.testing.assert_allclose(
        w + evaluate_faddeeva(-z, order=order),
        2 * np.exp(-z * z),
        atol=5e-7 if order == 16 else 2e-12,
    )


@pytest.mark.parametrize("order", [8, 12, 16, 24])
def test_jpole_all_matrix_entries_and_scalar_reference(order):
    z = np.array([[0.1 + 0.2j, 1 + 1j, 2 - 0.1j], [3 + 0.5j, -2 + 0.1j, 5 + 2j]])
    result = evaluate_plasma_dispersion(z, method="jpole", order=order)
    whole = result["Z"]
    assert whole.shape == z.shape
    assert np.all(whole != 0)
    for ix in np.ndindex(z.shape):
        np.testing.assert_allclose(
            whole[ix], evaluate_plasma_dispersion(z[ix], method="jpole", order=order)["Z"]
        )
    # Fixed rational truncation accuracy; this is not a uniformly accurate entire function.
    np.testing.assert_allclose(whole, 1j * np.sqrt(np.pi) * wofz(z), rtol=5e-5, atol=5e-6)
    # J-pole w is the corresponding approximation, with the original accuracy ceiling.
    np.testing.assert_array_equal(result["w"], whole / (1j * np.sqrt(np.pi)))
    np.testing.assert_allclose(result["w"], wofz(z), rtol=5e-5, atol=5e-6 / np.sqrt(np.pi))


@pytest.mark.parametrize("path", ["math32", "math16", "rational"])
@pytest.mark.parametrize("order", [0, True, 1.5, -2])
def test_invalid_truncation(path, order):
    with pytest.raises(TypeError, match="order.*legal.*scirel"):
        if path == "rational":
            evaluate_plasma_dispersion(1j, method="rational", order=order)
        else:
            evaluate_faddeeva(1j, order=order)


def test_explicit_empty_and_overflow():
    # Effective-order metadata retired; exact array comparisons retain default meaning.
    np.testing.assert_array_equal(
        evaluate_faddeeva(1j, order=None), evaluate_faddeeva(1j, order=32)
    )
    np.testing.assert_array_equal(evaluate_faddeeva(1j, order=16), wofz(1j))
    # Explicit None now selects each method's default, as authorized.
    for method, order in (("rational", 32), ("jpole", 8)):
        implicit = evaluate_plasma_dispersion(1j, method=method)
        explicit_none = evaluate_plasma_dispersion(1j, method=method, order=None)
        explicit_order = evaluate_plasma_dispersion(1j, method=method, order=order)
        for key in ("w", "Z"):
            np.testing.assert_array_equal(implicit[key], explicit_none[key])
            np.testing.assert_array_equal(explicit_none[key], explicit_order[key])
    with pytest.raises(FloatingPointError):
        evaluate_faddeeva(-40j)
    with pytest.raises(TypeError):
        evaluate_plasma_dispersion(1, method="jpole", order=10)


@pytest.mark.parametrize(
    "z", [1e200 + 0.1j, 1e200 - 0.1j, 1e308 + 1j, 1e308 - 1j, 1.79e308 + 1j, 1.79e308 - 1j]
)
def test_large_real_finite_response(z):
    # Gaussian exponential underflows; the algebraic response remains finite.
    expected = 1j / np.sqrt(np.pi) / z
    np.testing.assert_allclose(evaluate_faddeeva(z), expected, rtol=3e-15, atol=0)
    np.testing.assert_allclose(
        evaluate_plasma_dispersion(z, method="jpole", order=8)["Z"], -1 / z, rtol=5e-12, atol=0
    )


@pytest.mark.parametrize("method", ["scipy", "rational", "weideman", "jpole"])
@pytest.mark.parametrize("points", [0.3 + 0.2j, [[0j, 0.5 + 0.5j], [2 - 1j, 40j]]])
def test_family_has_exact_scientific_ports_and_no_mutation(method, points):
    z = np.asarray(points, dtype=np.complex128)
    original = z.copy()
    result = evaluate_plasma_dispersion(z, method=method)
    assert isinstance(result, Result)
    assert list(result) == ["w", "Z"]
    np.testing.assert_array_equal(z, original)
    for key in ("w", "Z"):
        assert result[key].shape == z.shape
        assert result[key].dtype == np.complex128
        assert np.isfinite(result[key]).all()
        assert getattr(result, key) is result[key]


@pytest.mark.parametrize("method", ["scipy", "weideman"])
@pytest.mark.parametrize("order", [0, 8, 32, 64, True, "64", [64]])
def test_unused_order_is_rejected(method, order):
    with pytest.raises(TypeError, match="order.*None.*scirel"):
        evaluate_plasma_dispersion(0j, method=method, order=order)


@pytest.mark.parametrize("method", [None, True, 3, [], {}, "dr", "gpdf", "fft", "SCIPY", "unknown"])
def test_invalid_selector(method):
    with pytest.raises(TypeError, match="method.*scipy.*rational.*weideman.*jpole.*scirel"):
        evaluate_plasma_dispersion(0j, method=method)


@pytest.mark.parametrize("method", ["rational", "jpole"])
@pytest.mark.parametrize("order", [False, np.bool_(True), "8", 8.0, [8], np.array([8]), 0, -1])
def test_wrong_controls(method, order):
    with pytest.raises(TypeError, match="order.*legal.*scirel"):
        evaluate_plasma_dispersion(0j, method=method, order=order)


@pytest.mark.parametrize("order", [1, 7, 16, 32, 64, np.int64(17)])
def test_positive_integer_orders_remain_unbounded_by_sampled_orders(order):
    z = [0.3 + 0.2j, -0.4 - 0.1j]
    w = evaluate_faddeeva(z, order=order)
    result = evaluate_plasma_dispersion(z, method="rational", order=order)
    np.testing.assert_array_equal(result.w, w)
    np.testing.assert_allclose(result.Z, 1j * np.sqrt(np.pi) * w, rtol=0, atol=0)


@pytest.mark.parametrize("method", [None, "scipy", "rational", "weideman", "jpole"])
@pytest.mark.parametrize(
    "bad", [True, [1, False], "1", ["1j"], object(), np.ma.array([1j], mask=[False])]
)
def test_wrong_input_kinds_fail_before_evaluation(method, bad):
    with pytest.raises(TypeError, match="z.*legal.*scirel"):
        if method is None:
            evaluate_faddeeva(bad)
        else:
            evaluate_plasma_dispersion(bad, method=method)


@pytest.mark.parametrize("method", [None, "scipy", "rational", "weideman", "jpole"])
@pytest.mark.parametrize("bad", [[], np.empty((2, 0)), [[1], [1, 2]], [np.nan], [np.inf]])
def test_invalid_input_values_fail_whole_call(method, bad):
    with pytest.raises(ValueError, match="z.*legal.*scirel"):
        if method is None:
            evaluate_faddeeva(bad)
        else:
            evaluate_plasma_dispersion(bad, method=method)


def test_finite_narrowing_rejects_values_outside_complex128():
    if np.finfo(np.longdouble).max <= np.finfo(np.float64).max:
        pytest.skip("longdouble has no wider finite range on this platform")
    bad = np.array([np.longdouble(np.finfo(float).max) * 2], dtype=np.longdouble)
    assert np.isfinite(bad).all()
    for method in ("scipy", "rational", "weideman", "jpole"):
        with np.errstate(over="raise"), pytest.raises(ValueError, match="complex128.*nonfinite"):
            evaluate_plasma_dispersion(bad, method=method)
    with np.errstate(over="raise"), pytest.raises(ValueError, match="complex128.*nonfinite"):
        evaluate_faddeeva(bad)


@pytest.mark.parametrize("method", ["scipy", "rational", "weideman", "jpole"])
def test_unrepresentable_element_rejects_entire_family_result(method):
    with pytest.raises(FloatingPointError):
        evaluate_plasma_dispersion([[0.2 + 0.3j, 1j], [-40j, 40j]], method=method)
    with pytest.raises(FloatingPointError):
        evaluate_faddeeva([[0.2 + 0.3j, 1j], [-40j, 40j]])


@pytest.mark.parametrize("consumer", ["generalized", "parallel"])
def test_existing_consumers_keep_declared_overflow_exception(consumer):
    # Real finite inputs reach the canonical Z overflow; no backend mock is used.
    if consumer == "generalized":
        from scirel.kinetic import evaluate_generalized_dispersion

        call = lambda: evaluate_generalized_dispersion(-30j)
    else:
        from scirel.kinetic.dispersion._fluid_parallel import em1d_parallel_residual

        state = dict(wps2=[1.0], vds=[0.0], vtzs=[1.0], wcs=[1.0], c2=1.0)
        call = lambda: em1d_parallel_residual(state, -30j, 1.0)
    with pytest.raises(ValueError, match="not representable"):
        call()

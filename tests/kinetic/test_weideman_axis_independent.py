"""Independent original-integral references for the fixed N64 imaginary axis."""

from functools import lru_cache
import warnings

import mpmath as mp
import numpy as np
import pytest

from scirel.kinetic import evaluate_plasma_dispersion


@lru_cache(maxsize=None)
def _axis_at_precision(y, digits):
    with mp.workdps(digits):
        y = mp.mpf(y)
        if y > 0:
            # From exp(y^2)*erfc(y), substitute u=2*y*(t-y) in
            # erfc(y)=2/sqrt(pi)*integral_y^infinity exp(-t^2) dt.
            integral = mp.quad(
                lambda u: mp.exp(-u - (u / (2 * y)) ** 2),
                [0, 1, 4, 16, mp.inf],
            )
            w = integral / (mp.sqrt(mp.pi) * y)
        else:
            w = mp.exp(y * y) * mp.erfc(y)
        return +w, +(mp.sqrt(mp.pi) * w)


def _axis_reference(y):
    low = _axis_at_precision(float(y), 90)
    high = _axis_at_precision(float(y), 140)
    with mp.workdps(140):
        for lower, higher in zip(low, high, strict=True):
            assert abs(lower - higher) / abs(higher) < mp.mpf("1e-75")
    return high


def _assert_axis_values(result, reference):
    w_reference, z_imaginary_reference = reference
    w = complex(result["w"])
    z = complex(result["Z"])
    assert w.imag == 0
    assert z.real == 0
    with mp.workdps(140):
        for actual, expected in ((w.real, w_reference), (z.imag, z_imaginary_reference)):
            assert abs(mp.mpf(actual) - expected) / abs(expected) <= mp.mpf("3e-15")


POSITIVE_AXIS = [
    0.0,
    26.0,
    np.nextafter(27.0, 0.0),
    27.0,
    np.nextafter(27.0, np.inf),
    np.nextafter(40.0, 0.0),
    40.0,
    np.nextafter(40.0, np.inf),
    1000.0,
    1e200,
    1e308,
    np.finfo(float).max,
]


@pytest.mark.parametrize("y", POSITIVE_AXIS)
def test_representable_positive_axis_matches_independent_integral(y):
    reference = _axis_reference(y)
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        result = evaluate_plasma_dispersion(complex(0, y), method="weideman")
    assert set(result) == {"Z", "w"}
    assert result["w"].shape == result["Z"].shape == ()
    assert result["w"].dtype == result["Z"].dtype == np.complex128
    _assert_axis_values(result, reference)


@pytest.mark.parametrize("y", [-26.0, -1.0, -0.0])
def test_existing_nonpositive_axis_matches_original_definition(y):
    reference = _axis_reference(y)
    result = evaluate_plasma_dispersion(complex(0, y), method="weideman")
    _assert_axis_values(result, reference)


def test_all_imaginary_matrix_preserves_shape_and_inputs():
    points = np.array([[0j, 27j], [-26j, 40j]])
    original = points.copy()
    references = [_axis_reference(value.imag) for value in points.flat]
    result = evaluate_plasma_dispersion(points, method="weideman")
    np.testing.assert_array_equal(points, original)
    assert result["w"].shape == result["Z"].shape == points.shape
    for index, reference in zip(np.ndindex(points.shape), references, strict=True):
        _assert_axis_values({key: result[key][index] for key in ("w", "Z")}, reference)


def test_mixed_matrix_keeps_original_complex_branch_and_axis_values():
    points = np.array([[27j, 0.5 + 0.5j], [2 - 1j, 40j]])
    original = points.copy()
    with mp.workdps(140):
        expected_w = np.array(
            [complex(mp.exp(-(mp.mpc(z) ** 2)) * mp.erfc(-1j * mp.mpc(z))) for z in points.flat]
        ).reshape(points.shape)
        expected_z = np.array(
            [
                complex(1j * mp.sqrt(mp.pi) * mp.exp(-(mp.mpc(z) ** 2)) * mp.erfc(-1j * mp.mpc(z)))
                for z in points.flat
            ]
        ).reshape(points.shape)
    result = evaluate_plasma_dispersion(points, method="weideman")
    np.testing.assert_array_equal(points, original)
    np.testing.assert_allclose(result["w"], expected_w, rtol=1e-12, atol=1e-13)
    np.testing.assert_allclose(result["Z"], expected_z, rtol=1e-12, atol=1e-13)


def test_final_z_overflow_raises_without_redundant_warning():
    w_reference, z_reference = _axis_reference(-26.625)
    with mp.workdps(140):
        maximum = mp.mpf(float(np.finfo(float).max))
        assert 0 < w_reference < maximum < z_reference
    # The expression is unchanged; the authorized interface retires the warning.
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        with pytest.raises(FloatingPointError, match="finite"):
            evaluate_plasma_dispersion(-26.625j, method="weideman")


@pytest.mark.parametrize("y", [-27.0, -40.0])
def test_truly_unrepresentable_negative_axis_still_rejects(y):
    w_reference, z_reference = _axis_reference(y)
    with mp.workdps(140):
        assert w_reference > mp.mpf(float(np.finfo(float).max))
        assert z_reference > mp.mpf(float(np.finfo(float).max))
    with (
        np.errstate(over="ignore", invalid="ignore"),
        pytest.raises(FloatingPointError, match="finite"),
    ):
        evaluate_plasma_dispersion(complex(0, y), method="weideman")


def test_one_unrepresentable_axis_element_rejects_the_whole_mapping():
    _axis_reference(40)
    _axis_reference(-27)
    with (
        np.errstate(over="ignore", invalid="ignore"),
        pytest.raises(FloatingPointError, match="finite"),
    ):
        evaluate_plasma_dispersion([[40j, 0.5 + 0.5j], [-27j, 27j]], method="weideman")

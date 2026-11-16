"""Pointwise source profiles from exact input distances, not just integrals."""

from decimal import Decimal, localcontext
from fractions import Fraction

import numpy as np
import pytest

from scirel.source import exponential_profile, gaussian_profile


def _reference(kind, rho, vpr, drho, parameter, width, total):
    """Square exact input distances independently of the factored production path."""
    radii = [Fraction(float(value)) for value in rho]
    w = Fraction(float(width))
    tiny = Fraction(1, 2**1022)
    if kind == "gaussian":
        distances = [(radius - Fraction(float(parameter))) ** 2 for radius in radii]
        denominator = max(2 * w**2, tiny)
        exponents = [-(distance - min(distances)) / denominator for distance in distances]
    else:
        effective_width = max(abs(w), tiny) * (1 if w > 0 else -1)
        # The additive location term cancels; no production endpoint is used.
        raw = [radius / effective_width for radius in radii]
        exponents = [value - max(raw) for value in raw]
    weights = [Fraction(float(v)) * Fraction(float(d)) for v, d in zip(vpr, drho)]
    references = []
    for precision in (120, 200):
        with localcontext() as context:
            context.prec = precision
            shape = [
                (Decimal(value.numerator) / Decimal(value.denominator)).exp() for value in exponents
            ]
            integral = sum(
                value * Decimal(weight.numerator) / Decimal(weight.denominator)
                for value, weight in zip(shape, weights)
            )
            references.append(
                [float(Decimal.from_float(float(total)) * value / integral) for value in shape]
            )
    assert references[0] == references[1], "independent precisions must agree after rounding"
    return references[1]


def _check_profile(kind, rho, vpr, drho, parameter, width, total):
    arrays = [np.array(value, dtype=np.float64) for value in (rho, vpr, drho)]
    before = [value.copy() for value in arrays]
    expected = _reference(kind, *arrays, parameter, width, total)
    function = gaussian_profile if kind == "gaussian" else exponential_profile
    options = {"center": parameter} if kind == "gaussian" else {"decay_start": parameter}
    actual = function(*arrays, width=width, total=total, **options)
    np.testing.assert_allclose(actual, expected, rtol=2e-15, atol=0)
    assert actual.shape == arrays[0].shape
    assert actual.dtype == np.float64
    assert np.all(np.isfinite(actual))
    for original, current in zip(before, arrays):
        np.testing.assert_array_equal(current, original)
    # A common positive volume scale changes amplitudes by its inverse.
    scaled = function(arrays[0], arrays[1] * 2**20, arrays[2], width=width, total=total, **options)
    np.testing.assert_allclose(scaled, np.asarray(expected) / 2**20, rtol=2e-15, atol=0)
    return actual


@pytest.mark.parametrize("sign", [1, -1])
@pytest.mark.parametrize("total", [1.0, -1.0, 0.0])
def test_gaussian_adjacent_center_distance_survives_normalization(sign, total):
    # Exact exponent offsets are [0, -2], above the denominator floor.
    _check_profile("gaussian", [0.5, 0.5 + 2**-53], [1, 1], [1, 1], 0.5, sign * 2**-54, total)


@pytest.mark.parametrize("sign", [1, -1])
def test_gaussian_adjacent_left_of_center(sign):
    # The predecessor of .5 is .5 - 2**-54, not .5 - 2**-53.
    _check_profile("gaussian", [0.5 - 2**-54, 0.5], [1, 1], [1, 1], 0.5, sign * 2**-55, 1.0)


@pytest.mark.parametrize("sign", [1, -1])
def test_gaussian_denominator_floor_preserves_resolved_shape(sign):
    # 2*w**2 is below tiny; rho[1]**2 is exactly tiny. Offsets: [0, -1].
    _check_profile("gaussian", [0, 2**-511], [1, 1], [1, 1], 0.0, sign * 2**-600, 1.0)


@pytest.mark.parametrize("center", [2.0**500, -(2.0**500)])
@pytest.mark.parametrize("sign", [1, -1])
def test_gaussian_remote_center_retains_finite_nonuniform_shape(center, sign):
    # Squared distances individually dwarf their differences; the normalized
    # profile still has distinct ordinary-sized entries, all checked directly.
    _check_profile("gaussian", [0, 0.5, 1], [1, 2, 4], [1, 1, 1], center, sign * 2.0**250, 3.0)


@pytest.mark.parametrize("width", [0.25, np.finfo(np.float64).max])
def test_gaussian_symmetric_or_wide_limit(width):
    _check_profile("gaussian", [0.25, 0.75], [1, 2], [1, 1], 0.5, width, 3.0)


@pytest.mark.parametrize("total", [3.0, -3.0])
def test_exponential_nonuniform_point_values_and_adjacent_ratios(total):
    actual = _check_profile("exponential", [0, 0.5, 1], [1, 2, 4], [1, 1, 1], 0.8, 1.0, total)
    with localcontext() as context:
        context.prec = 120
        adjacent_ratio = float(Decimal("0.5").exp())
    np.testing.assert_allclose(actual[1:] / actual[:-1], adjacent_ratio, rtol=2e-15, atol=0)


@pytest.mark.parametrize("sign", [1, -1])
def test_exponential_tiny_signed_width_floor_preserves_resolved_shape(sign):
    _check_profile("exponential", [0, 2**-1022], [1, 1], [1, 1], 0.8, sign * 2**-1074, 1.0)


@pytest.mark.parametrize("total", [2.0, -2.0])
@pytest.mark.parametrize("kind", ["exponential", "gaussian"])
def test_nonuniform_quadrature_widths_keep_each_cell_weight(kind, total):
    """A non-uniform ``drho_norm`` separates the volume weight from ``vpr`` alone.

    Every other pointwise case in this file uses unit grid widths, where the
    ``vpr*drho_norm`` product differs from ``vpr`` by one common factor that the
    normalization divides out. With unequal widths that factor is no longer
    common, so a dropped or mispaired width changes the point values; the
    reference sums the same exact rational weights independently.
    """
    parameter = 0.7 if kind == "exponential" else 0.5
    _check_profile(kind, [0.2, 0.55, 0.9], [1.0, 2.0, 4.0], [0.5, 0.25, 1.0], parameter, 1.0, total)

"""Regressions for exact signed cell sums before final float64 rounding."""

import itertools
import numpy as np
import pytest
from scirel.physics import calculate_stored_thermal_energy


def test_all_signed_pressure_orders_retain_small_residual():
    for p in itertools.permutations([1e30, 1.0, -1e30]):
        assert calculate_stored_thermal_energy(p, p, p, [1] * 3, [1] * 3) == (1.5,) * 3


def test_exact_product_cancellation_beyond_intermediate_float_range():
    p = [1e308, 1.0, -1e308]
    assert calculate_stored_thermal_energy(p, p, p, [1e308, 1, 1e308], [1] * 3) == (1.5,) * 3


def test_subnormal_products_accumulate_before_rounding():
    tiny = np.nextafter(0.0, 1.0)
    assert (
        calculate_stored_thermal_energy([tiny] * 4, [tiny] * 4, [tiny] * 4, [0.25] * 4, [1] * 4)
        == (2 * tiny,) * 3
    )


def test_final_overflow_and_zero_underflow_still_fail():
    for p, v, d in [([1e308], [2.0], [1.0]), ([1e-300], [1e-200], [1e-200])]:
        with pytest.raises(FloatingPointError):
            calculate_stored_thermal_energy(p, p, p, v, d)

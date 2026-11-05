"""Out-of-range values are clipped only with a visible warning."""

import numpy as np
import pytest

from scirel.collisions import (
    evaluate_atomic_hydrogen_charge_exchange_cross_section as sigma,
    evaluate_atomic_hydrogen_charge_exchange_rate as rate,
)


@pytest.mark.parametrize(
    "energy,freeman,upper",
    [(3.0e5, False, 2.5e5), (2.0e5, True, 1.0e5)],
)
def test_cross_section_warns_above_the_fit_and_keeps_its_value(energy, freeman, upper):
    with pytest.warns(RuntimeWarning, match="upper limit"):
        value = sigma(np.array([energy]), freeman=freeman)
    assert value[0] == sigma(np.array([upper]), freeman=freeman)[0]


@pytest.mark.parametrize(
    "temperature,energy",
    [(3.0e5, 1.0e3), (1.0e3, 3.0e5)],
)
def test_rate_warns_above_the_supported_range(temperature, energy):
    with pytest.warns(RuntimeWarning, match="upper limit"):
        rate(np.array([temperature]), np.array([energy]))


@pytest.mark.filterwarnings("error")
def test_no_warning_inside_the_supported_ranges():
    sigma(np.array([1.0e-3, 1.0, 2.5e5]))
    sigma(np.array([1.0e5]), freeman=True)
    rate(np.array([1.0, 5.0e4]), np.array([0.01, 1.0e5]))

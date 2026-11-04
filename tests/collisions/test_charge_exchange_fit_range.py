"""Above its fit range the cross section is held at its end value, which is reported to the caller."""

import numpy as np
import pytest

from scirel.collisions import (
    evaluate_atomic_hydrogen_charge_exchange_cross_section as sigma,
    evaluate_atomic_hydrogen_charge_exchange_rate as rate,
)


@pytest.mark.parametrize("energy, freeman", [(1.0e5, False), (2.0e5, True)])
def test_cross_section_warns_above_the_fit_and_keeps_its_value(energy, freeman):
    with pytest.warns(RuntimeWarning, match="upper limit"):
        value = sigma(np.array([energy]), freeman=freeman)
    assert value[0] == sigma(np.array([1.0e5 if freeman else 2.01e4]), freeman=freeman)[0]


@pytest.mark.parametrize("temperature, energy", [(5.0e4, 1.0e3), (1.0e3, 5.0e4)])
def test_rate_warns_above_the_fit(temperature, energy):
    with pytest.warns(RuntimeWarning, match="upper limit"):
        rate(np.array([temperature]), np.array([energy]))


@pytest.mark.filterwarnings("error")
def test_no_warning_inside_the_fit_or_below_it():
    sigma(np.array([1.0e-3, 1.0, 2.01e4]))
    sigma(np.array([1.0e5]), freeman=True)
    rate(np.array([1.0, 2.01e4]), np.array([0.01, 2.01e4]))

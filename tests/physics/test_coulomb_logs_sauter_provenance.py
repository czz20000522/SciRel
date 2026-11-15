"""Original-equation and unit regressions for EPFL LRP 630/99, not physical calibration.

Sauter, Angioni and Lin-Liu's February 1999 institutional author manuscript,
printed p. 7 (PDF p. 8), gives Eq. (18d) as ln Lambda_e (not Lambda_ei) and
Eq. (18e) as ln Lambda_ii. Both use densities in m^-3 and temperatures in eV.
Original record: https://infoscience.epfl.ch/handle/20.500.14299/23214
PDF SHA-256: 8c5e7bbf304254b2895e5f161c25536c7e2c517ff9ab7cd056223a0309232d11

References below use the original quotients, fixed original constants, and eV
inputs. They do not import production constants or read production values to
construct expected results. The publisher's final version and 2002 erratum are
not verified; neither are ee 31.0, Wesson or the physical origin of the NRL gap.
"""

import math

import numpy as np
import pytest

from scirel.physics import calculate_log_lambda_ei, calculate_log_lambda_ii


@pytest.mark.parametrize("temperature_ev", [25.0, 1000.0, 3750.0, 20000.0])
@pytest.mark.parametrize("density_m3", [1e17, 1e19, 8e21])
def test_ei_matches_manuscript_18d_with_ev_converted_to_kev(temperature_ev, density_m3):
    expected = 31.3 - math.log(math.sqrt(density_m3) / temperature_ev)
    actual = calculate_log_lambda_ei(temperature_ev / 1000.0, density_m3)
    assert actual == pytest.approx(expected, rel=0, abs=1e-14)


@pytest.mark.parametrize("temperature_ev", [25.0, 1000.0, 3750.0, 20000.0])
@pytest.mark.parametrize("density_m3", [1e17, 1e19, 8e21])
@pytest.mark.parametrize("charge", [1.0, 2.0, 6.0])
def test_ii_matches_manuscript_18e_with_cubic_charge_and_ev_units(
    temperature_ev, density_m3, charge
):
    expected = 30.0 - math.log(charge**3 * math.sqrt(density_m3) / temperature_ev**1.5)
    actual = calculate_log_lambda_ii(temperature_ev / 1000.0, density_m3, charge)
    assert actual == pytest.approx(expected, rel=0, abs=1e-14)


def test_manuscript_equations_preserve_broadcast_units_and_charge_power():
    temperature_ev = np.array([25.0, 1000.0, 20000.0])
    density_m3 = np.array([[1e17], [8e21]])
    charge = np.array([1.0, 2.0, 6.0])[:, None, None]
    expected_e = 31.3 - np.log(np.sqrt(density_m3) / temperature_ev)
    expected_ii = 30.0 - np.log(charge**3 * np.sqrt(density_m3) / temperature_ev**1.5)
    np.testing.assert_allclose(
        calculate_log_lambda_ei(temperature_ev / 1000.0, density_m3),
        expected_e,
        rtol=0,
        atol=1e-14,
    )
    np.testing.assert_allclose(
        calculate_log_lambda_ii(temperature_ev / 1000.0, density_m3, charge),
        expected_ii,
        rtol=0,
        atol=1e-14,
    )

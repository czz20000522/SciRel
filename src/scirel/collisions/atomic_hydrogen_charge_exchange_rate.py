"""Atomic-H charge-exchange rate coefficient.

Through ``2.01e4 eV`` in both temperature and impact energy, this module
retains the legacy nine-by-nine bivariate logarithmic fit.  When either input
is above that domain, it integrates the continuous composite cross section
against an equal-mass Maxwellian relative-speed distribution.  The high-energy
quadrature omits collision energies above the ``2.5e5 eV`` cross-section table
limit; that boundary is declared rather than extrapolated.
"""

from __future__ import annotations


import math

import numpy as np
from scipy.integrate import quad

from ._energy_input import (
    warn_above_fit,
    bivariate_log_fit,
    finite_nonnegative_energy,
    positive_real_array,
)
from .atomic_hydrogen_charge_exchange_cross_section import (
    _COMPOSITE_UPPER_EV,
    _composite_cross_section,
)
from .maxwellian_relative_speed_rate_average import AMU_KG, ELEMENTARY_CHARGE_C

__all__ = ["evaluate_atomic_hydrogen_charge_exchange_rate"]

_BIVARIATE_UPPER_EV = 2.01e4
_COEFFICIENTS = np.array(
    [
        [
            -1.829079581680e1,
            1.640252721210e-1,
            3.364564509137e-2,
            9.530225559189e-3,
            -8.519413589968e-4,
            -1.247583860943e-3,
            3.014307545716e-4,
            -2.499323170044e-5,
            6.932627237765e-7,
        ],
        [
            2.169137615703e-1,
            -1.106722014459e-1,
            -1.382158680424e-3,
            7.348786286628e-3,
            -6.343059502294e-4,
            -1.919569450380e-4,
            4.075019351738e-5,
            -2.850044983009e-6,
            6.966822400446e-8,
        ],
        [
            4.307131243894e-2,
            8.948693624917e-3,
            -1.209480567154e-2,
            -3.675019470470e-4,
            1.039643390686e-3,
            -1.553840717902e-4,
            2.670827249272e-6,
            7.695300597935e-7,
            -3.783302281524e-8,
        ],
        [
            -5.754895093075e-4,
            6.062141761233e-3,
            1.075907881928e-3,
            -8.119301728339e-4,
            8.911036876068e-6,
            3.175388949811e-5,
            -4.515123641755e-6,
            2.187439283954e-7,
            -2.911233951880e-9,
        ],
        [
            -1.552077120204e-3,
            -1.210431587568e-3,
            8.297212635856e-4,
            1.361661816974e-4,
            -1.008928628425e-4,
            1.080693990468e-5,
            5.106059413591e-7,
            -1.299275586093e-7,
            5.117133050290e-9,
        ],
        [
            -1.876800283030e-4,
            -4.052878751584e-5,
            -1.907025662962e-4,
            1.141663041636e-5,
            1.775681984457e-5,
            -3.149286923815e-6,
            3.105491554749e-8,
            2.274394089017e-8,
            -1.130988250912e-9,
        ],
        [
            1.125490270962e-4,
            2.875900435985e-5,
            1.338839628570e-5,
            -4.340802793033e-6,
            -7.003521917385e-7,
            2.318308730487e-7,
            -6.030983538280e-9,
            -1.755944926274e-9,
            1.005189187279e-10,
        ],
        [
            -1.238982763007e-5,
            -2.616998139678e-6,
            -1.171762874107e-7,
            3.517971869029e-7,
            -4.928692832866e-8,
            1.756388998863e-10,
            -1.446756795654e-10,
            7.143183138281e-11,
            -3.989884105603e-12,
        ],
        [
            4.163596197181e-7,
            7.558092849125e-8,
            -1.328404104165e-8,
            -9.170850253981e-9,
            3.208853883734e-9,
            -3.952740758950e-10,
            2.739558475782e-11,
            -1.693040208927e-12,
            6.388219930167e-14,
        ],
    ],
    dtype=float,
)


def _relative_speed_distribution(speed, beam_speed):
    """Return the equal-mass Maxwellian relative-speed density in normalized units."""
    if beam_speed < 1.0e-8:
        return 4.0 * speed**2 / math.sqrt(math.pi) * math.exp(-(speed**2))
    return (
        speed
        / (math.sqrt(math.pi) * beam_speed)
        * (math.exp(-((speed - beam_speed) ** 2)) - math.exp(-((speed + beam_speed) ** 2)))
    )


def _rate_from_composite_cross_section(temperature_ev, energy_ev):
    """Integrate the composite cross section against one Maxwellian target."""
    beam_speed = 0.0 if energy_ev == 0.0 else math.sqrt(energy_ev / temperature_ev)
    speed_limit = math.sqrt(_COMPOSITE_UPPER_EV / temperature_ev)

    def integrand(speed):
        collision_energy = temperature_ev * speed**2
        if collision_energy > _COMPOSITE_UPPER_EV:
            return 0.0
        cross_section = float(_composite_cross_section(max(collision_energy, 0.1)))
        return _relative_speed_distribution(speed, beam_speed) * cross_section * speed

    if beam_speed < 1.0e-8:
        integral, _error = quad(
            integrand,
            0.0,
            speed_limit,
            epsabs=0.0,
            epsrel=1.0e-10,
            limit=300,
        )
    else:
        split = min(beam_speed, speed_limit)
        left, left_error = quad(
            integrand,
            0.0,
            split,
            epsabs=0.0,
            epsrel=1.0e-10,
            limit=300,
        )
        right, right_error = quad(
            integrand,
            split,
            speed_limit,
            epsabs=0.0,
            epsrel=1.0e-10,
            limit=300,
        )
        integral = left + right
        _error = left_error + right_error

    thermal_speed = math.sqrt(2.0 * ELEMENTARY_CHARGE_C * temperature_ev / AMU_KG)
    return thermal_speed * integral


def evaluate_atomic_hydrogen_charge_exchange_rate(temperature_ev, energy_ev):
    """Return the H + H+ charge-exchange rate in m^3/s on paired samples.

    The existing nine-by-nine bivariate fit is retained for temperatures and
    impact energies up to ``2.01e4 eV``.  If either sample is above that fit
    domain, the result is obtained by integrating the continuous composite
    cross section against an equal-mass Maxwellian target.  The composite
    cross section is tabulated through ``2.5e5 eV``; larger collision energies
    are omitted from the integral.

    Parameters
    ----------
    temperature_ev
        Positive plasma temperatures in eV, as a scalar or array.
    energy_ev
        Nonnegative impact energies in eV with the same shape as
        ``temperature_ev``.

    Returns
    -------
    numpy.ndarray
        Rate coefficients in ``m^3/s`` with the paired input shape.

    Raises
    ------
    ValueError
        If inputs are non-real, non-finite, have unequal shapes, contain a
        nonpositive temperature or negative energy, or produce a non-finite or
        nonpositive rate.
    """
    temperature = positive_real_array(temperature_ev, "temperature_ev")
    energy = finite_nonnegative_energy(energy_ev)
    if temperature.shape != energy.shape:
        raise ValueError("temperature_ev and energy_ev must have the same shape")

    warn_above_fit(
        energy,
        _COMPOSITE_UPPER_EV,
        "evaluate_atomic_hydrogen_charge_exchange_rate",
        effect="uses the clipped upper edge for the Maxwellian integral",
    )
    warn_above_fit(
        temperature,
        _COMPOSITE_UPPER_EV,
        "evaluate_atomic_hydrogen_charge_exchange_rate",
        "temperature",
        effect="uses the clipped upper edge for the Maxwellian integral",
    )
    low_temperature = np.minimum(np.maximum(temperature, 0.1), _BIVARIATE_UPPER_EV)
    low_energy = np.minimum(np.maximum(energy, 0.1), _BIVARIATE_UPPER_EV)
    rate = np.asarray(
        np.exp(bivariate_log_fit(np.log(low_energy), np.log(low_temperature), _COEFFICIENTS))
        * 1.0e-6,
        dtype=float,
    )
    high_mask = (temperature > _BIVARIATE_UPPER_EV) | (energy > _BIVARIATE_UPPER_EV)
    high_temperature = np.minimum(np.maximum(temperature, 0.1), _COMPOSITE_UPPER_EV)
    high_energy = np.minimum(np.maximum(energy, 0.1), _COMPOSITE_UPPER_EV)
    for index in np.ndindex(rate.shape):
        if bool(high_mask[index]):
            rate[index] = _rate_from_composite_cross_section(
                float(high_temperature[index]), float(high_energy[index])
            )
    if not bool(np.all(np.isfinite(rate))) or np.any(rate <= 0.0):
        raise ValueError(
            "atomic hydrogen charge-exchange evaluation produced a non-finite or nonpositive rate"
        )
    return rate

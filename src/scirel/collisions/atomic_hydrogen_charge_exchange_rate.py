"""Atomic-H charge-exchange rate coefficient from a clipped bivariate fit.

This is a fit in temperature and impact energy, not a Maxwellian integral of
the separately exposed atomic-H charge-exchange cross section.
"""

from __future__ import annotations



import numpy as np

from ._energy_input import bivariate_log_fit, finite_nonnegative_energy, positive_real_array

__all__ = ["evaluate_atomic_hydrogen_charge_exchange_rate"]

_COEFFICIENTS = np.array(
    [
        [-1.829079581680e1, 1.640252721210e-1, 3.364564509137e-2, 9.530225559189e-3, -8.519413589968e-4, -1.247583860943e-3, 3.014307545716e-4, -2.499323170044e-5, 6.932627237765e-7],
        [2.169137615703e-1, -1.106722014459e-1, -1.382158680424e-3, 7.348786286628e-3, -6.343059502294e-4, -1.919569450380e-4, 4.075019351738e-5, -2.850044983009e-6, 6.966822400446e-8],
        [4.307131243894e-2, 8.948693624917e-3, -1.209480567154e-2, -3.675019470470e-4, 1.039643390686e-3, -1.553840717902e-4, 2.670827249272e-6, 7.695300597935e-7, -3.783302281524e-8],
        [-5.754895093075e-4, 6.062141761233e-3, 1.075907881928e-3, -8.119301728339e-4, 8.911036876068e-6, 3.175388949811e-5, -4.515123641755e-6, 2.187439283954e-7, -2.911233951880e-9],
        [-1.552077120204e-3, -1.210431587568e-3, 8.297212635856e-4, 1.361661816974e-4, -1.008928628425e-4, 1.080693990468e-5, 5.106059413591e-7, -1.299275586093e-7, 5.117133050290e-9],
        [-1.876800283030e-4, -4.052878751584e-5, -1.907025662962e-4, 1.141663041636e-5, 1.775681984457e-5, -3.149286923815e-6, 3.105491554749e-8, 2.274394089017e-8, -1.130988250912e-9],
        [1.125490270962e-4, 2.875900435985e-5, 1.338839628570e-5, -4.340802793033e-6, -7.003521917385e-7, 2.318308730487e-7, -6.030983538280e-9, -1.755944926274e-9, 1.005189187279e-10],
        [-1.238982763007e-5, -2.616998139678e-6, -1.171762874107e-7, 3.517971869029e-7, -4.928692832866e-8, 1.756388998863e-10, -1.446756795654e-10, 7.143183138281e-11, -3.989884105603e-12],
        [4.163596197181e-7, 7.558092849125e-8, -1.328404104165e-8, -9.170850253981e-9, 3.208853883734e-9, -3.952740758950e-10, 2.739558475782e-11, -1.693040208927e-12, 6.388219930167e-14],
    ],
    dtype=float,
)


def evaluate_atomic_hydrogen_charge_exchange_rate(temperature_ev, energy_ev):
    """Return the H + H+ charge-exchange fit in m^3/s on paired samples."""
    temperature = positive_real_array(temperature_ev, "temperature_ev")
    energy = finite_nonnegative_energy(energy_ev)
    if temperature.shape != energy.shape:
        raise ValueError("temperature_ev and energy_ev must have the same shape")

    clipped_temperature = np.minimum(np.maximum(temperature, 0.1), 2.01e4)
    clipped_energy = np.minimum(np.maximum(energy, 0.1), 2.01e4)
    log_temperature = np.log(clipped_temperature)
    log_energy = np.log(clipped_energy)
    log_rate = bivariate_log_fit(log_energy, log_temperature, _COEFFICIENTS)
    rate = np.exp(log_rate) * 1.0e-6
    if not np.all(np.isfinite(rate)) or np.any(rate <= 0.0):
        raise ValueError("atomic hydrogen charge-exchange fit produced a non-finite or nonpositive rate")
    return rate

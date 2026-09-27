"""FIDASIM colrad rate-matrix assembly from explicit transition tables.

Source: FIDASIM ``get_rate_matrix`` (the saved package
``碰撞辐射速率矩阵组装``) -- assemble the real collisional-radiative rate
matrix for one cell from explicit plasma densities and three transition
tables.  Preserved verbatim: the ``log10(E_b/A_b)`` and temperature table
coordinates, the source-order bilinear interpolation with low-rate
thresholds (rates below ``minlog`` become zero, and an index beyond the
upper table edge yields zero rates for that table), the same-mass
fast-ion density addition, and the Einstein column-sum diagonal rewrite
with off-diagonal population terms.

Registered hardenings against the saved arm: non-finite densities,
masses, temperatures or table contents pass the saved comparisons
silently and propagate NaN into the matrix, and ``exp`` of extreme table
entries can overflow; the assembled matrix must stay finite.
"""
from __future__ import annotations

import numpy as np

__all__ = ["assemble_collisional_radiative_rate_matrix"]


def _interpolate_transition(table, log_energy, log_temperature, density):
    try:
        pop = np.asarray(table["log_pop"], dtype=float)
        depop = np.asarray(table["log_depop"], dtype=float)
        nenergy, ntemperature = int(table["nenergy"]), int(table["ntemp"])
        logemin, logtmin = float(table["logemin"]), float(table["logtmin"])
        dlogE, dlogT = float(table["dlogE"]), float(table["dlogT"])
        minlog_pop, minlog_depop = float(table["minlog_pop"]), float(table["minlog_depop"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("transition table mapping must provide the declared finite fields") from exc
    if (pop.ndim != 4 or depop.shape != (pop.shape[0], nenergy, ntemperature)
            or not np.all(np.isfinite(pop)) or not np.all(np.isfinite(depop))
            or not all(np.isfinite(value) for value in (logemin, logtmin, dlogE, dlogT, minlog_pop, minlog_depop))):
        raise ValueError("transition table shapes must be (level, level, energy, temperature) and (level, energy, temperature) with finite entries")
    energy = max(log_energy, logemin)
    temperature = max(log_temperature, logtmin)
    i = np.floor((energy - logemin) / dlogE)
    j = np.floor((temperature - logtmin) / dlogT)
    if not (dlogE > 0.0 and dlogT > 0.0 and np.isfinite(i) and np.isfinite(j)
            and 0 <= i < nenergy - 1 and 0 <= j < ntemperature - 1):
        return (np.zeros(pop.shape[:2]), np.zeros(pop.shape[0]))
    i, j = int(i), int(j)
    x = (energy - (logemin + i * dlogE)) / dlogE
    y = (temperature - (logtmin + j * dlogT)) / dlogT
    values = ((1-x)*(1-y)*pop[:, :, i, j] + (1-x)*y*pop[:, :, i, j+1] + x*(1-y)*pop[:, :, i+1, j] + x*y*pop[:, :, i+1, j+1])
    loss = ((1-x)*(1-y)*depop[:, i, j] + (1-x)*y*depop[:, i, j+1] + x*(1-y)*depop[:, i+1, j] + x*y*depop[:, i+1, j+1])
    result_pop = np.where(values < minlog_pop, 0.0, density * np.exp(values * np.log(10.0)))
    result_loss = np.where(loss < minlog_depop, 0.0, density * np.exp(loss * np.log(10.0)))
    # Registered hardening: extreme table entries overflow exp to Inf.
    if not (np.all(np.isfinite(result_pop)) and np.all(np.isfinite(result_loss))):
        raise ValueError(
            "transition rates overflow to non-finite values for finite but "
            "extreme table entries (registered hardening)")
    return result_pop, result_loss


def assemble_collisional_radiative_rate_matrix(thermal_density_cm3, thermal_mass_amu, ion_temperature_kev, electron_density_cm3, electron_temperature_kev, impurity_density_cm3, fast_ion_density_cm3, beam_mass_amu, beam_energy_kev, hydrogen_table, electron_table, impurity_table, einstein_s_inv):
    """Assemble the source real rate matrix from explicit plasma and table contracts."""
    density, mass = np.asarray(thermal_density_cm3, float), np.asarray(thermal_mass_amu, float)
    einstein = np.asarray(einstein_s_inv, float)
    if (density.ndim != 1 or mass.shape != density.shape or einstein.ndim != 2
            or einstein.shape[0] != einstein.shape[1] or np.any(density < 0.0)
            or not np.all(np.isfinite(density)) or not np.all(np.isfinite(mass))
            or np.any(mass <= 0.0) or not np.all(np.isfinite(einstein))):
        raise ValueError("thermal species and einstein matrix shapes are invalid")
    if (not all(np.isfinite(value) for value in (ion_temperature_kev, electron_density_cm3,
                                                 electron_temperature_kev, impurity_density_cm3,
                                                 fast_ion_density_cm3, beam_mass_amu, beam_energy_kev))
            or min(ion_temperature_kev, electron_temperature_kev, beam_mass_amu, beam_energy_kev) <= 0.0
            or electron_density_cm3 < 0.0 or impurity_density_cm3 < 0.0 or fast_ion_density_cm3 < 0.0):
        raise ValueError("temperatures, densities, beam mass, and beam energy must be finite and valid")
    population = np.zeros_like(einstein)
    depopulation = np.zeros(einstein.shape[0])
    log_beam_per_amu = np.log10(beam_energy_kev / beam_mass_amu)
    for number_density, ion_mass in zip(density, mass):
        effective_density = number_density + (fast_ion_density_cm3 if beam_mass_amu == ion_mass else 0.0)
        pop, depop = _interpolate_transition(hydrogen_table, log_beam_per_amu, np.log10(ion_temperature_kev / ion_mass), effective_density)
        population += pop; depopulation += depop
    for table, temperature, number_density in ((electron_table, electron_temperature_kev, electron_density_cm3), (impurity_table, ion_temperature_kev, impurity_density_cm3)):
        pop, depop = _interpolate_transition(table, log_beam_per_amu, np.log10(temperature), number_density)
        population += pop; depopulation += depop
    result = einstein + population
    np.fill_diagonal(result, -np.sum(einstein, axis=0) - depopulation)
    # Registered hardening: the assembled matrix must stay finite.
    if not np.all(np.isfinite(result)):
        raise ValueError(
            "rate matrix is non-finite for finite but extreme input "
            "magnitudes (registered hardening)")
    return result

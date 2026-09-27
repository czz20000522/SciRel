"""Source-faithful FIDASIM get_dd_rate table interpolation.

Source: FIDASIM ``get_dd_rate`` -- bilinear interpolation of a log10 rate
table in (beam energy, ion temperature) with a per-branch third axis, then
``rate = density * 10^log_rate``.  Out-of-table beam energies/temperatures
below the axis minima clamp to the first cell; beyond the last interval the
source returns 0 (recorded behavior, preserved).  ``branch_index`` is
zero-based here (the source's branch 2 corresponds to 1).

Registered hardening: the exponentiated result must stay finite; the saved
arm would return Inf for finite but extreme table values.
"""
from __future__ import annotations

import numpy as np

__all__ = ["dd_reaction_rate_per_s"]


def dd_reaction_rate_per_s(*, beam_energy_kev, ion_temperature_kev, deuterium_target_density_cm3,
                           energy_log_min, energy_log_step, temperature_log_min,
                           temperature_log_step, log_rate_table, min_log_rate,
                           branch_index=1):
    """Return source-shaped DD rate; branch_index is zero-based (source branch 2 -> 1)."""
    table = np.asarray(log_rate_table, dtype=float)
    scalars = (beam_energy_kev, ion_temperature_kev, deuterium_target_density_cm3,
               energy_log_min, energy_log_step, temperature_log_min,
               temperature_log_step, min_log_rate)
    if (table.ndim != 3 or table.shape[0] < 2 or table.shape[1] < 2
            or isinstance(branch_index, bool)
            or not isinstance(branch_index, (int, np.integer))
            or not 0 <= branch_index < table.shape[2]):
        raise ValueError("log_rate_table must have shape (n_energy>=2,n_temperature>=2,n_branch) and a valid branch_index")
    if (not np.all(np.isfinite(table)) or not all(np.isfinite(x) for x in scalars)
            or beam_energy_kev <= 0 or ion_temperature_kev <= 0
            or deuterium_target_density_cm3 < 0
            or energy_log_step <= 0 or temperature_log_step <= 0):
        raise ValueError("finite positive energy, temperature and axis steps plus nonnegative density are required")
    x = max(np.log10(beam_energy_kev), energy_log_min)
    y = max(np.log10(ion_temperature_kev), temperature_log_min)
    u, v = (x - energy_log_min) / energy_log_step, (y - temperature_log_min) / temperature_log_step
    i, j = int(np.floor(u)), int(np.floor(v))
    if i < 0 or j < 0 or i >= table.shape[0] - 1 or j >= table.shape[1] - 1:
        return 0.0
    fu, fv = u - i, v - j
    rate_log = ((1 - fu) * (1 - fv) * table[i, j, branch_index]
                + fu * (1 - fv) * table[i + 1, j, branch_index]
                + (1 - fu) * fv * table[i, j + 1, branch_index]
                + fu * fv * table[i + 1, j + 1, branch_index])
    if rate_log < min_log_rate:
        return 0.0
    rate = float(deuterium_target_density_cm3 * np.exp(rate_log * np.log(10.0)))
    # Registered hardening: a finite table can exponentiate to Inf; the saved
    # arm returns it silently.
    if not np.isfinite(rate):
        raise ValueError(
            "DD rate overflowed to a non-finite value for finite but extreme "
            "table contents (registered hardening)")
    return rate

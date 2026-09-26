"""Explicit scalar thermal-speed scale for neutral species.

One leaf recovered from the saved KN1DPy ``热速度标度换算`` package (source
anchor ``KN1DPy/kinetic_h2.py:1360-1371``, the temperature/mass combination
of the source-entry dual-branch graphs, as recorded by the saved bundle's own
provenance section), integrated as :func:`compute_thermal_speed_m_s`:

the explicit second-moment thermal speed scale
``sqrt(2 e T_ev / (m_amu * m_H))`` with the source's frozen constants
(``m_H = 1.6726231e-27`` kg, ``e = 1.602177e-19`` J/eV).  This is the same
``Vth`` the already-integrated r59 sibling
``scirel.kinetic.hydrogen-saha-equilibrium-population`` does not consume and
that the axisymmetric moment reduction and boundary-flux normalization
relations below use internally.

**No repair is claimed.**  The saved formal implementation enforces its
declared contract (finite positive scalar temperature and mass, finite
positive result) and is reproduced bit for bit, messages included.

Evidence ceiling: this module establishes the scalar relation against an
independent recomputation with the frozen constants, the mass monotonicity,
and -- in the environment-gated replay test -- exact agreement with the saved
KN1DPy implementation.  The saved bundle's strict D1 qualification has been
withdrawn; that replay is historical development evidence, not qualified-L1
provenance.
"""
from __future__ import annotations

import math

__all__ = [
    "compute_thermal_speed_m_s",
]

_HYDROGEN_MASS_KG = 1.6726231e-27
_ELECTRON_VOLT_J = 1.602177e-19


def compute_thermal_speed_m_s(temperature_ev, mass_amu):
    """Return ``{'thermal_speed_m_s': v}`` with ``v = sqrt(2 e T / m)``.

    Parameters
    ----------
    temperature_ev
        Temperature in eV: a finite strictly positive scalar.
    mass_amu
        Particle mass in amu (as a multiple of the hydrogen mass): a finite
        strictly positive scalar.

    Returns
    -------
    dict
        ``{'thermal_speed_m_s': float}``, finite and strictly positive.

    Raises
    ------
    ValueError
        If either scalar is non-finite or nonpositive, or the result is not
        finite and positive.
    """
    temperature = float(temperature_ev)
    mass = float(mass_amu)
    if not math.isfinite(temperature) or temperature <= 0.0:
        raise ValueError("temperature_ev must be finite and positive")
    if not math.isfinite(mass) or mass <= 0.0:
        raise ValueError("mass_amu must be finite and positive")
    value = math.sqrt(2.0 * _ELECTRON_VOLT_J * temperature / (mass * _HYDROGEN_MASS_KG))
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("thermal speed must be finite and positive")
    return {"thermal_speed_m_s": value}

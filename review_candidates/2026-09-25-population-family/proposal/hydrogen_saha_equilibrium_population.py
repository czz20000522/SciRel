"""Atomic-hydrogen Saha equilibrium population density.

One leaf recovered from the saved KN1DPy ``nh_saha`` slice (source anchor
``KN1DPy/jh_related/nh_saha.py:25-46``), integrated as
:func:`evaluate_h_saha_equilibrium_population`:

the Saha equilibrium population density of atomic-hydrogen principal level
``n`` in ``m^-3``, formed from the paired electron density and electron
temperature with the saved source's frozen constants (Saha constant
``3.310e-28`` and ionization energy ``13.6057 eV``):
``n * (Saha * n) * n_level^2 * exp(chi / (n_level^2 T)) / T^1.5``.

**The saved formal contract is kept exactly, with no repair.**  The source
fills a ``1e32`` sentinel on its non-scientific branches; the saved formal
implementation exposes only the positive finite scientific branch and rejects
inputs outside it, so the sentinel is never promoted to data.  This module
reproduces that contract bit for bit: non-empty one-dimensional paired arrays,
finite and strictly positive density and temperature below the ``1e32``
domain limits, a principal level that is a scalar integer >= 1, and a result
that must be finite and strictly positive.  This is the one leaf in the
hydrogen-population family whose saved implementation already enforced its
declared document, so no repair is claimed.

Evidence ceiling: this module establishes the Saha relation against an
independent evaluation with the same frozen constants, the principal-level
scaling, the domain and failure contracts, and -- in the environment-gated
replay test -- exact agreement with the saved KN1DPy implementation including
its rejection behavior.  The saved bundle's strict D1 qualification has been
withdrawn; that replay is historical development evidence, not qualified-L1
provenance.  No test establishes the Saha model against an external
atomic-physics reference: the saved package records that residual as
``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "evaluate_h_saha_equilibrium_population",
]

_DENSITY_LIMIT_M3 = 1.0e32
_TEMPERATURE_LIMIT_EV = 1.0e32
_SAHA_CONSTANT = 3.310e-28
_IONIZATION_ENERGY_EV = 13.6057


def evaluate_h_saha_equilibrium_population(electron_density_m3, electron_temperature_ev, principal_level):
    """Return the source ``nh_saha`` equilibrium population density in m^-3.

    Parameters
    ----------
    electron_density_m3
        Electron densities in ``m^-3`` as a non-empty one-dimensional array;
        must be finite, strictly positive and below ``1e32``.
    electron_temperature_ev
        Electron temperatures in eV, a one-dimensional array of the same
        shape; must be finite, strictly positive and below ``1e32``.
    principal_level
        The atomic principal level ``n``: a scalar integer >= 1 (booleans and
        non-integral values are rejected).

    Returns
    -------
    numpy.ndarray
        Equilibrium population densities in ``m^-3`` with the inputs' shape.
        Finite and strictly positive for every accepted input; the source's
        ``1e32`` sentinel is never returned.

    Raises
    ------
    ValueError
        If the arrays are not non-empty, one-dimensional and of equal shape,
        contain non-finite values, leave the scientific domain (nonpositive
        or ``>= 1e32``), if ``principal_level`` is not a scalar integer >= 1,
        or if the computed population is not finite and positive.
    """
    density = np.asarray(electron_density_m3, dtype=float)
    temperature = np.asarray(electron_temperature_ev, dtype=float)
    if density.ndim != 1 or temperature.ndim != 1 or density.size == 0:
        raise ValueError("electron density and temperature must be non-empty one-dimensional arrays")
    if density.shape != temperature.shape:
        raise ValueError("electron density and temperature must have the same shape")
    if not np.all(np.isfinite(density)) or not np.all(np.isfinite(temperature)):
        raise ValueError("electron density and temperature must be finite")

    level_array = np.asarray(principal_level)
    if level_array.ndim != 0 or isinstance(principal_level, (bool, np.bool_)):
        raise ValueError("principal_level must be a scalar integer")
    level_value = float(level_array)
    if not np.isfinite(level_value) or not level_value.is_integer() or level_value < 1:
        raise ValueError("principal_level must be an integer >= 1")
    level = int(level_value)

    if np.any(density <= 0.0) or np.any(density >= _DENSITY_LIMIT_M3):
        raise ValueError("electron density is outside the source scientific domain")
    if np.any(temperature <= 0.0) or np.any(temperature >= _TEMPERATURE_LIMIT_EV):
        raise ValueError("electron temperature is outside the source scientific domain")

    level_squared = float(level * level)
    result = (
        density
        * (_SAHA_CONSTANT * density)
        * level_squared
        * np.exp(_IONIZATION_ENERGY_EV / (level_squared * temperature))
        / (temperature**1.5)
    )
    if not np.all(np.isfinite(result)) or np.any(result <= 0.0):
        raise ValueError("Saha population is not finite and positive for the supplied inputs")
    return result

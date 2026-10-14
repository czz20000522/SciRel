"""H+-on-H elastic momentum-transfer fit in m^2.

The input is projectile proton laboratory energy in eV with target H at rest.
The KN1D IDL primary sigma_el_p_h.pro uses E <= 10 eV for the low-energy
polynomial and E > 10 eV for the high-energy polynomial. This repairs the
Python translation's zero at exactly 10 eV; the original failure is preserved
in the scientific-correction receipt. The two empirical fits are not forced
continuous. Endpoint clipping [0.001, 1.01e5] eV and the leading singleton
output axis remain explicit. Fit fidelity does not establish accuracy outside
the cited experimental/model range or grant redistribution approval.
"""
from __future__ import annotations

import numpy as np

from ._energy_input import finite_nonnegative_energy

__all__ = [
    "evaluate_hydrogen_proton_elastic_cross_section",
]

_LOW_ENERGY_COEFFICIENTS = np.array(
    [-3.233966e1, -1.126918e-1, 5.287706e-3, -2.445017e-3, -1.044156e-3, 8.419691e-5, 3.824773e-5],
    dtype=float,
)
_HIGH_ENERGY_COEFFICIENTS = np.array([-3.231141e1, -1.386002e-1], dtype=float)


def evaluate_hydrogen_proton_elastic_cross_section(energy_ev):
    """Return the source H+-on-H elastic cross section in square metres.

    Parameters
    ----------
    energy_ev
        Collision energies in eV, as a scalar or array of any shape.  Values
        must be finite and nonnegative; energies outside the fit range are
        clipped to the range endpoints, the saved source's declared behavior.

    Returns
    -------
    numpy.ndarray
        Cross sections in ``m^2`` with one extra leading singleton axis
        compared with the input (the saved source's ``np.array([E])``
        wrapper convention). Exactly 10 eV uses the low polynomial; accepted
        values are positive and finite. The empirical breakpoint may jump.

    Raises
    ------
    ValueError
        If ``energy_ev`` contains a non-real, non-finite or negative value.
    """
    energy = finite_nonnegative_energy(energy_ev)
    clipped = np.clip(energy, 0.001, 1.01e5)
    result = np.zeros_like(clipped, dtype=float)
    low = clipped <= 10.0
    high = clipped > 10.0
    if np.any(low):
        result[low] = np.exp(
            np.polynomial.polynomial.polyval(np.log(clipped[low]), _LOW_ENERGY_COEFFICIENTS)
        ) * 1.0e-4
    if np.any(high):
        result[high] = np.exp(
            np.polynomial.polynomial.polyval(np.log(clipped[high]), _HIGH_ENERGY_COEFFICIENTS)
        ) * 1.0e-4
    return result[np.newaxis, ...]

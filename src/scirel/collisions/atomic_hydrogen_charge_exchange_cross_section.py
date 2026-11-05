"""Atomic-hydrogen charge-exchange cross-section fits.

The default relation is continuous over its declared domain: the Janev
nine-coefficient logarithmic polynomial below ``1.267317514018116e4 eV`` and
the Lindsay--Stebbings 2005 Table 1 fit above it through ``2.5e5 eV``.  The
Freeman--Jones analytic branch remains available as an independent comparison
through ``1e5 eV``.

Lindsay and Stebbings, JGR 110, A12213 (2005), Table 1 and section 4.1, define
the high-energy formula, its 5 eV--250 keV table range, and its stated
reliability.  The tests bind the formulas, their continuous crossing, the
source-range sampled values, endpoint warnings and the input contract.  They do
not claim a new experimental fit beyond that published parameterization.
"""

from __future__ import annotations


import numpy as np

from ._energy_input import clipped_energy, log_polynomial, warn_above_fit

__all__ = [
    "evaluate_atomic_hydrogen_charge_exchange_cross_section",
]

_JANE_COEFFICIENTS = np.array(
    [
        -3.274123792568e1,
        -8.916456579806e-2,
        -3.016990732025e-2,
        9.205482406462e-3,
        2.400266568315e-3,
        -1.927122311323e-3,
        3.654750340106e-4,
        -2.788866460622e-5,
        7.422296363524e-7,
    ]
)
_COMPOSITE_JOIN_EV = 1.267317514018116e4
_COMPOSITE_UPPER_EV = 2.5e5
_FREEMAN_UPPER_EV = 1.0e5


def _janev_cross_section(energy_ev):
    return np.exp(log_polynomial(np.log(energy_ev), _JANE_COEFFICIENTS)) * 1.0e-4


def _lindsay_stebbings_cross_section(energy_ev):
    energy_kev = np.asarray(energy_ev, dtype=float) / 1000.0
    log_energy = np.log(energy_kev)
    return (4.15 - 0.531 * log_energy) ** 2 * (1.0 - np.exp(-67.3 / energy_kev)) ** 4.5 * 1.0e-20


def _composite_cross_section(energy_ev):
    energy = np.asarray(energy_ev, dtype=float)
    janev = _janev_cross_section(energy)
    lindsay_stebbings = _lindsay_stebbings_cross_section(energy)
    return np.where(energy <= _COMPOSITE_JOIN_EV, janev, lindsay_stebbings)


def evaluate_atomic_hydrogen_charge_exchange_cross_section(energy_ev, freeman=False):
    """Return the H + H+ charge-exchange cross section in m^2.

    Parameters
    ----------
    energy_ev
        Collision energies in eV, as a scalar or array of any shape.  Values
        must be finite and nonnegative; energies outside a branch's fit range
        are clipped to that range's endpoints.
    freeman
        Scalar branch selector.  ``True`` selects the Freeman--Jones analytic
        fit with the ``[0.1, 1e5] eV`` clip.  The default selects the continuous
        Janev/Lindsay--Stebbings composite with the ``[0.1, 2.5e5] eV`` clip.
        Any scalar is interpreted as its truth value; arrays are rejected.

    Returns
    -------
    numpy.ndarray
        Cross sections in ``m^2`` with the input's shape.  Finite and strictly
        positive for every accepted input, because both fits are evaluated
        only on their clipped positive domains.

    Raises
    ------
    ValueError
        If ``energy_ev`` contains a non-real, non-finite or negative value, or if
        ``freeman`` is not a scalar.

    Notes
    -----
    The default uses the Janev polynomial through
    ``12673.17514018116 eV`` and the Lindsay--Stebbings fit

    ``(4.15 - 0.531 ln E_keV)^2 * (1 - exp(-67.3 / E_keV))^4.5 * 1e-20 m^2``

    above that crossing.  The fits agree at the join.  The Lindsay--Stebbings
    table spans ``0.005-250 keV`` and states about 11% reliability above 6 keV.

    References
    ----------
    Lindsay, B. G., and R. F. Stebbings (2005), Charge transfer cross sections
    for energetic neutral atom data analysis, JGR 110, A12213,
    doi:10.1029/2005JA011298, Table 1 and section 4.1.
    """
    selector = np.asarray(freeman)
    if selector.ndim != 0:
        raise ValueError("freeman must be a scalar branch selector, not an array")
    upper = _FREEMAN_UPPER_EV if bool(selector) else _COMPOSITE_UPPER_EV
    energy = clipped_energy(energy_ev, 0.1, upper)
    warn_above_fit(energy_ev, upper, "evaluate_atomic_hydrogen_charge_exchange_cross_section")
    if bool(selector):
        return (
            1.0e-4
            * 0.6937e-14
            * (1.0 - 0.155 * np.log10(energy)) ** 2
            / (1.0 + 0.1112e-14 * energy**3.3)
        )
    return _composite_cross_section(energy)

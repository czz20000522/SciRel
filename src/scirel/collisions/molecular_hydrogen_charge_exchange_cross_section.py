"""Molecular-hydrogen charge-exchange cross-section fit.

One leaf recovered from the saved KN1DPy ``sigma_cx_hh`` slice (source anchor
``KN1DPy/sigma/sigma_cx_hh.py:5-23`` with the shared polynomial evaluation
``KN1DPy/sigma/poly.py:3-10``; direct caller ``KN1DPy/kinetic_h2.py:1036-1049``),
integrated as
:func:`evaluate_molecular_hydrogen_charge_exchange_cross_section`:

the H2 + H2+ charge-exchange cross section in ``m^2`` as a function of the
collision energy in eV -- a Janev nine-coefficient logarithmic polynomial,
``exp(polyval(log(E), a)) * 1e-4``, evaluated on the source-clipped domain
``[0.1, 2.01e4] eV``.

**The fit domain is source-clipped, and the clipping is declared.**  Endpoint
values repeat outside the fit's range.  This is the saved source's declared
behavior, exercised by its package tests, and is kept unchanged.

**Input-contract repairs relative to the saved implementation.**  The saved
document declares the energy nonnegative, but its implementation silently
clipped negative energies to the lower endpoint; this module rejects them.
Non-real energies, including numeric strings and boolean cells, are also
rejected before float conversion.  The arithmetic is preserved on finite
nonnegative real inputs.

Evidence ceiling: this module establishes the clipped fit against an
independent evaluation of the same formula, the endpoint clipping, the input
and failure contracts, these repairs, and -- in the environment-gated replay
test -- exact agreement with the saved KN1DPy implementation on the declared
domain.  The saved bundle's strict D1 qualification has been withdrawn; that
replay is historical development evidence, not qualified-L1 provenance.  No
test establishes the fit against an external physical cross-section
reference: the saved package records that residual as ``validation_oracle_gap``.
This module evaluates no velocity mesh, no rate coefficient and no transport
source; those are separate relations.
"""
from __future__ import annotations

import numpy as np

from ._energy_input import finite_nonnegative_energy

__all__ = [
    "evaluate_molecular_hydrogen_charge_exchange_cross_section",
]

_COEFFICIENTS = np.array([
    -3.427958758517e1,
    -7.121484125189e-2,
    4.690466187943e-2,
    -8.033946660540e-3,
    -2.265090924593e-3,
    -2.102414848737e-4,
    1.948869487515e-4,
    -2.208124950005e-5,
    7.262446915488e-7,
])


def evaluate_molecular_hydrogen_charge_exchange_cross_section(energy_ev):
    """Return the H2 + H2+ charge-exchange cross section in m^2.

    Parameters
    ----------
    energy_ev
        Collision energies in eV, as a scalar or array of any shape.  Values
        must be finite and nonnegative; energies outside the fit range are
        clipped to the range endpoints, the saved source's declared behavior.

    Returns
    -------
    numpy.ndarray
        Cross sections in ``m^2`` with the input's shape.  Finite and strictly
        positive for every accepted input, because the fit is evaluated only
        on its clipped positive domain.

    Raises
    ------
    ValueError
        If ``energy_ev`` contains a non-real, non-finite or negative value.
    """
    energy = finite_nonnegative_energy(energy_ev)
    clipped = np.clip(energy, 0.1, 2.01e4)
    log_energy = np.log(clipped)
    log_sigma = np.polynomial.polynomial.polyval(log_energy, _COEFFICIENTS)
    return np.exp(log_sigma) * 1.0e-4

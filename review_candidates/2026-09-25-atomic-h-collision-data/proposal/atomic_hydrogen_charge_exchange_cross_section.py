"""Atomic-hydrogen charge-exchange cross-section fits.

One leaf recovered from the saved KN1DPy ``sigma_cx_h0`` slice (source anchor
``KN1DPy/sigma/sigma_cx_h0.py:7-32`` with the shared polynomial evaluation
``KN1DPy/poly.py:3-10``), integrated as
:func:`evaluate_atomic_hydrogen_charge_exchange_cross_section`:

the H + H+ charge-exchange cross section in ``m^2`` as a function of the
collision energy in eV.  The default branch is Janev's nine-coefficient
logarithmic polynomial, ``exp(polyval(log(E), a)) * 1e-4``; ``freeman=True``
selects the Freeman--Jones analytic fit
``1e-4 * 0.6937e-14 * (1 - 0.155 log10(E))^2 / (1 + 0.1112e-14 E^3.3)``.

**The fit domain is source-clipped, and the clipping is declared.**  The Janev
branch clips energies to ``[0.1, 2.01e4] eV`` and the Freeman--Jones branch to
``[0.1, 1e5] eV`` before evaluation, so endpoint values are repeated outside
each fit's range.  This is the saved source's declared behavior, exercised by
its package tests, and is kept unchanged.

**Two repairs relative to the saved implementation, both documented.**  The
saved document declares the energy nonnegative, but its implementation
silently clipped negative energies to the lower endpoint; this module rejects
them.  The saved document declares the ``freeman`` branch selector a scalar,
but its implementation reduced arbitrary arrays with ``np.any``; this module
requires a scalar and rejects arrays.  The rejection domain is otherwise
unchanged, and the two branches' arithmetic is preserved bit for bit on the
declared domain.

Evidence ceiling: this module establishes the two clipped fits against an
independent evaluation of the same formulas, the endpoint clipping, the input
and failure contracts, the two repairs, and -- in the environment-gated replay
test -- exact agreement with the saved KN1DPy implementation on the declared
domain.  The saved bundle's strict D1 qualification has been withdrawn; that
replay is historical development evidence, not qualified-L1 provenance.  No
test establishes the fits against an external physical cross-section
reference: the saved package records that residual as ``validation_oracle_gap``.
This module evaluates no velocity mesh, no rate coefficient and no transport
source; those are separate relations.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "evaluate_atomic_hydrogen_charge_exchange_cross_section",
]

_JANE_COEFFICIENTS = np.array([
    -3.274123792568e1, -8.916456579806e-2, -3.016990732025e-2,
    9.205482406462e-3, 2.400266568315e-3, -1.927122311323e-3,
    3.654750340106e-4, -2.788866460622e-5, 7.422296363524e-7,
])


def evaluate_atomic_hydrogen_charge_exchange_cross_section(energy_ev, freeman=False):
    """Return the H + H+ charge-exchange cross section in m^2.

    Parameters
    ----------
    energy_ev
        Collision energies in eV, as a scalar or array of any shape.  Values
        must be finite and nonnegative; energies outside a branch's fit range
        are clipped to that range's endpoints, the saved source's declared
        behavior.
    freeman
        Scalar branch selector.  ``True`` selects the Freeman--Jones analytic
        fit with the ``[0.1, 1e5] eV`` clip; the default selects the Janev
        logarithmic polynomial with the ``[0.1, 2.01e4] eV`` clip.  Any scalar
        is interpreted as its truth value; arrays are rejected.

    Returns
    -------
    numpy.ndarray
        Cross sections in ``m^2`` with the input's shape.  Finite and strictly
        positive for every accepted input, because both fits are evaluated
        only on their clipped positive domains.

    Raises
    ------
    ValueError
        If ``energy_ev`` contains a non-finite or negative value, or if
        ``freeman`` is not a scalar.
    """
    energy = np.asarray(energy_ev, dtype=float)
    if not np.all(np.isfinite(energy)):
        raise ValueError("energy_ev must be finite")
    if bool(np.any(energy < 0.0)):
        raise ValueError("energy_ev must be nonnegative")
    selector = np.asarray(freeman)
    if selector.ndim != 0:
        raise ValueError("freeman must be a scalar branch selector, not an array")
    if bool(selector):
        clipped = np.clip(energy, 0.1, 1.0e5)
        return 1.0e-4 * 0.6937e-14 * (1.0 - 0.155 * np.log10(clipped)) ** 2 / (1.0 + 0.1112e-14 * clipped**3.3)
    clipped = np.clip(energy, 0.1, 2.01e4)
    return np.exp(np.polynomial.polynomial.polyval(np.log(clipped), _JANE_COEFFICIENTS)) * 1.0e-4

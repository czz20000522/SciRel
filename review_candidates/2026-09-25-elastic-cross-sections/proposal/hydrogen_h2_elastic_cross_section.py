"""H-on-H2 elastic momentum-transfer cross-section fit.

One leaf recovered from the saved KN1DPy ``sigma_el_h_hh`` slice (source
anchor ``KN1DPy/sigma/sigma_el_h_hh.py:1-31``, caller
``KN1DPy/kinetic_h.py:970-984``), integrated as
:func:`evaluate_hydrogen_h2_elastic_cross_section`:

the H-on-H2 elastic momentum-transfer cross section in ``m^2`` as a function
of the collision energy in eV -- a single five-coefficient logarithmic
polynomial, ``exp(polyval(log(E), a)) * 1e-4``, evaluated on the
source-clipped domain ``[0.03, 1.01e4]`` eV.

**Two declared source behaviors are kept exactly.**  The endpoint clipping
repeats values outside the range, and the output shape preserves the source
``np.array([E])`` wrapper: the result carries one extra leading singleton axis
compared with the input.  The saved document's boilerplate instead declares
the output shaped like the input; this module keeps the implementation's
documented behavior and declares it explicitly, and the discrepancy is
recorded as an expert-review question rather than silently resolved.

**One repair relative to the saved implementation, documented.**  The saved
document declares the energy nonnegative, but its implementation silently
clipped negative energies to the lower endpoint; this module rejects them.
The rejection domain is otherwise unchanged and the arithmetic is preserved
bit for bit on the declared domain.

Evidence ceiling: this module establishes the clipped fit against an
independent evaluation of the same formula, the leading axis, the endpoint
clipping, the input and failure contracts, the repair, and -- in the
environment-gated replay test -- exact agreement with the saved KN1DPy
implementation on the declared domain.  The saved bundle's strict D1
qualification has been withdrawn; that replay is historical development
evidence, not qualified-L1 provenance.  No test establishes the fit against an
external physical cross-section reference: the saved package records that
residual as ``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "evaluate_hydrogen_h2_elastic_cross_section",
]

_COEFFICIENTS = np.array(
    [-3.495671e1, -4.062257e-1, -3.820531e-2, -9.404486e-3, 3.963723e-4],
    dtype=float,
)


def evaluate_hydrogen_h2_elastic_cross_section(energy_ev):
    """Return the source H-on-H2 elastic cross section in square metres.

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
        compared with the input (the saved source's ``np.array([E])`` wrapper
        convention).  Finite and strictly positive for every accepted input.

    Raises
    ------
    ValueError
        If ``energy_ev`` contains a non-finite or negative value.
    """
    energy = np.asarray(energy_ev, dtype=float)
    if not np.all(np.isfinite(energy)):
        raise ValueError("energy_ev must be finite")
    if bool(np.any(energy < 0.0)):
        raise ValueError("energy_ev must be nonnegative")
    clipped = np.clip(energy, 0.03, 1.01e4)
    result = np.exp(
        np.polynomial.polynomial.polyval(np.log(clipped), _COEFFICIENTS)
    ) * 1.0e-4
    return result[np.newaxis, ...]

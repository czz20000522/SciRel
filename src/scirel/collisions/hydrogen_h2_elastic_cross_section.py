"""H-on-H2 elastic momentum-transfer cross-section fit.

One leaf recovered from the saved the neutral-transport formulation ``sigma_el_h_hh`` slice, integrated as
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

**Input-contract repairs relative to the saved implementation.**  The saved
document declares the energy nonnegative, but its implementation silently
clipped negative energies to the lower endpoint; this module rejects them.
Non-real energies, including numeric strings and boolean cells, are also
rejected before float conversion.  The arithmetic is preserved on finite
nonnegative real inputs.

Evidence ceiling: this module establishes the clipped fit against an
independent evaluation of the same formula, the leading axis, the endpoint
clipping, the input and failure contracts, these repairs, and -- in the
environment-gated replay test -- exact agreement with the saved the neutral-transport formulation
implementation on the declared domain.  The saved bundle's strict D1
qualification has been withdrawn; that replay is historical development
evidence, not qualified-L1 provenance.  No test establishes the fit against an
external physical cross-section reference: the saved package records that
residual as ``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np

from ._energy_input import clipped_energy, log_polynomial

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
        If ``energy_ev`` contains a non-real, non-finite or negative value.
    """
    clipped = clipped_energy(energy_ev, 0.03, 1.01e4)
    result = np.exp(log_polynomial(np.log(clipped), _COEFFICIENTS)) * 1.0e-4
    return result[np.newaxis, ...]

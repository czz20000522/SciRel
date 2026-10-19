"""H2-on-H+ elastic momentum-transfer cross-section fit.

One leaf recovered from the saved KN1DPy ``sigma_el_p_hh`` slice (source
anchor ``KN1DPy/sigma/sigma_el_p_hh.py:1-31``, caller
``KN1DPy/kinetic_h2.py:1070-1093``), integrated as
:func:`evaluate_hydrogen2_proton_elastic_cross_section`:

the H2-on-H+ elastic momentum-transfer cross section in ``m^2`` as a function
of the collision energy in eV -- a single five-coefficient logarithmic
polynomial, ``exp(polyval(log(E), a)) * 1e-4``, evaluated on the
source-clipped domain ``[0.03, 1.01e4]`` eV.  Endpoint values repeat outside
the range, the saved source's declared behavior.

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
test establishes the fit against an external physical cross-section reference:
the saved package records that residual as ``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np

from ._energy_input import clipped_energy, log_polynomial

__all__ = [
    "evaluate_hydrogen2_proton_elastic_cross_section",
]

_COEFFICIENTS = np.array(
    [-3.355719e1, -5.696568e-1, -4.089556e-2, -1.143513e-2, 5.926596e-4],
    dtype=float,
)


def evaluate_hydrogen2_proton_elastic_cross_section(energy_ev):
    """Return the source H2-on-H+ elastic cross section in square metres.

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
        positive for every accepted input.

    Raises
    ------
    ValueError
        If ``energy_ev`` contains a non-real, non-finite or negative value.
    """
    clipped = clipped_energy(energy_ev, 0.03, 1.01e4)
    log_sigma = log_polynomial(np.log(clipped), _COEFFICIENTS)
    return np.exp(log_sigma) * 1.0e-4

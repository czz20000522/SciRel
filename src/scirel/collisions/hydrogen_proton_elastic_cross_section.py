"""H+-on-H elastic momentum-transfer cross-section fit.

One leaf recovered from the saved KN1DPy ``sigma_el_p_h`` slice (source anchor
``KN1DPy/sigma/sigma_el_p_h.py:1-42``, caller ``KN1DPy/kinetic_h.py:996-1016``),
integrated as :func:`evaluate_hydrogen_proton_elastic_cross_section`:

the H+-on-H elastic momentum-transfer cross section in ``m^2`` as a function
of the collision energy in eV -- a distinct logarithmic polynomial below and
above the 10 eV breakpoint, both scaled by ``1e-4``, evaluated on the
source-clipped domain ``[0.001, 1.01e5]`` eV.

**Two declared source behaviors are kept exactly.**  First, the breakpoint:
the source selects branches with strict inequalities, so a clipped energy of
exactly 10 eV stays exactly zero -- neither branch includes the breakpoint.
Second, the output shape: the source wraps its input as ``np.array([E])``, so
the saved formal implementation returns one extra leading singleton axis
compared with the input (a one-dimensional input of shape ``(n,)`` yields
``(1, n)``).  The saved document's boilerplate instead declares the output
shaped like the input; this module keeps the implementation's documented
behavior and declares it explicitly, and the discrepancy is recorded as an
expert-review question rather than silently resolved in either direction.

**One repair relative to the saved implementation, documented.**  The saved
document declares the energy nonnegative, but its implementation silently
clipped negative energies to the lower endpoint; this module rejects them.
The rejection domain is otherwise unchanged and the arithmetic is preserved
bit for bit on the declared domain.

Evidence ceiling: this module establishes the piecewise fit against an
independent evaluation of the same formulas, the breakpoint zero, the leading
axis, the endpoint clipping, the input and failure contracts, the repair, and
-- in the environment-gated replay test -- exact agreement with the saved
KN1DPy implementation on the declared domain.  The saved bundle's strict D1
qualification has been withdrawn; that replay is historical development
evidence, not qualified-L1 provenance.  No test establishes the fit against an
external physical cross-section reference: the saved package records that
residual as ``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np

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
        wrapper convention).  A clipped energy of exactly 10 eV is exactly
        zero, the source's strict-branch breakpoint behavior; all other
        accepted values are strictly positive and finite.

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
    clipped = np.clip(energy, 0.001, 1.01e5)
    result = np.zeros_like(clipped, dtype=float)
    low = clipped < 10.0
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

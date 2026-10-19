"""Atomic-hydrogen elastic cross-section fits.

One leaf recovered from the saved KN1DPy ``sigma_el_h_h`` slice (source anchor
``KN1DPy/sigma/sigma_el_h_h.py:19-38``, caller ``KN1DPy/kinetic_h.py:957``),
integrated as :func:`evaluate_atomic_hydrogen_elastic_cross_section`:

the H-on-H elastic cross section in ``m^2`` as a function of the collision
energy in eV.  The default branch is the source's five-coefficient
momentum-transfer fit; ``viscosity=True`` selects the source's distinct
five-coefficient viscosity fit.  Both branches use the source energy clipping
interval ``[0.03, 1.01e4]`` eV, ``exp(polyval(log(E), a)) * 1e-4``.

**The fit domain is source-clipped, and the clipping is declared.**  Endpoint
values repeat outside the range.  This is the saved source's declared behavior,
exercised by its package tests, and is kept unchanged.

**Input-contract repairs relative to the saved implementation.**  The
saved document declares the energy nonnegative, but its implementation
silently clipped negative energies to the lower endpoint; this module rejects
them.  The saved document declares the ``viscosity`` selector a scalar, but
its implementation relied on ``bool()`` coercion, which silently accepted
zero-dimensional and single-element arrays and failed on multi-element arrays
with NumPy's generic ambiguity error that does not name the quantity; this
module requires a zero-dimensional scalar and names the quantity.  The port
also rejects non-real energies, including numeric strings and boolean
cells, before float conversion.  Both branches' arithmetic is preserved on
finite nonnegative real inputs.

Evidence ceiling: this module establishes both clipped fits against
independent evaluations of the same formulas, the endpoint clipping, the input
and failure contracts, these repairs, and -- in the environment-gated replay
test -- exact agreement with the saved KN1DPy implementation on the declared
domain.  The saved bundle's strict D1 qualification has been withdrawn; that
replay is historical development evidence, not qualified-L1 provenance.  No
test establishes either fit against an external physical cross-section
reference: the saved package records that residual as ``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np

from ._energy_input import clipped_energy, log_polynomial

__all__ = [
    "evaluate_atomic_hydrogen_elastic_cross_section",
]

_MOMENTUM_TRANSFER_COEFFICIENTS = np.array(
    [-3.330843e1, -5.738374e-1, -1.028610e-1, -3.920980e-3, 5.964135e-4],
    dtype=float,
)
_VISCOSITY_COEFFICIENTS = np.array(
    [-3.344860e1, -4.238982e-1, -7.477873e-2, -7.915053e-3, -2.686129e-4],
    dtype=float,
)


def evaluate_atomic_hydrogen_elastic_cross_section(energy_ev, viscosity=False):
    """Return the source H-on-H elastic cross section in square metres.

    Parameters
    ----------
    energy_ev
        Collision energies in eV, as a scalar or array of any shape.  Values
        must be finite and nonnegative; energies outside the fit range are
        clipped to the range endpoints, the saved source's declared behavior.
    viscosity
        Scalar branch selector.  ``True`` selects the source viscosity fit;
        the default selects the momentum-transfer fit.  A zero-dimensional
        array is accepted as the scalar; any other array is rejected.

    Returns
    -------
    numpy.ndarray
        Cross sections in ``m^2`` with the input's shape.  Finite and strictly
        positive for every accepted input, because both fits are evaluated
        only on their clipped positive domain.

    Raises
    ------
    ValueError
        If ``energy_ev`` contains a non-real, non-finite or negative value, or if
        ``viscosity`` is not a scalar.
    """
    energy = clipped_energy(energy_ev, 0.03, 1.01e4)
    selector = np.asarray(viscosity)
    if selector.ndim != 0:
        raise ValueError("viscosity must be a scalar branch selector, not an array")
    clipped = energy
    coefficients = _VISCOSITY_COEFFICIENTS if bool(selector) else _MOMENTUM_TRANSFER_COEFFICIENTS
    return np.exp(log_polynomial(np.log(clipped), coefficients)) * 1.0e-4

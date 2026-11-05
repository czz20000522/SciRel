"""Molecular-hydrogen charge-exchange cross-section fit.

One leaf recovered from the saved the neutral-transport formulation ``sigma_cx_hh`` slice,
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
test -- exact agreement with the saved the neutral-transport formulation implementation on the declared
domain.  The saved bundle's strict D1 qualification has been withdrawn; that
replay is historical development evidence, not qualified-L1 provenance.  No
test establishes the fit against an external physical cross-section
reference: the saved package records that residual as ``validation_oracle_gap``.
This module evaluates no velocity mesh, no rate coefficient and no transport
source; those are separate relations.
"""

from __future__ import annotations


import numpy as np

from ._energy_input import clipped_energy, log_polynomial

__all__ = [
    "evaluate_molecular_hydrogen_charge_exchange_cross_section",
]

_COEFFICIENTS = np.array(
    [
        -3.427958758517e1,
        -7.121484125189e-2,
        4.690466187943e-2,
        -8.033946660540e-3,
        -2.265090924593e-3,
        -2.102414848737e-4,
        1.948869487515e-4,
        -2.208124950005e-5,
        7.262446915488e-7,
    ]
)


def evaluate_molecular_hydrogen_charge_exchange_cross_section(energy_ev):
    """Evaluate the H2 + H2+ charge-exchange cross section.

    Parameters
    ----------
    energy_ev : real scalar or array-like
        Collision energy. [eV] Shape: ``scalar or array``. The value must be finite
        and nonnegative. Values outside ``[0.1, 2.01e4]`` eV are clipped to the
        range endpoints.

    Returns
    -------
    cross_section_m2 : numpy.ndarray
        H2 + H2+ charge-exchange cross section. [m^2] Shape: ``same as
        energy_ev``. Every returned value is finite and strictly positive.

    Raises
    ------
    ValueError
        If ``energy_ev`` is not real numeric, is non-finite or is negative.

    See Also
    --------
    evaluate_atomic_hydrogen_charge_exchange_cross_section : The distinct H + H+
        charge-exchange relation.
    evaluate_hydrogen2_charge_exchange_rate : The molecular bivariate rate fit.
    average_cross_section_over_maxwellian : Accepts a compatible cross-section
        callable as an input port.

    Notes
    -----
    The relation uses one nine-coefficient logarithmic polynomial,
    ``exp(polyval(log(E_clipped), a)) * 1e-4``, on the clipped fit interval.
    Endpoint clipping is silent and intentional. The frozen fit is non-monotonic
    between about 978 and 8291 eV, so monotonicity is not promised. No external
    atomic-physics oracle is bound.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import evaluate_molecular_hydrogen_charge_exchange_cross_section, evaluate_atomic_hydrogen_charge_exchange_cross_section
    >>> energy = np.array([0.1, 1.0, 10.0, 100.0, 1.0e3, 1.0e4, 2.01e4])
    >>> cross_section = evaluate_molecular_hydrogen_charge_exchange_cross_section(energy)
    >>> assert cross_section.shape == energy.shape
    >>> assert np.all(np.isfinite(cross_section)) and np.all(cross_section > 0.0)
    >>> clipped = evaluate_molecular_hydrogen_charge_exchange_cross_section(np.array([0.01, 0.1, 3.0e4, 2.01e4]))
    >>> assert clipped[0] == clipped[1] and clipped[-1] == clipped[-2]
    >>> atomic = evaluate_atomic_hydrogen_charge_exchange_cross_section(energy)
    >>> assert not np.allclose(cross_section, atomic, rtol=1e-12, atol=0.0)
    >>> try:
    ...     evaluate_molecular_hydrogen_charge_exchange_cross_section(np.array([1.0, -0.5]))
    ... except ValueError as error:
    ...     assert 'nonnegative' in str(error)
    ... else:
    ...     raise AssertionError('a negative energy must be rejected')
    """
    clipped = clipped_energy(energy_ev, 0.1, 2.01e4)
    log_sigma = log_polynomial(np.log(clipped), _COEFFICIENTS)
    return np.exp(log_sigma) * 1.0e-4

"""Molecular-hydrogen charge-exchange cross-section fit.

Evaluate the H2 + H2+ charge-exchange cross section in ``m^2`` from collision
energy in ``eV`` using one Janev nine-coefficient logarithmic polynomial,
``exp(polyval(log(E_clipped), a)) * 1e-4``, on ``[0.1, 2.01e4] eV``.

**Boundary semantics.**  A positive input below the lower fit endpoint returns
the lower endpoint silently.  A positive input above the upper fit endpoint
returns the upper endpoint and emits one ``RuntimeWarning``; it is a declared
model limit, not an extrapolation.  Negative energies are rejected before
evaluation.  The fit is non-monotonic between about 978 and 8291 eV, so
monotonicity is not promised.

Evidence ceiling: tests establish this relation against an independent
evaluation of the same formula, endpoint behavior, warnings, and input/failure
contracts.  No external atomic-physics oracle is bound.  This callable
evaluates no velocity mesh, rate coefficient, or transport source; those are
separate relations.
"""

from __future__ import annotations


import numpy as np

from ._energy_input import clipped_energy, log_polynomial, warn_above_fit

__all__ = [
    "evaluate_molecular_hydrogen_charge_exchange_cross_section",
]

_FIT_LOWER_EV = 0.1
_FIT_UPPER_EV = 2.01e4
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
        and nonnegative. Values below ``0.1 eV`` are clipped to that endpoint
        silently. Values above ``2.01e4 eV`` are clipped to that endpoint and emit
        ``RuntimeWarning``.

    Returns
    -------
    cross_section_m2 : numpy.ndarray
        H2 + H2+ charge-exchange cross section. [m^2] Shape: ``same as
        energy_ev``. Every returned value is finite and strictly positive.

    Raises
    ------
    ValueError
        If ``energy_ev`` is not real numeric, is non-finite or is negative.

    Warns
    -----
    RuntimeWarning
        If a requested energy is above ``2.01e4 eV``. The returned value is the
        endpoint value, not an extrapolation.

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
    The frozen fit is non-monotonic between about 978 and 8291 eV, so
    monotonicity is not promised. No external atomic-physics oracle is bound.

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
    raw_energy = clipped_energy(energy_ev, _FIT_LOWER_EV, np.inf)
    warn_above_fit(
        raw_energy,
        _FIT_UPPER_EV,
        "evaluate_molecular_hydrogen_charge_exchange_cross_section",
    )
    energy = clipped_energy(raw_energy, _FIT_LOWER_EV, _FIT_UPPER_EV)
    log_sigma = log_polynomial(np.log(energy), _COEFFICIENTS)
    return np.exp(log_sigma) * 1.0e-4

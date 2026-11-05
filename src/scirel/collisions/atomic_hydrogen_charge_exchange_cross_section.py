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
    """Evaluate the H + H+ charge-exchange cross section.

    Parameters
    ----------
    energy_ev : real scalar or array-like
        Laboratory collision energy. [eV] Shape: ``scalar or array``. The value
        must be finite and nonnegative. Values below ``0.1`` eV clip silently to
        ``0.1`` eV. The default upper limit is ``2.5e5`` eV; the Freeman-Jones
        upper limit is ``1e5`` eV.
    freeman : scalar, optional
        Branch selector. [dimensionless] Shape: ``scalar``. The default ``False``
        selects the continuous Janev/Lindsay-Stebbings composite; a truthy scalar
        selects the independent Freeman-Jones branch. Arrays are rejected.

    Returns
    -------
    cross_section_m2 : numpy.ndarray
        Charge-exchange cross section for each accepted energy. [m^2] Shape:
        ``same as energy_ev``. Every returned value is finite and strictly
        positive on the selected clipped branch.

    Raises
    ------
    ValueError
        If ``energy_ev`` is not real numeric, is non-finite or is negative, or if
        ``freeman`` is not a scalar branch selector.
    RuntimeWarning
        If a requested energy is above the selected branch's upper limit. The
        returned value is the endpoint value and is not extrapolated.

    See Also
    --------
    evaluate_atomic_hydrogen_charge_exchange_rate : Integrates the default
        composite cross section above its low-energy fit domain.
    evaluate_molecular_hydrogen_charge_exchange_cross_section : The distinct
        H2 + H2+ charge-exchange relation.
    average_cross_section_over_maxwellian : Accepts a compatible cross-section
        callable as an input port.

    Notes
    -----
    The default relation uses the Janev polynomial below the continuous crossing
    at ``12673.17514018116`` eV and the Lindsay-Stebbings 2005 Table 1 fit above
    it. The high-energy formula is

    ``(4.15 - 0.531 * ln(E_keV))**2
    * (1 - exp(-67.3 / E_keV))**4.5 * 1e-20 m^2``.

    The default high-energy endpoint is 250 keV and emits ``RuntimeWarning`` above
    that range. The Freeman-Jones branch is an independent comparison fit through
    100 keV, not the default. The Lindsay-Stebbings table starts at 5 eV, so the
    low-energy Janev portion below 5 eV is not validated by that table.

    References
    ----------
    Lindsay, B. G., and R. F. Stebbings (2005), Charge transfer cross sections
    for energetic neutral atom data analysis, JGR 110, A12213,
    doi:10.1029/2005JA011298, Table 1 and section 4.1.

    Examples
    --------
    >>> import warnings
    >>> import numpy as np
    >>> from scirel.collisions import evaluate_atomic_hydrogen_charge_exchange_cross_section
    >>> energy = np.array([0.1, 1.0, 10.0, 1.0e4, 1.267317514018116e4, 3.0e4, 1.0e5])
    >>> composite = evaluate_atomic_hydrogen_charge_exchange_cross_section(energy)
    >>> assert composite.shape == energy.shape
    >>> assert np.all(np.isfinite(composite)) and np.all(composite > 0.0)
    >>> freeman = evaluate_atomic_hydrogen_charge_exchange_cross_section(energy, freeman=True)
    >>> assert np.all(np.isfinite(freeman)) and np.all(freeman > 0.0)
    >>> with warnings.catch_warnings(record=True) as caught:
    ...     warnings.simplefilter('always')
    ...     clipped = evaluate_atomic_hydrogen_charge_exchange_cross_section(np.array([0.01, 0.1, 3.0e5, 2.5e5]))
    >>> assert len(caught) == 1 and issubclass(caught[0].category, RuntimeWarning)
    >>> assert clipped[0] == clipped[1] and clipped[-1] == clipped[-2]
    >>> try:
    ...     evaluate_atomic_hydrogen_charge_exchange_cross_section(np.array([1.0, -0.5]))
    ... except ValueError as error:
    ...     assert 'nonnegative' in str(error)
    ... else:
    ...     raise AssertionError('a negative energy must be rejected')
    >>> try:
    ...     evaluate_atomic_hydrogen_charge_exchange_cross_section(energy, freeman=np.ones((2, 2)))
    ... except ValueError as error:
    ...     assert 'freeman' in str(error)
    ... else:
    ...     raise AssertionError('an array branch selector must be rejected')
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

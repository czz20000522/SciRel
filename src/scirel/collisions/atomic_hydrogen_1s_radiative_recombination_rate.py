"""H(1s) radiative recombination rate from the saved analytic fit."""

from __future__ import annotations

import warnings

import numpy as np

from scirel import ApplicabilityWarning

from ._energy_input import positive_real_array

__all__ = ["evaluate_atomic_hydrogen_1s_radiative_recombination_rate"]

_RY_EV = 13.58
_LEVEL_N = 1.0
_A_NL = 3.92
_X_NL = 0.35
# Declared validated interval of the fit: within it the rate agrees with an independent
# Stobbe (1930) photoionization cross section combined with the Milne relation to 5% or
# better (issue #10, comment 6773932012). The fit form itself switches asymptotic branch
# near 38.8 eV and falls as T^-1.5 far above it, where the exact rate keeps falling more
# slowly, so values above the interval understate the true rate by 37% at 1 keV and about
# 2.0-2.1x at 10-20 keV.
_VALIDATED_LOW_EV = 0.1
_VALIDATED_HIGH_EV = 30.0
_FIT_LOW_EV = 0.1
_FIT_HIGH_EV = 2.01e4


def evaluate_atomic_hydrogen_1s_radiative_recombination_rate(electron_temperature_ev):
    """Evaluate the H(1s) radiative-recombination rate coefficient.

    Parameters
    ----------
    electron_temperature_ev : real scalar or array-like
        Electron temperature. [eV] Shape: ``scalar or array``. The value must be
        finite and strictly positive. Positive values outside ``[0.1, 2.01e4]`` eV
        are clipped to the nearest endpoint.

    Returns
    -------
    rate_m3_s : numpy.ndarray
        H(1s) radiative-recombination rate coefficient for
        ``H+ + e -> H(1s) + hv``. [m^3/s] Shape: ``same as
        electron_temperature_ev``. The dtype is float64 and every returned value is
        finite and strictly positive.

    Raises
    ------
    ValueError
        If ``electron_temperature_ev`` is not real numeric, is non-finite or is
        nonpositive, or if the evaluated fit is not finite and strictly positive.
    ApplicabilityWarning
        Emitted rather than raised, and listed here because the contract's
        ``failure_semantics`` names it: any input temperature above ``30 eV``
        returns the fit's own value at that temperature with this warning (see
        Warns), never an exception.

    Warns
    -----
    ApplicabilityWarning
        If any input temperature is above ``30 eV``, the upper end of the
        interval in which this fit is validated. Above 30 eV the fit's own value
        at that temperature is still returned (the fit interval itself is
        ``[0.1, 2.01e4] eV``), and it understates the true rate: about 37% low at
        1 keV and a factor of about 2.0-2.1 low at 10-20 keV, so recombination
        rates built from it are biased low, not merely coarse.

    See Also
    --------
    evaluate_janev_electron_impact_ionization_rate : Electron-impact ionization
        rate fits for H and H2.
    evaluate_atomic_hydrogen_charge_exchange_rate : Atomic-hydrogen
        charge-exchange rate coefficient.
    average_cross_section_over_maxwellian : General mesh-based Maxwellian
        average of a caller-supplied cross section.

    Notes
    -----
    This is the level-one Storey-type analytic fit with fixed ``Ry=13.58`` eV,
    ``n=1``, ``A_nl=3.92`` and ``x_nl=0.35``. The relation evaluates

    ``A_nl * 1e-14 * sqrt(ionization_energy / Ry)
    * (b_n**1.5 / (b_n + x_nl)) * 1e-6``

    after clipping the temperature to the declared fit interval. Endpoint values
    repeat outside that interval. Excited-level, three-body and dielectronic
    recombination are separate relations. No external atomic-physics reference is
    bound by this callable.

    The fit is validated only on ``[0.1, 30] eV``, where it agrees with an
    independent oracle built from the exact H(1s) photoionization cross section
    (Stobbe 1930 closed form) combined with the Milne relation to 5.3% or better,
    the largest departure being at the 0.1 eV edge (fit/oracle ratios 0.947,
    0.965, 1.043 and 1.049 at 0.1, 1, 10 and 30 eV, so at most 4.9% from 1 eV up),
    and that oracle
    reproduces Osterbrock & Ferland (2006) Table 2.1 (alpha_1 = 1.58e-13 cm^3/s
    at 1e4 K). Above 30 eV the fit's ``b**1.5/(b+x)`` form has already switched
    to its ``T**-1.5`` asymptotic branch while the exact rate falls more slowly,
    so the ratio leaves the 5% band and keeps falling. Values above 30 eV are
    returned (clipped to the fit interval) with a warning; they are not
    extrapolations the fit was built for.

    Examples
    --------
    >>> import warnings
    >>> import numpy as np
    >>> import scirel
    >>> from scirel.collisions import evaluate_atomic_hydrogen_1s_radiative_recombination_rate
    >>> t = np.array([0.01, 1.0, 50000.0])
    >>> with warnings.catch_warnings(record=True) as caught:
    ...     warnings.simplefilter('always')
    ...     r = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(t)
    ...     edge = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(
    ...         np.array([0.1, 1.0, 20100.0])
    ...     )
    >>> assert r.shape == (3,) and np.all(np.isfinite(r)) and np.all(r > 0.0)
    >>> assert np.array_equal(r, edge)
    >>> # one warning per out-of-range call: the 50000 eV sample and the 20100 eV one
    >>> assert len(caught) == 2 and issubclass(caught[0].category, scirel.ApplicabilityWarning)
    """
    temperature = positive_real_array(electron_temperature_ev, "electron_temperature_ev")
    clipped = np.minimum(np.maximum(temperature, 0.1), 2.01e4)
    if np.any(temperature > _VALIDATED_HIGH_EV):
        highest = float(np.max(temperature))
        warnings.warn(
            "evaluate_atomic_hydrogen_1s_radiative_recombination_rate: electron temperature above"
            f" the validated limit of {_VALIDATED_HIGH_EV:g} eV (highest input {highest:.6g} eV)"
            " returns the fit's own value at that temperature and understates the true H(1s)"
            " radiative-recombination rate: about 37% low at 1 keV and a factor of about 2.0-2.1 low"
            " at 10-20 keV"
            " (scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient)",
            ApplicabilityWarning,
            stacklevel=2,
        )
    ionization_energy_ev = _RY_EV / _LEVEL_N
    b_n = ionization_energy_ev / clipped
    rate = (
        _A_NL
        * 1.0e-14
        * np.sqrt(ionization_energy_ev / _RY_EV)
        * (b_n**1.5 / (b_n + _X_NL))
        * 1.0e-6
    )
    if not np.all(np.isfinite(rate)) or np.any(rate <= 0.0):
        raise ValueError(
            "H(1s) radiative recombination fit produced a non-finite or nonpositive rate"
        )
    return rate

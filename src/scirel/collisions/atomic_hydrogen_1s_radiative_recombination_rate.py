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
# Declared validated interval of the fit. Accuracy is measured against an independent oracle
# (Stobbe 1930 photoionization closed form + Milne relation with g_n/g_+ = 2): the observed
# worst departure on a 601-point log grid over [0.1, 30] eV is 5.72% at about 19.5 eV, so the
# declared bound is 5.75% and the earlier 5.3% claim is refuted by the 20 eV point (+5.715%).
# The fit form itself switches asymptotic branch near 38.8 eV and falls as T^-1.5 far above,
# where the exact rate keeps falling more slowly, so values above the interval understate the
# true rate by 37% at 1 keV and about 2.0-2.1x at 10-20 keV. Below 0.1 eV the endpoint value
# returned understates the exact rate, by about 3.4x at 0.01 eV.
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
    ApplicabilityWarning
        If any input temperature is below ``0.1 eV``, the fit's own lower limit.
        Such samples return the 0.1 eV endpoint value, which understates the true
        rate: the independent Stobbe-Milne oracle is about 3.4 times the returned
        value at 0.01 eV, so the bias grows as the input falls below the limit.

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

    The fit is validated only on ``[0.1, 30] eV``. Its accuracy there is
    measured against an independent oracle: the exact H(1s) photoionization cross
    section (Stobbe 1930 closed form) combined with the Milne relation, with the
    level-one statistical weight ratio ``g_n/g_+ = 2`` and a Maxwell average. That
    oracle gives ``1.581929e-13 cm^3/s`` at 1e4 K, consistent with the
    ``1.58e-13 cm^3/s`` commonly quoted for this rate (the printed table itself
    was not re-checked, see the contract's limitations).

    The observed worst departure on a 601-point logarithmic grid over
    ``[0.1, 30] eV`` is **5.72%** at about 19.5 eV (fit/oracle ratios 0.9473,
    0.9648, 1.0433, 1.0572 and 1.0491 at 0.1, 1, 10, 20 and 30 eV). That is an
    observed maximum on the sampled grid, not a proof of a continuous upper
    bound, so the declared envelope is ``5.75%`` over the interval; the earlier
    ``5.3%`` claim is refuted by the 20 eV point (+5.715%). Above 30 eV the
    fit's ``b**1.5/(b+x)`` form has already switched to its ``T**-1.5``
    asymptotic branch while the exact rate falls more slowly, so the departure
    keeps growing. Values above 30 eV, and below 0.1 eV, are returned at the fit
    interval's endpoints with a warning; they are not extrapolations.

    Examples
    --------
    >>> import warnings
    >>> import numpy as np
    >>> import scirel
    >>> from scirel.collisions import evaluate_atomic_hydrogen_1s_radiative_recombination_rate
    >>> t = np.array([0.1, 1.0, 50000.0])
    >>> with warnings.catch_warnings(record=True) as caught:
    ...     warnings.simplefilter('always')
    ...     r = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(t)
    >>> assert r.shape == (3,) and np.all(np.isfinite(r)) and np.all(r > 0.0)
    >>> # the 50000 eV sample is above the validated limit: one warning, value still returned
    >>> assert len(caught) == 1 and issubclass(caught[0].category, scirel.ApplicabilityWarning)
    >>> edge = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(np.array([0.1, 1.0]))
    >>> np.testing.assert_array_equal(r[:2], edge)
    >>> with warnings.catch_warnings(record=True) as low:
    ...     warnings.simplefilter('always')
    ...     clipped = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(
    ...         np.array([0.01, 20100.0])
    ...     )
    >>> # both ends clip to their interval endpoint, and both announced themselves
    >>> assert len(low) == 2 and np.all(clipped > 0.0)
    """
    temperature = positive_real_array(electron_temperature_ev, "electron_temperature_ev")
    clipped = np.minimum(np.maximum(temperature, 0.1), 2.01e4)
    if np.any(temperature < _VALIDATED_LOW_EV):
        lowest = float(np.min(temperature))
        warnings.warn(
            "evaluate_atomic_hydrogen_1s_radiative_recombination_rate: electron temperature below"
            f" the fit's lower limit of {_VALIDATED_LOW_EV:g} eV (lowest input {lowest:.6g} eV)"
            " returns the value at that limit, which understates the true H(1s)"
            " radiative-recombination rate: the exact Stobbe-Milne rate is about 3.4 times the"
            " returned value at 0.01 eV"
            " (scirel.collisions.atomic-hydrogen-1s-radiative-recombination-rate-coefficient)",
            ApplicabilityWarning,
            stacklevel=2,
        )
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

"""H(1s) radiative recombination rate from the saved analytic fit."""

from __future__ import annotations


import numpy as np

from ._energy_input import positive_real_array

__all__ = ["evaluate_atomic_hydrogen_1s_radiative_recombination_rate"]

_RY_EV = 13.58
_LEVEL_N = 1.0
_A_NL = 3.92
_X_NL = 0.35


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

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import evaluate_atomic_hydrogen_1s_radiative_recombination_rate
    >>> t = np.array([0.01, 1.0, 50000.0])
    >>> r = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(t)
    >>> edge = evaluate_atomic_hydrogen_1s_radiative_recombination_rate(np.array([0.1, 1.0, 20100.0]))
    >>> assert r.shape == (3,) and np.all(np.isfinite(r)) and np.all(r > 0.0)
    >>> assert np.array_equal(r, edge)
    """
    temperature = positive_real_array(electron_temperature_ev, "electron_temperature_ev")
    clipped = np.minimum(np.maximum(temperature, 0.1), 2.01e4)
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

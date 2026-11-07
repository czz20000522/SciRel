"""H2 charge-exchange rate coefficient from a clipped bivariate fit.

This molecular fit is distinct from the atomic-H fit and from explicit
Maxwellian integration of the separate molecular charge-exchange cross section.
"""

from __future__ import annotations


import numpy as np

from ._energy_input import (
    bivariate_log_fit,
    finite_nonnegative_energy,
    positive_real_array,
    warn_above_fit,
)

__all__ = ["evaluate_hydrogen2_charge_exchange_rate"]

_FIT_LOWER_EV = 0.1
_FIT_UPPER_EV = 2.01e4

_COEFFICIENTS = np.array(
    [
        [
            -2.013143517466e01,
            1.875197914224e-01,
            6.865479604288e-02,
            6.246595384100e-03,
            -5.017891372102e-03,
            -3.907644829287e-04,
            2.786239030986e-04,
            -2.942576591004e-05,
            9.352275354690e-07,
        ],
        [
            2.643458086299e-01,
            -1.177247941077e-01,
            -6.758032286178e-03,
            8.585003721992e-03,
            -3.261863407467e-04,
            -3.322528542186e-04,
            6.015471216449e-05,
            -4.039435357369e-06,
            9.730479674748e-08,
        ],
        [
            7.295645990688e-02,
            6.053418575149e-03,
            -1.068656224307e-02,
            -9.371235639464e-04,
            9.735708783528e-04,
            -9.933049259228e-05,
            -6.786246802840e-06,
            1.438327767305e-06,
            -5.530742535057e-08,
        ],
        [
            -1.022454343675e-02,
            7.350954380641e-03,
            6.814213275702e-04,
            -8.156435157073e-04,
            2.903991825737e-05,
            3.223596225946e-05,
            -5.199055182831e-06,
            2.852443990256e-07,
            -4.825480212106e-09,
        ],
        [
            -4.801198168030e-03,
            -1.111612877392e-03,
            8.373319888351e-04,
            1.392977576749e-04,
            -9.316910697276e-05,
            8.814981236658e-06,
            6.675626166047e-07,
            -1.325441927019e-07,
            5.012529587757e-09,
        ],
        [
            1.141613586234e-03,
            -1.371389288760e-04,
            -1.733761953296e-04,
            1.602610140599e-05,
            1.464235749797e-05,
            -2.944711701791e-06,
            6.365231650682e-08,
            1.872976659964e-08,
            -1.014883015867e-09,
        ],
        [
            -3.388853048483e-05,
            4.426148343648e-05,
            9.992317920676e-06,
            -5.333970870280e-06,
            -2.999105886511e-07,
            2.275612517364e-07,
            -1.173422836715e-08,
            -1.364602870139e-09,
            9.566404348683e-11,
        ],
        [
            -6.418225985394e-06,
            -3.652063962019e-06,
            1.351312819077e-07,
            4.285396408056e-07,
            -7.184302986068e-08,
            -3.265552364687e-10,
            1.585228996542e-10,
            6.431866226702e-11,
            -4.507074278992e-12,
        ],
        [
            3.555592819527e-07,
            1.012701361110e-07,
            -1.993091213299e-08,
            -1.131561847140e-08,
            3.678869095972e-09,
            -3.639982258214e-10,
            2.056662091085e-11,
            -1.804254277469e-12,
            9.042973335167e-14,
        ],
    ],
    dtype=float,
)


def evaluate_hydrogen2_charge_exchange_rate(temperature_ev, energy_ev):
    """Evaluate the H2 + H2+ charge-exchange rate fit on paired samples.

    Parameters
    ----------
    temperature_ev : real scalar or array-like
        Plasma temperature paired with each impact energy. [eV] Shape:
        ``scalar or array``. The value must be finite and strictly positive.
        Values below ``0.1 eV`` are clipped to that endpoint silently. Values
        above ``2.01e4 eV`` are clipped to that endpoint and emit
        ``RuntimeWarning``.
    energy_ev : real scalar or array-like
        Impact energy paired with each temperature. [eV] Shape: ``same as
        temperature_ev``. The value must be finite and nonnegative. Values
        below ``0.1 eV`` are clipped to that endpoint silently. Values above
        ``2.01e4 eV`` are clipped to that endpoint and emit ``RuntimeWarning``.

    Returns
    -------
    rate_m3_s : numpy.ndarray
        H2 + H2+ Maxwellian charge-exchange rate coefficient. [m^3/s] Shape:
        ``same as both inputs``. Every returned value is finite and strictly
        positive.

    Raises
    ------
    ValueError
        If either input is not real numeric, is non-finite or has the wrong shape,
        if temperature is nonpositive or energy is negative, or if the evaluated
        rate is not finite and positive.

    Warns
    -----
    RuntimeWarning
        If either paired sample is above ``2.01e4 eV``. The fit uses the endpoint
        value in that dimension; it does not extrapolate.

    See Also
    --------
    evaluate_atomic_hydrogen_charge_exchange_rate : The distinct atomic-H rate
        fit.
    evaluate_molecular_hydrogen_charge_exchange_cross_section : The separate
        molecular cross-section fit.
    average_cross_section_over_maxwellian : Explicit mesh-based Maxwellian
        averaging with caller-supplied volumes.

    Notes
    -----
    This relation evaluates the retained molecular nine-by-nine bivariate
    logarithmic fit; it does not integrate the molecular cross section at runtime.
    Both inputs are clipped independently in each dimension. The two inputs must
    have exactly the same shape; NumPy broadcasting is not used. The frozen fit is
    non-monotonic in impact energy, so a monotone rate must not be inferred. No
    external atomic-physics oracle is bound.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import evaluate_hydrogen2_charge_exchange_rate, evaluate_atomic_hydrogen_charge_exchange_rate
    >>> t = np.array([0.1, 10.0, 20100.0])
    >>> e = np.array([0.2, 10.0, 20100.0])
    >>> r = evaluate_hydrogen2_charge_exchange_rate(t, e)
    >>> a = evaluate_atomic_hydrogen_charge_exchange_rate(t, e)
    >>> assert r.shape == (3,) and np.all(np.isfinite(r)) and np.all(r > 0.0)
    >>> assert not np.allclose(r, a, rtol=1e-12, atol=0.0)
    """
    temperature = positive_real_array(temperature_ev, "temperature_ev")
    energy = finite_nonnegative_energy(energy_ev)
    if temperature.shape != energy.shape:
        raise ValueError("temperature_ev and energy_ev must have the same shape")

    warn_above_fit(
        energy,
        _FIT_UPPER_EV,
        "evaluate_hydrogen2_charge_exchange_rate",
        effect="uses the clipped upper edge in that fit dimension",
    )
    warn_above_fit(
        temperature,
        _FIT_UPPER_EV,
        "evaluate_hydrogen2_charge_exchange_rate",
        quantity="temperature",
        effect="uses the clipped upper edge in that fit dimension",
    )
    clipped_temperature = np.clip(temperature, _FIT_LOWER_EV, _FIT_UPPER_EV)
    clipped_energy = np.clip(energy, _FIT_LOWER_EV, _FIT_UPPER_EV)
    log_temperature = np.log(clipped_temperature)
    log_energy = np.log(clipped_energy)
    log_rate = bivariate_log_fit(log_energy, log_temperature, _COEFFICIENTS)
    rate = np.exp(log_rate) * 1.0e-6
    if not np.all(np.isfinite(rate)) or np.any(rate <= 0.0):
        raise ValueError(
            "molecular hydrogen charge-exchange fit produced a non-finite or nonpositive rate"
        )
    return rate

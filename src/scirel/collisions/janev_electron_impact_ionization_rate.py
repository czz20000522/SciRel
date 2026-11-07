"""Janev electron-impact ionization-rate fits for H and H2."""

from __future__ import annotations


import numpy as np

from ._energy_input import log_polynomial, positive_real_array, warn_above_fit

__all__ = ["evaluate_janev_electron_impact_ionization_rate"]

_FIT_LOWER_EV = 0.1
_FIT_UPPER_EV = 2.01e4
_COEFFICIENTS = {
    "H": np.array(
        [
            -3.271396786375e1,
            1.353655609057e1,
            -5.739328757388,
            1.563154982022,
            -2.877056004391e-1,
            3.482559773737e-2,
            -2.631976175590e-3,
            1.119543953861e-4,
            -2.039149852002e-6,
        ]
    ),
    "H2": np.array(
        [
            -3.568640293666e1,
            1.733468989961e1,
            -7.767469363538,
            2.211579405415,
            -4.169840174384e-1,
            5.088289820867e-2,
            -3.832737518325e-3,
            1.612863120371e-4,
            -2.893391904431e-6,
        ]
    ),
}


def evaluate_janev_electron_impact_ionization_rate(
    electron_temperature_ev,
    target_species,
):
    """Evaluate the Janev electron-impact ionization rate for H or H2.

    Parameters
    ----------
    electron_temperature_ev : real scalar or array-like
        Electron temperature for the selected Maxwellian fit. [eV] Shape:
        ``scalar or array``. The value must be finite and strictly positive.
        Values below ``0.1 eV`` are clipped to that endpoint silently. Values
        above ``2.01e4 eV`` are clipped to that endpoint and emit
        ``RuntimeWarning``.
    target_species : {'H', 'H2'}
        Target-species selector. [dimensionless enumeration] Shape: ``scalar``.
        The value must be the exact string ``'H'`` or ``'H2'``; there is no
        fallback branch.

    Returns
    -------
    rate_m3_s : numpy.ndarray
        Maxwellian electron-impact ionization rate coefficient for the selected
        target. [m^3/s] Shape: ``same as electron_temperature_ev``. Every returned
        value is finite and strictly positive.

    Raises
    ------
    ValueError
        If ``electron_temperature_ev`` is not real numeric, is non-finite or is
        nonpositive, if ``target_species`` is not exactly ``'H'`` or ``'H2'``, or
        if the evaluated rate is not finite and positive.

    Warns
    -----
    RuntimeWarning
        If a temperature is above ``2.01e4 eV``. The returned value is the
        endpoint value, not an extrapolation.

    See Also
    --------
    evaluate_atomic_hydrogen_1s_radiative_recombination_rate : The H(1s)
        radiative-recombination rate fit.
    average_cross_section_over_maxwellian : Explicit mesh-based Maxwellian
        averaging of a caller-supplied cross section.

    Notes
    -----
    The H and H2 branches each use the declared nine-coefficient Janev
    logarithmic polynomial,
    ``exp(polyval(log(T_clipped), a_species)) * 1e-6``. The two coefficient sets
    are distinct and are not interchangeable. Each fit has a single temperature
    maximum in the sampled range (about 137 eV for H and 156 eV for H2), so the
    rate is not monotone. No external atomic-physics oracle is bound, and a rate
    coefficient is not by itself a density-scaled source or sink.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import evaluate_janev_electron_impact_ionization_rate
    >>> t = np.array([0.01, 10.0, 50000.0])
    >>> h = evaluate_janev_electron_impact_ionization_rate(t, 'H')
    >>> h2 = evaluate_janev_electron_impact_ionization_rate(t, 'H2')
    >>> edge = evaluate_janev_electron_impact_ionization_rate(np.array([0.1, 10.0, 20100.0]), 'H')
    >>> assert h.shape == (3,) and np.all(np.isfinite(h)) and np.all(h > 0.0)
    >>> assert np.array_equal(h, edge)
    >>> assert not np.allclose(h, h2, rtol=1e-12, atol=0.0)
    """
    if not isinstance(target_species, str) or target_species not in _COEFFICIENTS:
        raise ValueError("target_species must be H or H2")
    temperature = positive_real_array(electron_temperature_ev, "electron_temperature_ev")
    warn_above_fit(
        temperature,
        _FIT_UPPER_EV,
        "evaluate_janev_electron_impact_ionization_rate",
        quantity="temperature",
        effect="returns the endpoint rate rather than extrapolating",
    )
    clipped = np.clip(temperature, _FIT_LOWER_EV, _FIT_UPPER_EV)
    rate = np.exp(log_polynomial(np.log(clipped), _COEFFICIENTS[target_species])) * 1.0e-6
    if not np.all(np.isfinite(rate)) or np.any(rate <= 0.0):
        raise ValueError("Janev ionization fit produced a non-finite or nonpositive rate")
    return rate

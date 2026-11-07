"""H-on-H2 elastic momentum-transfer cross-section fit.

Evaluate the H-on-H2 elastic momentum-transfer cross section in ``m^2`` from
collision energy in ``eV`` with one five-coefficient logarithmic polynomial,
``exp(polyval(log(E_clipped), a)) * 1e-4``, on ``[0.03, 1.01e4] eV``.

A positive input below ``0.03 eV`` returns the lower endpoint silently. A
positive input above ``1.01e4 eV`` returns the upper endpoint and emits one
``RuntimeWarning``. Negative energies are rejected before evaluation. The
output shape equals the input shape. No external experimental cross-section
reference is bound.
"""

from __future__ import annotations


import numpy as np

from ._energy_input import clipped_energy, log_polynomial, warn_above_fit

__all__ = [
    "evaluate_hydrogen_h2_elastic_cross_section",
]

_FIT_LOWER_EV = 0.03
_FIT_UPPER_EV = 1.01e4
_COEFFICIENTS = np.array(
    [-3.495671e1, -4.062257e-1, -3.820531e-2, -9.404486e-3, 3.963723e-4],
    dtype=float,
)


def evaluate_hydrogen_h2_elastic_cross_section(energy_ev):
    """Evaluate the H-on-H2 elastic momentum-transfer cross section.

    Parameters
    ----------
    energy_ev : real scalar or array-like
        Collision energy. [eV] Shape: ``scalar or array``. The value must be finite
        and nonnegative. Values below ``0.03 eV`` are clipped to that endpoint
        silently. Values above ``1.01e4 eV`` are clipped to that endpoint and emit
        ``RuntimeWarning``.

    Returns
    -------
    cross_section_m2 : numpy.ndarray
        H-on-H2 elastic momentum-transfer cross section. [m^2] Shape: ``same as
        energy_ev``. Every returned value is finite and strictly positive.

    Raises
    ------
    ValueError
        If ``energy_ev`` is not real numeric, is non-finite or is negative.

    Warns
    -----
    RuntimeWarning
        If a requested energy is above ``1.01e4 eV``. The returned value is the
        endpoint value, not an extrapolation.

    See Also
    --------
    evaluate_hydrogen2_hydrogen2_elastic_cross_section : The H2-on-H2 elastic fit.
    evaluate_hydrogen_proton_elastic_cross_section : The H+-on-H elastic fit.
    average_cross_section_over_maxwellian : Accepts a compatible cross-section
        callable as an input port.

    Notes
    -----
    The relation uses one five-coefficient logarithmic polynomial,
    ``exp(polyval(log(E_clipped), a)) * 1e-4``, on the clipped fit interval. The
    output preserves the input shape. No external experimental cross-section
    reference is bound.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import evaluate_hydrogen_h2_elastic_cross_section
    >>> energy = np.array([0.03, 1.0, 10.0, 100.0, 1.0e3, 1.01e4])
    >>> result = evaluate_hydrogen_h2_elastic_cross_section(energy)
    >>> assert result.shape == energy.shape
    >>> assert np.all(np.isfinite(result)) and np.all(result > 0.0)
    >>> clipped = evaluate_hydrogen_h2_elastic_cross_section(np.array([0.01, 0.03, 2.0e4, 1.01e4]))
    >>> assert clipped[0] == clipped[1] and clipped[-1] == clipped[-2]
    >>> try:
    ...     evaluate_hydrogen_h2_elastic_cross_section(np.array([1.0, -0.5]))
    ... except ValueError as error:
    ...     assert 'nonnegative' in str(error)
    ... else:
    ...     raise AssertionError('a negative energy must be rejected')
    """
    raw_energy = clipped_energy(energy_ev, _FIT_LOWER_EV, np.inf)
    warn_above_fit(raw_energy, _FIT_UPPER_EV, "evaluate_hydrogen_h2_elastic_cross_section")
    energy = clipped_energy(raw_energy, _FIT_LOWER_EV, _FIT_UPPER_EV)
    return np.exp(log_polynomial(np.log(energy), _COEFFICIENTS)) * 1.0e-4

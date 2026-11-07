"""H2-on-H2 elastic momentum-transfer cross-section fit.

Evaluate the H2-on-H2 elastic momentum-transfer cross section in ``m^2`` from
collision energy in ``eV`` with one five-coefficient logarithmic polynomial,
``exp(polyval(log(E_clipped), a)) * 1e-4``, on ``[0.03, 1.01e4] eV``. The
``viscosity=True`` selector remains a documented same-fit fallback, not a
second parameterization, and emits no extra warning.

A positive input below ``0.03 eV`` returns the lower endpoint silently. A
positive input above ``1.01e4 eV`` returns the upper endpoint and emits one
``RuntimeWarning``. Negative energies are rejected before evaluation. No
independent molecular-viscosity measurement or external experimental
cross-section reference is bound.
"""

from __future__ import annotations


import numpy as np

from ._energy_input import clipped_energy, log_polynomial, warn_above_fit

__all__ = [
    "evaluate_hydrogen2_hydrogen2_elastic_cross_section",
]

_FIT_LOWER_EV = 0.03
_FIT_UPPER_EV = 1.01e4
_COEFFICIENTS = np.array(
    [-3.430345e1, -2.960406e-1, -6.382532e-2, -7.557519e-3, 2.606259e-4],
    dtype=float,
)


def evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy_ev, viscosity=False):
    """Evaluate the H2-on-H2 elastic momentum-transfer cross section.

    Parameters
    ----------
    energy_ev : real scalar or array-like
        Collision energy. [eV] Shape: ``scalar or array``. The value must be finite
        and nonnegative. Values below ``0.03 eV`` are clipped to that endpoint
        silently. Values above ``1.01e4 eV`` are clipped to that endpoint and emit
        ``RuntimeWarning``.
    viscosity : bool or integer, optional
        Same-fit fallback selector. [dimensionless] Shape: ``scalar``. The default
        ``False`` selects the momentum-transfer fit. ``True`` selects the retained
        no-op fallback, which evaluates the same fit. Arrays and non-integral
        scalars are rejected.

    Returns
    -------
    cross_section_m2 : numpy.ndarray
        H2-on-H2 elastic momentum-transfer cross section. [m^2] Shape: ``same as
        energy_ev``. Every returned value is finite and strictly positive.

    Raises
    ------
    ValueError
        If ``energy_ev`` is not real numeric, is non-finite or is negative, or if
        ``viscosity`` is not a scalar boolean or integer.

    Warns
    -----
    RuntimeWarning
        If a requested energy is above ``1.01e4 eV``. The returned value is the
        endpoint value, not an extrapolation. The fallback selector itself emits
        no warning.

    See Also
    --------
    evaluate_atomic_hydrogen_elastic_cross_section : The H-on-H elastic
        momentum-transfer and viscosity fits.
    evaluate_hydrogen_h2_elastic_cross_section : The H-on-H2 elastic fit.
    average_cross_section_over_maxwellian : Accepts a compatible cross-section
        callable as an input port.

    Notes
    -----
    The relation uses one five-coefficient logarithmic polynomial on the clipped
    fit interval. ``viscosity=True`` is a documented same-fit fallback, not a
    second viscosity parameterization; it emits no extra warning. No independent
    molecular-viscosity measurement or external experimental cross-section
    reference is bound.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import evaluate_hydrogen2_hydrogen2_elastic_cross_section
    >>> energy = np.array([0.03, 1.0, 10.0, 100.0, 1.0e3, 1.01e4])
    >>> result = evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy)
    >>> assert result.shape == energy.shape
    >>> assert np.all(np.isfinite(result)) and np.all(result > 0.0)
    >>> np.testing.assert_array_equal(
    ...     evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy, viscosity=True),
    ...     result,
    ... )
    >>> try:
    ...     evaluate_hydrogen2_hydrogen2_elastic_cross_section(energy, viscosity=np.ones((2, 2)))
    ... except ValueError as error:
    ...     assert 'scalar boolean' in str(error)
    ... else:
    ...     raise AssertionError('an array selector must be rejected')
    >>> try:
    ...     evaluate_hydrogen2_hydrogen2_elastic_cross_section(np.array([1.0, -0.5]))
    ... except ValueError as error:
    ...     assert 'nonnegative' in str(error)
    ... else:
    ...     raise AssertionError('a negative energy must be rejected')
    """
    selector = np.asarray(viscosity)
    if selector.shape != ():
        raise ValueError("viscosity must be a scalar boolean")
    if not np.issubdtype(selector.dtype, np.bool_) and not np.issubdtype(
        selector.dtype, np.integer
    ):
        raise ValueError("viscosity must be a scalar boolean")
    raw_energy = clipped_energy(energy_ev, _FIT_LOWER_EV, np.inf)
    warn_above_fit(
        raw_energy,
        _FIT_UPPER_EV,
        "evaluate_hydrogen2_hydrogen2_elastic_cross_section",
    )
    energy = clipped_energy(raw_energy, _FIT_LOWER_EV, _FIT_UPPER_EV)
    log_sigma = log_polynomial(np.log(energy), _COEFFICIENTS)
    return np.exp(log_sigma) * 1.0e-4

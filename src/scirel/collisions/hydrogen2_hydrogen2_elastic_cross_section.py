"""H2-on-H2 elastic momentum-transfer cross-section fit.

One leaf recovered from the saved the neutral-transport formulation ``sigma_el_hh_hh`` slice, integrated as
:func:`evaluate_hydrogen2_hydrogen2_elastic_cross_section`:

the H2-on-H2 elastic momentum-transfer cross section in ``m^2`` as a function
of the collision energy in eV -- a single five-coefficient logarithmic
polynomial, ``exp(polyval(log(E), a)) * 1e-4``, evaluated on the
source-clipped domain ``[0.03, 1.01e4]`` eV.

**The saved implementation's selector validation is kept as the contract.**
``viscosity=True`` is the source's documented fallback that evaluates the same
momentum-transfer fit (the source emits a non-scientific warning there, which
is not reproduced); the selector must be a scalar boolean or integer, and the
saved implementation already rejects arrays and non-integral scalars.  The
endpoint clipping repeats values outside the range.

**Input-contract repairs relative to the saved implementation.**  The saved
document declares the energy nonnegative, but its implementation silently
clipped negative energies to the lower endpoint; this module rejects them.
Non-real energies, including numeric strings and boolean cells, are also
rejected before float conversion.  The arithmetic is preserved on finite
nonnegative real inputs.

Evidence ceiling: this module establishes the clipped fit against an
independent evaluation of the same formula, the viscosity fallback, the
selector validation, the endpoint clipping, the input and failure contracts,
these repairs, and -- in the environment-gated replay test -- exact agreement
with the saved the neutral-transport formulation implementation on the declared domain.  The saved
bundle's strict D1 qualification has been withdrawn; that replay is historical
development evidence, not qualified-L1 provenance.  No test establishes the
fit against an external physical cross-section reference: the saved package
records that residual as ``validation_oracle_gap``.
"""

from __future__ import annotations


import numpy as np

from ._energy_input import clipped_energy, log_polynomial

__all__ = [
    "evaluate_hydrogen2_hydrogen2_elastic_cross_section",
]

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
        and nonnegative. Values outside ``[0.03, 1.01e4]`` eV are clipped to the
        range endpoints.
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
    second viscosity parameterization; it emits no extra warning. Endpoint
    clipping is silent and intentional. No independent molecular-viscosity
    measurement or external experimental cross-section reference is bound.

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
    clipped = clipped_energy(energy_ev, 0.03, 1.01e4)
    log_sigma = log_polynomial(np.log(clipped), _COEFFICIENTS)
    return np.exp(log_sigma) * 1.0e-4

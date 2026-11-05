"""Atomic-hydrogen elastic cross-section fits.

One leaf recovered from the saved the neutral-transport formulation ``sigma_el_h_h`` slice,
integrated as :func:`evaluate_atomic_hydrogen_elastic_cross_section`:

the H-on-H elastic cross section in ``m^2`` as a function of the collision
energy in eV.  The default branch is the source's five-coefficient
momentum-transfer fit; ``viscosity=True`` selects the source's distinct
five-coefficient viscosity fit.  Both branches use the source energy clipping
interval ``[0.03, 1.01e4]`` eV, ``exp(polyval(log(E), a)) * 1e-4``.

**The fit domain is source-clipped, and the clipping is declared.**  Endpoint
values repeat outside the range.  This is the saved source's declared behavior,
exercised by its package tests, and is kept unchanged.

**Input-contract repairs relative to the saved implementation.**  The
saved document declares the energy nonnegative, but its implementation
silently clipped negative energies to the lower endpoint; this module rejects
them.  The saved document declares the ``viscosity`` selector a scalar, but
its implementation relied on ``bool()`` coercion, which silently accepted
zero-dimensional and single-element arrays and failed on multi-element arrays
with NumPy's generic ambiguity error that does not name the quantity; this
module requires a zero-dimensional scalar and names the quantity.  The port
also rejects non-real energies, including numeric strings and boolean
cells, before float conversion.  Both branches' arithmetic is preserved on
finite nonnegative real inputs.

Evidence ceiling: this module establishes both clipped fits against
independent evaluations of the same formulas, the endpoint clipping, the input
and failure contracts, these repairs, and -- in the environment-gated replay
test -- exact agreement with the saved the neutral-transport formulation implementation on the declared
domain.  The saved bundle's strict D1 qualification has been withdrawn; that
replay is historical development evidence, not qualified-L1 provenance.  No
test establishes either fit against an external physical cross-section
reference: the saved package records that residual as ``validation_oracle_gap``.
"""

from __future__ import annotations


import numpy as np

from ._energy_input import clipped_energy, log_polynomial

__all__ = [
    "evaluate_atomic_hydrogen_elastic_cross_section",
]

_MOMENTUM_TRANSFER_COEFFICIENTS = np.array(
    [-3.330843e1, -5.738374e-1, -1.028610e-1, -3.920980e-3, 5.964135e-4],
    dtype=float,
)
_VISCOSITY_COEFFICIENTS = np.array(
    [-3.344860e1, -4.238982e-1, -7.477873e-2, -7.915053e-3, -2.686129e-4],
    dtype=float,
)


def evaluate_atomic_hydrogen_elastic_cross_section(energy_ev, viscosity=False):
    """Evaluate the H-on-H elastic momentum-transfer or viscosity cross section.

    Parameters
    ----------
    energy_ev : real scalar or array-like
        Collision energy. [eV] Shape: ``scalar or array``. The value must be finite
        and nonnegative. Values outside ``[0.03, 1.01e4]`` eV are clipped to the
        range endpoints.
    viscosity : scalar, optional
        Branch selector. [dimensionless] Shape: ``scalar``. The default ``False``
        selects the momentum-transfer fit; a truthy zero-dimensional scalar selects
        the distinct viscosity fit. Higher-rank selectors are rejected.

    Returns
    -------
    cross_section_m2 : numpy.ndarray
        Elastic cross section for the selected branch. [m^2] Shape: ``same as
        energy_ev``. Every returned value is finite and strictly positive.

    Raises
    ------
    ValueError
        If ``energy_ev`` is not real numeric, is non-finite or is negative, or if
        ``viscosity`` is not a zero-dimensional scalar.

    See Also
    --------
    evaluate_hydrogen2_hydrogen2_elastic_cross_section : The H2-on-H2 elastic
        momentum-transfer fit.
    evaluate_hydrogen_h2_elastic_cross_section : The H-on-H2 elastic
        momentum-transfer fit.
    average_cross_section_over_maxwellian : Accepts a compatible cross-section
        callable as an input port.

    Notes
    -----
    Both branches use a five-coefficient logarithmic polynomial,
    ``exp(polyval(log(E_clipped), a)) * 1e-4``, on the clipped fit interval.
    The two coefficient sets describe different cross sections and are not
    interchangeable. Endpoint clipping is intentional and silent. No external
    experimental cross-section reference is bound by this callable.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import evaluate_atomic_hydrogen_elastic_cross_section
    >>> energy = np.array([0.03, 1.0, 10.0, 100.0, 1.0e3, 1.01e4])
    >>> momentum = evaluate_atomic_hydrogen_elastic_cross_section(energy)
    >>> viscosity = evaluate_atomic_hydrogen_elastic_cross_section(energy, viscosity=True)
    >>> assert momentum.shape == energy.shape
    >>> assert np.all(np.isfinite(momentum)) and np.all(momentum > 0.0)
    >>> assert not np.allclose(momentum, viscosity, rtol=1e-12, atol=0.0)
    >>> clipped = evaluate_atomic_hydrogen_elastic_cross_section(np.array([0.01, 0.03, 2.0e4, 1.01e4]))
    >>> assert clipped[0] == clipped[1] and clipped[-1] == clipped[-2]
    >>> try:
    ...     evaluate_atomic_hydrogen_elastic_cross_section(np.array([1.0, -0.5]))
    ... except ValueError as error:
    ...     assert 'nonnegative' in str(error)
    ... else:
    ...     raise AssertionError('a negative energy must be rejected')
    >>> try:
    ...     evaluate_atomic_hydrogen_elastic_cross_section(energy, viscosity=np.ones((2, 2)))
    ... except ValueError as error:
    ...     assert 'viscosity' in str(error)
    ... else:
    ...     raise AssertionError('an array selector must be rejected')
    """
    energy = clipped_energy(energy_ev, 0.03, 1.01e4)
    selector = np.asarray(viscosity)
    if selector.ndim != 0:
        raise ValueError("viscosity must be a scalar branch selector, not an array")
    clipped = energy
    coefficients = _VISCOSITY_COEFFICIENTS if bool(selector) else _MOMENTUM_TRANSFER_COEFFICIENTS
    return np.exp(log_polynomial(np.log(clipped), coefficients)) * 1.0e-4

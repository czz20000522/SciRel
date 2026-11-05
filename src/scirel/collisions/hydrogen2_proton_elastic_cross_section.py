"""H2-on-H+ elastic momentum-transfer cross-section fit.

One leaf recovered from the saved the neutral-transport formulation ``sigma_el_p_hh`` slice, integrated as
:func:`evaluate_hydrogen2_proton_elastic_cross_section`:

the H2-on-H+ elastic momentum-transfer cross section in ``m^2`` as a function
of the collision energy in eV -- a single five-coefficient logarithmic
polynomial, ``exp(polyval(log(E), a)) * 1e-4``, evaluated on the
source-clipped domain ``[0.03, 1.01e4]`` eV.  Endpoint values repeat outside
the range, the saved source's declared behavior.

**Input-contract repairs relative to the saved implementation.**  The saved
document declares the energy nonnegative, but its implementation silently
clipped negative energies to the lower endpoint; this module rejects them.
Non-real energies, including numeric strings and boolean cells, are also
rejected before float conversion.  The arithmetic is preserved on finite
nonnegative real inputs.

Evidence ceiling: this module establishes the clipped fit against an
independent evaluation of the same formula, the endpoint clipping, the input
and failure contracts, these repairs, and -- in the environment-gated replay
test -- exact agreement with the saved the neutral-transport formulation implementation on the declared
domain.  The saved bundle's strict D1 qualification has been withdrawn; that
replay is historical development evidence, not qualified-L1 provenance.  No
test establishes the fit against an external physical cross-section reference:
the saved package records that residual as ``validation_oracle_gap``.
"""

from __future__ import annotations


import numpy as np

from ._energy_input import clipped_energy, log_polynomial

__all__ = [
    "evaluate_hydrogen2_proton_elastic_cross_section",
]

_COEFFICIENTS = np.array(
    [-3.355719e1, -5.696568e-1, -4.089556e-2, -1.143513e-2, 5.926596e-4],
    dtype=float,
)


def evaluate_hydrogen2_proton_elastic_cross_section(energy_ev):
    """Evaluate the H2-on-H+ elastic momentum-transfer cross section.

    Parameters
    ----------
    energy_ev : real scalar or array-like
        Collision energy. [eV] Shape: ``scalar or array``. The value must be finite
        and nonnegative. Values outside ``[0.03, 1.01e4]`` eV are clipped to the
        range endpoints.

    Returns
    -------
    cross_section_m2 : numpy.ndarray
        H2-on-H+ elastic momentum-transfer cross section. [m^2] Shape: ``same as
        energy_ev``. Every returned value is finite and strictly positive.

    Raises
    ------
    ValueError
        If ``energy_ev`` is not real numeric, is non-finite or is negative.

    See Also
    --------
    evaluate_hydrogen_proton_elastic_cross_section : The H+-on-H piecewise fit.
    evaluate_hydrogen2_hydrogen2_elastic_cross_section : The H2-on-H2 elastic fit.
    average_cross_section_over_maxwellian : Accepts a compatible cross-section
        callable as an input port.

    Notes
    -----
    The relation uses one five-coefficient logarithmic polynomial,
    ``exp(polyval(log(E_clipped), a)) * 1e-4``, on the clipped fit interval.
    Endpoint clipping is silent and intentional. No external experimental
    cross-section reference is bound.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import evaluate_hydrogen2_proton_elastic_cross_section
    >>> energy = np.array([0.03, 1.0, 10.0, 100.0, 1.0e3, 1.01e4])
    >>> result = evaluate_hydrogen2_proton_elastic_cross_section(energy)
    >>> assert result.shape == energy.shape
    >>> assert np.all(np.isfinite(result)) and np.all(result > 0.0)
    >>> clipped = evaluate_hydrogen2_proton_elastic_cross_section(np.array([0.01, 0.03, 2.0e4, 1.01e4]))
    >>> assert clipped[0] == clipped[1] and clipped[-1] == clipped[-2]
    >>> try:
    ...     evaluate_hydrogen2_proton_elastic_cross_section(np.array([1.0, -0.5]))
    ... except ValueError as error:
    ...     assert 'nonnegative' in str(error)
    ... else:
    ...     raise AssertionError('a negative energy must be rejected')
    """
    clipped = clipped_energy(energy_ev, 0.03, 1.01e4)
    log_sigma = log_polynomial(np.log(clipped), _COEFFICIENTS)
    return np.exp(log_sigma) * 1.0e-4

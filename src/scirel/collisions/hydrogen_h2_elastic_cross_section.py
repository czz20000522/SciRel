"""H-on-H2 elastic momentum-transfer cross-section fit.

One leaf recovered from the saved the neutral-transport formulation ``sigma_el_h_hh`` slice, integrated as
:func:`evaluate_hydrogen_h2_elastic_cross_section`:

the H-on-H2 elastic momentum-transfer cross section in ``m^2`` as a function
of the collision energy in eV -- a single five-coefficient logarithmic
polynomial, ``exp(polyval(log(E), a)) * 1e-4``, evaluated on the
source-clipped domain ``[0.03, 1.01e4]`` eV.

**Two declared source behaviors are kept exactly.**  The endpoint clipping
repeats values outside the range, and the output shape equals the input shape,
matching the canonical KN1DPy commit ``bb22c872`` source.  The older saved
package's ``np.array([E])`` wrapper is not retained; the source conflict was
resolved against the canonical E-archive source.

**Input-contract repairs relative to the saved implementation.**  The saved
document declares the energy nonnegative, but its implementation silently
clipped negative energies to the lower endpoint; this module rejects them.
Non-real energies, including numeric strings and boolean cells, are also
rejected before float conversion.  The arithmetic is preserved on finite
nonnegative real inputs.

Evidence ceiling: this module establishes the clipped fit against an
independent evaluation of the same formula, the input-preserving output shape,
the endpoint clipping, the input and failure contracts, these repairs, and --
in the environment-gated replay test -- exact agreement with the canonical
KN1DPy implementation on the declared domain.  The saved bundle's strict D1
qualification has been withdrawn; that replay is historical development
evidence, not qualified-L1 provenance.  No test establishes the fit against an
external physical cross-section reference: the saved package records that
residual as ``validation_oracle_gap``.
"""

from __future__ import annotations


import numpy as np

from ._energy_input import clipped_energy, log_polynomial

__all__ = [
    "evaluate_hydrogen_h2_elastic_cross_section",
]

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
        and nonnegative. Values outside ``[0.03, 1.01e4]`` eV are clipped to the
        range endpoints.

    Returns
    -------
    cross_section_m2 : numpy.ndarray
        H-on-H2 elastic momentum-transfer cross section. [m^2] Shape: ``same as
        energy_ev``. Every returned value is finite and strictly positive.

    Raises
    ------
    ValueError
        If ``energy_ev`` is not real numeric, is non-finite or is negative.

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
    output preserves the input shape. Endpoint clipping is silent and intentional.
    No external experimental cross-section reference is bound.

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
    clipped = clipped_energy(energy_ev, 0.03, 1.01e4)
    return np.exp(log_polynomial(np.log(clipped), _COEFFICIENTS)) * 1.0e-4

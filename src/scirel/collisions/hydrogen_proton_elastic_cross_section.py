"""H+-on-H elastic momentum-transfer fit in m^2.

The input is projectile proton laboratory energy in eV with target H at rest;
the function converts it to the center-of-mass energy ``E_cm = E_lab/2``
(equal masses, stationary target) before evaluating the parameterization,
whose tabulated variable is the center-of-mass energy (Janev 1995, ch. 11
p. 298, via the KN1DPy ``sigma_el_p_h`` source). The valid laboratory range
of the underlying table is 0.2-200 eV (APID 8, 1999, p. 1 and p. 77); the
declared fit domain remains the KN1DPy clipping window. The canonical
KN1DPy commit ``bb22c872`` uses ``E < 10`` for the low-energy polynomial and
``E >= 10`` for the high-energy polynomial, so exactly 10 eV uses the
high-energy branch. The two empirical fits are not forced continuous.
Endpoint clipping [0.001, 1.01e5] eV and the input-preserving output shape
are explicit. Fit fidelity does not establish accuracy outside the cited
experimental/model range or grant redistribution approval.
"""

from __future__ import annotations


import numpy as np

from ._energy_input import clipped_energy, log_polynomial

__all__ = [
    "evaluate_hydrogen_proton_elastic_cross_section",
]

_LOW_ENERGY_COEFFICIENTS = np.array(
    [-3.233966e1, -1.126918e-1, 5.287706e-3, -2.445017e-3, -1.044156e-3, 8.419691e-5, 3.824773e-5],
    dtype=float,
)
_HIGH_ENERGY_COEFFICIENTS = np.array([-3.231141e1, -1.386002e-1], dtype=float)


def evaluate_hydrogen_proton_elastic_cross_section(energy_ev):
    """Evaluate the H+-on-H elastic momentum-transfer cross section.

    Parameters
    ----------
    energy_ev : real scalar or array-like
        Laboratory proton energy in the stationary-hydrogen-target frame. [eV]
        Shape: ``scalar or array``. The value must be finite and nonnegative.
        Values outside ``[0.001, 1.01e5]`` eV are clipped to the range endpoints.

    Returns
    -------
    cross_section_m2 : numpy.ndarray
        H+-on-H elastic momentum-transfer cross section. [m^2] Shape: ``same as
        energy_ev``. Every returned value is finite and strictly positive.

    Raises
    ------
    ValueError
        If ``energy_ev`` is not real numeric, is non-finite or is negative.

    See Also
    --------
    evaluate_hydrogen2_proton_elastic_cross_section : The H2-on-H+ elastic fit.
    evaluate_atomic_hydrogen_elastic_cross_section : The H-on-H elastic fits.
    assemble_atomic_hydrogen_collision_matrices : Uses this fit in ``SIG_H_P``.

    Notes
    -----
    This is a piecewise empirical momentum-transfer fit evaluated at the
    center-of-mass energy ``E_cm = E_lab/2``. Laboratory energies below 20 eV
    use a seven-coefficient low-energy logarithmic polynomial; laboratory
    energies at or above 20 eV use a two-coefficient high-energy polynomial.
    Exactly 20 eV laboratory (10 eV center-of-mass) belongs to the high-energy
    branch. The two segments are not forced to be continuous, so a finite jump
    at the breakpoint is retained. Endpoint clipping is silent and does not
    imply experimental accuracy outside the declared range.

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.collisions import evaluate_hydrogen_proton_elastic_cross_section
    >>> y = evaluate_hydrogen_proton_elastic_cross_section(np.array([np.nextafter(20., 0.), 20., np.nextafter(20., np.inf)]))
    >>> assert y.shape == (3,)
    >>> assert np.isfinite(y).all() and (y > 0).all()
    >>> high = np.exp(np.polynomial.polynomial.polyval(np.log(10.0), np.array([-3.231141e1, -1.386002e-1]))) * 1.0e-4
    >>> np.testing.assert_allclose(y[1], high, rtol=1e-15)
    """
    clipped = clipped_energy(energy_ev, 0.001, 1.01e5)
    # Equal-mass symmetric system with a stationary target: the parameterized
    # variable of the Janev fit is the center-of-mass energy (issue #10 item 2).
    center_of_mass = clipped / 2.0
    result = np.zeros_like(clipped, dtype=float)
    low = center_of_mass < 10.0
    high = center_of_mass >= 10.0
    if np.any(low):
        result[low] = (
            np.exp(log_polynomial(np.log(center_of_mass[low]), _LOW_ENERGY_COEFFICIENTS)) * 1.0e-4
        )
    if np.any(high):
        result[high] = (
            np.exp(log_polynomial(np.log(center_of_mass[high]), _HIGH_ENERGY_COEFFICIENTS)) * 1.0e-4
        )
    return result

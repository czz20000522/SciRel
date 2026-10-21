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

# HELD: human-review exposure guard
from scirel._hold import require_review_import
require_review_import(__name__)


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
    """Return the source H2-on-H2 elastic cross section in square metres.

    Parameters
    ----------
    energy_ev
        Collision energies in eV, as a scalar or array of any shape.  Values
        must be finite and nonnegative; energies outside the fit range are
        clipped to the range endpoints, the saved source's declared behavior.
    viscosity
        Scalar boolean or integer selector.  ``True`` selects the source's
        documented fallback, which evaluates the same momentum-transfer fit;
        the default is the momentum-transfer fit itself.  Arrays and
        non-integral scalars are rejected, the saved implementation's own
        validation.

    Returns
    -------
    numpy.ndarray
        Cross sections in ``m^2`` with the input's shape.  Finite and strictly
        positive for every accepted input.

    Raises
    ------
    ValueError
        If ``energy_ev`` contains a non-real, non-finite or negative value, or if
        ``viscosity`` is not a scalar boolean/integer.
    """
    selector = np.asarray(viscosity)
    if selector.shape != ():
        raise ValueError("viscosity must be a scalar boolean")
    if not np.issubdtype(selector.dtype, np.bool_) and not np.issubdtype(selector.dtype, np.integer):
        raise ValueError("viscosity must be a scalar boolean")
    clipped = clipped_energy(energy_ev, 0.03, 1.01e4)
    log_sigma = log_polynomial(np.log(clipped), _COEFFICIENTS)
    return np.exp(log_sigma) * 1.0e-4

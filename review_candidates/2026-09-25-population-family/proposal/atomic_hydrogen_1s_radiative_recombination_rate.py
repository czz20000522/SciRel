"""Atomic-hydrogen 1s radiative recombination rate fit.

One leaf recovered from the saved KN1DPy ``sigmav_rec_h1s`` slice (source
anchor ``KN1DPy/sigma/sigmav_rec_h1s.py:3-25`` with caller evidence
``KN1DPy/kinetic_h.py:862`` and ``KN1DPy/kinetic_h.py:867-881``), integrated
as :func:`evaluate_atomic_hydrogen_1s_radiative_recombination_rate`:

the H+ + e -> H(1s) + hv radiative recombination rate coefficient in ``m^3/s``
as a Storey-type analytic form with the saved source's frozen constants
(Rydberg ``13.58 eV``, ``A_nl = 3.92``, ``x_nl = 0.35``, level ``n = 1``),
evaluated on the source-clipped domain ``[0.1, 2.01e4] eV`` and scaled by
``1e-6`` from the source's ``1e-14``-based expression.

**The constants and the closed form are the saved source's, exactly.**  The
temperature is sequentially clipped to ``[0.1, 2.01e4] eV``, the excited-level
binning parameter is ``b_n = (Ry/n^2) / T``, and the rate is
``A_nl * 1e-14 * sqrt((Ry/n^2) / Ry) * (b_n^1.5 / (b_n + x_nl)) * 1e-6``.

**One repair relative to the saved implementation, documented.**  The saved
document declares a positive temperature, but its implementation silently
clipped a nonpositive temperature into the fit domain; this module rejects
it.  The rejection domain is otherwise unchanged and the arithmetic is
preserved bit for bit on the declared domain.

Evidence ceiling: this module establishes the closed form against an
independent evaluation with the same frozen constants, the endpoint clipping,
the input and failure contracts, the repair, and -- in the environment-gated
replay test -- exact agreement with the saved KN1DPy implementation on the
declared domain.  The saved bundle's strict D1 qualification has been
withdrawn; that replay is historical development evidence, not qualified-L1
provenance.  No test establishes the fit against an external atomic-physics
reference: the saved package records that residual as
``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "evaluate_atomic_hydrogen_1s_radiative_recombination_rate",
]

_RY_EV = 13.58
_LEVEL_N = 1.0
_A_NL = 3.92
_X_NL = 0.35


def evaluate_atomic_hydrogen_1s_radiative_recombination_rate(electron_temperature_ev):
    """Return the source H+ + e -> H(1s) + hv rate coefficient in m^3/s.

    Parameters
    ----------
    electron_temperature_ev
        Electron temperatures in eV, scalar or array; must be finite and
        strictly positive.  In-domain values above or below the fit range are
        clipped to ``[0.1, 2.01e4] eV``, the saved source's declared behavior.

    Returns
    -------
    numpy.ndarray
        Rate coefficients in ``m^3/s`` with the input's shape.  Finite and
        strictly positive for every accepted input.

    Raises
    ------
    ValueError
        If ``electron_temperature_ev`` contains a non-finite or nonpositive
        value.
    """
    temperature = np.asarray(electron_temperature_ev, dtype=float)
    if not np.all(np.isfinite(temperature)):
        raise ValueError("electron_temperature_ev must be finite")
    if bool(np.any(temperature <= 0.0)):
        raise ValueError("electron_temperature_ev must be positive")
    clipped = np.minimum(np.maximum(temperature, 0.1), 2.01e4)
    ionization_energy_ev = _RY_EV / _LEVEL_N
    b_n = ionization_energy_ev / clipped
    return _A_NL * 1.0e-14 * np.sqrt(ionization_energy_ev / _RY_EV) * (b_n**1.5 / (b_n + _X_NL)) * 1.0e-6

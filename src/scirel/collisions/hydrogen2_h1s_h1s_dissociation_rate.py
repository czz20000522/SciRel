"""KN1DPy H2 + e -> H(1s) + H(1s) + e electron-impact rate coefficient.

One leaf recovered from the saved KN1DPy dissociation-rate slice (source
anchor KN1DPy/sigma/sigmav_h1s_h1s_hh.py:5-27, shared polynomial evaluation KN1DPy/sigma/poly.py:3-10, caller KN1DPy/kinetic_h2.py:938), integrated as
:func:`evaluate_hydrogen2_h1s_h1s_dissociation_rate`:

the H2 + e -> H(1s) + H(1s) + e electron-impact rate coefficient in ``m^3/s`` as a
temperature-only nine-coefficient logarithmic polynomial -- the temperature in
eV, evaluated with the saved source's Horner loop on the clipped domain
``[0.1, 2.01e4] eV`` and scaled by ``1e-6``.

**The evaluation is the saved source's, exactly.**  The temperature is
sequentially clipped to ``[0.1, 2.01e4] eV``, the polynomial is accumulated in
the source's Horner order, and the result is ``exp(log_rate) * 1e-6``.  The
bounded fit domain keeps the exponential representable for every accepted
input.

**One repair relative to the saved implementation, documented.**  The saved
document declares a positive temperature, but its implementation silently
clipped a nonpositive temperature into the fit domain; this module rejects
it.  The rejection domain is otherwise unchanged: the same finite check the
saved implementation already performed, the same clipping of in-domain values
and the same arithmetic, bit for bit.

Evidence ceiling: this module establishes the fit against an independent
``polyval`` evaluation of the same coefficient table, the source Horner order
by exact equality, the input and failure contracts, the repair, and -- in the
environment-gated replay test -- exact agreement with the saved KN1DPy
implementation on the declared domain.  The saved bundle's strict D1
qualification has been withdrawn; that replay is historical development
evidence, not qualified-L1 provenance.  No test establishes the fit against an
external atomic-physics reference: the saved package records that residual as
``validation_oracle_gap``.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "evaluate_hydrogen2_h1s_h1s_dissociation_rate",
]

_COEFFICIENTS = np.array(
    [
    -27.87217511174,
    10.52252660075,
    -4.97321234786,
    1.451198183114,
    -0.3062790554644,
    0.04433379509258,
    -0.004096344172875,
    0.0002159670289222,
    -4.928545325189e-06,
    ],
    dtype=float,
)


def evaluate_hydrogen2_h1s_h1s_dissociation_rate(temperature_ev):
    """Return the source rate coefficient in m^3/s for the H2 + e -> H(1s) + H(1s) + e channel.

    Parameters
    ----------
    temperature_ev
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
        If ``temperature_ev`` contains a non-finite or nonpositive value.
    """
    temperature = np.asarray(temperature_ev, dtype=float)
    if not np.all(np.isfinite(temperature)):
        raise ValueError("temperature_ev must be finite")
    if bool(np.any(temperature <= 0.0)):
        raise ValueError("temperature_ev must be positive")
    clipped = np.minimum(np.maximum(temperature, 0.1), 2.01e4)
    log_temperature = np.log(clipped)
    log_rate = np.full_like(log_temperature, _COEFFICIENTS[-1], dtype=float)
    for coefficient in _COEFFICIENTS[-2::-1]:
        log_rate = log_rate * log_temperature + coefficient
    return np.exp(log_rate) * 1.0e-6

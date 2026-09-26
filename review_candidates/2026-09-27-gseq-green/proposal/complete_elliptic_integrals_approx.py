"""GSEQ approximation for complete elliptic integrals K(m) and E(m).

Source: GSEQ ``fun_ellipEK`` ``apx==1`` polynomial-logarithmic approximation
for ``0 <= m <= 1`` (the ``m = k^2`` squared-modulus convention), consumed by
the GSEQ filament-coil Green response.  This is the source's own special-
function implementation, kept verbatim -- including the whole-array singular
guard -- because it is the contract the Green operator was recorded against.
The baseline ``scirel.field`` filament assets instead use
``scipy.special.ellipk/ellipe``; on a 2,000,001-point sweep of ``m`` in
``[1e-6, 0.999999]`` the two implementations agree to at most 8.5e-9 relative
in ``K`` and 1.6e-8 in ``E`` (sampled evidence, not a bound over the
continuous domain).

Source guard semantics (verbatim, vector test ``if (k2 == 1.0)``): when
*every* element equals 1 the source returns the finite sentinel
``K = 1.0e300, E = 1``; when any element differs, the polynomial-log branch
runs and the ``m == 1`` elements yield ``K = +Inf`` and ``E = NaN``
(``0 * -Inf``).  These encoded singular returns are preserved as-is, not
reinterpreted as input errors.
"""
from __future__ import annotations

import numpy as np

__all__ = ["evaluate_complete_elliptic_integrals"]


def evaluate_complete_elliptic_integrals(modulus_squared):
    """Return the source's apx==1 K(m), E(m) approximation for 0 <= m <= 1."""
    m = np.asarray(modulus_squared, dtype=float)
    if not np.all(np.isfinite(m)) or np.any(m < 0.0) or np.any(m > 1.0):
        raise ValueError("modulus_squared must be finite and lie in [0,1]")
    p = 1.0 - m
    with np.errstate(divide="ignore", invalid="ignore"):
        a_k = ((((0.01451196212 * p + 0.03742563713) * p + 0.03590092383) * p + 0.09666344259) * p + 1.38629436112)
        b_k = ((((0.00441787012 * p + 0.03328355346) * p + 0.06880248576) * p + 0.12498593597) * p + 0.5)
        a_e = ((((0.01736506451 * p + 0.04757383546) * p + 0.0626060122) * p + 0.44325141463) * p + 1.0)
        b_e = ((((0.00526449639 * p + 0.04069697526) * p + 0.09200180037) * p + 0.2499836831) * p)
        k = a_k - b_k * np.log(p)
        e = a_e - b_e * np.log(p)
    # The source guards with the VECTOR test `if (k2 == 1.0)`, which is true only when every
    # element equals 1. In that whole-array case the source returns the finite sentinel
    # K = 1.0D+300, E = 1. When any element differs the guard is false and the polynomial-log
    # branch runs, so the m == 1 elements take log(0): K = +Inf and E = NaN (0 * Inf).
    if np.all(m == 1.0):
        return np.full_like(m, 1.0e300), np.full_like(m, 1.0)
    return k, e

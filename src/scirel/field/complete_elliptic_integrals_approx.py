"""GSEQ approximation for complete elliptic integrals K(m) and E(m).

Source: GSEQ MATLAB ``fun_ellipEK`` ``apx==1`` polynomial-logarithmic approximation
for ``0 <= m <= 1`` (the ``m = k^2`` squared-modulus convention), consumed by
the GSEQ filament-coil Green response.  This is the source's own special-
function branch on the open interval. The singular endpoint is corrected
element by element to the mathematical limits K(1)=+Inf and E(1)=1;
it does not claim source parity at that endpoint.
The baseline ``scirel.field`` filament assets instead use
``scipy.special.ellipk/ellipe``; on a 2,000,001-point sweep of ``m`` in
``[1e-6, 0.999999]`` the two implementations agree to at most 8.5e-9 relative
in ``K`` and 1.6e-8 in ``E`` (sampled evidence, not a bound over the
continuous domain).

The original whole-array guard returned a false finite K sentinel for an
all-one array and NaN for E(1) in a mixed array. This D2 correction preserves
all interior approximation arithmetic, but removes the batch-dependent
endpoint. The +Inf is the divergent integral, not a finite magnetic-field
value; the filament-field consumer continues to reject singular geometry.
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
    # Integral limits are independent of neighboring array elements.
    return np.where(m == 1.0, np.inf, k), np.where(m == 1.0, 1.0, e)

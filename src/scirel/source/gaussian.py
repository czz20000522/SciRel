# Derived from TORAX: Copyright 2024 DeepMind Technologies Limited.
# Licensed under Apache-2.0; retained license: licenses/torax/LICENSE.
"""Volume-normalized Gaussian radial source profile.

Source: accepted TORAX f21a878998abd74e6812f57d8bb8891641fecfc6,
torax/_src/sources/formulas.py:gaussian_profile. The explicit metric ports
replace Geometry without changing its cell-volume sum. This is distinct from
SciRel's KN1D spatial source normalization and flux-surface interpolation.
"""
from __future__ import annotations
import numpy as np
from ._common import grid, normalize_log_shape, scalar, width_scalar

__all__ = ["gaussian_profile"]


def gaussian_profile(rho_norm, vpr, drho_norm, *, center, width, total):
    """Return a cell profile whose discrete volume integral equals ``total``.

    ``rho_norm`` is the dimensionless cell coordinate in increasing order;
    ``vpr`` is the volume metric (m³ per normalized-radius unit) and
    ``drho_norm`` is each cell's integration weight. ``center`` and ``width``
    are dimensionless. ``total`` has the source quantity times m³. The
    returned float64 vector is ``total * exp(-(rho-center)^2/(2 width^2))``
    normalized by ``sum(profile*vpr*drho_norm)``. Zero or nonfinite widths
    preserve TORAX's direct-call NaN boundary; finite nonzero signed widths
    are accepted (the Gaussian is even in width).

    All grid ports are nonempty equal-length 1D vectors; parameters are real
    scalars, with no broadcasting or defaults. Integer/float32/float64 inputs
    convert to float64. The numerical denominator is floored at float64 tiny,
    retaining the repaired TORAX tiny-width convention. Grid/type/nonfinite
    center/total errors raise ValueError. Unrepresentable float64 results or
    loss of the target integral beyond 64 epsilons relative raise
    FloatingPointError; negligible tails may round to zero.
    """
    rho, vpr_a, drho = grid(rho_norm, vpr, drho_norm)
    c = scalar(center, "center")
    w = width_scalar(width)
    total_f = scalar(total, "total")
    if w == 0 or not np.isfinite(w):
        return np.full(rho.shape, np.nan, dtype=np.float64)
    # Factor the difference of squares before subtraction. Squaring distances
    # first loses all grid-scale information for a remote finite center.
    r = np.asarray(rho, dtype=np.longdouble)
    ref = r[0] if c <= rho[0] else r[-1] if c >= rho[-1] else r[np.argmin(np.abs(r - c))]
    delta_square = (r - ref) * (r + ref - 2 * np.longdouble(c))
    # Preserve the repaired source's float64 denominator floor for tiny widths.
    den = max(np.longdouble(2) * np.longdouble(w) * np.longdouble(w), np.longdouble(np.finfo(np.float64).tiny))
    log_shape = -delta_square / den
    weights = np.asarray(vpr_a, dtype=np.longdouble) * np.asarray(drho, dtype=np.longdouble)
    return normalize_log_shape(log_shape, weights, total_f)

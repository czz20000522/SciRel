# Derived profile conventions: the profile convention, Copyright 2024 DeepMind Technologies Limited.
# Retained attribution: see licenses/.
"""Volume-normalized exponential radial source profile.

Normalization cancels decay_start; this is not a cutoff profile or a
velocity-space Maxwellian. The retained licence and reference are above.
"""

from __future__ import annotations
import numpy as np
from ._common import grid, normalize_log_shape, scalar, width_scalar

__all__ = ["exponential_profile"]


def exponential_profile(rho_norm, vpr, drho_norm, *, decay_start, width, total):
    """Return a volume-normalized exponential profile on a nonuniform grid.

    The unnormalized relation is ``exp(-(decay_start-rho_norm)/width)``;
    ``decay_start`` therefore cancels exactly after normalization, while its
    finite scalar boundary remains part of the API. ``width`` must be a finite
    nonzero scalar for a profile; zero and nonfinite values return an all-NaN
    vector to preserve the source direct-call behavior. Inputs and output have
    the same units and integration contract as :func:`gaussian_profile`.
    All grid ports are nonempty equal-length 1D vectors; parameters are real
    scalars, with no broadcasting or defaults. The numerical absolute width
    is floored at float64 tiny with its sign retained. Integer and float32/64
    inputs convert to float64. Malformed geometry/type or nonfinite
    decay_start/total raises ValueError; unrepresentable output or loss of
    discrete normalization beyond 64 epsilons relative raises
    FloatingPointError. Negligible tails may round to zero.
    """
    rho, vpr_a, drho = grid(rho_norm, vpr, drho_norm)
    scalar(decay_start, "decay_start")
    w = width_scalar(width)
    total_f = scalar(total, "total")
    if w == 0 or not np.isfinite(w):
        return np.full(rho.shape, np.nan, dtype=np.float64)
    # Subtract a grid endpoint before exponentiation; this is algebraically
    # identical to the source normalization and avoids overflow in start/w.
    reference = rho[0] if np.signbit(w) else rho[-1]
    safe_width = np.copysign(max(abs(w), np.finfo(np.float64).tiny), w)
    log_shape = (np.asarray(rho, dtype=np.longdouble) - np.longdouble(reference)) / np.longdouble(
        safe_width
    )
    weights = np.asarray(vpr_a, dtype=np.longdouble) * np.asarray(drho, dtype=np.longdouble)
    return normalize_log_shape(log_shape, weights, total_f)

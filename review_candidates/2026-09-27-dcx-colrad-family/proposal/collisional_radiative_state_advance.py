"""FIDASIM colrad eigenstate advance for one spatial step.

Source: FIDASIM ``colrad`` (the saved package ``碰撞辐射本征态推进``) --
advance the neutral level densities one time step with the source's real
eigen-decomposition order, project the time-integrated densities, and
emit the transition photon rate from the emitting state via the caller's
Einstein coefficient.  Outside the plasma the ballistic rule applies: the
state is unchanged, the integrated density is ``state * dt`` and no
photons are produced.  The real-eigenstate contract (imaginary parts at
most 1e-12) is part of the source semantics.

Registered hardenings against the saved arm: non-finite states, dt,
matrix entries or Einstein rate pass the saved comparisons silently and
propagate NaN, ``exp`` of extreme eigenvalues can overflow to Inf, and
``np.maximum(NaN, 0.0)`` stays NaN; the emitting index accepts bools and
floats; all returned values must be finite and the index must be a strict
in-range integer.
"""
from __future__ import annotations

import numpy as np

__all__ = ["advance_collisional_radiative_states"]


def advance_collisional_radiative_states(states, rate_matrix_s_inv, dt_s, in_plasma, emitting_state_index, einstein_transition_rate_s_inv):
    """Return source-style next states, time-integrated densities, and photons."""
    state = np.asarray(states, dtype=float)
    if not np.isscalar(dt_s) or isinstance(dt_s, (bool, np.bool_)):
        raise ValueError("dt_s must be a real scalar (registered hardening)")
    if state.ndim != 1 or np.any(state < 0.0) or dt_s < 0.0:
        raise ValueError("states must be a nonnegative vector and dt_s must be nonnegative")
    if (not np.all(np.isfinite(state)) or not np.isfinite(dt_s)
            or not isinstance(in_plasma, (bool, np.bool_))
            or not np.isfinite(einstein_transition_rate_s_inv)
            or einstein_transition_rate_s_inv < 0.0):
        raise ValueError("states, dt_s and the Einstein rate must be finite and the plasma gate a bool (registered hardening)")
    if not in_plasma:
        return state.copy(), state * dt_s, 0.0
    matrix = np.asarray(rate_matrix_s_inv, dtype=float)
    if (matrix.shape != (state.size, state.size) or not np.all(np.isfinite(matrix))):
        raise ValueError("rate_matrix_s_inv must be (n_levels, n_levels) with finite entries (registered hardening)")
    eigval, eigvec = np.linalg.eig(matrix)
    if np.max(np.abs(eigval.imag)) > 1.0e-12 or np.max(np.abs(eigvec.imag)) > 1.0e-12:
        raise ValueError("source real-eigenstate contract is not satisfied")
    eigval, eigvec = eigval.real, eigvec.real
    coefficient = np.linalg.solve(eigvec, state)
    exponential = np.exp(eigval * dt_s)
    denominator = np.where(eigval == 0.0, 1.0, eigval)
    next_state = np.maximum(eigvec @ (coefficient * exponential), 0.0)
    integrated_density = np.maximum(eigvec @ (coefficient * (exponential - 1.0) / denominator), 0.0)
    index = emitting_state_index
    if (isinstance(index, (bool, np.bool_)) or not isinstance(index, (int, np.integer))
            or not 0 <= index < state.size):
        raise ValueError("emitting_state_index must be a zero-based in-range integer")
    photons = float(integrated_density[index] * einstein_transition_rate_s_inv)
    # Registered hardening: extreme eigenvalues overflow exp to Inf and NaN
    # survives np.maximum; the saved arm returns them silently.
    if not (np.all(np.isfinite(next_state)) and np.all(np.isfinite(integrated_density))
            and np.isfinite(photons)):
        raise ValueError(
            "colrad outputs are non-finite for finite but extreme input "
            "magnitudes (registered hardening)")
    return next_state, integrated_density, photons

# Derived from TORAX: Copyright 2024 DeepMind Technologies Limited.
# Licensed under Apache-2.0; the retained source license is licenses/torax/LICENSE.
# SciRel D2 changes: stable small-energy evaluation, explicit domain/failure
# handling, NumPy implementation, and bounded mathematical applicability.
"""Fast ion heating partition relation.

The TORAX D1 implementation evaluates Mikkelsen's dimensionless relation
``f_i(x)`` with ``x² = E_birth / (10 m_fast T_e)``.  Its direct expression has
an avoidable 0/0 at zero birth energy although the continuous limit of this mathematical relation is
``f_i(0)=1``.  This SciRel successor makes that boundary explicit and rejects
nonphysical inputs instead of returning NaN/inf.  The D1 source and its exact
failure are retained in the D2 evidence record.
"""
import numpy as np


def fast_ion_fractional_heating(
    birth_energy, T_e, fast_ion_mass
):
    """Return the ion fraction for fast-ion birth energy.

    Parameters are in keV (``birth_energy`` and ``T_e``) and amu
    (``fast_ion_mass``).  Inputs must be finite and strictly positive except
    ``birth_energy``, which may be zero.  Scalar or broadcastable arrays are
    accepted; the result has the broadcast shape and is dimensionless.

    This evaluates the specified local Mikkelsen approximation
    ``f_i = 2/x² integral_0^x t/(1+t³) dt``, with
    ``x² = birth_energy/(10*fast_ion_mass*T_e)``. Numerical verification
    supports this fixed relation, including its mathematical zero-energy
    limit. Applicability to a particular plasma composition or collisional
    regime and experimental calibration are not established here. This
    function does not simulate trajectories or transport evolution.

    Raises ValueError for invalid inputs or incompatible broadcast shapes,
    and FloatingPointError if the computed dimensionless ratio or result
    is nonfinite. Finite dimensional inputs can still overflow that ratio.
    """
    E, Te, mass = np.broadcast_arrays(
        np.asarray(birth_energy, dtype=float),
        np.asarray(T_e, dtype=float),
        np.asarray(fast_ion_mass, dtype=float),
    )
    if not (np.all(np.isfinite(E)) and np.all(np.isfinite(Te)) and np.all(np.isfinite(mass))):
        raise ValueError("birth_energy, T_e, and fast_ion_mass must be finite")
    if np.any(E < 0) or np.any(Te <= 0) or np.any(mass <= 0):
        raise ValueError("birth_energy must be nonnegative; T_e and fast_ion_mass must be positive")
    # Compute ratios in log space to avoid overflow in the dimensional product.
    with np.errstate(divide="ignore", over="ignore", under="ignore"):
        x2 = np.exp(np.log(E) - np.log(10.0) - np.log(mass) - np.log(Te))
    if not np.all(np.isfinite(x2)):
        raise FloatingPointError("dimensionless energy ratio is not finite")
    small = x2 < 0.01
    y = np.where(small, x2, 0.0)**1.5
    out = np.zeros_like(x2)
    for k in range(12):
        out += 2.0 * (-y)**k / (3*k + 2)
    xn = np.sqrt(x2[~small])
    x2n = x2[~small]
    numerator = (1.0 / 6.0) * np.log((1.0 - xn + x2n) / (1.0 + 2.0 * xn + x2n))
    numerator += (np.arctan((2.0 * xn - 1.0) / np.sqrt(3.0)) + np.pi / 6.0) / np.sqrt(3.0)
    out[~small] = 2.0 * numerator / x2n
    if not np.all(np.isfinite(out)):
        raise FloatingPointError("fast-ion heating relation produced a nonfinite result")
    return out.item() if out.ndim == 0 else out

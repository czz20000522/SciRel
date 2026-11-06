"""Fast ion heating partition relation.

The local Mikkelsen approximation uses ``x² = E_birth/(10 m_fast T_e)``.
The zero-energy limit is evaluated explicitly, while positive inputs use a
series near the origin and the closed form elsewhere.
"""

import numpy as np


__all__ = ["fast_ion_fractional_heating"]


def fast_ion_fractional_heating(birth_energy, T_e, fast_ion_mass):
    """Return the ion fraction for fast-ion birth energy.

    Parameters
    ----------
    birth_energy : real scalar or array_like
        Fast-ion birth energy [keV]. Finite and nonnegative.
    T_e : real scalar or array_like
        Electron temperature [keV]. Finite and strictly positive.
    fast_ion_mass : real scalar or array_like
        Fast-ion mass [amu]. Finite and strictly positive, broadcast-compatible
        with the other inputs.

    Returns
    -------
    ion_fraction : float64 scalar or ndarray
        Fraction of fast-ion heating deposited into ions [dimensionless], with
        the broadcast input shape.

    Raises
    ------
    ValueError
        If an input is nonfinite, outside its stated domain, or incompatible
        for broadcasting.
    FloatingPointError
        If the dimensionless ratio or the final fraction is nonfinite.

    See Also
    --------
    calculate_dd_neutron_lab_energy_kev : Evaluate a related fusion kinematics
        relation.

    Notes
    -----
    The local Mikkelsen approximation uses
    ``x**2 = birth_energy / (10 * fast_ion_mass * T_e)`` and

    .. math:: f_i = 2 / x^2 * integral_0^x t / (1 + t^3) dt.

    The zero-energy limit is evaluated explicitly. Positive inputs use a
    twelve-term series near the origin and the closed form elsewhere. The
    result does not establish applicability to a particular plasma composition,
    collisional regime, or experimental calibration, and it does not simulate
    trajectories or transport.

    Examples
    --------
    >>> from scirel.plasma.fast_ion_heating import fast_ion_fractional_heating
    >>> assert fast_ion_fractional_heating(0.0, 10.0, 2.0) == 1.0
    >>> value = fast_ion_fractional_heating(20.0, 4.0, 2.0)
    >>> assert 0.0 < value < 1.0
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
    # Compute the dimensionless ratio in log space to avoid an unnecessary
    # overflow in the dimensional product.
    with np.errstate(divide="ignore", over="ignore", under="ignore"):
        x2 = np.exp(np.log(E) - np.log(10.0) - np.log(mass) - np.log(Te))
    if not np.all(np.isfinite(x2)):
        raise FloatingPointError("dimensionless energy ratio is not finite")
    small = x2 < 0.01
    y = np.zeros_like(x2)
    y[small] = x2[small] ** 1.5
    out = np.zeros_like(x2)
    if np.any(small):
        # The series is only used for small x².  Avoid evaluating all twelve
        # terms for entries that are replaced by the closed form below.
        ys = y[small]
        series = np.zeros_like(ys)
        for k in range(12):
            series += 2.0 * (-ys) ** k / (3 * k + 2)
        out[small] = series
    xn = np.sqrt(x2[~small])
    x2n = x2[~small]
    numerator = (1.0 / 6.0) * np.log((1.0 - xn + x2n) / (1.0 + 2.0 * xn + x2n))
    numerator += (np.arctan((2.0 * xn - 1.0) / np.sqrt(3.0)) + np.pi / 6.0) / np.sqrt(3.0)
    out[~small] = 2.0 * numerator / x2n
    if not np.all(np.isfinite(out)):
        raise FloatingPointError("fast-ion heating relation produced a nonfinite result")
    return out.item() if out.ndim == 0 else out

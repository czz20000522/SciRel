"""Fast ion heating partition relation.

The local Mikkelsen approximation uses ``x² = E_birth/(10 m_fast T_e)``.
The zero-energy limit is evaluated explicitly, while positive inputs use a
series near the origin and the closed form elsewhere.
"""

import numpy as np


__all__ = ["fast_ion_fractional_heating"]


def _preserve_real_values(value, name, active):
    """Expand array protocols once, preserving metadata before combining containers."""
    if np.ma.isMaskedArray(value) or isinstance(value, (complex, np.complexfloating)):
        raise ValueError(f"{name} must contain real, unmasked numeric values")
    if isinstance(value, np.ndarray):
        if np.iscomplexobj(value):
            raise ValueError(f"{name} must contain real, unmasked numeric values")
        if value.dtype != object:
            return value
    elif not hasattr(value, "__array__") and not isinstance(value, (list, tuple)):
        return value

    marker = id(value)
    if marker in active:
        raise ValueError(f"{name} must contain acyclic real, unmasked numeric values")
    active.add(marker)
    try:
        if isinstance(value, np.ndarray):
            result = np.empty(value.shape, dtype=object)
            for index, item in enumerate(value.flat):
                result.flat[index] = _preserve_real_values(item, name, active)
            return result
        if isinstance(value, (list, tuple)):
            # Visible sequence members define the input even for subclasses
            # providing __array__; that conversion could erase member masks.
            return [_preserve_real_values(item, name, active) for item in value]
        # Only opaque inputs reach their array protocol. Unlike asarray,
        # asanyarray retains a returned MaskedArray; reuse the result once.
        return _preserve_real_values(np.asanyarray(value), name, active)
    finally:
        active.remove(marker)


def _real_unmasked_input(value, name):
    """Validate before conversion can discard an imaginary part or a mask."""
    try:
        preserved = _preserve_real_values(value, name, set())
        # Capture buffer/interface dtypes without requesting real conversion.
        # Nested protocol results were already expanded without losing masks.
        raw = _preserve_real_values(np.asanyarray(preserved), name, set())
        return np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain real, unmasked numeric values") from exc


def fast_ion_fractional_heating(birth_energy, T_e, fast_ion_mass):
    """Return the ion fraction for fast-ion birth energy.

    Parameters
    ----------
    birth_energy : real scalar or array_like
        Fast-ion birth energy [keV]. Finite, real, unmasked and nonnegative.
    T_e : real scalar or array_like
        Electron temperature [keV]. Finite, real, unmasked and strictly positive.
    fast_ion_mass : real scalar or array_like
        Fast-ion mass [amu]. Finite, real, unmasked and strictly positive,
        broadcast-compatible with the other inputs.

    Returns
    -------
    ion_fraction : float64 scalar or ndarray
        Fraction of fast-ion heating deposited into ions [dimensionless], with
        the broadcast input shape.

    Raises
    ------
    ValueError
        If an input is complex, masked, not convertible to real numeric values,
        nonfinite, outside its stated domain, or incompatible for broadcasting.
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

    Lists and tuples, including subclasses, use their visible sequence members
    and shape rather than a custom array conversion. Other array-like objects
    use their array representation, preserving masks and complex dtypes until
    validation. A masked or complex value is rejected before conversion to real.

    Examples
    --------
    >>> from scirel.plasma.fast_ion_heating import fast_ion_fractional_heating
    >>> assert fast_ion_fractional_heating(0.0, 10.0, 2.0) == 1.0
    >>> value = fast_ion_fractional_heating(20.0, 4.0, 2.0)
    >>> assert 0.0 < value < 1.0
    """
    E, Te, mass = np.broadcast_arrays(
        _real_unmasked_input(birth_energy, "birth_energy"),
        _real_unmasked_input(T_e, "T_e"),
        _real_unmasked_input(fast_ion_mass, "fast_ion_mass"),
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

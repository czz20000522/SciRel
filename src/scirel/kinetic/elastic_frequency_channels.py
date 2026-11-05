"""Sum three elastic coefficients Omega=nu/Vth [m^-1] in caller order."""

from __future__ import annotations

import numpy as np

__all__ = ["sum_elastic_frequency_channels"]


def _real_array(value, name):
    try:
        raw = np.asarray(value)
        if raw.dtype.kind not in "iuf" or (
            isinstance(value, (list, tuple))
            and any(
                isinstance(item, (bool, np.bool_)) for item in np.asarray(value, dtype=object).flat
            )
        ):
            raise ValueError
        result = np.asarray(raw, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must contain finite real values") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain finite real values")
    return result


def sum_elastic_frequency_channels(frequency_profiles_m_inv):
    r"""Sum exactly three already normalized inverse-length elastic collision coefficients Omega=nu/Vth in caller channel order.

    Parameters
    ----------
    frequency_profiles_m_inv : sequence of real array-like, shape list[3] of equal-shape arrays
        Exactly three elastic coefficient profiles Omega_q=nu_q/Vth, all normalized with the same Vth. [m^-1].
        Constraints: Exactly three non-empty finite arrays of one common shape, in caller order.

    Returns
    -------
    elastic_frequency_m_inv : float64 array, shape common shape
        Summed inverse-length elastic coefficient for spatial transport. [m^-1].
        Constraints: Finite; equals the pointwise sum in the declared order.

    Raises
    ------
    ValueError
        Raises ValueError when the channel count is not three, any channel is empty, shapes differ, or any value is non-real or non-finite; implicit boolean, string and complex conversion is rejected. Raises ValueError when the evaluation produces a non-finite result where the contract demands finiteness; no fallback is selected. Not applicable. Never returned; a rejected call produces no result.

    See Also
    --------
    scirel.kinetic.assemble_neutral_total_collision_frequency : Related neutral-transport operation.

    Notes
    -----
        The three channels are added left to right in caller order (float summation order preserved); exactly three channels are admitted
    exactly three non-empty finite equal-shape profiles

    Examples
    --------
    >>> import numpy as np
    >>> from scirel.kinetic import sum_elastic_frequency_channels
    >>> result = sum_elastic_frequency_channels([np.array([1.0, 2.0]), np.array([0.5, 1.0]), np.array([0.25, 0.5])])
    >>> np.testing.assert_array_equal(result['elastic_frequency_m_inv'], [1.75, 3.5])
    >>> try:
    ...     sum_elastic_frequency_channels([np.ones(3), np.ones(3)])
    ... except ValueError as error:
    ...     assert 'exactly three' in str(error)
    ... else:
    ...     raise AssertionError('a two-channel call must be rejected')
    """
    if (
        not isinstance(frequency_profiles_m_inv, (list, tuple))
        or len(frequency_profiles_m_inv) != 3
    ):
        raise ValueError("frequency_profiles_m_inv must contain exactly three channels")
    arrays = [
        _real_array(profile, "frequency_profiles_m_inv") for profile in frequency_profiles_m_inv
    ]
    if any(array.ndim == 0 or array.size == 0 for array in arrays):
        raise ValueError("frequency channels must be non-empty arrays")
    shape = arrays[0].shape
    if any(array.shape != shape for array in arrays):
        raise ValueError("frequency channels must have identical shapes")
    with np.errstate(over="ignore"):
        # Parenthesize the three-channel reduction so its accumulation order
        # is deterministic across NumPy backends.
        total = (arrays[0] + arrays[1]) + arrays[2]
    if not np.all(np.isfinite(total)):
        raise ValueError("the summed elastic frequency is not finite")
    return {"elastic_frequency_m_inv": total}

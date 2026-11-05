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
    """Return ``{'elastic_frequency_m_inv': total}`` in caller channel order."""
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
